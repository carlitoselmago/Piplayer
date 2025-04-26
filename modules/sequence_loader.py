# modules/sequence_loader.py
from __future__ import annotations
import mido
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class MidiEvent:
    time_s: float            # absolute time in seconds
    track: str               # track name (or "Track-N")
    msg: mido.Message        # the raw mido message


class SequenceLoader:
    """
    Loads a SMF (.mid) file, converts delta times → absolute seconds,
    keeps events sorted chronologically.
    """

    def __init__(self, midi_path: str):
        self.midi_path = midi_path
        self.events: list[MidiEvent] = []
        self.track_names: list[str] = []
        self._load()

    # ------------------------------------------------------------
    def _load(self) -> None:
        mid = mido.MidiFile(self.midi_path)

        # Defaults (can be overridden by SetTempo)
        tempo = 500_000                     # µs per beat = 120 BPM
        ticks_per_beat = mid.ticks_per_beat

        # Collect track names
        name_by_track = {}


        for i, track in enumerate(mid.tracks):
            for msg in track:
                if msg.type == "track_name":
                    name_by_track[i] = msg.name
                    break

        # Fallback: assign default names if any tracks are unnamed
        self.track_names = [
            name_by_track.get(i, f"Track-{i}") for i in range(len(mid.tracks))
        ]

        # Walk all tracks side-by-side
        absolute_time_ticks = [0] * len(mid.tracks)
        iterators = [iter(t) for t in mid.tracks]
        pointers = [next(it, None) for it in iterators]

        while any(p is not None for p in pointers):
            # Select the next earliest event across tracks
            next_track = min(
                (ti for ti, msg in enumerate(pointers) if msg is not None),
                key=lambda ti: absolute_time_ticks[ti] + pointers[ti].time,
            )
            msg = pointers[next_track]
            absolute_time_ticks[next_track] += msg.time

            # Handle tempo changes
            if msg.type == "set_tempo":
                tempo = msg.tempo

            # Convert ticks → seconds
            time_s = (absolute_time_ticks[next_track] / ticks_per_beat) * (tempo / 1_000_000)

            # Store only musical events for now
            if msg.type in ("note_on", "note_off"):
                self.events.append(
                    MidiEvent(time_s, name_by_track[next_track], msg)
                )

            # Advance pointer in that track
            pointers[next_track] = next(iterators[next_track], None)

        # Sort (should already be sorted, but just in case)
        self.events.sort(key=lambda e: e.time_s)

    # ------------------------------------------------------------
    def debug_print(self) -> None:
        print(f"\nMIDI DEBUG: {len(self.events)} note events\n" + "-" * 40)
        for ev in self.events:
            t = f"{ev.time_s:7.3f}"
            if ev.msg.type == "note_on":
                print(f"{t}  {ev.track:<10} NOTE-ON  ch={ev.msg.channel+1} "
                      f"note={ev.msg.note}  vel={ev.msg.velocity}")
            else:
                print(f"{t}  {ev.track:<10} note-off ch={ev.msg.channel+1} note={ev.msg.note}")
        print("-" * 40 + "\n")
