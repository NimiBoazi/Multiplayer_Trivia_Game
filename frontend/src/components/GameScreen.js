import React from 'react';
import Question from './Question';
import Options from './Options';
import Timer from './Timer';
import Helps from './Helps';
import Chat from './Chat';
import Scoreboard from './Scoreboard';

import { CLASSIC_MODE, BATTLE_ROYALE_MODE } from '../config';

// Helper for ordinal suffix
function getOrdinalSuffix(i) {
    if (i <= 0) return "";
    const j = i % 10, k = i % 100;
    if (j === 1 && k !== 11) return "st";
    if (j === 2 && k !== 12) return "nd";
    if (j === 3 && k !== 13) return "rd";
    return "th";
}

function GameScreen({
    gameData,
    questionData,
    questionResult,
    playerHelps,
    chatMessages,
    mySid,
    username,
    amIEliminated,
    myPlace,
    onSendMessage,
    onSendEmoji,
}) {
    const { mode, players, initial_player_count } = gameData;
    // questionData can be null initially if game is starting, handle gracefully
    const { 
        question = "Loading question...", 
        question_number = 0, 
        total_questions = 0, 
        duration = 30, // Default duration
        difficulty = "N/A", 
        active_player_count 
    } = questionData || {}; // Provide default empty object if questionData is null
    
    const me = players.find(p => p.sid === mySid || (p.username === username && !p.is_bot));
    const isSpectating = mode === BATTLE_ROYALE_MODE && amIEliminated;

    return (
        <div className={`game-screen ${isSpectating ? 'spectating' : ''}`}>
            <div className="game-main-content">
                {mode === BATTLE_ROYALE_MODE && (
                    <div className="player-counter">
                        Players Remaining: {active_player_count !== undefined ? active_player_count : (initial_player_count || 'N/A')} / {initial_player_count || 'N/A'}
                    </div>
                )}
                {isSpectating && (
                    <div className="elimination-message spectator-view">
                        <h2>You were eliminated!</h2>
                        <p>You placed: <strong>{myPlace}{getOrdinalSuffix(myPlace)}</strong></p>
                        <p>Now spectating...</p>
                    </div>
                )}

                <Timer duration={duration} questionKey={`${gameData.game_id || 'g'}-${question_number}`} />
                <Question
                    text={question}
                    number={question_number}
                    total={total_questions}
                    difficulty={difficulty}
                />
                {!questionResult && questionData && questionData.options && ( // Ensure options exist
                     <Options
                        options={questionData.options}
                        correctAnswer={null}
                        disabled={!!questionResult || isSpectating}
                        isSpectating={isSpectating}
                    />
                )}
               
                {questionResult && (
                    <div className="question-feedback">
                        <p>Correct Answer: <strong>{questionResult.correct_answer}</strong></p>
                        {/* More detailed round scores can be shown here from questionResult.round_scores */}
                    </div>
                )}
                 <Helps 
                    helps={playerHelps} 
                    disabled={!!questionResult || isSpectating || (me && me.answered_this_round) || (mode === BATTLE_ROYALE_MODE && helpTypeDisabledInBR())} // helpTypeDisabledInBR can be a new helper
                />
            </div>
            <aside className="game-sidebar">
                <Scoreboard players={players} mySid={mySid} gameMode={mode} />
                <Chat
                  messages={chatMessages}
                  mySid={mySid}
                  username={username}
                  onSendMessage={onSendMessage}
                  onSendEmoji={onSendEmoji}
                />
            </aside>
        </div>
    );
}

// Example helper if you want to disable specific helps in BR
function helpTypeDisabledInBR(helpType) {
    // if (helpType === 'call_friend') return true;
    return false; // By default, no helps are disabled in BR unless specified
}


export default GameScreen;