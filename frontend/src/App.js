import React, { useState, useCallback } from 'react';


import Lobby from './components/Lobby';
import GameScreen from './components/GameScreen';
import Leaderboard from './components/Leaderboard';
import './App.css';
import { useGameSocket } from './hooks/useGameSocket';


// Centralized config/constants
import { CLASSIC_MODE, BATTLE_ROYALE_MODE, formatGameMode, LOBBY_DEFAULT_WAIT_TIME, BOT_DIFFICULTY_LEVELS } from './config';

function App() {
    const [username, setUsername] = useState(''); // Confirmed username
    const [tempUsername, setTempUsername] = useState(''); // For input field
    const [gameState, setGameState] = useState('username_prompt'); // username_prompt, lobby, game, leaderboard
    const [desiredMode, setDesiredMode] = useState(null); // User's chosen mode before joining lobby
    const [botDifficulty, setBotDifficulty] = useState(BOT_DIFFICULTY_LEVELS.EASY); // New state, default to Easy

    // Tracking some UI-only state
    // const [gameInProgressMode, setGameInProgressMode] = useState(null); // If needed, derive from gameData.mode

    // Socket/game state via centralized hook
    const {
      isConnected,
      mySid,
      gameInProgressMode,
      lobbyData,
      gameData,
      questionData,
      questionResult,
      leaderboardData,
      playerHelps,
      chatMessages,
      // actions
      joinLobby,
      sendChatMessage,
      sendEmoji,
      // setters (optional use)
      setLobbyData,
      setGameData,
      setQuestionData,
      setQuestionResult,
      setLeaderboardData,
    } = useGameSocket();

    // Derive top-level UI state from hook state
    React.useEffect(() => {
      if (gameData && gameData.mode && gameState !== 'game') {
        setGameState('game');
        setIsJoining(false);
      }
    }, [gameData, gameState]);

    React.useEffect(() => {
      if (leaderboardData && gameState !== 'leaderboard') {
        setGameState('leaderboard');
        setIsJoining(false);
      }
    }, [leaderboardData, gameState]);

    React.useEffect(() => {
      // Only auto-switch to lobby if this user has chosen a mode (desiredMode)
      if (!gameData && desiredMode && gameState !== 'game' && gameState !== 'leaderboard') {
        setGameState('lobby');
      }
    }, [desiredMode, gameData, gameState]);


    const [currentError, setCurrentError] = useState('');
    const [isJoining, setIsJoining] = useState(false);

    // Battle Royale specific state for the current player
    const [amIEliminated, setAmIEliminated] = useState(false);
    const [myPlace, setMyPlace] = useState(0);

    const resetToLobbySelection = () => {
        setGameState('username_prompt'); // Or a 'mode_selection' state if username is kept
        setDesiredMode(null);
        setGameData(null);
        setQuestionData(null);
        setQuestionResult(null);
        setLeaderboardData(null);
        setAmIEliminated(false);
        setMyPlace(0);
        setLobbyData({ mode: null, time_remaining: LOBBY_DEFAULT_WAIT_TIME, players: [], is_active: false });
        // Don't clear username if they might want to play again with the same name.
        // For simplicity, going back to username_prompt forces re-entry.
    };

    const attemptJoinLobby = useCallback((modeToJoin) => {
        // Check tempUsername and isJoining (these are already correctly in deps if it was there before)
        if (tempUsername.trim() && !isJoining) {
            setIsJoining(true); // Setter, stable
            setCurrentError(''); // Setter, stable

            const currentTrimmedUsername = tempUsername.trim(); // Derived from tempUsername
            setUsername(currentTrimmedUsername); // Setter, stable
            setDesiredMode(modeToJoin);   // Setter, stable
            setGameState('lobby'); // Immediately show lobby while waiting for server updates

            // This console.log will now show the CURRENT botDifficulty because this function instance is fresh
            console.log(`Attempting to join ${modeToJoin} lobby as ${currentTrimmedUsername} with bot difficulty: ${botDifficulty}`);

            joinLobby({ username: currentTrimmedUsername, mode: modeToJoin, bot_difficulty: botDifficulty });
        } else if (!tempUsername.trim()) {
            setCurrentError("Please enter a username.");
            setIsJoining(false);
        } else if (isJoining) {
            console.log("Join attempt already in progress");
        }
    }, [
        tempUsername,
        isJoining,
        botDifficulty,
        setUsername, setDesiredMode, setIsJoining, setCurrentError
    ]);

    // Render logic
    if (gameState === 'username_prompt') {
        return (
            <div className="App username-prompt">
                <h1>Real-Time Trivia!</h1>
                <input
                    type="text"
                    placeholder="Enter your username"
                    value={tempUsername}
                    onChange={(e) => setTempUsername(e.target.value)}
                />

                {/* --- NEW BOT DIFFICULTY SELECTOR --- */}
                <div className="bot-difficulty-selector">
                    <label>Bot Difficulty: </label>
                    {Object.entries(BOT_DIFFICULTY_LEVELS).map(([key, value]) => (
                        <label key={value} htmlFor={`bot-diff-${value}`}>
                            <input
                                type="radio"
                                id={`bot-diff-${value}`}
                                name="botDifficulty"
                                value={value}
                                checked={botDifficulty === value}
                                onChange={(e) => setBotDifficulty(e.target.value)}
                                disabled={isJoining || !!gameInProgressMode}
                            />
                            {key.charAt(0) + key.slice(1).toLowerCase()}
                        </label>
                    ))}
                </div>
                {/* --- END NEW SELECTOR --- */}

                <div className="mode-selection">
                    <button
                        onClick={() => attemptJoinLobby(CLASSIC_MODE)}
                        disabled={isJoining || !isConnected || !!gameInProgressMode}>
                        {isJoining && desiredMode === CLASSIC_MODE ? 'Joining Classic...' : 'Join Classic Lobby'}
                    </button>
                    <button
                        onClick={() => attemptJoinLobby(BATTLE_ROYALE_MODE)}
                        disabled={isJoining || !isConnected || !!gameInProgressMode}>
                        {isJoining && desiredMode === BATTLE_ROYALE_MODE ? 'Joining BR...' : 'Join Battle Royale'}
                    </button>
                </div>
                {!isConnected && <p>Connecting...</p>}
                {gameInProgressMode && <p className="game-in-progress-notice">A {gameInProgressMode} game is currently in progress. Please wait.</p>}
                {currentError && <p className="error-message">{currentError}</p>}
            </div>
        );
    }

    return (
        <div className="App">
            <header className="App-header">
            <h1>
                Trivia Master
                {username && ` - ${username}`}
                {gameData && gameData.mode && ` -${formatGameMode(gameData.mode)}`}
            </h1>
                <p>Connection: {isConnected ? 'Connected' : 'Disconnected'}</p>
                {currentError && <p className="error-message">{currentError}</p>}
            </header>
            <main>
                {gameState === 'lobby' && (
                    <Lobby
                        lobbyData={lobbyData}
                        desiredMode={desiredMode}
                        username={username}
                        gameInProgressMode={gameInProgressMode}
                    />
                )}
                {gameState === 'game' && gameData && questionData && mySid && (
                    <GameScreen
                        gameData={gameData}
                        questionData={questionData}
                        questionResult={questionResult}
                        playerHelps={playerHelps}
                        chatMessages={chatMessages}
                        mySid={mySid}
                        username={username}
                        amIEliminated={amIEliminated}
                        myPlace={myPlace}
                        onSendMessage={sendChatMessage}
                        onSendEmoji={sendEmoji}
                    />
                )}
                {gameState === 'leaderboard' && leaderboardData && (
                    <Leaderboard
                        leaderboardData={leaderboardData}
                        onPlayAgain={resetToLobbySelection}
                    />
                )}
            </main>
        </div>
    );
}

export default App;