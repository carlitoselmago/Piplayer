# modules/audio_player.py

import subprocess
import socket
import json
import os
import time
from pydub import AudioSegment

class AudioPlayer:
    """
    Audio player using mpv with IPC control for real-time syncing.
    """

    def __init__(self, filename: str):
        self.filename = filename
        self.process: subprocess.Popen | None = None
        self.duration = AudioSegment.from_file(filename).duration_seconds
        self.socket_path = "/tmp/mpv_socket"
        self.sock: socket.socket | None = None

    def start(self, position: float = 0.0) -> None:
        self.stop()  # Ensure any previous player is killed

        if os.path.exists(self.socket_path):
            os.remove(self.socket_path)

        args = [
            "mpv",
            "--no-terminal",
            "--quiet",
            "--audio-display=no",
            f"--start={position:.3f}",
            f"--input-ipc-server={self.socket_path}",
            self.filename
        ]

        self.process = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Wait for mpv to create the socket and become ready
        for _ in range(50):  # try for up to ~2.5 sec
            if os.path.exists(self.socket_path):
                try:
                    self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    self.sock.connect(self.socket_path)
                    return
                except ConnectionRefusedError:
                    time.sleep(0.05)
            time.sleep(0.05)

        print("⚠️  mpv IPC socket not available")
        self.sock = None

    def stop(self) -> None:
        if self.sock:
            try:
                self.sock.close()
            except OSError:
                pass
            self.sock = None

        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.process.wait()

    def wait_done(self) -> None:
        if self.process:
            self.process.wait()

    def is_playing(self) -> bool:
        return self.process and self.process.poll() is None

    def seek(self, seconds: float) -> None:
        if not self.sock:
            return
        try:
            msg = {"command": ["seek", seconds, "absolute"]}
            self.sock.sendall((json.dumps(msg) + "\n").encode("utf-8"))
        except (BrokenPipeError, OSError):
            print("⚠️  Could not send seek command to mpv")
