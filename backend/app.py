import os
import time
import random
import uuid
from threading import RLock, Timer as ThreadingTimer

from flask import Flask, request  # request will be None in timer threads
from flask_socketio import SocketIO, emit, join_room, leave_room

# Import refactored modules
from backend import config
from backend.constants import CLASSIC_MODE, BATTLE_ROYALE_MODE
from backend.questions import get_random_questions
from backend.llm import get_gemini_model, get_llm_advice

# Flask/SocketIO initialization using config
app = Flask(__name__)
app.config['SECRET_KEY'] = config.SECRET_KEY
socketio = SocketIO(app, cors_allowed_origins=config.CORS_ALLOWED_ORIGINS, async_mode=config.ASYNC_MODE)

# Local aliases to config values (to minimize code churn)
LOBBY_WAIT_TIME = config.LOBBY_WAIT_TIME
QUESTIONS_PER_GAME = config.QUESTIONS_PER_GAME
QUESTION_DURATION = config.QUESTION_DURATION
POINTS_BASE = config.POINTS_BASE
MIN_BOTS = config.MIN_BOTS
MAX_BOTS = config.MAX_BOTS
# Bot difficulty alias
DEFAULT_BOT_DIFFICULTY = config.DEFAULT_BOT_DIFFICULTY


# Load bot names from configurable file
BOT_NAMES_FILE = config.BOT_NAMES_FILE
bot_names_list = []
try:
    with open(BOT_NAMES_FILE, 'r') as f:
        bot_names_list = [n.strip() for n in f if n.strip()]
    if not bot_names_list:
        raise FileNotFoundError
except FileNotFoundError:
    bot_names_list = ["BotAlpha", "BotBeta", "BotGamma"]

# --- SINGLE GAME STATE MANAGEMENT ---
current_game = None  # Will hold game data: { ..., 'mode': CLASSIC_MODE | BATTLE_ROYALE_MODE, ... }
lobby_players = {}  # { sid: {'username': string, 'desired_mode': string} }
lobby_lock = RLock()

# Lobby managed via LobbyManager
# Helper: ensure game creation happens within Flask app context when called from background threads

def _create_game_from_lobby_with_context(mode):
    with app.app_context():
        create_game_from_lobby(mode)

from backend.lobby import LobbyManager
lobby_manager = LobbyManager(
    socketio=socketio,
    namespace=config.DEFAULT_NAMESPACE,
    wait_time=LOBBY_WAIT_TIME,
    lock=lobby_lock,
    get_players_for_mode=lambda mode: {sid: p for sid, p in lobby_players.items() if p.get('desired_mode') == mode},
    is_game_active=lambda: current_game is not None,
    on_countdown_finished=lambda mode: _create_game_from_lobby_with_context(mode),
)

DEFAULT_NAMESPACE = config.DEFAULT_NAMESPACE  # Define for clarity

from backend.game import next_question as gm_next_question, reveal_answers_and_scores as gm_reveal_answers_and_scores, end_game as gm_end_game

def calculate_points(t):
    return int(POINTS_BASE * max(0.1, (QUESTION_DURATION - t) / QUESTION_DURATION))

