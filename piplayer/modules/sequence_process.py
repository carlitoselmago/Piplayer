# modules/sequence_process.py
import time
from .gpio_driver import GPIODriver
from .http_switch_driver import HTTPSWITCHdriver
from .sequence_loader import MidiEvent


class SequenceProcess:
    """Standalone worker process that triggers events using a shared clock."""

    @staticmethod
    def run(events: list[MidiEvent], time_fn, drivers: list) -> None:
        cycle_start = time_fn()

        for ev in events:
            target = cycle_start + ev.time_s
            delay = target - time_fn()

            if delay > 0:
                time.sleep(delay)

            for driver in drivers:
                if ev.msg.type == "note_on":
                    driver.note_on(ev.msg.note, ev.msg.velocity)
                elif ev.msg.type == "note_off":
                    driver.note_off(ev.msg.note)

        # cleanup (optional but correct)
        for driver in drivers:
            if hasattr(driver, "cleanup"):
                driver.cleanup()