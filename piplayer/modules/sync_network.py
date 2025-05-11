# modules/sync_network.py
"""Network‑based time‑synchronisation helpers.

Master  ➔  UDP broadcast  ➔  Followers

Packet format (JSON):
{
  "t_play":  12.345,        # master *playback* position (s)
  "sent":    123456.789     # master local monotonic() at the moment of send
}

Followers use
    delay = now_local - sent
    est_play = t_play + delay/2
and low‑pass‑filter the drift.
"""

import socket
import threading
import time
import json
from typing import Callable, Optional

PORT            = 5005
BROADCAST_IP    = "255.255.255.255"
SYNC_INTERVAL   = 0.02   # 20 ms packets
ALPHA           = 0.1    # smoothing factor for low‑pass (follower)

# ---------------------------------------------------------------------------
class SyncMaster:
    """Broadcasts current *playback* position every 20 ms via UDP broadcast.

    Parameters
    ----------
    time_provider : Callable[[], float]
        Function that returns current **playback time in seconds**.
        If omitted, we will transmit raw time.monotonic().
    """

    def __init__(self, time_provider: Optional[Callable[[], float]] = None):
        self._get_play_time = time_provider or (lambda: time.monotonic())
        self._running = False
        self._thread: Optional[threading.Thread] = None

    # .................................................................
    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._broadcast_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join()

    # .................................................................
    def _broadcast_loop(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        while self._running:
            play_t = self._get_play_time()          # playback position (s)
            sent   = time.monotonic()               # local monotonic timestamp

            payload = json.dumps({"t_play": play_t, "sent": sent}).encode()
            sock.sendto(payload, (BROADCAST_IP, PORT))
            time.sleep(SYNC_INTERVAL)

# ---------------------------------------------------------------------------
class SyncFollower:
    """Listens for master broadcast and produces a smoothed synced clock."""

    def __init__(self):
        self._offset   = 0.0   # seconds added to local monotonic to match master
        self._running  = False
        self._thread: Optional[threading.Thread] = None

    # .................................................................
    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join()

    # .................................................................
    def _listen_loop(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", PORT))
        sock.settimeout(1.0)

        while self._running:
            try:
                data, _ = sock.recvfrom(2048)
                now_local = time.monotonic()
                msg = json.loads(data.decode())
                t_play = msg.get("t_play")
                sent   = msg.get("sent")
                if t_play is None or sent is None:
                    continue

                net_delay   = now_local - sent          # RTT/2 approximation
                est_master  = t_play + net_delay / 2.0  # estimated master play time
                local_play  = now_local + self._offset  # our current play time
                drift       = est_master - local_play

                # Low‑pass filter the drift → smooth correction
                self._offset += ALPHA * drift

            except socket.timeout:
                continue
            except Exception as exc:
                print(f"[SyncFollower] Error: {exc}")

    # .................................................................
    def get_synced_time(self) -> float:
        """Return follower‑side clock aligned to the master."""
        return time.monotonic() + self._offset
