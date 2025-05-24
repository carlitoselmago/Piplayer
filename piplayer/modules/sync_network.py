import socket, threading, time, json, collections, statistics, uuid

# ─── Configuration ───────────────────────────────────────────
PORT            = 5005
BROADCAST_IP    = "255.255.255.255"
SYNC_PERIOD_S   = 0.50

OUTLIER_RTT     = 0.120
WIN             = 20
LARGE_DRIFT     = 1.00
SYNC_TOLERANCE  = 0.25
SYNC_GRACE_S    = 10.0
TIMEOUT_S       = 2.0   # ⏱ stop trusting master after this idle time

# ─── SyncMaster ──────────────────────────────────────────────
class SyncMaster:
    def __init__(self):
        self._t0 = time.monotonic()
        self.running = False
        self.session_id = str(uuid.uuid4())  # 💡 unique ID for this run
        self.seq = 0

    def start(self):
        self.running = True
        print(f"[SyncMaster] ID = {self.session_id[:8]}")
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        while self.running:
            now = time.monotonic()
            pkt = {
                "t": now - self._t0,
                "sent": now,
                "id": self.session_id,
                "seq": self.seq
            }
            sock.sendto(json.dumps(pkt).encode(), (BROADCAST_IP, PORT))
            self.seq += 1
            time.sleep(SYNC_PERIOD_S)

    def stop(self): self.running = False

# ─── SyncFollower ────────────────────────────────────────────
class SyncFollower:
    def __init__(self):
        self._t0 = time.monotonic()
        self._pairs = collections.deque(maxlen=WIN)
        self._a = 1.0
        self._b = 0.0
        self._drifts = collections.deque(maxlen=10)
        self.running = False
        self._master_id = None
        self._last_received = 0.0

    def _local(self) -> float:
        return time.monotonic() - self._t0

    def start(self):
        self.running = True
        threading.Thread(target=self._listen, daemon=True).start()

    def _listen(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('', PORT))

        while self.running:
            try:
                data, addr = sock.recvfrom(256)
                recv = time.monotonic()
                pkt = json.loads(data.decode())

                t_m  = pkt.get("t")
                sent = pkt.get("sent")
                mid  = pkt.get("id")
                seq  = pkt.get("seq")

                if None in (t_m, sent, mid):
                    continue

                # Identity match
                if self._master_id is None:
                    self._master_id = mid
                    print(f"[SyncFollower] Master locked: {mid[:8]}")
                elif mid != self._master_id:
                    print(f"[SyncFollower] Ignoring other master {mid[:8]}")
                    continue

                rtt = recv - sent
                if rtt > OUTLIER_RTT:
                    continue

                one_way = rtt / 2
                master_now = t_m + one_way
                self._pairs.append((master_now, recv - self._t0))
                self._last_received = recv

                if len(self._pairs) >= 3:
                    self._recalc_lr()

                drift = master_now - self.get_time()
                self._drifts.append(drift)

            except Exception as e:
                print("[SyncFollower] Error:", e)

    def _recalc_lr(self):
        xs, ys = zip(*self._pairs)
        mx, my = statistics.mean(xs), statistics.mean(ys)
        cov = sum((x - mx) * (y - my) for x, y in self._pairs)
        var = sum((x - mx)**2 for x in xs)
        if var > 1e-9:
            self._a = cov / var
            self._b = my - self._a * mx

    def get_time(self) -> float:
        if len(self._pairs) < 3:
            raise RuntimeError("[SyncFollower] No valid sync received.")
        return (self._local() - self._b) / self._a

    get_synced_time = get_time  # for legacy calls

    def median_drift(self) -> float:
        if len(self._drifts) < 3:
            return 0.0
        lst = sorted(self._drifts)
        n = len(lst)
        return lst[n//2] if n % 2 else (lst[n//2 - 1] + lst[n//2]) / 2.0

    def out_of_tolerance(self) -> bool:
        if not self.has_active_master():
            return False
        if self._local() < SYNC_GRACE_S:
            return False
        return abs(self.median_drift()) > SYNC_TOLERANCE

    def has_sync(self) -> bool:
        return len(self._pairs) >= 3

    def has_active_master(self) -> bool:
        return (time.monotonic() - self._last_received) < TIMEOUT_S

    def stop(self): self.running = False
