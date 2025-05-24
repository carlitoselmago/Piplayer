# cli.py

import time
import argparse
import json
import multiprocessing
from typing import Optional

from .modules.audio_player import AudioPlayer     # uses follower=...
from .modules.terminal_gui import TerminalGUI
from .modules.sequence_loader import SequenceLoader
from .modules.sequence_process import SequenceProcess
from .modules.sync_network   import SyncMaster, SyncFollower



class PiPlayer:
    def __init__(
        self,
        audio_file: Optional[str] = None,
        sequence_file: Optional[str] = None,
        loop: bool = False,
        gui: bool = False,
        config_file: Optional[str] = None,
        mode: str = "local",               # local | master | follower
    ):
        self.audio_file   = audio_file
        self.sequence_file= sequence_file
        self.loop         = loop
        self.config_file  = config_file
        self.mode         = mode

        self.audio_player:   Optional[AudioPlayer]      = None
        self.sequence:       Optional[SequenceLoader]   = None
        self.gui:            Optional[TerminalGUI]      = None
        self.sequence_proc:  Optional[multiprocessing.Process] = None
        self.sync:           Optional[SyncFollower]     = None


        if self.audio_file:
            self.audio_player = AudioPlayer(self.audio_file)

        if self.sequence_file:
            self.sequence = SequenceLoader(self.sequence_file)


        self.sequence_duration = max(
            (ev.time_s for ev in self.sequence.events), default=0.0
        ) if self.sequence else 0.0


        # optional GUI prep  ︙ (unchanged) ︙
        if gui:
            track_events = {}

            # ( … same as before – omitted for brevity … )
            # keep all existing GUI code here
    # ────────────────────────────────────────────────────────

    def play(self) -> None:
        print("Starting PiPlayer…")
        if self.gui:
            self.gui.start()


        # create sync object
        if self.mode == "master":
            print("🧭  Sync Mode: MASTER")
            self.sync = SyncMaster()
            self.sync.start()
        elif self.mode == "follower":
            print("🎯  Sync Mode: FOLLOWER")
            self.sync = SyncFollower()
            self.sync.start()

            # ✅ Fix 3: Wait for actual sync packets to arrive
            print("[SyncFollower] Waiting for sync packets...")
            timeout = time.monotonic() + 5.0
            while time.monotonic() < timeout:
                if self.sync.has_sync():   # You’ll define this below
                    print("[SyncFollower] ✅ Sync lock acquired.")
                    break
                time.sleep(0.1)
            else:
                print("[SyncFollower] ❌ Timeout — no master detected. Exiting.")
                return  # or raise SystemExit(1)


        try:
            wait_for_sync = False
            wait_after_sync = False
            sync_timer = 0

            while True:
                if self.gui:
                    self.gui.reset()


                cycle_start_monotonic = time.monotonic()


                # ─── AUDIO ──────────────────────────────────────
                if self.audio_player:
                    if self.mode == "follower":
                        # pass whole follower object
                        self.audio_player.start(follower=self.sync)
                    else:
                        self.audio_player.start()         # local / master


                # ─── SEQUENCE (GPIO/MIDI) ──────────────────────

                if self.sequence:
                    fresh_events = list(self.sequence.events)
                    time_fn = self.sync.get_time if self.sync else time.monotonic
                    self.sequence_proc = multiprocessing.Process(
                        target=SequenceProcess.run,
                        args=(fresh_events, time_fn),
                        daemon=True
                    )
                    self.sequence_proc.start()


                # ─── MAIN LOOP ─────────────────────────────────

                while True:
                    now_mono = time.monotonic()

                    if self.gui:
                        self.gui.update(now_mono - cycle_start_monotonic)


                    # audio finished?
                    if self.audio_player and not self.audio_player.is_playing():
                        if self.loop:
                            if self.mode == "follower":
                                self.audio_player.start(follower=self.sync)
                            else:
                                self.audio_player.start()
                            cycle_start_monotonic = now_mono
                            continue
                        break

                    # sequence-only end?
                    if (not self.audio_player) and self.sequence:
                        t = (self.sync.get_time() if self.sync else now_mono) \
                            - cycle_start_monotonic
                        if t >= self.sequence_duration:
                            if self.loop:
                                fresh_events = list(self.sequence.events)
                                time_fn = self.sync.get_time if self.sync else time.monotonic
                                self.sequence_proc = multiprocessing.Process(
                                    target=SequenceProcess.run,
                                    args=(fresh_events, time_fn),
                                    daemon=True
                                )
                                self.sequence_proc.start()
                                cycle_start_monotonic = now_mono
                                continue

                            break

                    time.sleep(0.05)

                # graceful shutdown of cycle
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
    multiprocessing.set_start_method("fork", force=True)

    p = argparse.ArgumentParser(description="PiPlayer – audio + GPIO/MIDI player")
    p.add_argument("audio_file", nargs="?", default=None, help="Audio/Video file")
    p.add_argument("-s", "--sequence", help="Sequence file (MIDI)")
    p.add_argument("-l", "--loop", action="store_true", help="Loop playback")
    p.add_argument("-g", "--gui",  action="store_true", help="Show ASCII GUI")
    p.add_argument("--mode", choices=["local", "master", "follower"],
                   default="local", help="Clock mode")
    p.add_argument("--debug-midi", action="store_true",
                   help="Just dump note events and exit")
    args = p.parse_args()

    if args.debug_midi and args.sequence:
        SequenceLoader(args.sequence).debug_print()

        return

    PiPlayer(
        audio_file=args.audio_file,
        sequence_file=args.sequence,
        loop=args.loop,
        gui=args.gui,
        mode=args.mode,

    ).play()

