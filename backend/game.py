import time
from threading import Timer as ThreadingTimer
from typing import Dict, Any, Callable

from backend.constants import CLASSIC_MODE, BATTLE_ROYALE_MODE


def next_question(*, current_game: Dict[str, Any], socketio, namespace: str, config, get_random_questions: Callable, calculate_points: Callable, bot_action: Callable):
    if not current_game or current_game.get('game_state') != 'in_progress':
        print("next_question: No active game or game not in progress.")
        return

    # --- Clear bot state from PREVIOUS question ---
    if 'bot_answer_timers' in current_game:
        for _, timer_obj_old in current_game['bot_answer_timers'].items():
            if timer_obj_old.is_alive():
                timer_obj_old.cancel()
    current_game['bot_answer_timers'] = {}
    current_game['bot_data_for_round'] = {}
    # --- END Clear bot state ---

    # --- Battle Royale: Win condition check (BEFORE new question) ---
    if current_game['mode'] == BATTLE_ROYALE_MODE:
        print(f"BR Next Q Check: Active players = {len(current_game['active_player_sids'])}, SIDs: {current_game['active_player_sids']}")
        if len(current_game['active_player_sids']) <= 1:
            print("Battle Royale win condition met (<=1 active player). Ending game from next_question.")
            return _end_game_internal(current_game=current_game, socketio=socketio, namespace=namespace)

    # --- Reset round-specific states for active players ---
    sids_to_reset_for_round = current_game['active_player_sids'] if current_game['mode'] == BATTLE_ROYALE_MODE else current_game['players'].keys()
    for player_sid in sids_to_reset_for_round:
        if player_sid in current_game['players']:
            current_game['players'][player_sid]['answered_this_round'] = False
            current_game['players'][player_sid]['current_answer_correct'] = None

    current_game['current_question_index'] += 1

    # --- Difficulty Logic Determination ---
    target_difficulty_for_this_round = current_game['adaptive_difficulty']

    if current_game['mode'] == BATTLE_ROYALE_MODE:
        current_game['questions_at_current_difficulty_streak'] += 1
        if current_game['questions_at_current_difficulty_streak'] >= config.BR_DIFFICULTY_STEP_QUESTIONS:
            target_difficulty_for_this_round = min(10, current_game['adaptive_difficulty'] + 1)
            current_game['questions_at_current_difficulty_streak'] = 0
            print(f"BR Difficulty Increased! New target level: {target_difficulty_for_this_round}")
        current_game['adaptive_difficulty'] = target_difficulty_for_this_round

    elif current_game['mode'] == CLASSIC_MODE:
        if current_game['current_question_index'] > 0:
            correct_human_answers, total_human_answers_this_round = 0, 0
            for sid in current_game['human_player_sids']:
                player = current_game['players'].get(sid)
                if player and player.get('answered_last_round_correctly') is not None:
                    total_human_answers_this_round += 1
                    if player.get('answered_last_round_correctly'):
                        correct_human_answers += 1
            if total_human_answers_this_round > 0:
                accuracy = correct_human_answers / total_human_answers_this_round
                new_classic_difficulty = current_game['adaptive_difficulty']
                if accuracy > 0.65:
                    new_classic_difficulty = min(10, current_game['adaptive_difficulty'] + 1)
                elif accuracy < 0.35:
                    new_classic_difficulty = max(1, current_game['adaptive_difficulty'] - 1)
                if new_classic_difficulty != current_game['adaptive_difficulty']:
                    print(f"Classic Adaptive difficulty changed to: {new_classic_difficulty} (Prev: {current_game['adaptive_difficulty']}, Acc: {accuracy:.2f})")
                    current_game['adaptive_difficulty'] = new_classic_difficulty
            target_difficulty_for_this_round = current_game['adaptive_difficulty']
        else:
            target_difficulty_for_this_round = 1

    # --- Handle running out of questions ---
    if current_game['current_question_index'] >= len(current_game['questions']):
        if current_game['mode'] == BATTLE_ROYALE_MODE:
            print(f"BR Game {current_game['game_id']}: Ran out of questions. Replenishing at current difficulty {target_difficulty_for_this_round}...")
            new_questions_batch = get_random_questions(config.QUESTIONS_PER_GAME, diff=target_difficulty_for_this_round)
            if not new_questions_batch:
                print("CRITICAL ERROR: Could not fetch new questions for BR. Ending game.")
                return _end_game_internal(current_game=current_game, socketio=socketio, namespace=namespace)
            current_game['questions'].extend(new_questions_batch)
            print(f"Replenished {len(new_questions_batch)} questions. Total now: {len(current_game['questions'])}")
        else:
            print("Classic Mode: All questions asked. Ending game.")
            return _end_game_internal(current_game=current_game, socketio=socketio, namespace=namespace)

    # --- Fetch Question ---
    print(f"Fetching question for game mode {current_game['mode']} at target difficulty {target_difficulty_for_this_round}")
    q_list = get_random_questions(1, diff=target_difficulty_for_this_round)
    if not q_list:
        print(f"Warning: No question found at target difficulty {target_difficulty_for_this_round}. Fetching any question.")
        q_list = get_random_questions(1)
        if not q_list:
            print("CRITICAL: No questions available at all. Ending game.")
            return _end_game_internal(current_game=current_game, socketio=socketio, namespace=namespace)

    current_q_data = q_list[0]
    current_game['questions'][current_game['current_question_index']] = current_q_data

    # --- Prepare and Emit Question Payload ---
    question_payload = {
        'question': current_q_data['question'],
        'options': current_q_data['options'],
        'question_number': current_game['current_question_index'] + 1,
        'total_questions': "Ongoing" if current_game['mode'] == BATTLE_ROYALE_MODE else len(current_game['questions']),
        'duration': config.QUESTION_DURATION,
        'difficulty': current_q_data.get('difficulty', 'N/A'),
        'target_difficulty_level': target_difficulty_for_this_round,
        'active_player_count': len(current_game['active_player_sids']) if current_game['mode'] == BATTLE_ROYALE_MODE else None,
        'initial_player_count': current_game.get('initial_player_count') if current_game['mode'] == BATTLE_ROYALE_MODE else None,
    }
    socketio.emit('new_question', question_payload, room=current_game['room_name'], namespace=namespace)
    current_game['question_start_time'] = time.time()

    # --- Bot Actions for the NEW question ---
    for sid, player_data in current_game['players'].items():
        if player_data['is_bot'] and (current_game['mode'] == CLASSIC_MODE or sid in current_game['active_player_sids']):
            bot_action(sid, current_q_data)

    # --- Start Question Timer ---
    if current_game.get('question_timer'):
        current_game['question_timer'].cancel()
    # reveal_callback must be provided by the caller using a closure over the same current_game
    # The caller should set current_game['question_timer'] to this timer


