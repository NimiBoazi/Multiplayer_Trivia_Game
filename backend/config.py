import os
from dotenv import load_dotenv

# Load environment variables from a .env file if present
load_dotenv()

BASE_DIR = os.path.dirname(__file__)


# Flask/SocketIO
SECRET_KEY = os.getenv('SECRET_KEY', 'your_very_secret_key!')
CORS_ALLOWED_ORIGINS = os.getenv('CORS_ALLOWED_ORIGINS', '*')
ASYNC_MODE = os.getenv('ASYNC_MODE', 'threading')  # eventlet, gevent, threading
DEFAULT_NAMESPACE = os.getenv('DEFAULT_NAMESPACE', '/')

# Server
BACKEND_HOST = os.getenv('BACKEND_HOST', '0.0.0.0')
BACKEND_PORT = int(os.getenv('BACKEND_PORT', '5001'))
DEBUG = os.getenv('DEBUG', 'true').lower() in ('1', 'true', 'yes', 'y')
ALLOW_UNSAFE_WERKZEUG = os.getenv('ALLOW_UNSAFE_WERKZEUG', 'true').lower() in ('1', 'true', 'yes', 'y')

# Game configuration
LOBBY_WAIT_TIME = int(os.getenv('LOBBY_WAIT_TIME', '30'))
QUESTIONS_PER_GAME = int(os.getenv('QUESTIONS_PER_GAME', '10'))
QUESTION_DURATION = int(os.getenv('QUESTION_DURATION', '20'))
POINTS_BASE = int(os.getenv('POINTS_BASE', '1000'))
MIN_BOTS = int(os.getenv('MIN_BOTS', '5'))
MAX_BOTS = int(os.getenv('MAX_BOTS', '9'))
BR_MIN_TOTAL_ENTITIES = int(os.getenv('BR_MIN_TOTAL_ENTITIES', '3'))  # Min total players for BR
BR_DIFFICULTY_STEP_QUESTIONS = int(os.getenv('BR_DIFFICULTY_STEP_QUESTIONS', '5'))  # Increase difficulty every N questions in BR
BR_INITIAL_QUESTIONS_BATCH = int(os.getenv('BR_INITIAL_QUESTIONS_BATCH', '30'))  # Initial question batch for BR

# Files (default to backend directory)
BOT_NAMES_FILE = os.getenv('BOT_NAMES_FILE') or os.path.join(BASE_DIR, 'bot_names.txt')
QUESTIONS_CSV_FILE = os.getenv('QUESTIONS_CSV_FILE') or os.path.join(BASE_DIR, 'trivia_questions_filtered.csv')

# LLM / Gemini
LLM_MODEL_TO_USE = os.getenv('LLM_MODEL_TO_USE', 'gemini-1.5-flash-latest')

# Bot behavior
DEFAULT_BOT_DIFFICULTY = os.getenv('DEFAULT_BOT_DIFFICULTY', 'easy')
BOT_DIFFICULTY_SETTINGS = {
    'easy': {
        'accuracy': float(os.getenv('BOT_EASY_ACCURACY', '0.60')),
        'min_delay_factor': float(os.getenv('BOT_EASY_MIN_DELAY_FACTOR', '0.4')),
        'max_delay_factor': float(os.getenv('BOT_EASY_MAX_DELAY_FACTOR', '0.8')),
    },
    'advanced': {
        'accuracy': float(os.getenv('BOT_ADVANCED_ACCURACY', '0.78')),
        'min_delay_factor': float(os.getenv('BOT_ADVANCED_MIN_DELAY_FACTOR', '0.3')),
        'max_delay_factor': float(os.getenv('BOT_ADVANCED_MAX_DELAY_FACTOR', '0.65')),
    },
    'expert': {
        'accuracy': float(os.getenv('BOT_EXPERT_ACCURACY', '0.90')),
        'min_delay_factor': float(os.getenv('BOT_EXPERT_MIN_DELAY_FACTOR', '0.2')),
        'max_delay_factor': float(os.getenv('BOT_EXPERT_MAX_DELAY_FACTOR', '0.5')),
    },
}

