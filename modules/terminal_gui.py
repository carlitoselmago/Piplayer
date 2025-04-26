import curses
import threading
import time


class TerminalGUI:
    """
    Very small real-time playback monitor.

    Example:
        AUDIO  [#####●------------------------------]
        GPIO17 [##●---------------------------------]
    """

    def __init__(self, total_seconds: float, track_names: list[str]):
        self.total = max(total_seconds, 0.001)     # avoid div/0
        self.tracks = track_names
        self._stop = False
        self._thread: threading.Thread | None = None
        self.now = 0.0                             # current position (s)

    # ---------- public API ----------
    def start(self) -> None:
        self._stop = False
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def update(self, seconds_elapsed: float) -> None:
        self.now = seconds_elapsed

    def stop(self) -> None:
        self._stop = True
        if self._thread:
            self._thread.join()

    # ---------- internal ----------
    def _run(self) -> None:
        curses.wrapper(self._curses_main)

    def _curses_main(self, stdscr):
        curses.curs_set(0)
        stdscr.nodelay(True)

        while not self._stop:
            stdscr.erase()
            max_y, max_x = stdscr.getmaxyx()
            bar_w = max(max_x - 12, 10)            # dynamic width
            stdscr.border()

            for idx, track in enumerate(self.tracks):
                y = idx + 1
                pct = min(self.now / self.total, 1.0)
                filled = int(pct * bar_w)
                line = "#" * filled + "-" * (bar_w - filled)
                dot_pos = min(filled, bar_w - 1)
                line = line[:dot_pos] + "●" + line[dot_pos + 1:]
                stdscr.addstr(y, 1, f"{track:<6} [{line}]")

            stdscr.refresh()
            time.sleep(0.05)                       # 20 FPS refresh
