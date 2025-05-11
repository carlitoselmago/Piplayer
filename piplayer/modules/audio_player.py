import mpv
from pydub import AudioSegment
import time

class AudioPlayer:
    """
    Audio player using python-mpv for IPC control and real-time syncing.
    """

    def __init__(self, filename: str):
        self.filename = filename
        self.player = mpv.MPV(ytdl=False, osc=True, loglevel="info", log_handler=print)
        self.player.loadfile(filename)  # Load the file
        self.duration = AudioSegment.from_file(filename).duration_seconds

    def start(self, position: float = 0.0) -> None:
        """Start playback from a specific position."""
        self.player.play(self.filename)
        #self.player.seek(f"{position:.3f}", "absolute", "exact")

    def wait_done(self) -> None:
        """Wait until the audio finishes playing."""
        self.player.wait_for_playback()

    def stop(self) -> None:
        """Stop playback."""
        self.player.stop()

    def is_playing(self) -> bool:
        """Check if audio is still playing."""
        return self.player.playback_time is not None and self.player.playback_time < self.duration

    def seek(self, position: float) -> None:
        """Seek to a specific position in the audio."""
        self.player.seek(f"{position:.3f}", "absolute", "exact")