def _stop_lobby_countdown_sequence(emit_update=False): # Renamed emit_update for clarity
    global lobby_countdown_timer_obj, lobby_countdown_active, lobby_current_time_remaining, lobby_mode_in_countdown

    if lobby_countdown_timer_obj and lobby_countdown_timer_obj.is_alive():
        lobby_countdown_timer_obj.cancel(); lobby_countdown_timer_obj = None

    was_active = lobby_countdown_active
    stopped_mode_for_emit = lobby_mode_in_countdown # Capture before reset

    lobby_countdown_active = False
    lobby_mode_in_countdown = None # Reset
    lobby_current_time_remaining = LOBBY_WAIT_TIME

    if was_active and emit_update and stopped_mode_for_emit: # Ensure there was a mode to report as stopped
        print(f"{stopped_mode_for_emit.capitalize()} lobby countdown stopped and reset.")
        # Players still in lobby_players waiting for this mode (if any, e.g., if stopped early by admin)
        remaining_players_for_stopped_mode = [p for p in lobby_players.values() if p.get('desired_mode') == stopped_mode_for_emit]

        context_needed = not request and hasattr(app, 'app_context')
        if context_needed:
            with app.app_context():
                socketio.emit('lobby_countdown_update', {
                    'mode': stopped_mode_for_emit, # Send the mode that was stopped
                    'time_remaining': lobby_current_time_remaining,
                    'players': remaining_players_for_stopped_mode,
                    'is_active': False
                    }, namespace=DEFAULT_NAMESPACE)
        elif hasattr(socketio, 'emit'):
             socketio.emit('lobby_countdown_update', {
                'mode': stopped_mode_for_emit, # Send the mode
                'time_remaining': lobby_current_time_remaining,
                'players': remaining_players_for_stopped_mode,
                'is_active': False
                }, namespace=DEFAULT_NAMESPACE)

    if was_active:  # Only trigger if a countdown was actually running and now stopped
        lobby_manager.trigger_next_waiting_lobby_if_any([CLASSIC_MODE, BATTLE_ROYALE_MODE])

