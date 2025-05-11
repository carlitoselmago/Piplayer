# modules/audio_player.py
import subprocess
from pydub import AudioSegment
import time

class AudioPlayer:
    """
    Simple audio player using mpv subprocess for better sync reliability.
    Supports seeking and monitoring playback status.
    """
    def __init__(self, filename: str):
        self.filename = filename
        self.seg = AudioSegment.from_file(filename)
        self.duration = self.seg.duration_seconds
        self.process: subprocess.Popen | None = None
        self._start_time: float | None = None

    def start(self, seek: float = 0.0) -> None:
        """Start or restart playback at a given position."""
        self.stop()
        args = ["mpv", "--no-terminal", "--quiet", "--audio-display=no"]
        if seek > 0:
            args.append(f"--start={seek}")
        args.append(self.filename)

        self.process = subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        self._start_time = time.monotonic() - seek

    def is_playing(self) -> bool:
        """Returns True if the audio process is running."""
        return self.process and self.process.poll() is None

    def stop(self) -> None:
        """Terminate audio playback."""
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None

    def wait_done(self) -> None:
        """Block until playback completes."""
        if self.process:
            self.process.wait()

    def get_position(self) -> float:
        """Returns playback position in seconds."""
        if not self._start_time:
            return 0.0
        return time.monotonic() - self._start_time
