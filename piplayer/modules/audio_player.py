# modules/audio_player.py

import subprocess
from pydub import AudioSegment

class AudioPlayer:
    """
    Audio player using mpv subprocess, with duration info via pydub.
    """

    def __init__(self, filename: str):
        self.filename = filename
        self.process: subprocess.Popen | None = None

        # Load duration only (no decoding needed)
        seg = AudioSegment.from_file(filename)
        self.duration = seg.duration_seconds

    def start(self, position: float = 0.0) -> None:
        self.stop()  # Stop previous if any
        args = [
            "mpv",
            "--no-terminal", "--quiet", "--audio-display=no",
            f"--start={position:.3f}",
            self.filename
        ]
        self.process = subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    def wait_done(self) -> None:
        if self.process:
            self.process.wait()

    def stop(self) -> None:
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.process.wait()

    def is_playing(self) -> bool:
        return self.process and self.process.poll() is None
