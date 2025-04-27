# modules/signal_controller.py

from modules.sequence_loader import MidiEvent
from modules.gpio_driver import GPIODriver
from modules.audio_player import AudioPlayer

class SignalController:
    """
    Sequence controller that fires events directly based on playback time.
    """

    def __init__(self, events: list[MidiEvent], audio_player: AudioPlayer | None = None):
        self.events = sorted(events, key=lambda e: e.time_s)
        self.audio_player = audio_player
        self.log: list[str] = []

        # Prepare GPIO driver
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

    def fire(self, ev: MidiEvent) -> None:
        """Immediately fire an event."""
        if ev.msg.type == "note_on":
            msg = f"[{ev.time_s:7.3f}s] {ev.track:<10} → ON  note={ev.msg.note} vel={ev.msg.velocity}"
            self.log.append(msg)

            if self.gpio_driver:
                self.gpio_driver.note_on(ev.msg.note, ev.msg.velocity)

        elif ev.msg.type == "note_off":
            msg = f"[{ev.time_s:7.3f}s] {ev.track:<10} → OFF note={ev.msg.note}"
            self.log.append(msg)

            if self.gpio_driver:
                self.gpio_driver.note_off(ev.msg.note)
