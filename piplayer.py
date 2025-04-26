import time
import argparse
from modules.audio_player import AudioPlayer
from modules.terminal_gui import TerminalGUI
# from modules.sequence_loader import SequenceLoader
# from modules.signal_controller import SignalController


class PiPlayer:
    def __init__(
        self,
        audio_file: str | None = None,
        sequence_file: str | None = None,
        loop: bool = False,
        gui: bool = False,
    ):
        self.audio_file = audio_file
        self.sequence_file = sequence_file
        self.loop = loop

        # ---------- components ----------
        self.audio_player: AudioPlayer | None = None
        self.sequence = None
        self.signal_controller = None
        self.gui: TerminalGUI | None = None

        if self.audio_file:
            self.audio_player = AudioPlayer(self.audio_file)

        # Optional ASCII GUI
        if gui and self.audio_player:
            dur = self.audio_player.duration
            tracks = ["AUDIO"]
            # if self.sequence_file: tracks.extend(self.sequence.track_names)
            self.gui = TerminalGUI(dur, tracks)

        # Future: sequence / signal controller
        # if self.sequence_file:
        #     self.sequence = SequenceLoader(self.sequence_file)
        #     self.signal_controller = SignalController(self.sequence)

    # --------------------------------------------------------------------- #
    def play(self) -> None:
        print("Starting PiPlayer...")
        if self.gui:
            self.gui.start()

        try:
            while True:
                cycle_start = time.monotonic()

                if self.audio_player:
                    self.audio_player.start()
                if self.signal_controller:
                    self.signal_controller.start(cycle_start)

                # ----- monitoring loop -----
                while True:
                    now = time.monotonic() - cycle_start
                    if self.gui:
                        self.gui.update(now)

                    # Finished?  (time-based so it works with any backend)
                    if (not self.audio_player) or (now >= self.audio_player.duration):
                        break

                    time.sleep(0.02)  # 20 Hz check

                if self.audio_player:
                    self.audio_player.wait_done()
                if self.signal_controller:
                    self.signal_controller.wait_done()

                if not self.loop:
                    break

        except KeyboardInterrupt:
            print("\nStopping playback…")
            if self.audio_player:
                self.audio_player.stop()
            if self.signal_controller:
                self.signal_controller.stop()

        finally:
            if self.gui:
                self.gui.stop()


# ------------------------------------------------------------------------- #
def main() -> None:
    parser = argparse.ArgumentParser(
        description="PiPlayer – play audio and synchronized signals."
    )
    parser.add_argument("audio_file", help="Path to an audio file (WAV or MP3)")
    parser.add_argument("-s", "--sequence", help="Path to a sequence file")
    parser.add_argument("-l", "--loop", action="store_true", help="Loop playback")
    parser.add_argument("-g", "--gui", action="store_true", help="ASCII progress GUI")

    args = parser.parse_args()

    player = PiPlayer(
        audio_file=args.audio_file,
        sequence_file=args.sequence,
        loop=args.loop,
        gui=args.gui,
    )
    player.play()


if __name__ == "__main__":
    main()
