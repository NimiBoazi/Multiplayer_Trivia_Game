// Frontend configuration and shared constants

// Backend URL (override in .env as REACT_APP_BACKEND_URL)
export const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:5001';

// Game modes
export const CLASSIC_MODE = 'classic';
export const BATTLE_ROYALE_MODE = 'battle_royale';
export const formatGameMode = (mode) => {
  if (!mode) return '';
  if (mode === CLASSIC_MODE) return 'Classic';
  if (mode === BATTLE_ROYALE_MODE) return 'Battle Royale';
  return mode;
};

// Lobby default wait time (seconds)
export const LOBBY_DEFAULT_WAIT_TIME = parseInt(process.env.REACT_APP_LOBBY_WAIT_TIME || '30', 10);

// Bot difficulty levels (UI)
export const BOT_DIFFICULTY_LEVELS = {
  EASY: 'easy',
  ADVANCED: 'advanced',
  EXPERT: 'expert',
};

