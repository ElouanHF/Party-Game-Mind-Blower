"""The grace-period countdown.

When the host presses End party, the server starts a background task that
sleeps until the deadline and then moves everyone into review. If the phase
has already moved on (everyone answered early, or the dev "Skip timer"
button was used), the task does nothing.
"""
from __future__ import annotations

import time
from typing import Callable


def start_grace_timer(socketio, game, deadline: float, on_change: Callable[[], None]) -> None:
    def wait_then_finish():
        while True:
            remaining = deadline - time.time()
            if remaining <= 0:
                break
            socketio.sleep(min(remaining, 0.5))
            with game.lock:
                if game.grace_deadline != deadline:
                    return  # grace already finished some other way
        with game.lock:
            if game.grace_deadline == deadline:
                game.finish_grace()
                on_change()

    socketio.start_background_task(wait_then_finish)
