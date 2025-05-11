# modules/sync_network.py
import socket
import struct
import threading
import time

BROADCAST_PORT = 5005
SYNC_INTERVAL = 0.2  # seconds
ALPHA = 0.05         # smoothing factor for follower


class SyncMaster:
    def __init__(self, time_func):
        self.time_func = time_func
        self._stop = False
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._stop = False
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop = True
        if self._thread:
            self._thread.join()

    def _run(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            while not self._stop:
                now = self.time_func()
                message = struct.pack('d', now)
                sock.sendto(message, ('<broadcast>', BROADCAST_PORT))
                time.sleep(SYNC_INTERVAL)


class SyncFollower:
    def __init__(self):
        self._offset = 0.0
        self.drift = 0.0
        self._stop = False
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._stop = False
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop = True
        if self._thread:
            self._thread.join()

    def _listen_loop(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('', BROADCAST_PORT))
            sock.settimeout(1.0)

            while not self._stop:
                try:
                    data, _ = sock.recvfrom(1024)
                    recv_time = time.monotonic()
                    (master_time,) = struct.unpack('d', data)

                    # Estimate delay and drift
                    estimated_drift = recv_time - master_time
                    self.drift = estimated_drift
                    self._offset += ALPHA * estimated_drift

                except socket.timeout:
                    continue

    def get_synced_time(self) -> float:
        return time.monotonic() - self._offset
