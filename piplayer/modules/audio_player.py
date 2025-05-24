"""
audio_player.py  –  mpv wrapper with master-clock sync (seek-only).

Assumptions
-----------
• We run either in LOCAL/MASTER mode (no follower) or in FOLLOWER mode,
  where a SyncFollower object is passed in and provides get_time().
• mpv’s reported time_pos lags actual output by MPV_LATENCY seconds.
• After every seek mpv takes ~0.8–1.0 s to refill decode buffer; during
  that time we must ignore the stale time_pos to avoid a seek-cascade.
"""

from mpv import MPV
import threading, time
from typing import Protocol, Optional


# ───────── interface follower must expose ─────────
class ClockSource(Protocol):
    def get_time(self) -> float: ...


# ───────── tweakables ─────────────────────────────
MPV_LATENCY      = 0.10  # 🔽 tighter estimate for fast decode
SEEK_THRESHOLD   = 0.10  # 🔽 react to smaller drift
LARGE_DRIFT      = 0.50  # 🔽 correct more often if sync degrades
SEEK_COOLDOWN    = 3.0   # 🔽 allow more frequent small seeks
SEEK_SETTLE      = 0.6   # 🔽 less delay after each seek
PREDICTIVE_LEAD  = 0.15  # 🔼 slightly more proactive positioning
SYNC_POLL        = 0.25  # 🔼 faster reaction loop

# --------------------------------------------------


class AudioPlayer:
    def __init__(self, filename: str):
        self.filename = filename
        self.player = MPV(input_default_bindings=True)
        self._follower: Optional[ClockSource] = None

        self._thr:   Optional[threading.Thread] = None
        self._stop_evt = threading.Event()

        self._last_seek  = 0.0      # monotonic time of last seek
        self._settle_until = 0.0    # time until which we ignore drift

    # ───────────────────────────────────────────────
    def start(self, follower: Optional[ClockSource] = None):
        """Start playback.  Pass follower in FOLLOWER mode."""
        self.stop()
        self._follower = follower

        # Capture master time *before* mpv buffering delay
        start_target = follower.get_time() if follower else 0.0

        self.player.play(self.filename)

        # Wait until mpv publishes first time_pos
        while self.player.time_pos is None:
            time.sleep(0.05)

        # Initial seek in follower mode
        if follower:
            target = max(0.0, start_target + PREDICTIVE_LEAD)
            print(f"[Audio] initial seek → {target:.2f}s")
            try:
                self.player.seek(target, reference="absolute")
            except Exception as e:
                print("[Audio] initial seek error:", e)

        # allow immediate correction after we start the thread
        self._last_seek = 0.0
        self._settle_until = time.monotonic() + SEEK_SETTLE

        if follower and follower.has_sync():
            self._stop_evt.clear()
            self._thr = threading.Thread(target=self._sync_loop, daemon=True)
            self._thr.start()

    # ───────────────────────────────────────────────
    def _sync_loop(self):
        stable_interval = 1000.0   # slow check when in sync
        active_interval = 0.25  # fast check when drift is big or adjusting

        while not self._stop_evt.is_set():
            if self.player.time_pos is None or not self._follower:
                time.sleep(active_interval)
                continue

            # Ignore drift while mpv is settling after a seek
            now = time.monotonic()
            if now < self._settle_until:
                time.sleep(active_interval)
                continue

            player_pos = (self.player.time_pos or 0.0) - MPV_LATENCY
            master_time = self._follower.get_time()
            drift = player_pos - master_time

            print(f"[Audio] Master={master_time:.2f}s  "
                f"Player={player_pos:.2f}s  Drift={drift:+.3f}s")

            if abs(drift) < SEEK_THRESHOLD:
                time.sleep(stable_interval)
                continue

            cooldown_ok = (now - self._last_seek) >= SEEK_COOLDOWN
            large_drift = abs(drift) > LARGE_DRIFT

            if not cooldown_ok and not large_drift:
                time.sleep(stable_interval)
                continue

            # Perform seek
            target = master_time + PREDICTIVE_LEAD
            print(f"[Audio] SEEK  drift {drift:+.3f}s → {target:.2f}s")
            try:
                self.player.seek(target, reference="absolute")
                self._last_seek = now
                self._settle_until = now + SEEK_SETTLE
            except Exception as e:
                print("[Audio] seek error:", e)

            time.sleep(active_interval)


    # ───────────────────────────────────────────────
    def stop(self):
        if self._thr:
            self._stop_evt.set()
            self._thr.join()
            self._thr = None
        try:
            self.player.command("stop")
        except Exception:
            pass

    def wait_done(self):
        while self.player.time_pos is not None:
            time.sleep(0.1)

    def is_playing(self):
        return self.player.time_pos is not None
