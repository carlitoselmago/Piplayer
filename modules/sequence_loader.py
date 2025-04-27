# modules/sequence_loader.py

from dataclasses import dataclass
from mido import MidiFile, Message, MetaMessage

@dataclass
class MidiEvent:
    time_s: float
    track: str
    msg: Message | MetaMessage

class SequenceLoader:
    """Loads a MIDI file and extracts time-aligned events."""
    
    def __init__(self, filename: str):
        self.filename = filename
        self.events: list[MidiEvent] = []
        self.track_names: list[str] = []
        self._load()

    def _load(self) -> None:
        mid = MidiFile(self.filename)
        tempo = 500000  # default tempo (us per beat)
        time_s = 0.0
        name_by_track = {}
        
        for i, track in enumerate(mid.tracks):
            name = f"Track-{i}"
            self.track_names.append(name)
            name_by_track[i] = name

        for i, track in enumerate(mid.tracks):
            abs_time = 0.0
            for msg in track:
                abs_time += msg.time

                if msg.type == "set_tempo":
                    tempo = msg.tempo

                if msg.type == "track_name":
                    name_by_track[i] = msg.name.strip()

                if msg.type in ("note_on", "note_off"):
                    seconds = (abs_time * tempo) / 1_000_000 / mid.ticks_per_beat
                    event = MidiEvent(
                        time_s=seconds,
                        track=name_by_track[i],
                        msg=msg
                    )
                    self.events.append(event)

    def debug_print(self) -> None:
        print(f"\nMIDI DEBUG: {len(self.events)} note events")
        print("----------------------------------------")
        for ev in self.events:
            if ev.msg.type == "note_on":
                print(f"{ev.time_s:7.3f}  {ev.track:<10}  NOTE-ON  ch={ev.msg.channel+1} note={ev.msg.note} vel={ev.msg.velocity}")
            elif ev.msg.type == "note_off":
                print(f"{ev.time_s:7.3f}  {ev.track:<10}  note-off ch={ev.msg.channel+1} note={ev.msg.note}")
        print("----------------------------------------\n")
