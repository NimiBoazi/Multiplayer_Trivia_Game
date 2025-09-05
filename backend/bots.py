import random
import uuid
from threading import Timer as ThreadingTimer
from . import config


def schedule_bot_answer(current_game, bot_sid, question_data, calculate_points):
    """Schedules (and stores) a bot's answer timer and data in current_game.
    Returns the created timer.
    """
    game_bot_difficulty_str = current_game.get('bot_difficulty', config.DEFAULT_BOT_DIFFICULTY)
    difficulty_params = config.BOT_DIFFICULTY_SETTINGS.get(
        game_bot_difficulty_str, config.BOT_DIFFICULTY_SETTINGS[config.DEFAULT_BOT_DIFFICULTY]
    )

    target_bot_accuracy = difficulty_params['accuracy']
    min_delay = config.QUESTION_DURATION * difficulty_params['min_delay_factor']
    max_delay = config.QUESTION_DURATION * difficulty_params['max_delay_factor']
    if max_delay < min_delay:
        max_delay = min_delay + 0.1
    answer_delay = random.uniform(min_delay, max_delay)

    def bot_thinks_and_answers_internal(was_forced=False, forced_params_from_reveal=None):
        if not current_game or current_game.get('game_state') != 'in_progress' or bot_sid not in current_game['players']:
            return
        bot_player_current_data = current_game['players'][bot_sid]
        if bot_player_current_data.get('is_eliminated'):
            return
        if bot_player_current_data.get('answered_this_round') and not was_forced:
            return

        current_target_accuracy_for_roll = (
            forced_params_from_reveal['accuracy'] if was_forced and forced_params_from_reveal else target_bot_accuracy
        )
        current_question_data_for_decision = (
            forced_params_from_reveal['question_data'] if was_forced and forced_params_from_reveal else question_data
        )
        delay_for_points_calculation = (
            forced_params_from_reveal['delay_for_points'] if was_forced and forced_params_from_reveal else answer_delay
        )

        is_correct_this_time = random.random() < current_target_accuracy_for_roll
        chosen_answer = (
            current_question_data_for_decision['correct_answer']
            if is_correct_this_time
            else random.choice(
                [opt for opt in current_question_data_for_decision['options'] if opt != current_question_data_for_decision['correct_answer']]
            )
            if current_question_data_for_decision['options']
            else None
        )

        current_game['players'][bot_sid]['answered_this_round'] = True
        current_game['players'][bot_sid]['current_answer_correct'] = is_correct_this_time
        current_game['players'][bot_sid]['potential_points_this_round'] = (
            calculate_points(delay_for_points_calculation) if is_correct_this_time else 0
        )

    # Store per-round data for possible forcing
    current_game.setdefault('bot_data_for_round', {})[bot_sid] = {
        'force_params': {
            'accuracy': target_bot_accuracy,
            'question_data': question_data,
            'delay_for_points': answer_delay,
        },
        'timer_function_ref': bot_thinks_and_answers_internal,
    }

    # Timer management
    current_game.setdefault('bot_answer_timers', {})
    if bot_sid in current_game['bot_answer_timers'] and current_game['bot_answer_timers'][bot_sid].is_alive():
        current_game['bot_answer_timers'][bot_sid].cancel()

    timer = ThreadingTimer(answer_delay, bot_thinks_and_answers_internal, kwargs={'was_forced': False, 'forced_params_from_reveal': None})
    current_game['bot_answer_timers'][bot_sid] = timer
    timer.start()
    return timer


def create_bots(num_bots_to_add_final, bot_names_list):
    bots = {}
    available_bot_names = (
        [f"GenericBot_{i+1}" for i in range(num_bots_to_add_final)]
        if not bot_names_list
        else random.sample(bot_names_list, k=min(len(bot_names_list), num_bots_to_add_final))
    )
    for i in range(num_bots_to_add_final):
        bot_sid = f"bot_{uuid.uuid4()}"
        bot_name = available_bot_names[i] if i < len(available_bot_names) else f"FallbackBot{i+1}_{random.randint(100,999)}"
        bots[bot_sid] = {
            'username': bot_name,
            'score': 0,
            'is_bot': True,
            'helps': {'fifty_fifty': True, 'call_friend': True, 'double_score': True},
            'sid': bot_sid,
            'is_eliminated': False,
            'place': 0,
        }
    return bots

