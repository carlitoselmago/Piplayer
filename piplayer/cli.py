# cli.py

import time
import argparse
import json
import multiprocessing
from typing import Optional
from .modules.audio_player import AudioPlayer
from .modules.terminal_gui import TerminalGUI
from .modules.sequence_loader import SequenceLoader
from .modules.sequence_process import SequenceProcess
from .modules.sync_network import SyncMaster, SyncFollower

SYNC_TOLERANCE = 0.05
SYNC_GRACE_TIME = 3.0
SYNC_JUMP_AHEAD = 0.25


class PiPlayer:
    def __init__(
        self,
        audio_file: Optional[str] = None,
        sequence_file: Optional[str] = None,
        loop: bool = False,
        gui: bool = False,
        config_file: Optional[str] = None,
        mode: Optional[str] = None,
    ):
        self.audio_file = audio_file
        self.sequence_file = sequence_file
        self.loop = loop
        self.config_file = config_file
        self.mode = mode  # "master", "follower", or None
        self.sync: Optional[SyncMaster | SyncFollower] = None

        self.audio_player: Optional[AudioPlayer] = None
        self.sequence: Optional[SequenceLoader] = None
        self.gui: Optional[TerminalGUI] = None
        self.sequence_proc: Optional[multiprocessing.Process] = None

        if self.audio_file:
            self.audio_player = AudioPlayer(self.audio_file)

        if self.sequence_file:
            self.sequence = SequenceLoader(self.sequence_file)

        if self.sequence and self.sequence.events:
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

        if self.mode == "follower":
            print("🎯 Sync Mode: FOLLOWER")
            self.sync = SyncFollower()
            self.sync.start()

    def play(self) -> None:
        print("Starting PiPlayer...")
        if self.gui:
            self.gui.start()

        try:
            wait_for_sync = False
            wait_after_sync = False
            sync_timer = 0

            while True:
                if self.gui:
                    self.gui.reset()

                cycle_start = self.get_time()

                if self.audio_player:
                    self.audio_player.start()

                    if self.mode == "master" and self.sync is None:
                        print("🧭 Sync Mode: MASTER")
                        self.sync = SyncMaster(self.audio_player.get_position)
                        self.sync.start()

                if self.sequence:
                    fresh_events = list(self.sequence.events)
                    self.sequence_proc = multiprocessing.Process(
                        target=SequenceProcess.run,
                        args=(fresh_events, cycle_start),
                        daemon=True
                    )
                    self.sequence_proc.start()

                while True:
                    if self.gui:
                        now = self.get_time() - cycle_start
                        self.gui.update(now)

                    # Sync follower logic
                    if self.mode == "follower" and self.audio_player and isinstance(self.sync, SyncFollower):
                        local_pos = self.audio_player.get_position()
                        master_time = self.sync.get_synced_time()
                        drift = master_time - local_pos
                        now = time.monotonic()

                        if wait_for_sync:
                            if abs(drift) - (now - sync_timer) < 0:
                                print("[sync] playback resumes")
                                self.audio_player.resume()
                                wait_for_sync = False
                                wait_after_sync = now
                            else:
                                continue

                        if wait_after_sync and now - wait_after_sync < SYNC_GRACE_TIME:
                            continue

                        if abs(drift) > SYNC_TOLERANCE and local_pos > SYNC_GRACE_TIME:
                            print(f"[sync] jump to {master_time + SYNC_JUMP_AHEAD:.2f}s (drift={drift:.3f}s)")
                            self.audio_player.pause()
                            self.audio_player.seek(master_time + SYNC_JUMP_AHEAD)
                            wait_for_sync = True
                            sync_timer = now
                        else:
                            print(f"[drift] {drift:+.3f} s")

                    # End conditions
                    if self.audio_player and not self.audio_player.is_playing():
                        break

                    if not self.audio_player and self.sequence:
                        now = self.get_time() - cycle_start
                        if now >= self.sequence_duration:
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
    multiprocessing.set_start_method('fork', force=True)

    parser = argparse.ArgumentParser(
        description="PiPlayer – Play audio and synchronized GPIO/MIDI signals."
    )
    parser.add_argument("audio_file", nargs="?", default=None,
                        help="Path to an audio file (WAV or MP3)")
    parser.add_argument("-s", "--sequence", help="Path to a sequence file (MIDI)")
    parser.add_argument("-l", "--loop", action="store_true", help="Loop playback indefinitely")
    parser.add_argument("-g", "--gui", action="store_true", help="Show ASCII progress GUI")
    parser.add_argument("--debug-midi", action="store_true",
                        help="Print all Note events in the MIDI file and exit")
    parser.add_argument("--mode", choices=["master", "follower"], default=None,
                        help="Run in master or follower sync mode")

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
