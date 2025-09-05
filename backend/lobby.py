from threading import RLock, Timer as ThreadingTimer
from typing import Callable, Dict, Any, Optional, List


class LobbyManager:
    """
    Manages a single active lobby countdown at a time for a specific mode.

    External dependencies are injected to minimize coupling:
      - socketio: for emit
      - namespace: socket namespace
      - lock: shared lock for thread-safety when reading players
      - get_players_for_mode(mode) -> Dict[sid, player_data]
      - is_game_active() -> bool
      - on_countdown_finished(mode) -> None (creates a game)
    """

    def __init__(
        self,
        *,
        socketio,
        namespace: str,
        wait_time: int,
        lock: Optional[RLock],
        get_players_for_mode: Callable[[str], Dict[str, Dict[str, Any]]],
        is_game_active: Callable[[], bool],
        on_countdown_finished: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.socketio = socketio
        self.namespace = namespace
        self.wait_time = wait_time
        self.lock = lock or RLock()
        self.get_players_for_mode = get_players_for_mode
        self.is_game_active = is_game_active
        self.on_countdown_finished = on_countdown_finished

        self._timer: Optional[ThreadingTimer] = None
        self.countdown_active: bool = False
        self.time_remaining: int = self.wait_time
        self.mode_in_countdown: Optional[str] = None

    # ----- Public API -----

    def start(self, mode: str) -> None:
        """Start a countdown for the given mode if not already active and no game is running."""
        with self.lock:
            if self.is_game_active():
                return
            # If already active for this mode, just emit current status
            if self.countdown_active and self.mode_in_countdown == mode:
                self._emit_update(active=True, mode=mode)
                return

            # Switch to this mode countdown
            players_for_mode = self.get_players_for_mode(mode)
            if not players_for_mode:
                # Nothing to do
                self._reset_internal()
                self._emit_update(active=False, mode=mode, players=[])
                return

            self.countdown_active = True
            self.mode_in_countdown = mode
            self.time_remaining = self.wait_time
            self._emit_update(active=True, mode=mode, players=list(players_for_mode.values()))
            self._schedule_next_tick()

    def stop(self, *, emit_update: bool = False) -> None:
        """Stop any active countdown and optionally emit an update to clients."""
        with self.lock:
            self._cancel_timer()
            was_active = self.countdown_active
            stopped_mode = self.mode_in_countdown
            self._reset_internal()
            if was_active and emit_update and stopped_mode:
                remaining_players = list(self.get_players_for_mode(stopped_mode).values())
                self._emit_update(active=False, mode=stopped_mode, players=remaining_players)

    def trigger_next_waiting_lobby_if_any(self, modes_priority: List[str]) -> None:
        """If idle, try starting a countdown for the first mode that has players waiting."""
        with self.lock:
            if self.is_game_active() or self.countdown_active:
                return
            for mode in modes_priority:
                players = self.get_players_for_mode(mode)
                if players:
                    self.mode_in_countdown = mode
                    # Call start which will check again and emit
                    self.start(mode)
                    return

    # ----- Internal helpers -----

    def _schedule_next_tick(self) -> None:
        self._cancel_timer()
        self._timer = ThreadingTimer(1.0, self._tick)
        self._timer.start()

    def _cancel_timer(self) -> None:
        if self._timer and self._timer.is_alive():
            self._timer.cancel()
        self._timer = None

    def _tick(self) -> None:
        # Timer callback; keep it resilient and lock-protected
        with self.lock:
            if self.is_game_active():
                # Game started while counting down; stop without emitting end (game events will update UI)
                self._reset_internal()
                return
            if not self.countdown_active or not self.mode_in_countdown:
                # Nothing to do
                self._reset_internal()
                return

            players_for_mode = self.get_players_for_mode(self.mode_in_countdown)
            if not players_for_mode:
                # Everyone left; stop and emit update for this mode
                ended_mode = self.mode_in_countdown
                self._reset_internal()
                self._emit_update(active=False, mode=ended_mode, players=[])
                # Try next waiting lobby
                return

            self.time_remaining -= 1
            if self.time_remaining <= 0:
                # Fire game creation callback then stop and emit inactive
                finished_mode = self.mode_in_countdown
                if self.on_countdown_finished:
                    # Call without holding lock to avoid deadlocks if callback re-enters
                    # But we need to release lock first
                    pass
                # Release lock and run callback, then re-acquire to finalize state
                self.lock.release()
                try:
                    if self.on_countdown_finished:
                        self.on_countdown_finished(finished_mode)
                finally:
                    self.lock.acquire()

                # Reset and emit inactive for finished mode
                self._reset_internal()
                self._emit_update(active=False, mode=finished_mode, players=[])
                return

            # Normal tick - emit update and schedule next
            self._emit_update(active=True, mode=self.mode_in_countdown, players=list(players_for_mode.values()))
            self._schedule_next_tick()

    def _emit_update(self, *, active: bool, mode: Optional[str], players: Optional[list] = None) -> None:
        payload = {
            'mode': mode,
            'time_remaining': self.time_remaining if active else self.wait_time,
            'players': players if players is not None else [],
            'is_active': active,
        }
        try:
            self.socketio.emit('lobby_countdown_update', payload, namespace=self.namespace)
        except Exception as e:
            # Be defensive; don't crash timer on emit failures
            print(f"LobbyManager emit error: {e}")

    def _reset_internal(self) -> None:
        self.countdown_active = False
        self.mode_in_countdown = None
        self.time_remaining = self.wait_time
        self._cancel_timer()

