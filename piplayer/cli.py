#!/usr/bin/env python3

import time
import argparse
import json
import multiprocessing
from typing import Optional

from piplayer.modules.audio_player import AudioPlayer
from piplayer.modules.terminal_gui import TerminalGUI
from piplayer.modules.sequence_loader import SequenceLoader
from piplayer.modules.sequence_process import SequenceProcess
from piplayer.modules.sync_network import SyncMaster, SyncFollower


class PiPlayer:
    def __init__(
        self,
        audio_file: Optional[str] = None,
        sequence_file: Optional[str] = None,
        loop: bool = False,
        gui: bool = False,
        config_file: Optional[str] = None,
        master: bool = False,
        follow: bool = False,
    ):
        self.audio_file = audio_file
        self.sequence_file = sequence_file
        self.loop = loop
        self.config_file = config_file
        self.master = master
        self.follow = follow

        self.audio_player: Optional[AudioPlayer] = None
        self.sequence: Optional[SequenceLoader] = None
        self.gui: Optional[TerminalGUI] = None
        self.sequence_proc: Optional[multiprocessing.Process] = None

        self.sync = None
        if self.master:
            self.sync = SyncMaster()
            self.sync.start()
            self.get_time = time.monotonic
        elif self.follow:
            self.sync = SyncFollower()
            self.sync.start()
            self.get_time = self.sync.get_synced_time
        else:
            self.get_time = time.monotonic

        if self.audio_file:
            self.audio_player = AudioPlayer(self.audio_file)

        if self.sequence_file:
            self.sequence = SequenceLoader(self.sequence_file)

        if self.sequence:
            self.sequence_duration = max(ev.time_s for ev in self.sequence.events)
        else:
            self.sequence_duration = 0.0

        if gui:
            track_events = {}

            if self.audio_player:
                track_events["audio"] = []
                audio_duration = self.audio_player.duration
            else:
                audio_duration = 0.0

            midi_duration = 0.0
            if self.sequence:
                active_tracks = self.sequence.track_names

                if self.config_file:
                    with open(self.config_file) as f:
                        config = json.load(f)
                        mappings = config.get("track_mappings", {})
                        active_tracks = [t for t in active_tracks if mappings.get(t)]

                for track in active_tracks:
                    clean_track = track if track.strip() else "empty"
                    track_events[clean_track] = [
                        ev.time_s for ev in self.sequence.events
                        if ev.track == track and ev.msg.type == "note_on"
                    ]

                if self.sequence.events:
                    midi_duration = max(ev.time_s for ev in self.sequence.events)

            total_duration = max(audio_duration, midi_duration)

            if total_duration > 0:
                self.gui = TerminalGUI(total_duration, track_events)

    def play(self) -> None:
        print("Starting PiPlayer...")
        if self.gui:
            self.gui.start()

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

                # Main monitoring loop
                while True:
                    now = self.get_time() - cycle_start

                    if self.gui:
                        self.gui.update(now)

                    if self.audio_player and not self.audio_player.is_playing():
                        if self.loop:
                            self.audio_player.start()
                            cycle_start = self.get_time()
                            continue
                        else:
                            break

                    if not self.audio_player and self.sequence:
                        if now >= self.sequence_duration:
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

                    if self.follow and self.audio_player and self.audio_player.is_playing():
                        self.audio_player.seek(self.get_time())

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


# -------------------------------------------------------------------
def main() -> None:
    multiprocessing.set_start_method('fork', force=True)

    parser = argparse.ArgumentParser(
        description="PiPlayer – Play audio and synchronized GPIO/MIDI signals."
    )
    parser.add_argument("audio_file", nargs="?", default=None,
                        help="Path to an audio file (WAV or MP3)")
    parser.add_argument("-s", "--sequence", help="Path to a sequence file (MIDI)")
    parser.add_argument("-l", "--loop", action="store_true", help="Loop playback indefinitely")
    parser.add_argument("-g", "--gui", action="store_true", help="Show ASCII progress GUI")
    parser.add_argument("--master", action="store_true", help="Run as time sync master")
    parser.add_argument("--follow", action="store_true", help="Follow time sync from network")
    parser.add_argument("--debug-midi", action="store_true",
                        help="Print all Note events in the MIDI file and exit")

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
        master=args.master,
        follow=args.follow
    )
    player.play()
