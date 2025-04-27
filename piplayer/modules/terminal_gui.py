# modules/terminal_gui.py
import curses
import threading
import time

class TerminalGUI:
    """
    Real-time playback monitor with per-track progress bars and mm:ss display.
    """

    def __init__(self, total_seconds: float, track_events: dict[str, list[float]]):
        self.total = max(total_seconds, 0.001)
        self.track_events = track_events  # Dict of track name -> list of note-on times
        self.track_names = list(track_events.keys())
        self._stop = False
        self._thread: threading.Thread | None = None
        self.now = 0.0

    def start(self) -> None:
        self.start_time = time.monotonic()
        self._stop = False
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def update(self, seconds_elapsed: float) -> None:
        self.now = seconds_elapsed

    def stop(self) -> None:
        self._stop = True
        if self._thread:
            self._thread.join()

    def _run(self) -> None:
        curses.wrapper(self._curses_main)

    def reset(self) -> None:
        """Reset GUI timer (for clean loop restarts)."""
        self.start_time = time.monotonic()

    def _curses_main(self, stdscr):
        curses.curs_set(0)
        stdscr.nodelay(True)

        while not self._stop:
            stdscr.erase()
            max_y, max_x = stdscr.getmaxyx()
            bar_w = max(max_x - 20, 10)  # leave space for labels + timestamp

            # Update "now" from time.monotonic
            now_monotonic = time.monotonic() - self.start_time
            self.now = now_monotonic

            # Time strings
            now_m, now_s = divmod(int(self.now), 60)
            total_m, total_s = divmod(int(self.total), 60)
            time_str = f"{now_m:02}:{now_s:02} / {total_m:02}:{total_s:02}"

            # Title
            stdscr.addstr(1, 2, " PiPlayer Monitor ")

            # Draw each track
            for idx, track in enumerate(self.track_names):
                y = 3 + idx
                pct = min(self.now / self.total, 1.0)
                filled = int(pct * bar_w)
                line = "-" * bar_w

                events = self.track_events.get(track, [])

                # Overlay note-on events
                for t in events:
                    ev_pos = int((t / self.total) * bar_w)
                    ev_pos = min(ev_pos, bar_w - 1)
                    line = line[:ev_pos] + "●" + line[ev_pos + 1:]

                # Overlay moving position
                dot_pos = min(filled, bar_w - 1)
                line = line[:dot_pos] + "▶" + line[dot_pos + 1:]

                stdscr.addstr(y, 2, f"{track:<6} [{line}]")

            # Draw time info under all tracks
            stdscr.addstr(5 + len(self.track_names), 2, time_str)

            stdscr.refresh()
            time.sleep(0.05)

