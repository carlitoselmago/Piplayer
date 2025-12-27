# cli.py

import time
import argparse
import json
import multiprocessing
from typing import Optional, List

from .modules.audio_player import AudioPlayer
from .modules.terminal_gui import TerminalGUI
from .modules.sequence_loader import SequenceLoader
#from .modules.sequence_process import SequenceProcess
from .modules.sequence_process_mercedes import SequenceProcess
from .modules.sync_network import SyncMaster, SyncFollower

from .modules.gpio_driver import GPIODriver
from .modules.http_switch_driver import HTTPSWITCHdriver


class PiPlayer:
    def __init__(
        self,
        audio_file: Optional[str] = None,
        sequence_file: Optional[str] = None,
        loop: bool = False,
        gui: bool = False,
        config_file: Optional[str] = None,
        mode: str = "local",   # local | master | follower
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
        self.sync: Optional[SyncFollower | SyncMaster] = None

        self.drivers: List[object] = []

        if self.audio_file:
            self.audio_player = AudioPlayer(self.audio_file)

        if self.sequence_file:
            self.sequence = SequenceLoader(self.sequence_file)

        self.sequence_duration = max(
            (ev.time_s for ev in self.sequence.events), default=0.0
        ) if self.sequence else 0.0

        # ─── Load config and build drivers ──────────────────────────────
        if self.config_file:
            self._load_config_and_build_drivers()

        # ─── GUI prep ───────────────────────────────────────────────────
        if gui and self.sequence:
            track_events = {}
            for track in self.sequence.track_names:
                clean = track if track.strip() else "empty"
                track_events[clean] = [
                    ev.time_s for ev in self.sequence.events
                    if ev.track == track and ev.msg.type == "note_on"
                ]

            if self.audio_player:
                track_events["audio"] = []

            total_duration = max(
                self.audio_player.duration if self.audio_player else 0.0,
                self.sequence_duration
            )

            if total_duration > 0:
                self.gui = TerminalGUI(total_duration, track_events)

    # ──────────────────────────────────────────────────────────────────
    def _load_config_and_build_drivers(self) -> None:
        with open(self.config_file) as f:
            config = json.load(f)

        tracks_cfg = config.get("tracks", {})

        for track_name, cfg in tracks_cfg.items():
            proto = cfg.get("protocol", "NONE")

            if proto == "GPIO":
                # simple GPIO: note == pin
                notes = {
                    ev.msg.note
                    for ev in self.sequence.events
                    if ev.track == track_name and ev.msg.type == "note_on"
                }
                if notes:
                    self.drivers.append(GPIODriver(sorted(notes)))

            elif proto == "HTTP_SWITCH":
                ip = cfg.get("ip")
                electric_group = cfg.get("electric_group", 0)

                if not ip:
                    print(f"[Config Warning] HTTP_SWITCH track '{track_name}' has no IP")
                    continue

                # Track-level driver: all notes go to same IP
                self.drivers.append(
                    HTTPSWITCHdriver(
                        ip=ip,
                        electric_group=electric_group,
                        track=track_name,
                        mock=False
                    )
                )

                # Store metadata on driver for later use
                self.drivers[-1].track = track_name
                self.drivers[-1].ip = ip
                self.drivers[-1].electric_group = electric_group

            elif proto == "NONE":
                continue

            else:
                print(f"[Config Warning] Unknown protocol '{proto}' on track '{track_name}'")

    # ──────────────────────────────────────────────────────────────────
    def play(self) -> None:
        print("Starting PiPlayer…")
        if self.gui:
            self.gui.start()

        # ─── Sync setup ────────────────────────────────────────────────
        if self.mode == "master":
            print("🧭 Sync Mode: MASTER")
            self.sync = SyncMaster(self.audio_player.get_position if self.audio_player else None)
            self.sync.start()

        elif self.mode == "follower":
            print("🎯 Sync Mode: FOLLOWER")
            self.sync = SyncFollower()
            self.sync.start()

        try:
            while True:
                if self.gui:
                    self.gui.reset()

                cycle_start = time.monotonic()

                # ─── AUDIO ──────────────────────────────────────────────
                if self.audio_player:
                    if self.mode == "follower":
                        self.audio_player.start(follower=self.sync)
                    else:
                        self.audio_player.start()

                # ─── SEQUENCE ───────────────────────────────────────────
                if self.sequence:
                    events = list(self.sequence.events)
                    time_fn = self.sync.get_time if self.sync else time.monotonic

                    self.sequence_proc = multiprocessing.Process(
                        target=SequenceProcess.run,
                        args=(events, time_fn, self.drivers),
                        daemon=True
                    )
                    self.sequence_proc.start()

                # ─── MAIN LOOP ──────────────────────────────────────────
                while True:
                    now = time.monotonic()

                    if self.gui:
                        self.gui.update(now - cycle_start)

                    if self.audio_player and not self.audio_player.is_playing():
                        if self.loop:
                            if self.mode == "follower":
                                self.audio_player.start(follower=self.sync)
                            else:
                                self.audio_player.start()
                            cycle_start = now
                            continue
                        break

                    if not self.audio_player and self.sequence:
                        t = (self.sync.get_time() if self.sync else now) - cycle_start
                        if t >= self.sequence_duration:
                            break

                    time.sleep(0.05)

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


# ─────────────────────────────────────────────────────────────────────
def main() -> None:
    multiprocessing.set_start_method("fork", force=True)

    p = argparse.ArgumentParser(description="PiPlayer – audio + GPIO/MIDI player")
    p.add_argument("audio_file", nargs="?", default=None, help="Audio file")
    p.add_argument("-s", "--sequence", help="Sequence file (MIDI)")
    p.add_argument("-l", "--loop", action="store_true", help="Loop playback")
    p.add_argument("-c", "--config", help="Config file", required=True)
    p.add_argument("-g", "--gui", action="store_true", help="Show ASCII GUI")
    p.add_argument("--mode", choices=["local", "master", "follower"],
                   default="local", help="Clock mode")
    p.add_argument("--debug-midi", action="store_true",
                   help="Dump MIDI events and exit")
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
        config_file=args.config,
    ).play()


if __name__ == "__main__":
    main()