def create_game_from_lobby(mode_being_created): # Takes mode as argument now
    global lobby_players, current_game

    game_id = f"{mode_being_created}_{uuid.uuid4()}"
    game_players_data = {}
    human_sids_in_game = []
    game_effective_bot_difficulty = DEFAULT_BOT_DIFFICULTY # Default for the game

    with lobby_lock:
        if current_game is not None:
            print(f"Create_game ({mode_being_created}): Game already active ({current_game['game_id']}). Aborting creation.");
            return

        players_to_move = {sid: p_data for sid, p_data in lobby_players.items() if p_data.get('desired_mode') == mode_being_created}
        if not players_to_move:
            print(f"Create_game ({mode_being_created}): No players found for this mode in lobby. Aborting creation.");
            return

        # Determine game's bot difficulty from the first human player initiating this game
        first_human_processed_for_difficulty = False
        for sid, p_data in players_to_move.items():
            if not p_data.get('is_bot', False): # Check if it's a human's preference
                game_effective_bot_difficulty = p_data.get('bot_difficulty_pref', DEFAULT_BOT_DIFFICULTY)
                print(f"Game bot difficulty set to '{game_effective_bot_difficulty}' based on player {p_data['username']}.")
                first_human_processed_for_difficulty = True
                break
        if not first_human_processed_for_difficulty and players_to_move: # Fallback if somehow no human preference was found among movers
             print("Warning: No human player found to set game bot difficulty from players_to_move, using default.")


        # Remove moved players from the global lobby_players list
        for sid in players_to_move.keys():
            if sid in lobby_players:
                del lobby_players[sid]

        print(f"Starting {mode_being_created} game {game_id}. Moving {len(players_to_move)} players.")
        for sid, player_info in players_to_move.items():
            game_players_data[sid] = {
                'username': player_info['username'], 'score': 0, 'is_bot': False,
                'helps': {'fifty_fifty': True, 'call_friend': True, 'double_score': True},
                'sid': sid, 'is_eliminated': False, 'place': 0
            }
            join_room(game_id, sid=sid, namespace=DEFAULT_NAMESPACE)
            human_sids_in_game.append(sid)

    if not human_sids_in_game:
        print(f"Error: No human players were actually processed for game {game_id}. Aborting.")
        current_game = None
        return

    num_bots_to_add_final = 0
    print(f"DEBUG: Bot addition logic for mode: {mode_being_created}, humans: {len(human_sids_in_game)}")

    if mode_being_created == CLASSIC_MODE:
        if len(human_sids_in_game) == 1:
            num_bots_to_add_final = random.randint(MIN_BOTS, MAX_BOTS)
            print(f"Classic (1 human): Adding random {num_bots_to_add_final} bots.")
        # else: 0 bots for classic if >1 human or 0 humans (though 0 humans is handled earlier)

    elif mode_being_created == BATTLE_ROYALE_MODE:
        MIN_TOTAL_ENTITIES_FOR_BR = config.BR_MIN_TOTAL_ENTITIES

        if len(human_sids_in_game) == 0:  # Should have been caught earlier, but defensive
            num_bots_to_add_final = 0  # Cannot start BR with 0 humans typically
            print("BR: No humans, no bots added.")
        elif len(human_sids_in_game) < MIN_TOTAL_ENTITIES_FOR_BR:
            potential_random_bots = random.randint(MIN_BOTS, MAX_BOTS)
            needed_to_reach_min_total = MIN_TOTAL_ENTITIES_FOR_BR - len(human_sids_in_game)
            if potential_random_bots < needed_to_reach_min_total:
                num_bots_to_add_final = min(needed_to_reach_min_total, MAX_BOTS)
                print(f"BR ({len(human_sids_in_game)} humans): Random bots ({potential_random_bots}) too few. Adding {num_bots_to_add_final} to meet min total {MIN_TOTAL_ENTITIES_FOR_BR}.")
            else:
                num_bots_to_add_final = min(potential_random_bots, MAX_BOTS)
                print(f"BR ({len(human_sids_in_game)} humans): Adding random {num_bots_to_add_final} bots (capped by MAX_BOTS if needed).")
        else:
            num_bots_to_add_final = 0
            print(f"BR ({len(human_sids_in_game)} humans): Sufficient players, no bots added.")

    # The rest of your bot instantiation code remains the same:
    if num_bots_to_add_final > 0:
        actual_bots_added_count = 0
        # ... (bot name selection and adding to game_players_data) ...
        if not bot_names_list:
            available_bot_names = [f"GenericBot_{i+1}" for i in range(num_bots_to_add_final)]
        else:
            available_bot_names = random.sample(bot_names_list, k=min(len(bot_names_list), num_bots_to_add_final))

        for i in range(num_bots_to_add_final):
            bot_sid = f"bot_{uuid.uuid4()}"
            bot_name = available_bot_names[i] if i < len(available_bot_names) else f"FallbackBot{i+1}_{random.randint(100,999)}"
            game_players_data[bot_sid] = {
                'username': bot_name, 'score': 0, 'is_bot': True,
                'helps': {'fifty_fifty':True,'call_friend':True,'double_score':True},
                'sid': bot_sid, 'is_eliminated': False, 'place': 0
            }
            actual_bots_added_count +=1
        if actual_bots_added_count > 0:
             print(f"Successfully added {actual_bots_added_count} bots to {mode_being_created} game {game_id}.")
    initial_active_sids = list(human_sids_in_game)
    initial_active_sids.extend([sid for sid, p_data in game_players_data.items() if p_data['is_bot']])

    initial_game_difficulty = 5 # Default for classic
    if mode_being_created == BATTLE_ROYALE_MODE:
        initial_game_difficulty = 1  # BR starts at difficulty 1
        print(f"Battle Royale game {game_id} starting at difficulty {initial_game_difficulty}.")

    current_game = {
        'game_id': game_id,
        'mode': mode_being_created,
        'players': game_players_data,
        'questions': get_random_questions(
            QUESTIONS_PER_GAME if mode_being_created == CLASSIC_MODE else config.BR_INITIAL_QUESTIONS_BATCH,  # Initial batch size
            diff=initial_game_difficulty  # Use the determined initial difficulty
        ),
        'current_question_index': -1,
        'game_state': 'in_progress',
        'adaptive_difficulty': initial_game_difficulty, # Store the game's current difficulty level
        'human_player_sids': human_sids_in_game,
        'active_player_sids': initial_active_sids,
        'room_name': game_id,
        'initial_player_count': len(initial_active_sids),
        'bot_difficulty': game_effective_bot_difficulty,
        # For BR difficulty progression
        'questions_at_current_difficulty_streak': 0 if mode_being_created == BATTLE_ROYALE_MODE else -1 # -1 for classic (no streak)
    }

    print(f"Game {current_game['game_id']} ({current_game['mode']}) created with bot difficulty '{current_game['bot_difficulty']}'. Initial Active: {len(initial_active_sids)}")
    game_start_payload = {
        'game_id': current_game['game_id'], 'mode': current_game['mode'],
        'players': list(current_game['players'].values()),
        'initial_player_count': current_game.get('initial_player_count')
    }
    # Emit to the game room (preferred)
    socketio.emit('game_starting', game_start_payload, room=current_game['room_name'], namespace=DEFAULT_NAMESPACE)
    # Fallback: also emit directly to each human sid to ensure delivery even if room join was missed
    for sid in human_sids_in_game:
        socketio.emit('game_starting', game_start_payload, room=sid, namespace=DEFAULT_NAMESPACE)
    socketio.sleep(2)
    # Delegate to game manager function wrapper
    gm_next_question(
        current_game=current_game,
        socketio=socketio,
        namespace=DEFAULT_NAMESPACE,
        config=config,
        get_random_questions=get_random_questions,
        calculate_points=calculate_points,
        bot_action=bot_action,
    )
    # Wire the question timer now using the same closure over current_game
    if current_game and current_game.get('game_state') == 'in_progress':
        if current_game.get('question_timer'):
            current_game['question_timer'].cancel()
        current_game['question_timer'] = ThreadingTimer(QUESTION_DURATION, lambda: gm_reveal_answers_and_scores(
            current_game=current_game,
            socketio=socketio,
            namespace=DEFAULT_NAMESPACE,
            app=app,
            config=config,
            calculate_points=calculate_points,
            get_llm_advice=get_llm_advice,
        ))
        current_game['question_timer'].start()

