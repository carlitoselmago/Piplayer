#!/usr/bin/env python3
# piplayer/cli.py
"""
PiPlayer main CLI.
Supports local / master / follower modes.
Follower prints drift every second and re-cues if absolute drift > 50 ms.
"""

import time
import math
import argparse
import json
import multiprocessing
from typing import Optional

from .modules.audio_player import AudioPlayer
from .modules.terminal_gui import TerminalGUI
from .modules.sequence_loader import SequenceLoader
from .modules.sequence_process import SequenceProcess
from .modules.sync_network import SyncMaster, SyncFollower

DRIFT_LIMIT    = 0.050   # seconds
RECUE_COOLDOWN = 1.0     # seconds between re-cues


class PiPlayer:
    def __init__(
        self,
        audio_file: Optional[str] = None,
        sequence_file: Optional[str] = None,
        loop: bool = False,
        gui: bool = False,
        config_file: Optional[str] = None,
        mode: str = "local",
    ):
        self.audio_file = audio_file
        self.sequence_file = sequence_file
        self.loop = loop
        self.config_file = config_file
        self.mode = mode

        self.audio_player: Optional[AudioPlayer] = None
        self.sequence: Optional[SequenceLoader] = None
        self.gui: Optional[TerminalGUI] = None
        self.sequence_proc: Optional[multiprocessing.Process] = None
        self.sync: Optional[SyncFollower] = None

        if self.audio_file:
            self.audio_player = AudioPlayer(self.audio_file)

        if self.sequence_file:
            self.sequence = SequenceLoader(self.sequence_file)

        if self.sequence and self.sequence.events:
            self.sequence_duration = max(ev.time_s for ev in self.sequence.events)
        else:
            self.sequence_duration = 0.0

        if gui:
            self._init_gui()

    def _init_gui(self) -> None:
        track_events = {}
        audio_duration = 0.0
        if self.audio_player:
            track_events["audio"] = []
            audio_duration = self.audio_player.duration

        midi_duration = 0.0
        if self.sequence:
            active_tracks = self.sequence.track_names
            if self.config_file:
                with open(self.config_file) as f:
                    cfg = json.load(f).get("track_mappings", {})
                    active_tracks = [t for t in active_tracks if cfg.get(t)]

            for track in active_tracks:
                name = track if track.strip() else "--empty--"
                track_events[name] = [
                    ev.time_s for ev in self.sequence.events
                    if ev.track == track and ev.msg.type == "note_on"
                ]

            if self.sequence.events:
                midi_duration = max(ev.time_s for ev in self.sequence.events)

        total_duration = max(audio_duration, midi_duration)
        if total_duration > 0:
            self.gui = TerminalGUI(total_duration, track_events)

    def play(self) -> None:
        print("Starting PiPlayer…")
        if self.gui:
            self.gui.start()

        if self.mode == "master":
            self.sync = SyncMaster(self.get_time)
            self.sync.start()
            print("🧭  SYNC: master")
        elif self.mode == "follower":
            self.sync = SyncFollower()
            self.sync.start()
            print("🎯  SYNC: follower")

        try:
            while True:
                if self.gui:
                    self.gui.reset()

                cycle_start = self.get_time()

                if self.audio_player:
                    self.audio_player.start()

                if self.sequence:
                    fresh_events = list(self.sequence.events)
                    self.sequence_proc = multiprocessing.Process(
                        target=SequenceProcess.run,
                        args=(fresh_events, cycle_start),
                        daemon=True
                    )
                    self.sequence_proc.start()

                while True:
                    now_play = self.get_time() - cycle_start

                    if self.gui:
                        self.gui.update(now_play)

                    if isinstance(self.sync, SyncFollower):
                        drift = self.sync.drift
                        if int(self.get_time()) != int(self.get_time() - 0.2):
                            print(f"[drift] {drift:+.4f} s")

                        now_t = self.get_time()
                        if (abs(drift) > DRIFT_LIMIT and
                            now_t - getattr(self, "_last_correction", 0.0) > RECUE_COOLDOWN):

                            new_pos = now_t % self.audio_player.duration
                            print(f"[re-cue] drift {drift:+.3f}s → seek {new_pos:.3f}s")

                            self.audio_player.start(seek=new_pos)

                            if self.sequence and self.sequence.events:
                                fresh = list(self.sequence.events)
                                self.sequence_proc = multiprocessing.Process(
                                    target=SequenceProcess.run,
                                    args=(fresh, self.get_time() - new_pos),
                                    daemon=True
                                )
                                self.sequence_proc.start()


                            cycle_start = self.get_time() - new_pos
                            self._last_correction = now_t
                            continue

                    if self.audio_player and not self.audio_player.is_playing():
                        if self.loop:
                            self.audio_player.start()
                            cycle_start = self.get_time()
                            continue
                        else:
                            break

                    if not self.audio_player and self.sequence:
                        if now_play >= self.sequence_duration:
                            if self.loop:
                                fresh_events = list(self.sequence.events)
                                self.sequence_proc = multiprocessing.Process(
                                    target=SequenceProcess.run,
                                    args=(fresh_events, self.get_time()),
                                    daemon=True
                                )
                                self.sequence_proc.start()
                                cycle_start = self.get_time()
                                continue
                            else:
                                break

                    time.sleep(0.02)

                if self.audio_player:
                    self.audio_player.wait_done()
                if self.sequence_proc:
                    self.sequence_proc.terminate()
                    self.sequence_proc.join()
                    self.sequence_proc = None

                if not self.loop:
                    break

        except KeyboardInterrupt:
            print("\nStopping playback…")
            if self.audio_player:
                self.audio_player.stop()
            if self.sequence_proc:
                self.sequence_proc.terminate()
                self.sequence_proc.join()

        finally:
            if self.gui:
                self.gui.stop()
            if self.sync:
                self.sync.stop()

    def get_time(self) -> float:
        if isinstance(self.sync, SyncFollower):
            return self.sync.get_synced_time()
        return time.monotonic()


def main() -> None:
    multiprocessing.set_start_method("fork", force=True)

    parser = argparse.ArgumentParser(
        description="PiPlayer – audio + GPIO/MIDI playback with optional network sync"
    )
    parser.add_argument("audio_file", nargs="?", default=None,
                        help="Audio file (WAV/MP3)")
    parser.add_argument("-s", "--sequence", help="Sequence file (MIDI)")
    parser.add_argument("-l", "--loop", action="store_true",
                        help="Loop playback indefinitely")
    parser.add_argument("-g", "--gui", action="store_true",
                        help="Show ASCII progress GUI")
    parser.add_argument("--mode", choices=["local", "master", "follower"],
                        default="local", help="Sync mode (default=local)")
    parser.add_argument("--debug-midi", action="store_true",
                        help="Print note events and exit")

    args = parser.parse_args()

    if args.debug_midi:
        seq = SequenceLoader(args.sequence)
        seq.debug_print()
        return

    player = PiPlayer(
        audio_file=args.audio_file,
        sequence_file=args.sequence,
        loop=args.loop,
        gui=args.gui,
        mode=args.mode,
    )
    player.play()


if __name__ == "__main__":
    main()
