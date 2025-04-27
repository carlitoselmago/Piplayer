# modules/signal_controller.py

import threading
import time
from modules.sequence_loader import MidiEvent
from modules.gpio_driver import GPIODriver

class SignalController:
    """
    Lightweight event player for MIDI events.
    """

    def __init__(self, events: list[MidiEvent]):
        self.events = sorted(events, key=lambda e: e.time_s)
        self._thread: threading.Thread | None = None
        self._stop_requested: bool = False
        self._started: bool = False
        self._log: list[str] = []

        # Prepare the GPIO driver
        self.gpio_driver: GPIODriver | None = None
        self._prepare_gpio()

    def _prepare_gpio(self) -> None:
        """Analyze events and initialize GPIO driver if needed."""
        pins_needed = set()

        for ev in self.events:
            if ev.msg.type == "note_on":
                pins_needed.add(ev.msg.note)

        if pins_needed:
            print(f"[SignalController] Preparing GPIO for pins: {pins_needed}")
            self.gpio_driver = GPIODriver(list(pins_needed))

    # -------------------------------------------------------
    def start(self, reference_time: float) -> None:
        if self._started:
            return
        self._stop_requested = False
        self._thread = threading.Thread(
            target=self._run,
            args=(reference_time,),
            daemon=True
        )
        self._thread.start()
        self._started = True

    def wait_done(self) -> None:
        if self._thread:
            self._thread.join()

    def stop(self) -> None:
        self._stop_requested = True
        if self.gpio_driver:
            self.gpio_driver.cleanup()

    # -------------------------------------------------------
    def _run(self, reference_time: float) -> None:
        for ev in self.events:
            target_time = reference_time + ev.time_s

            while not self._stop_requested:
                now = time.monotonic()
                if now >= target_time:
                    self._fire(ev)
                    break
                time.sleep(0.001)

        self._started = False

    def _fire(self, ev: MidiEvent) -> None:
        if ev.msg.type == "note_on":
            msg = f"[{ev.time_s:7.3f}s] {ev.track:<10} → ON  note={ev.msg.note} vel={ev.msg.velocity}"
            self._log.append(msg)

            if self.gpio_driver:
                self.gpio_driver.note_on(ev.msg.note, ev.msg.velocity)

        elif ev.msg.type == "note_off":
            msg = f"[{ev.time_s:7.3f}s] {ev.track:<10} → OFF note={ev.msg.note}"
            self._log.append(msg)

            if self.gpio_driver:
                self.gpio_driver.note_off(ev.msg.note)