# next_question delegated to backend.game.gm_next_question wrapper during game creation

def reveal_answers_and_scores():
    global current_game
    gm_reveal_answers_and_scores(
        current_game=current_game,
        socketio=socketio,
        namespace=DEFAULT_NAMESPACE,
        app=app,
        config=config,
        calculate_points=calculate_points,
        get_llm_advice=get_llm_advice,
    )
    # After reveal, brief pause to let clients render results and reset local round state
    if current_game and current_game.get('game_state') == 'in_progress':
        socketio.sleep(2)
        gm_next_question(
            current_game=current_game,
            socketio=socketio,
            namespace=DEFAULT_NAMESPACE,
            config=config,
            get_random_questions=get_random_questions,
            calculate_points=calculate_points,
            bot_action=bot_action,
        )
        # Re-arm the question timer for the next reveal
        if current_game and current_game.get('game_state') == 'in_progress':
            if current_game.get('question_timer'):
                current_game['question_timer'].cancel()
            current_game['question_timer'] = ThreadingTimer(QUESTION_DURATION, reveal_answers_and_scores)
            current_game['question_timer'].start()
    return

# This is the timer function that will call bot_thinks_and_answers
from backend.bots import schedule_bot_answer

def bot_action(bot_sid, question_data):
    global current_game
    if not current_game or bot_sid not in current_game['players']:
        return
    bot_player_initial_data = current_game['players'][bot_sid]
    if bot_player_initial_data.get('is_eliminated'):
        return
    schedule_bot_answer(current_game, bot_sid, question_data, calculate_points)
def end_game():
    global current_game
    gm_end_game(current_game=current_game, socketio=socketio, namespace=DEFAULT_NAMESPACE, lobby_manager=lobby_manager)
    current_game = None

@socketio.on('connect')
def handle_connect():
    sid = request.sid; print(f"Client connected: {sid}")
    with lobby_lock:
        is_active = lobby_manager.countdown_active and current_game is None
        time_if_active = lobby_manager.time_remaining if is_active else LOBBY_WAIT_TIME
        players_if_active = list(lobby_players.values()) if is_active else []
        mode_if_active = lobby_manager.mode_in_countdown if is_active else None
        emit('connection_ack', {
            'sid': sid,
            'message': 'Connected!',
            'lobby_status': {
                'mode': mode_if_active,
                'time_remaining': time_if_active,
                'players': players_if_active,
                'is_active': is_active
            }
        })

