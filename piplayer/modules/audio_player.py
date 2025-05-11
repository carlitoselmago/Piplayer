# modules/audio_player.py

from pydub import AudioSegment
import simpleaudio as sa
import time

class AudioPlayer:
    """
    Simple audio player for WAV and MP3 using pydub and simpleaudio.
    Supports start, stop, pause, resume, and seek.
    """

    def __init__(self, filename: str):
        self.filename = filename
        self.seg = AudioSegment.from_file(filename)
        self._play_obj: sa.PlayObject | None = None
        self._start_time: float | None = None
        self._paused_time: float | None = None
        self._pause_offset: float = 0.0

        self.duration = self.seg.duration_seconds  # total duration in seconds
        
    def start(self, seek: float = 0.0) -> None:
        """Start playing the audio from a specific time (default 0.0)."""
        self.stop()  # <-- Prevent overlapping by stopping previous playback

        segment = self.seg[seek * 1000:]
        raw_data = segment.raw_data
        num_channels = segment.channels
        bytes_per_sample = segment.sample_width
        sample_rate = segment.frame_rate

        wave_obj = sa.WaveObject(
            raw_data,
            num_channels=num_channels,
            bytes_per_sample=bytes_per_sample,
            sample_rate=sample_rate
        )
        self._play_obj = wave_obj.play()
        self._start_time = time.monotonic() - seek
        self._paused_time = None
        self._pause_offset = 0.0


    def wait_done(self) -> None:
        """Wait until the audio finishes."""
        if self._play_obj:
            self._play_obj.wait_done()

    def stop(self) -> None:
        """Stop playback."""
        if self._play_obj:
            self._play_obj.stop()
        self._start_time = None
        self._paused_time = None
        self._pause_offset = 0.0

    def pause(self) -> None:
        """Pause playback and store the current position."""
        if self._play_obj and self._play_obj.is_playing():
            self._play_obj.stop()
            self._paused_time = time.monotonic()
            self._pause_offset = self.get_position()

    def resume(self) -> None:
        """Resume playback from paused position."""
        if self._paused_time is not None:
            self.start(seek=self._pause_offset)

    def seek(self, position: float) -> None:
        """Seek to a specific position in seconds."""
        self.stop()
        self.start(seek=position)

    def get_position(self) -> float:
        """Return the current playback position in seconds."""
        if self._start_time is None:
            return 0.0
        return time.monotonic() - self._start_time

    def is_playing(self) -> bool:
        """Check if audio is currently playing."""
        return self._play_obj is not None and self._play_obj.is_playing()
