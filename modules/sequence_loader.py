# modules/sequence_loader.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List
from mido import MidiFile, Message, MetaMessage


@dataclass
class MidiEvent:
    time_s: float
    track: str
    msg: Message | MetaMessage


class SequenceLoader:
    """
    Loads a Standard MIDI File and returns an **absolute-time-sorted**
    list of MidiEvent objects (seconds since start).
    """

    def __init__(self, midi_path: str):
        self.midi_path = midi_path
        self.events: List[MidiEvent] = []
        self.track_names: List[str] = []

        self._load()

    # -----------------------------------------------------------------
    def _load(self) -> None:
        mid = MidiFile(self.midi_path)
        ticks_per_beat = mid.ticks_per_beat
        default_tempo = 500_000          # 120 BPM

        # Each track keeps its own running “ticks” counter
        abs_ticks = [0] * len(mid.tracks)
        current_tempo = default_tempo

        # Keep a name for every track (may be overwritten by “track_name”)
        for i, trk in enumerate(mid.tracks):
            self.track_names.append(f"Track-{i}")

        # Walk *all* tracks simultaneously
        # We step through messages in chronological order by repeatedly
        # picking the track whose “next message” has the smallest delta.
        iterators = [iter(t) for t in mid.tracks]
        pointers  = [next(it, None) for it in iterators]

        while any(msg is not None for msg in pointers):
            # Which track’s next message happens earliest?
            next_track = min(
                (ti for ti, msg in enumerate(pointers) if msg is not None),
                key=lambda ti: abs_ticks[ti] + pointers[ti].time
            )
            msg = pointers[next_track]
            abs_ticks[next_track] += msg.time

            # Tempo changes are global (apply to ALL following tracks)
            if msg.type == "set_tempo":
                current_tempo = msg.tempo

            # Track name (cosmetic)
            if msg.type == "track_name":
                self.track_names[next_track] = msg.name.strip()

            # Convert *that* track’s current absolute tick value → seconds
            secs = (abs_ticks[next_track] / ticks_per_beat) * (current_tempo / 1_000_000)

            # Store musical events
            if msg.type in ("note_on", "note_off"):
                self.events.append(
                    MidiEvent(secs, self.track_names[next_track], msg)
                )

            # Advance to that track’s next message
            pointers[next_track] = next(iterators[next_track], None)

        # Finally sort (safety) so events are strictly chronological
        self.events.sort(key=lambda e: e.time_s)

    # -----------------------------------------------------------------
    def debug_print(self) -> None:
        print(f"\nMIDI DEBUG: {len(self.events)} note events\n" + "-" * 40)
        for ev in self.events:
            if ev.msg.type == "note_on":
                print(f"{ev.time_s:7.3f}s  {ev.track:<10} NOTE-ON  "
                      f"note={ev.msg.note:<3} vel={ev.msg.velocity}")
            else:
                print(f"{ev.time_s:7.3f}s  {ev.track:<10} note-off "
                      f"note={ev.msg.note}")
        print("-" * 40 + "\n")
