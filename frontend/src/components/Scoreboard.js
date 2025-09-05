import React from 'react';

function Scoreboard({ players, mySid }) {
    const sortedPlayers = [...players].sort((a, b) => b.score - a.score);

    return (
        <div className="scoreboard">
            <h4>Scores</h4>
            <ul>
                {sortedPlayers.map(player => (
                    <li key={player.sid || player.username} className={(player.sid === mySid || (player.username === window.username && !player.is_bot)) ? 'my-score' : ''}> {/* Assuming window.username is set for current player */}
                        {player.username}{player.is_bot ? ' (Bot)' : ''}: {player.score}
                    </li>
                ))}
            </ul>
        </div>
    );
}
export default Scoreboard;