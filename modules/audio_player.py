import os
import sounddevice as sd
import soundfile as sf
import numpy as np


class AudioPlayer:
    """
    Lightweight WAV / MP3 player using sounddevice + soundfile.
    start()      – begins playback (non-blocking)
    wait_done()  – blocks until playback ends
    stop()       – aborts immediately
    """

    def __init__(self, file_path: str):
        if not os.path.exists(file_path):
            raise FileNotFoundError(file_path)

        # Read full file as float32 numpy array
        self.data, self.sr = sf.read(file_path, dtype="float32", always_2d=True)
        self.duration = len(self.data) / self.sr          # seconds, float

        self.playing: bool = False

    # ---------- public API ----------
    def start(self) -> None:
        """Begin playback (returns immediately)."""
        sd.stop()                                 # be sure nothing else runs
        sd.play(self.data, self.sr, blocking=False)
        self.playing = True

    def wait_done(self) -> None:
        """Block until current playback ends."""
        if self.playing:
            sd.wait()
            self.playing = False

    def stop(self) -> None:
        """Stop playback immediately."""
        if self.playing:
            sd.stop()
            self.playing = False
