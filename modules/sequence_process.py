# modules/sequence_process.py

import time
from modules.gpio_driver import GPIODriver
from modules.sequence_loader import MidiEvent

class SequenceProcess:
    """Standalone worker process for sequence event triggering."""

    @staticmethod
    def run(events: list[MidiEvent], cycle_start: float) -> None:
        gpio_driver = None
        pins_needed = {ev.msg.note for ev in events if ev.msg.type == "note_on"}
        if pins_needed:
            gpio_driver = GPIODriver(list(pins_needed))

        print(f"[SequenceProcess] new cycle start = {cycle_start:.6f}")
        for ev in events:
            target = cycle_start + ev.time_s
            # ─── DEBUG: show every event up-front ───
            print(f"[DBG-schedule] t={ev.time_s:7.3f}s  note={getattr(ev.msg,'note','-'):>3}  "
                f"track={ev.track}")

            delay = target_time - time.monotonic()
            if delay > 0:
                time.sleep(delay)

            # ─── DEBUG: show when it really fires ───
            print(f"[DBG-fire]     now={time.monotonic():.6f}  target={target:.6f}  "
                f"note={getattr(ev.msg,'note','-'):>3}")

            if ev.msg.type == "note_on":
                if gpio_driver:
                    gpio_driver.note_on(ev.msg.note, ev.msg.velocity)
            elif ev.msg.type == "note_off":
                if gpio_driver:
                    gpio_driver.note_off(ev.msg.note)

