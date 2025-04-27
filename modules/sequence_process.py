# modules/sequence_process.py
import time
from modules.gpio_driver import GPIODriver
from modules.sequence_loader import MidiEvent


class SequenceProcess:
    """Standalone worker process that triggers events by system clock."""

    @staticmethod
    def run(events: list[MidiEvent], cycle_start: float) -> None:
        # ────────── prepare GPIO ──────────
        pins_needed = {ev.msg.note for ev in events if ev.msg.type == "note_on"}
        gpio = GPIODriver(sorted(pins_needed)) if pins_needed else None

        # ────────── main loop ──────────
        for ev in events:
            target = cycle_start + ev.time_s

            # Sleep exactly the remaining time (no busy-loop, no extra break)
            delay = target - time.monotonic()
            if delay > 0:
                time.sleep(delay)

            # Fire the event
            if ev.msg.type == "note_on":
                if gpio:
                    gpio.note_on(ev.msg.note, ev.msg.velocity)
            elif ev.msg.type == "note_off":
                if gpio:
                    gpio.note_off(ev.msg.note)