@socketio.on('disconnect')
def handle_disconnect():
    global current_game
    sid = request.sid; print(f"Client disconnected: {sid}")
    p_name_left = "Unknown"
    if current_game and sid in current_game['players']:
        p_d = current_game['players'][sid]; p_name_left = p_d['username']
        print(f"Player {p_name_left}({sid}) disconnected from game {current_game['game_id']}.")
        if not p_d['is_bot']:
            current_game['human_player_sids'].remove(sid)
            socketio.emit('player_left',{'sid':sid,'username':p_name_left,'players':[p for ps,p in current_game['players'].items() if ps!=sid]}, room=current_game['room_name'], namespace=DEFAULT_NAMESPACE) # ADDED NAMESPACE
        del current_game['players'][sid]
        if not p_d['is_bot'] and not current_game['human_player_sids'] and current_game['game_state']=='in_progress':
            if current_game.get('question_timer'): current_game['question_timer'].cancel()
            end_game()
        return
    with lobby_lock:
        if sid in lobby_players:
            p_name_left = lobby_players[sid]['username']; del lobby_players[sid]
            print(f"Player {p_name_left}({sid}) removed from lobby.")
            if not lobby_players and lobby_manager.countdown_active:
                lobby_manager.stop(emit_update=True)
            elif lobby_manager.countdown_active:
                # Re-emit current state for this lobby
                mode = lobby_manager.mode_in_countdown
                players_for_mode = [p for p in lobby_players.values() if p.get('desired_mode') == mode]
                socketio.emit('lobby_countdown_update', {
                    'mode': mode,
                    'time_remaining': lobby_manager.time_remaining,
                    'players': players_for_mode,
                    'is_active': True
                }, namespace=DEFAULT_NAMESPACE)
        # else: print(f"SID {sid} not in game or lobby.") # Already covered by specific logs