def reveal_answers_and_scores(*, current_game: Dict[str, Any], socketio, namespace: str, app, config, calculate_points: Callable, get_llm_advice: Callable):
    if not current_game or current_game.get('game_state') != 'in_progress':
        print("reveal_answers_and_scores: No active/valid game to process.")
        return

    # This function is often called by a timer, so SocketIO calls need app_context
    with app.app_context():
        # Cancel the main question timer if it's still running
        if current_game.get('question_timer') and current_game['question_timer'].is_alive():
            current_game['question_timer'].cancel()
            current_game['question_timer'] = None

        # --- Force pending bots to answer and cancel their async timers ---
        if 'bot_answer_timers' in current_game:
            for bot_sid, timer_obj in list(current_game['bot_answer_timers'].items()):
                # Cancel any pending timer so it doesn't fire after reveal
                if timer_obj.is_alive():
                    timer_obj.cancel()
                # If a bot hasn't answered, force decision using stored params via stored function
                if bot_sid in current_game['players'] and not current_game['players'][bot_sid].get('answered_this_round'):
                    if 'bot_data_for_round' in current_game and bot_sid in current_game['bot_data_for_round']:
                        stored_record = current_game['bot_data_for_round'][bot_sid]
                        fn = stored_record.get('timer_function_ref')
                        params = stored_record.get('force_params')
                        if callable(fn):
                            try:
                                fn(was_forced=True, forced_params_from_reveal=params)
                            except Exception as e:
                                print(f"Error forcing bot {bot_sid} answer: {e}")
            current_game['bot_answer_timers'].clear()

        # --- Compute results and update scores ---
        q_idx = current_game['current_question_index']
        q_data = current_game['questions'][q_idx]

        is_br = current_game['mode'] == BATTLE_ROYALE_MODE
        human_sids = list(current_game['human_player_sids'])

        # Aggregate results for emit
        player_result_snapshot = {}

        for sid, pdata in list(current_game['players'].items()):
            is_active_for_round = (sid in current_game['active_player_sids']) if is_br else True
            if not is_active_for_round:
                continue

            answered = pdata.get('answered_this_round', False)
            correct = pdata.get('current_answer_correct', False)
            potential_pts = int(pdata.get('potential_points_this_round', 0) or 0)

            # Update helps for next round
            pdata.setdefault('helps', {'fifty_fifty': True, 'call_friend': True, 'double_score': True})

            if pdata.get('is_bot'):
                # For bots, we already computed correctness/potential points. Add to score if correct.
                if correct:
                    pdata['score'] = pdata.get('score', 0) + potential_pts
            else:
                # Humans: score if correct
                if correct:
                    pdata['score'] = pdata.get('score', 0) + potential_pts

            # Track last round correctness for adaptive difficulty
            pdata['answered_last_round_correctly'] = True if correct else False

            player_result_snapshot[sid] = {
                'score': pdata.get('score', 0),
                'answered_this_round': answered,
                'is_eliminated': pdata.get('is_eliminated', False),
                'place': pdata.get('place', 0),
                'helps': pdata.get('helps', {}),
            }

        # Battle Royale elimination logic (simple: wrong answers eliminate)
        if is_br:
            still_active = []
            for sid in list(current_game['active_player_sids']):
                pdata = current_game['players'].get(sid)
                if not pdata:
                    continue
                if not pdata.get('answered_this_round') or not pdata.get('current_answer_correct'):
                    # Eliminate
                    pdata['is_eliminated'] = True
                else:
                    still_active.append(sid)
            current_game['active_player_sids'] = still_active

        # Emit results
        payload = {
            'mode': current_game['mode'],
            'question_number': q_idx + 1,
            'correct_answer': q_data['correct_answer'],
            'player_data': player_result_snapshot,
            'active_player_count': len(current_game.get('active_player_sids', [])) if is_br else None,
        }
        socketio.emit('question_result', payload, room=current_game['room_name'], namespace=namespace)

        # Battle Royale: check win condition
        if is_br:
            active_count = len(current_game.get('active_player_sids', []))
            if active_count <= 1:
                print(f"Battle Royale win condition met (Active players: {active_count}). Ending game.")
                socketio.sleep(3)
                return _end_game_internal(current_game=current_game, socketio=socketio, namespace=namespace)

        socketio.sleep(5)  # Pause to show results before next question
        # Next question will be triggered by the caller wrapper to ensure timer wiring remains in app.py


def end_game(*, current_game: Dict[str, Any], socketio, namespace: str, lobby_manager):
    return _end_game_internal(current_game=current_game, socketio=socketio, namespace=namespace, lobby_manager=lobby_manager)


def _end_game_internal(*, current_game: Dict[str, Any], socketio, namespace: str, lobby_manager=None):
    if not current_game:
        return
    print(f"Game {current_game['game_id']} ended.")
    game_room = current_game['room_name']
    lead = sorted([
        {'username': p['username'], 'score': p['score'], 'is_bot': p['is_bot']}
        for p in current_game['players'].values()
    ], key=lambda x: x['score'], reverse=True)
    socketio.emit('game_over', {'leaderboard': lead}, room=game_room, namespace=namespace)
    # Cancel timer if present
    if current_game.get('question_timer'):
        current_game['question_timer'].cancel()
    # Reset
    current_game.clear()
    if lobby_manager:
        lobby_manager.stop(emit_update=True)
    print("Game ended. Lobby dormant.")

