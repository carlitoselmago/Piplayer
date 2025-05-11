# modules/sync_network.py

import socket
import threading
import time
import json

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
            payload = {
                "t": now,       # This is the master sync time (playback time)
                "sent": now     # The exact time it was sent
            }
            msg = json.dumps(payload).encode("utf-8")
            sock.sendto(msg, (BROADCAST_IP, PORT))
            time.sleep(SYNC_INTERVAL)

    def stop(self):
        self.running = False


class SyncFollower:
    def __init__(self):
        self.offset = 0.0  # time correction offset
        self.running = False

    def start(self):
        self.running = True
        thread = threading.Thread(target=self._listen_loop, daemon=True)
        thread.start()

    def _listen_loop(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('', PORT))
        while self.running:
            try:
                data, _ = sock.recvfrom(4096)
                now = time.monotonic()
                msg = json.loads(data.decode("utf-8"))
                
                master_time = msg.get("t")
                master_sent = msg.get("sent")
                if master_time is None or master_sent is None:
                    continue

                delay = now - master_sent  # total delay
                estimated_master_time = master_time + (delay / 2)
                local_time = now
                drift = estimated_master_time - local_time

                # Apply smoothing (low-pass filter)
                self.offset = 0.9 * self.offset + 0.1 * drift

            except Exception as e:
                print(f"[SyncFollower] Error: {e}")

    def get_synced_time(self) -> float:
        return time.monotonic() + self.offset

    def stop(self):
        self.running = False
