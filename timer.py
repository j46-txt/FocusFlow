# timer.py
# -*- coding: utf-8 -*-
import time
from dataclasses import dataclass
from typing import Callable
import settings

@dataclass
class TimerState:
    mode: str = 'pomodoro'  # 'pomodoro', 'break', 'stopwatch'
    status: str = 'idle'    # 'idle', 'running', 'paused'
    seconds_remaining: int = 25 * 60
    seconds_elapsed: int = 0
    seconds_focused_in_turn: int = 0  # Tracks real focused seconds in the current active block

class FocusTimer:
    def __init__(self, on_tick: Callable[[], None], on_complete: Callable[[int, str], None], on_timer_end: Callable[[str], None]):
        self.state = TimerState()
        self.on_tick = on_tick
        self.on_complete = on_complete
        self.on_timer_end = on_timer_end
        self._last_tick_time: float = 0.0
        self.sync_durations()

    def sync_durations(self) -> None:
        self.pomodoro_duration = settings.get_pomodoro_minutes() * 60
        self.break_duration = settings.get_break_minutes() * 60
        if self.state.status == 'idle':
            if self.state.mode == 'pomodoro':
                self.state.seconds_remaining = self.pomodoro_duration
            elif self.state.mode == 'break':
                self.state.seconds_remaining = self.break_duration

        def start(self) -> None:
            if self.state.status == 'idle':
                self.sync_durations()
                if self.state.mode == 'stopwatch':
                    self.state.seconds_elapsed = 0
                self.state.seconds_focused_in_turn = 0
            self.state.status = 'running'
            self._last_tick_time = time.time()
            self.on_tick()

    def pause(self) -> None:
        if self.state.status == 'running':
            self.state.status = 'paused'
            # Secure exact fractional study data into the database upon pausing
            if self.state.mode in ('pomodoro', 'stopwatch') and self.state.seconds_focused_in_turn > 0:
                self.on_complete(self.state.seconds_focused_in_turn, self.state.mode)
            self.state.seconds_focused_in_turn = 0
        self.on_tick()

    def handle_disconnect(self) -> None:
        """Triggers an automatic pause flush when no client interfaces are active."""
        if self.state.status == 'running':
            self.pause()

    def skip(self) -> None:
        if self.state.mode == 'break':
            self.state.mode = 'pomodoro'
            self._reset()
            self.start()

    def reset(self) -> None:
        self.state.seconds_focused_in_turn = 0
        self._reset()
        self.on_tick()

    def stop(self) -> None:
        if self.state.mode == 'stopwatch':
            if self.state.status == 'running' and self.state.seconds_focused_in_turn > 0:
                self.on_complete(self.state.seconds_focused_in_turn, self.state.mode)
            self.state.seconds_focused_in_turn = 0
            self._reset()
            self.on_tick()

    def set_mode(self, new_mode: str) -> None:
        new_mode = new_mode.lower()
        if new_mode not in ('pomodoro', 'stopwatch'):
            return
        self.state.mode = new_mode
        self._reset()
        self.on_tick()

    def tick(self) -> None:
        if self.state.status != 'running':
            return
        now = time.time()
        delta = int(now - self._last_tick_time)
        if delta > 0:
            self._last_tick_time += delta  
            
            if self.state.mode in ('pomodoro', 'stopwatch'):
                self.state.seconds_focused_in_turn += delta

            if self.state.mode in ('pomodoro', 'break'):
                self.state.seconds_remaining -= delta
                if self.state.seconds_remaining <= 0:
                    is_pomodoro = self.state.mode == 'pomodoro'
                    
                    self.state.status = 'idle'
                    self.on_timer_end(self.state.mode)
                    
                    if is_pomodoro and self.state.seconds_focused_in_turn > 0:
                        self.on_complete(self.state.seconds_focused_in_turn, 'pomodoro')
                    self.state.seconds_focused_in_turn = 0
                    
                    if is_pomodoro:
                        self.state.mode = 'break'
                    else:
                        self.state.mode = 'pomodoro'
                        
                    self._reset()
                    self.start()
                    return
            elif self.state.mode == 'stopwatch':
                self.state.seconds_elapsed += delta
            self.on_tick()

    def _reset(self) -> None:
        self.state.status = 'idle'
        self.sync_durations()
        if self.state.mode == 'pomodoro':
            self.state.seconds_remaining = self.pomodoro_duration
        elif self.state.mode == 'break':
            self.state.seconds_remaining = self.break_duration
        else:
            self.state.seconds_elapsed = 0
        self.state.seconds_focused_in_turn = 0

    @property
    def display_time(self) -> str:
        secs = max(0, self.state.seconds_remaining if self.state.mode in ('pomodoro', 'break') else self.state.seconds_elapsed)
        mins, secs = divmod(secs, 60)
        hours, mins = divmod(mins, 60)
        if hours > 0:
            return f"{hours:02d}:{mins:02d}:{secs:02d}"
        return f"{mins:02d}:{secs:02d}"
