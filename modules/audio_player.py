# modules/audio_player.py

from pydub import AudioSegment
import simpleaudio as sa
import time

class AudioPlayer:
    """
    Simple audio player for WAV and MP3 using pydub and simpleaudio.
    """

    def __init__(self, filename: str):
        self.filename = filename
        self.seg = AudioSegment.from_file(filename)
        self._play_obj: sa.PlayObject | None = None
        self._start_time: float | None = None

        self.duration = self.seg.duration_seconds  # total duration in seconds

    def start(self) -> None:
        """Start playing the audio."""
        raw_data = self.seg.raw_data
        num_channels = self.seg.channels
        bytes_per_sample = self.seg.sample_width
        sample_rate = self.seg.frame_rate

        wave_obj = sa.WaveObject(
            raw_data,
            num_channels=num_channels,
            bytes_per_sample=bytes_per_sample,
            sample_rate=sample_rate
        )
        self._play_obj = wave_obj.play()
        self._start_time = time.monotonic()

    def wait_done(self) -> None:
        """Wait until the audio finishes."""
        if self._play_obj:
            self._play_obj.wait_done()

    def stop(self) -> None:
        """Stop playback."""
        if self._play_obj:
            self._play_obj.stop()

    def get_position(self) -> float:
        """Return the current playback position in seconds."""
        if self._start_time is None:
            return 0.0
        return time.monotonic() - self._start_time
