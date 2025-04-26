# modules/signal_controller.py
import threading
import time
from modules.sequence_loader import MidiEvent


class SignalController:
    """
    Lightweight event player.

    Takes a list of MidiEvent objects, and schedules them
    relative to a given start time (aligned to audio playback).
    """

    def __init__(self, events: list[MidiEvent]):
        self.events = sorted(events, key=lambda e: e.time_s)
        self._thread: threading.Thread | None = None
        self._stop_requested: bool = False
        self._started: bool = False

    # -------------------------------------------------------
    def start(self, reference_time: float) -> None:
        """Start the event scheduler relative to reference_time."""
        if self._started:
            return  # already running
        self._stop_requested = False
        self._thread = threading.Thread(
            target=self._run,
            args=(reference_time,),
            daemon=True
        )
        self._thread.start()
        self._started = True

    def wait_done(self) -> None:
        """Block until all events have fired."""
        if self._thread:
            self._thread.join()

    def stop(self) -> None:
        """Stop immediately."""
        self._stop_requested = True

    # -------------------------------------------------------
    def _run(self, reference_time: float) -> None:
        """Worker thread that fires events at the correct time."""
        for ev in self.events:
            target_time = reference_time + ev.time_s

            # Wait until it's time to fire
            while not self._stop_requested:
                now = time.monotonic()
                if now >= target_time:
                    self._fire(ev)
                    break
                time.sleep(0.001)  # very tight poll (~1ms)

        self._started = False

    def _fire(self, ev: MidiEvent) -> None:
        """Fire an event. For now, just print it."""
        if ev.msg.type == "note_on":
            print(f"[{ev.time_s:7.3f}s] {ev.track:<10} → ON  note={ev.msg.note} vel={ev.msg.velocity}")
        elif ev.msg.type == "note_off":
            print(f"[{ev.time_s:7.3f}s] {ev.track:<10} → OFF note={ev.msg.note}")
