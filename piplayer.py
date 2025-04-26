# piplayer.py

import time
import argparse
from modules.audio_player import AudioPlayer
#from sequence_loader import SequenceLoader
#from signal_controller import SignalController

class PiPlayer:
    def __init__(self, audio_file: str = None, sequence_file: str = None, loop: bool = False):
        self.audio_file = audio_file
        self.sequence_file = sequence_file
        self.loop = loop
        
        self.audio_player = None
        self.sequence = None
        self.signal_controller = None

        # Initialize components if given
        if self.audio_file:
            self.audio_player = AudioPlayer(self.audio_file)
        
        if self.sequence_file:
            self.sequence = SequenceLoader(self.sequence_file)
            self.signal_controller = SignalController(self.sequence)

    def play(self):
        """Start playback of audio and signal sequence in sync."""
        print("Starting PiPlayer...")
        
        try:
            while True:
                start_time = time.monotonic()

                # Start audio if available
                if self.audio_player:
                    self.audio_player.start()

                # Start signal controller
                if self.signal_controller:
                    self.signal_controller.start(start_time)

                # Wait for audio to finish if there is audio
                if self.audio_player:
                    self.audio_player.wait_done()
                
                # If not looping, break
                if not self.loop:
                    break

                print("Looping playback...")

        except KeyboardInterrupt:
            print("Stopping playback...")

            if self.audio_player:
                self.audio_player.stop()
            if self.signal_controller:
                self.signal_controller.stop()

            print("Playback stopped.")

def main():
    parser = argparse.ArgumentParser(description="PiPlayer - Play audio and synchronized signals on a Raspberry Pi.")
    parser.add_argument("audio_file", nargs="?", default=None, help="Path to the audio file (e.g., audio.wav)")
    parser.add_argument("--sequence", "-s", help="Path to the sequence file (e.g., signals.mid or signals.csv)")
    parser.add_argument("--loop", "-l", action="store_true", help="Loop playback indefinitely")

    args = parser.parse_args()

    player = PiPlayer(
        audio_file=args.audio_file,
        sequence_file=args.sequence,
        loop=args.loop
    )
    player.play()

if __name__ == "__main__":
    main()
