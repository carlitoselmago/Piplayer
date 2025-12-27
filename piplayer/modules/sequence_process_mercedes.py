# modules/sequence_process.py

import time
import threading

from .gpio_driver import GPIODriver
from .http_switch_driver import HTTPSWITCHdriver
from .sequence_loader import MidiEvent

print(":::: MERCEDES VARIANT :::::::")


MAX_SWITCH_PER_GROUP = 1
CYCLE_TIME = 0.2


class GroupPowerManager:
    def __init__(self, drivers):
        self.drivers = [d for d in drivers if isinstance(d, HTTPSWITCHdriver)]
        self.running = False
        self.thread = None

    def start(self):
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self.loop, daemon=True)
        self.thread.start()
        print("[GROUP MANAGER] started")

    def stop(self):
        self.running = False

    def loop(self):
        while self.running:
            time.sleep(CYCLE_TIME)

            groups = {}
            for d in self.drivers:
                if d.electric_group is None:
                    continue
                groups.setdefault(d.electric_group, []).append(d)

            for gid, devices in groups.items():
                requested = [d for d in devices if d.requested_on]

                # if safe, just apply requested
                if len(requested) <= MAX_SWITCH_PER_GROUP:
                    for d in devices:
                        d.force_state(d.requested_on)
                    continue

                # too many → alternate
                now_idx = int(time.time() / CYCLE_TIME) % len(requested)

                allowed = requested[now_idx]

                for d in devices:
                    d.force_state(d is allowed)


class SequenceProcess:
    """Standalone worker process that triggers events using a shared clock."""

    @staticmethod
    def run(events: list[MidiEvent], time_fn, drivers: list) -> None:
        cycle_start = time_fn()

        manager = GroupPowerManager(drivers)
        manager.start()

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

        manager.stop()

        for driver in drivers:
            if hasattr(driver, "cleanup"):
                driver.cleanup()
