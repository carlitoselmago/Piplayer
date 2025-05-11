# modules/sync_network.py
import socket
import struct
import threading
import time

BROADCAST_PORT = 5005
GRACE_MS = 50
LATENCY_ALPHA = 0.1

def get_millis() -> int:
    return int(time.time() * 1000)

class SyncMaster:
    def __init__(self, time_func=None):
        self._stop = False
        self._thread = None
        self.time_func = time_func or (lambda: time.monotonic())
        self.start_time = get_millis()

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
                now = get_millis()
                elapsed = int((now - self.start_time))
                packet = struct.pack('!QQ', elapsed, now)
                sock.sendto(packet, ('255.255.255.255', BROADCAST_PORT))
                time.sleep(1)


class SyncFollower:
    def __init__(self):
        self.drift_correction = 0
        self.start_time = get_millis()
        self.smoothed_latency = 0
        self.initialized = False
        self.lock = threading.Lock()
        self._stop = False
        self._thread = None

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
                    t_recv = get_millis()
                    data, _ = sock.recvfrom(1024)
                    t_now = get_millis()

                    elapsed_master, t_sent = struct.unpack('!QQ', data)
                    sample_latency = (t_now - t_sent) // 2

                    if not self.initialized:
                        self.smoothed_latency = sample_latency
                        corrected_master = elapsed_master + self.smoothed_latency
                        self.drift_correction = corrected_master - (t_now - self.start_time)
                        self.initialized = True
                        print(f"[SYNC] Initial drift correction: {self.drift_correction} ms")
                        continue

                    self.smoothed_latency = int(LATENCY_ALPHA * sample_latency + (1 - LATENCY_ALPHA) * self.smoothed_latency)
                    corrected_master = elapsed_master + self.smoothed_latency
                    local_elapsed = t_now - self.start_time + self.drift_correction
                    drift = corrected_master - local_elapsed

                    if abs(drift) > GRACE_MS:
                        with self.lock:
                            self.drift_correction += drift
                        print(f"[SYNC] Adjusted by {drift} ms (latency={self.smoothed_latency} ms)")

                except (socket.timeout, struct.error):
                    continue

    def get_synced_time(self) -> float:
        now = get_millis()
        with self.lock:
            synced_time = (now - self.start_time + self.drift_correction) / 1000.0
        return synced_time
