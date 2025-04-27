# piplayer.py

import time
import argparse
import json
import multiprocessing
from modules.audio_player import AudioPlayer
from modules.terminal_gui import TerminalGUI
from modules.sequence_loader import SequenceLoader
from modules.sequence_process import SequenceProcess

class PiPlayer:
    def __init__(
        self,
        audio_file: str | None = None,
        sequence_file: str | None = None,
        loop: bool = False,
        gui: bool = False,
        config_file: str | None = None,
    ):
        self.audio_file = audio_file
        self.sequence_file = sequence_file
        self.loop = loop
        self.config_file = config_file

        self.audio_player: AudioPlayer | None = None
        self.sequence: SequenceLoader | None = None
        self.gui: TerminalGUI | None = None
        self.sequence_proc: multiprocessing.Process | None = None

        if self.audio_file:
            self.audio_player = AudioPlayer(self.audio_file)

        if self.sequence_file:
            self.sequence = SequenceLoader(self.sequence_file)

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

                cycle_start = time.monotonic()

                if self.audio_player:
                    self.audio_player.start()

                if self.sequence:
                    self.sequence_proc = multiprocessing.Process(
                        target=SequenceProcess.run,
                        args=(self.sequence.events, cycle_start),
                        daemon=True
                    )
                    self.sequence_proc.start()

                # Monitoring loop
                while True:
                    now = time.monotonic() - cycle_start

                    if self.gui:
                        self.gui.update(now)

                    if self.audio_player and now >= self.audio_player.duration:
                        break

                    if not self.audio_player and now >= 9999:
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

# -------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="PiPlayer – play audio and synchronized signals."
    )
    parser.add_argument("audio_file", nargs="?", default=None,
                        help="Path to an audio file (WAV or MP3)")
    parser.add_argument("-s", "--sequence", help="Path to a sequence file")
    parser.add_argument("-l", "--loop", action="store_true", help="Loop playback")
    parser.add_argument("-g", "--gui", action="store_true", help="ASCII progress GUI")
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
    )
    player.play()

if __name__ == "__main__":
    multiprocessing.set_start_method('fork')
    main()
