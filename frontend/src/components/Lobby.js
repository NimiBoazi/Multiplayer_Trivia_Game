import React from 'react';
import { formatGameMode, LOBBY_DEFAULT_WAIT_TIME as LOBBY_DEFAULT_WAIT_TIME_DISPLAY } from '../config';

function Lobby({ lobbyData, desiredMode, username, gameInProgressMode }) {
    const { mode: activeLobbyModeFromServer, time_remaining, players, is_active } = lobbyData;

    let titleText = "Lobby Area";
    let messageText = "";
    let playersToShow = [];
    let showPlayerList = false;
    let timeToDisplay = LOBBY_DEFAULT_WAIT_TIME_DISPLAY;
    let isMyLobbyCountingDown = is_active && activeLobbyModeFromServer === desiredMode;

    const formattedDesiredMode = desiredMode ? formatGameMode(desiredMode) : "a specific";
    const formattedActiveLobbyMode = activeLobbyModeFromServer ? formatGameMode(activeLobbyModeFromServer) : "";

    if (gameInProgressMode) {
        titleText = `${formatGameMode(gameInProgressMode)} Game in Progress`;
        messageText = `Please wait for the current game to finish.`;
    } else if (is_active && activeLobbyModeFromServer) { // A lobby countdown is globally active
        titleText = `${formattedActiveLobbyMode} Lobby`;
        if (isMyLobbyCountingDown) { // It's my desired mode's lobby
            messageText = `Game starts in: `;
            timeToDisplay = time_remaining;
            playersToShow = players; // Server sends players for the active lobby
            showPlayerList = true;
        } else if (desiredMode) { // Another mode's lobby is active, I'm waiting for mine
            messageText = `A ${formattedActiveLobbyMode} lobby is counting down. You are waiting for the ${formattedDesiredMode} lobby.`;
            // For simplicity, if lobby isn't the active one, we won't show a player list yet.
            // playersToShow = allLobbyPlayersFromApp.filter(p => p.desired_mode === desiredMode);
            // if (playersToShow.length > 0) showPlayerList = true;
        } else { // No desired mode selected by user, but some lobby is active
             messageText = `A ${formattedActiveLobbyMode} lobby is counting down. Choose a mode from the main screen to join.`;
        }
    } else if (desiredMode) { // No active countdown globally, but this client has selected a mode
        titleText = `${formattedDesiredMode} Lobby`;
        messageText = `Waiting for players to start the ${formattedDesiredMode} lobby...`;
        // `lobbyData.players` from server should be for this `desiredMode` if it just became inactive or is the next to go
        if (lobbyData.mode === desiredMode || (lobbyData.mode === null && lobbyData.players.length > 0 && lobbyData.players.every(p => p.desired_mode === desiredMode))) {
             playersToShow = lobbyData.players;
        }
        if (playersToShow.length > 0 || desiredMode) { // Show list if players are there, or at least the header if mode selected
            showPlayerList = true;
        }
    } else { // No desired mode, no active countdown, no game in progress
        messageText = "Select a game mode from the main screen to join or start a lobby.";
    }

    return (
        <div className="lobby card-container">
            <h2>{titleText}</h2>
            <p>
                {messageText} 
                {isMyLobbyCountingDown && <strong>{timeToDisplay} seconds</strong>}
            </p>
            
            {showPlayerList && (
                 <>
                    <h3>
                        Players in {formattedDesiredMode} Lobby ({playersToShow.length}):
                    </h3>
                    {playersToShow.length > 0 ? (
                        <ul>
                            {playersToShow.map((player) => (
                                <li key={player.sid || player.username} className={player.username === username ? 'my-name-in-lobby' : ''}>
                                    {player.username}
                                    {/* If player object from server contains desired_mode: 
                                        <span> (for {formatGameMode(player.desired_mode)})</span> 
                                    */}
                                </li>
                            ))}
                        </ul>
                    ) : (
                        <p>Waiting for players for {formattedDesiredMode} mode...</p>
                    )}
                 </>
            )}
             {!showPlayerList && !gameInProgressMode && desiredMode && !isMyLobbyCountingDown && (
                 <p>The {formattedDesiredMode} lobby will start after the current activity or when more players join its queue.</p>
            )}
        </div>
    );
}

export default Lobby;