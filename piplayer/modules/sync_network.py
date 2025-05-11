# modules/sync_network.py
import socket
import threading
import time
import struct

PORT = 5005
BROADCAST_IP = '255.255.255.255'
SYNC_INTERVAL = 0.02  # 20ms

class SyncMaster:
    def __init__(self):
        self.running = False

    def start(self):
        self.running = True
        thread = threading.Thread(target=self._broadcast_loop, daemon=True)
        thread.start()

    def _broadcast_loop(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        while self.running:
            now = time.monotonic()
            msg = struct.pack('d', now)  # 8-byte float
            sock.sendto(msg, (BROADCAST_IP, PORT))
            time.sleep(SYNC_INTERVAL)

    def stop(self):
        self.running = False


class SyncFollower:
    def __init__(self):
        self.offset = 0.0  # time correction
        self.running = False

    def start(self):
        self.running = True
        thread = threading.Thread(target=self._listen_loop, daemon=True)
        thread.start()

    def _listen_loop(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('', PORT))
        while self.running:
            data, _ = sock.recvfrom(1024)
            master_time = struct.unpack('d', data)[0]
            now = time.monotonic()
            drift = master_time - now
            # apply correction (e.g. low-pass filter)
            self.offset = 0.9 * self.offset + 0.1 * drift  # smooth
            print(f"[SYNC] Drift: {drift:.3f}, Adjusted offset: {self.offset:.3f}")

    def get_synced_time(self):
        return time.monotonic() + self.offset

    def stop(self):
        self.running = False
