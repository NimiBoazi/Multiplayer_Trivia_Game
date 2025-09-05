import { useEffect, useCallback, useState } from 'react';
import { socket } from '../socket';
import { BATTLE_ROYALE_MODE, LOBBY_DEFAULT_WAIT_TIME } from '../config';

export function useGameSocket() {
  const [isConnected, setIsConnected] = useState(socket.connected);
  const [mySid, setMySid] = useState(null);
  const [gameInProgressMode, setGameInProgressMode] = useState(null);
  const [lobbyData, setLobbyData] = useState({ mode: null, time_remaining: LOBBY_DEFAULT_WAIT_TIME, players: [], is_active: false });
  const [gameData, setGameData] = useState(null);
  const [questionData, setQuestionData] = useState(null);
  const [questionResult, setQuestionResult] = useState(null);
  const [leaderboardData, setLeaderboardData] = useState(null);
  const [playerHelps, setPlayerHelps] = useState({ fifty_fifty: true, call_friend: true, double_score: true });
  const [chatMessages, setChatMessages] = useState([]);
  const [lastError, setLastError] = useState('');

  const connect = useCallback(() => {
    if (!socket.connected) socket.connect();
  }, []);

  const disconnect = useCallback(() => {
    if (socket.connected) socket.disconnect();
  }, []);

  // Emits
  const joinLobby = useCallback(({ username, mode, bot_difficulty }) => {
    socket.emit('join_lobby_request', { username, mode, bot_difficulty });
  }, []);

  const submitAnswer = useCallback((answer) => {
    socket.emit('submit_answer', { answer });
  }, []);

  const useHelp = useCallback((type) => {
    socket.emit('use_help', { type });
  }, []);

  const sendChatMessage = useCallback((message) => {
    socket.emit('send_chat_message', { message });
  }, []);

  const sendEmoji = useCallback((emoji) => {
    socket.emit('send_chat_message', { emoji });
  }, []);

  // Handlers
  const handleConnect = useCallback(() => {
    setIsConnected(true);
  }, []);

  const handleDisconnect = useCallback(() => {
    setIsConnected(false);
  }, []);

  const handleConnectionAck = useCallback((data) => {
    setMySid(data.sid);
    setGameInProgressMode(data.game_in_progress_mode || null);
    if (data.lobby_status) setLobbyData(data.lobby_status);
  }, []);

  const handleLobbyUpdate = useCallback((data) => {
    setLobbyData(data);
  }, []);

  const handleError = useCallback((data) => {
    if (data && data.message) setLastError(data.message);
    // auto clear after a short period
    setTimeout(() => setLastError(''), 5000);
  }, []);

  const handleGameStarting = useCallback((data) => {
    setGameData(data);
    const me = data.players.find((p) => p.sid === mySid || (p.username === (window.username || '') && !p.is_bot));
    if (me && me.helps) setPlayerHelps(me.helps);
    else setPlayerHelps({ fifty_fifty: true, call_friend: true, double_score: true });
    setChatMessages([]);
  }, [mySid]);

  const handleNewQuestion = useCallback((data) => {
    setQuestionData(data);
    setQuestionResult(null);
    // Reset per-round client flags so options are clickable immediately
    setGameData((prev) => (prev ? ({
      ...prev,
      players: prev.players.map((p) => ({
        ...p,
        answered_this_round: false,
        current_answer_correct: null,
        potential_points_this_round: 0,
      })),
    }) : prev));
  }, []);

  const handleQuestionResult = useCallback((data) => {
    setQuestionResult(data);
    if (data.player_data && mySid && data.player_data[mySid]) {
      const myResultData = data.player_data[mySid];
      setPlayerHelps(myResultData.helps);
    }
    if (gameData && data.player_data) {
      const updatedPlayers = gameData.players.map((p) => (data.player_data[p.sid] ? { ...p, ...data.player_data[p.sid] } : p));
      setGameData((prev) => ({ ...prev, players: updatedPlayers }));
    }
    if (data.mode === BATTLE_ROYALE_MODE && data.active_player_count !== undefined) {
      setQuestionData((prev) => (prev ? { ...prev, active_player_count: data.active_player_count } : null));
    }
  }, [mySid, gameData]);

  const handleGameOver = useCallback((data) => {
    setLeaderboardData(data);
    setQuestionData(null);
    setQuestionResult(null);
    setGameInProgressMode(null);
    setLobbyData({ mode: null, time_remaining: LOBBY_DEFAULT_WAIT_TIME, players: [], is_active: false });
  }, []);

  const handleHelpResult = useCallback((data) => {
    if (data.helps_remaining) setPlayerHelps(data.helps_remaining);
    if (data.type === 'fifty_fifty' && data.options && Array.isArray(data.options)) {
      setQuestionData((prev) => (prev ? { ...prev, options: data.options, fiftyFiftyUsedThisQuestion: true } : prev));
    }
    if (data.type === 'double_score' && data.message) {
      setQuestionData((prev) => (prev ? { ...prev, doubleScoreActiveThisQuestion: true } : prev));
    }
    if (data.type === 'call_friend' && data.advice) {
      // No-op here; UI can alert if needed
    }
  }, []);

  const handleNewChatMessage = useCallback((message) => setChatMessages((prev) => [...prev, message]), []);

  const handlePlayerUsedHelp = useCallback((data) => setChatMessages((prev) => [...prev, { type: 'system', text: `${data.username} used ${data.help_type}.` }]), []);

  const handlePlayerLeft = useCallback((data) => {
    if (gameData && gameData.players) setGameData((prev) => ({ ...prev, players: prev.players.filter((p) => p.sid !== data.sid) }));
    setChatMessages((prev) => [...prev, { type: 'system', text: `${data.username} has left.` }]);
  }, [gameData]);

  useEffect(() => {
    socket.on('connect', handleConnect);
    socket.on('disconnect', handleDisconnect);
    socket.on('connection_ack', handleConnectionAck);
    socket.on('error_message', handleError);
    socket.on('lobby_countdown_update', handleLobbyUpdate);
    socket.on('game_starting', handleGameStarting);
    socket.on('new_question', handleNewQuestion);
    socket.on('question_result', handleQuestionResult);
    socket.on('game_over', handleGameOver);
    socket.on('help_result', handleHelpResult);
    socket.on('new_chat_message', handleNewChatMessage);
    socket.on('player_used_help', handlePlayerUsedHelp);
    socket.on('player_left', handlePlayerLeft);

    if (!socket.connected) socket.connect();

    return () => {
      socket.off('connect', handleConnect);
      socket.off('disconnect', handleDisconnect);
      socket.off('connection_ack', handleConnectionAck);
      socket.off('error_message', handleError);
      socket.off('lobby_countdown_update', handleLobbyUpdate);
      socket.off('game_starting', handleGameStarting);
      socket.off('new_question', handleNewQuestion);
      socket.off('question_result', handleQuestionResult);
      socket.off('game_over', handleGameOver);
      socket.off('help_result', handleHelpResult);
      socket.off('new_chat_message', handleNewChatMessage);
      socket.off('player_used_help', handlePlayerUsedHelp);
      socket.off('player_left', handlePlayerLeft);
    };
  }, [handleConnect, handleDisconnect, handleConnectionAck, handleLobbyUpdate, handleGameStarting, handleNewQuestion, handleQuestionResult, handleGameOver, handleHelpResult, handleNewChatMessage, handlePlayerUsedHelp, handlePlayerLeft]);

  return {
    // connection
    isConnected,
    mySid,
    connect,
    disconnect,

    // lobby & game
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
    submitAnswer,
    useHelp,
    sendChatMessage,
    sendEmoji,

    // setters (if parent wants to sync/override)
    setLobbyData,
    setGameData,
    setQuestionData,
    setQuestionResult,
    setLeaderboardData,
    setPlayerHelps,
    setChatMessages,
  };
}

