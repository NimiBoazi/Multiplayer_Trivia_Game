# Real-Time Multiplayer Trivia Game

A full-stack real-time multiplayer trivia game featuring Classic and Battle Royale modes, intelligent bots, player power-ups, and AI-powered assistance.

## 🎮 Features

### Game Modes
- **Classic Mode**: Traditional trivia with scoring based on speed and accuracy
- **Battle Royale Mode**: Elimination-based gameplay with adaptive difficulty scaling

### Player Features
- **Power-ups**: 50/50 (eliminate wrong answers), Double Score, Call a Friend (AI assistance via Google Gemini)
- **Real-time Chat**: In-game messaging and emoji reactions
- **Disconnect/Rejoin**: Robust handling of network interruptions
- **Responsive UI**: Modern React interface with real-time updates

### Bot System
- **Three Difficulty Levels**: Easy (60% accuracy), Advanced (78% accuracy), Expert (90% accuracy)
- **Realistic Behavior**: Variable response times and human-like answer patterns
- **Dynamic Scaling**: Automatic bot addition based on player count

### Technical Features
- **Real-time Communication**: WebSocket-based using Socket.IO
- **Thread-safe State Management**: RLock-protected game state
- **Asynchronous Lobby System**: Independent countdown timers for different game modes
- **Modular Architecture**: Separated concerns for lobby, game, and transport layers

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
- npm or yarn

### Backend Setup

1. **Navigate to backend directory**:
   ```bash
   cd backend
   ```

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables** (optional):
   Create a `.env` file in the backend directory:
   ```env
   SECRET_KEY=your_secret_key_here
   BACKEND_HOST=0.0.0.0
   BACKEND_PORT=5001
   DEBUG=true
   
   # Game Configuration
   LOBBY_WAIT_TIME=30
   QUESTIONS_PER_GAME=10
   QUESTION_DURATION=20
   POINTS_BASE=1000
   
   # Bot Configuration
   DEFAULT_BOT_DIFFICULTY=easy
   MIN_BOTS=5
   MAX_BOTS=9
   
   # Google Gemini API (for Call a Friend feature)
   GOOGLE_APPLICATION_CREDENTIALS=path/to/your/service-account.json
   LLM_MODEL_TO_USE=gemini-1.5-flash-latest
   ```

4. **Start the backend server**:
   ```bash
   python app.py
   ```
   The server will start on `http://localhost:5001`

### Frontend Setup

1. **Navigate to frontend directory**:
   ```bash
   cd frontend
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Set up environment variables** (optional):
   Create a `.env` file in the frontend directory:
   ```env
   REACT_APP_BACKEND_URL=http://localhost:5001
   REACT_APP_LOBBY_WAIT_TIME=30
   ```

4. **Start the development server**:
   ```bash
   npm start
   ```
   The app will open at `http://localhost:3000`

## 🎯 How to Play

1. **Enter Username**: Choose your display name
2. **Select Game Mode**: Classic or Battle Royale
3. **Choose Bot Difficulty**: Easy, Advanced, or Expert (affects bot opponents)
4. **Join Lobby**: Wait for other players or start with bots
5. **Answer Questions**: Click the correct answer as quickly as possible
6. **Use Power-ups**: Strategic use of 50/50, Double Score, or Call a Friend
7. **Win**: Score highest (Classic) or be the last player standing (Battle Royale)

## 🏗️ Architecture

### Backend (Python/Flask)
- **Flask-SocketIO**: Real-time WebSocket communication
- **Modular Design**: Separate modules for game logic, lobby management, bots, and questions
- **Thread-safe Operations**: RLock protection for concurrent access
- **Pandas Integration**: Efficient question filtering and difficulty management

### Frontend (React)
- **Socket.IO Client**: Real-time server communication
- **Custom Hooks**: Centralized game state management
- **Component Architecture**: Reusable UI components for lobby, game, and leaderboard
- **Responsive Design**: Mobile-friendly interface

### Key Components
- **Lobby Manager**: Handles player queuing and game creation
- **Game Engine**: Manages rounds, scoring, and elimination logic
- **Bot Framework**: Configurable AI opponents with realistic behavior
- **Question System**: Difficulty-aware question selection and management

## 🔧 Configuration

### Game Settings
- `LOBBY_WAIT_TIME`: Seconds to wait before starting a game (default: 30)
- `QUESTIONS_PER_GAME`: Number of questions in Classic mode (default: 10)
- `QUESTION_DURATION`: Time limit per question in seconds (default: 20)
- `POINTS_BASE`: Maximum points for instant correct answer (default: 1000)

### Bot Settings
- `DEFAULT_BOT_DIFFICULTY`: Default bot difficulty level
- `MIN_BOTS`/`MAX_BOTS`: Bot count range for single-player Classic games
- `BR_MIN_TOTAL_ENTITIES`: Minimum players needed for Battle Royale

### Battle Royale Settings
- `BR_DIFFICULTY_STEP_QUESTIONS`: Questions between difficulty increases
- `BR_INITIAL_QUESTIONS_BATCH`: Initial question pool size

## 📁 Project Structure

```
├── backend/
│   ├── app.py              # Main Flask application
│   ├── config.py           # Configuration management
│   ├── lobby.py            # Lobby management system
│   ├── game.py             # Core game logic
│   ├── bots.py             # Bot behavior and AI
│   ├── questions.py        # Question management
│   ├── llm.py              # AI integration (Gemini)
│   └── requirements.txt    # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── hooks/          # Custom React hooks
│   │   └── config.js       # Frontend configuration
│   └── package.json        # Node.js dependencies
└── README.md
```