@socketio.on('join_lobby_request')
def on_join_lobby_request(data):
    global current_game, lobby_players
    sid = request.sid
    username = data.get('username', f'Player_{sid[:4]}').strip()
    desired_mode = data.get('mode', CLASSIC_MODE)

    # --- Get bot_difficulty from client ---
    player_bot_difficulty_pref = data.get('bot_difficulty', DEFAULT_BOT_DIFFICULTY).lower()
    if player_bot_difficulty_pref not in config.BOT_DIFFICULTY_SETTINGS:
        player_bot_difficulty_pref = DEFAULT_BOT_DIFFICULTY

    if desired_mode not in [CLASSIC_MODE, BATTLE_ROYALE_MODE]:
        emit('error_message', {'message': 'Invalid game mode.'})
        return
    if not username:
        emit('error_message', {'message': 'Username cannot be empty.'})
        return

    if current_game:
        if sid in current_game['players'] and current_game['mode'] == desired_mode:
            print(f"Player {username} rejoining active {desired_mode} game {current_game['game_id']}.")
            join_room(current_game['room_name'], sid=sid, namespace=DEFAULT_NAMESPACE)
            # Send comprehensive game state for rejoin
            emit('game_starting', {
                'game_id': current_game['game_id'],
                'mode': current_game['mode'],
                'players': list(current_game['players'].values()),
                'initial_player_count': current_game.get('initial_player_count'),
                'current_question_data': current_game['questions'][current_game['current_question_index']] if current_game.get('current_question_index', -1) >=0 else None,
                'question_number': current_game.get('current_question_index', -1) + 1,
                'is_rejoin': True,
                'active_player_sids': current_game.get('active_player_sids', [])
            }, room=sid) # Only to this player
            return
        else:
            emit('error_message', {'message': f"A {current_game['mode']} game is in progress. Please wait."})
            return

    with lobby_lock:
        if sid in lobby_players: # Player is already in the system
            old_player_data = lobby_players[sid]
            lobby_players[sid]['username'] = username # Update username
            lobby_players[sid]['bot_difficulty_pref'] = player_bot_difficulty_pref # Update bot difficulty preference

            if old_player_data.get('desired_mode') != desired_mode:
                # Player is switching their desired mode
                print(f"Player {username} switching desired mode from {old_player_data.get('desired_mode')} to {desired_mode}")
                lobby_players[sid]['desired_mode'] = desired_mode

                if lobby_countdown_active and lobby_mode_in_countdown == old_player_data.get('desired_mode'):
                    # They were in the active countdown lobby and want to switch out
                    players_still_in_old_mode_countdown = [p for p in lobby_players.values() if p.get('desired_mode') == old_player_data.get('desired_mode')]
                    if not players_still_in_old_mode_countdown:
                        print(f"Last player left {old_player_data.get('desired_mode')} countdown due to mode switch. Stopping.")
                        _stop_lobby_countdown_sequence(emit_update_if_stopped_early=True) # This will try to trigger next
                    else:
                        socketio.emit('lobby_countdown_update', {
                            'mode': old_player_data.get('desired_mode'),
                            'time_remaining': lobby_current_time_remaining,
                            'players': players_still_in_old_mode_countdown,
                            'is_active': True
                        }, namespace=DEFAULT_NAMESPACE)
                # Try to see if their NEW desired mode can start a lobby or if they should just wait
                # This will be handled by the logic block below.
            # else: Player just updated username or re-clicked join for same mode.

        else: # New player to the system
            lobby_players[sid] = {
                'sid': sid,
                'username': username,
                'desired_mode': desired_mode,
                'bot_difficulty_pref': player_bot_difficulty_pref # Store preference
            }
            print(f"Player {username}({sid}) added to lobby_players for mode: {desired_mode}, bot diff pref: {player_bot_difficulty_pref}.")

        # Logic for starting/joining/waiting for a lobby for THEIR desired_mode
        # This section determines if a new countdown starts, or if player joins existing, or waits.
        if not lobby_manager.countdown_active and current_game is None:
            print(f"No active countdown. Player {username} wants {desired_mode}. Setting this as active lobby mode.")
            lobby_manager.start(desired_mode)
        elif lobby_manager.countdown_active and lobby_manager.mode_in_countdown == desired_mode:
            players_for_this_countdown = [p for p in lobby_players.values() if p.get('desired_mode') == desired_mode]
            print(f"Player {username} joining active {desired_mode} countdown.")
            # Broadcast to update player list for everyone in that lobby
            socketio.emit('lobby_countdown_update', {
                'mode': desired_mode,
                'time_remaining': lobby_manager.time_remaining,
                'players': players_for_this_countdown,
                'is_active': True
            }, namespace=DEFAULT_NAMESPACE)
        elif lobby_manager.countdown_active and lobby_manager.mode_in_countdown != desired_mode:
            players_waiting_for_their_mode = [p for p in lobby_players.values() if p.get('desired_mode') == desired_mode]
            print(f"Player {username} wants {desired_mode}, but {lobby_manager.mode_in_countdown} is active. Player will wait.")
            emit('lobby_countdown_update', {
                'mode': desired_mode,
                'time_remaining': LOBBY_WAIT_TIME,
                'players': players_waiting_for_their_mode,
                'is_active': False # Their desired lobby is not the one counting down
            }, room=sid) # Inform only this player about their specific waiting queue
            emit('error_message', {'message': f"A {lobby_manager.mode_in_countdown} lobby is active. You've been added to the queue for {desired_mode}."})
        elif not lobby_manager.countdown_active and current_game is None and any(p.get('desired_mode') == desired_mode for p in lobby_players.values()):
            # This case handles if trigger_next_waiting_lobby_if_any might have been missed or conditions changed.
            # If no countdown, no game, and there are players for this mode, try to start.
            print(f"No active countdown, but players for {desired_mode} exist. Attempting to start.")
            lobby_manager.start(desired_mode)

@socketio.on('submit_answer')
def handle_answer(data):
    global current_game
    sid=request.sid
    if not current_game or sid not in current_game['players']: emit('error_message',{'message':'Not in game.'});return
    p=current_game['players'][sid]
    if p['is_bot'] or p.get('answered_this_round'): emit('error_message',{'message':'Invalid/Already answered.'});return
    ans=data.get('answer'); q_d=current_game['questions'][current_game['current_question_index']]
    t_t=time.time()-current_game['question_start_time']; is_c=(ans==q_d['correct_answer'])
    pts=0
    if is_c: pts=calculate_points(t_t)
    if is_c and p.get('used_double_score_this_round'): pts*=2; p['used_double_score_this_round']=False
    p['answered_this_round']=True; p['current_answer_correct']=is_c; p['potential_points_this_round']=pts
    emit('answer_receipt',{'message':'Answer received.'})
    all_h_ans=True
    for h_sid in current_game['human_player_sids']:
        if h_sid in current_game['players'] and not current_game['players'][h_sid].get('answered_this_round'): all_h_ans=False;break
    if all_h_ans and current_game.get('question_timer'):
        current_game['question_timer'].cancel();current_game['question_timer']=None
        reveal_answers_and_scores()

