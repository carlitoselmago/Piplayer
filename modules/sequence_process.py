# modules/sequence_process.py

import time
from modules.gpio_driver import GPIODriver
from modules.sequence_loader import MidiEvent

class SequenceProcess:
    """Standalone worker process for sequence event triggering."""

    @staticmethod
    @staticmethod
    def run(events: list[MidiEvent], cycle_start: float) -> None:
        gpio_driver = None
        pins_needed = set()

        for ev in events:
            if ev.msg.type == "note_on":
                pins_needed.add(ev.msg.note)

        if pins_needed:
            gpio_driver = GPIODriver(list(pins_needed))

        print(f"[SequenceProcess] New Cycle Start Time: {cycle_start:.3f}")

        for ev in events:
            target_time = cycle_start + ev.time_s
            print(f"[SequenceProcess] Scheduling event at {ev.time_s:.3f}s -> Absolute {target_time:.3f}")

            # Wait until target time
            while time.monotonic() < target_time:
                time.sleep(0.001)

            # Fire event
            if ev.msg.type == "note_on":
                print(f"[SequenceProcess] Firing ON: Track {ev.track} Note {ev.msg.note}")
                if gpio_driver:
                    gpio_driver.note_on(ev.msg.note, ev.msg.velocity)
            elif ev.msg.type == "note_off":
                print(f"[SequenceProcess] Firing OFF: Track {ev.track} Note {ev.msg.note}")
                if gpio_driver:
                    gpio_driver.note_off(ev.msg.note)

