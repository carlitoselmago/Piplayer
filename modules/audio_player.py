# modules/audio_player.py

import simpleaudio as sa
from pydub import AudioSegment
import threading

class AudioPlayer:
    def __init__(self, file_path):
        self.file_path = file_path
        self.audio_segment = None
        self.play_obj = None
        self._load_audio()
        self._stop_requested = False

    def _load_audio(self):
        """Load audio file into memory."""
        print(f"Loading audio file: {self.file_path}")
        if self.file_path.lower().endswith(".wav"):
            self.audio_segment = AudioSegment.from_wav(self.file_path)
        elif self.file_path.lower().endswith(".mp3"):
            self.audio_segment = AudioSegment.from_mp3(self.file_path)
        else:
            raise ValueError("Unsupported audio format. Only WAV and MP3 are supported.")

    def start(self):
        """Start audio playback in a separate thread."""
        self._stop_requested = False
        threading.Thread(target=self._play_audio, daemon=True).start()

    def _play_audio(self):
        """Internal method to handle audio playback."""
        raw_data = self.audio_segment.raw_data
        sample_rate = self.audio_segment.frame_rate
        num_channels = self.audio_segment.channels
        bytes_per_sample = self.audio_segment.sample_width

        self.play_obj = sa.play_buffer(
            raw_data,
            num_channels,
            bytes_per_sample,
            sample_rate
        )

        # Wait until finished unless stop requested
        while self.play_obj.is_playing():
            if self._stop_requested:
                self.play_obj.stop()
                break

    def wait_done(self):
        """Block until audio playback is finished."""
        if self.play_obj:
            self.play_obj.wait_done()

    def stop(self):
        """Stop audio playback."""
        if self.play_obj and self.play_obj.is_playing():
            self._stop_requested = True
            self.play_obj.stop()

