import React from 'react';

// Helper for ordinal suffix
function getOrdinalSuffix(i) { /* ... same as above ... */ }

function Leaderboard({ leaderboardData, onPlayAgain }) {
    const { leaderboard, mode } = leaderboardData;

    return (
        <div className="leaderboard">
            <h2>Game Over!</h2>
            <h3>Leaderboard:</h3>
            <ol>
                {leaderboard.map((player, index) => (
                    <li key={player.username + index}> {/* Ensure unique key */}
                        {mode === 'battle_royale' && player.place > 0 ? `${player.place}${getOrdinalSuffix(player.place)} Place: ` : ''}
                        {player.username} {player.is_bot ? '(Bot)' : ''} - {player.score} points
                        {index === 0 && player.place !== 0 && (!mode || mode === 'classic' || (mode === 'battle_royale' && player.place === 1)) && <span> 🏆 Winner!</span>}
                        {mode === 'battle_royale' && player.place === 1 && index !== 0 && <span> 🏆 Winner!</span>} {/* BR winner might not be index 0 if sorted by score after place */}
                    </li>
                ))}
            </ol>
            <button onClick={onPlayAgain}>Play Again</button>
        </div>
    );
}

export default Leaderboard;