@socketio.on('use_help')
def handle_use_help(data):
    global current_game
    sid=request.sid
    if not current_game or sid not in current_game['players']:
        emit('error_message',{'message':'Not in game.'}); return

    player_obj = current_game['players'][sid] # Use a clearer variable name like player_obj or p
    help_type_requested = data.get('type')

    if player_obj['is_bot'] or not player_obj['helps'].get(help_type_requested):
        emit('error_message',{'message':f"Cannot use help: {help_type_requested}."}); return

    player_obj['helps'][help_type_requested] = False # Mark help as used
    current_question = current_game['questions'][current_game['current_question_index']]

    response_payload = {'type': help_type_requested, 'helps_remaining': player_obj['helps']} # Initialize with common fields

    if help_type_requested == 'fifty_fifty':
        correct_ans = current_question['correct_answer']
        incorrect_opts = [opt for opt in current_question['options'] if opt != correct_ans]

        # Ensure there's at least one incorrect option to choose from for the 50/50
        if incorrect_opts:
            chosen_incorrect = random.choice(incorrect_opts)
            options_for_5050 = [correct_ans, chosen_incorrect]
        else:
            # Fallback: should not happen with 3 wrong answers, but as a safeguard
            options_for_5050 = [correct_ans, current_question['options'][0] if current_question['options'][0] != correct_ans else current_question['options'][1]]

        random.shuffle(options_for_5050)
        response_payload['options'] = options_for_5050
        print(f"DEBUG: 50/50 help for {player_obj['username']}. Options sent: {response_payload['options']}")

    elif help_type_requested == 'call_friend':
        response_payload['advice'] = get_llm_advice(current_question['question'], current_question['options'])
        print(f"DEBUG: Call a friend help for {player_obj['username']}. Advice: {response_payload['advice']}")

    elif help_type_requested == 'double_score':
        player_obj['used_double_score_this_round'] = True # Flag for server-side score calculation
        response_payload['message'] = 'Score for this question will be doubled if correct!' # <<< MOVED INSIDE
        print(f"DEBUG: Double score help activated for {player_obj['username']}.")

    emit('help_result', response_payload) # To single user (the requester)

    # Notify other players that a help was used (without revealing specifics like 50/50 options)
    socketio.emit('player_used_help', {
        'username': player_obj['username'],
        'help_type': help_type_requested.replace('_',' ').title()
    }, room=current_game['room_name'], skip_sid=sid, namespace=DEFAULT_NAMESPACE)

@socketio.on('send_chat_message')
def handle_chat_message(data):
    global current_game
    sid=request.sid
    if not current_game or sid not in current_game['players']: emit('error_message',{'message':'Chat only in game.'});return
    p=current_game['players'][sid]; msg_txt=data.get('message','').strip(); msg_emoji=data.get('emoji')
    if not msg_txt and not msg_emoji: return
    chat_p={'sender_sid':sid,'sender_name':p['username'],'is_bot':p['is_bot']}
    if msg_txt: chat_p['text']=msg_txt
    if msg_emoji: chat_p['emoji']=msg_emoji
    socketio.emit('new_chat_message',chat_p,room=current_game['room_name'], namespace=DEFAULT_NAMESPACE) # ADDED NAMESPACE

if __name__ == '__main__':
    print("Starting Flask-SocketIO server (Single Game Model)...")
    get_gemini_model()
    socketio.run(
        app,
        host=config.BACKEND_HOST,
        port=config.BACKEND_PORT,
        debug=config.DEBUG,
        allow_unsafe_werkzeug=config.ALLOW_UNSAFE_WERKZEUG,
    )