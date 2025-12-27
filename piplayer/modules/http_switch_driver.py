# modules/http_switch_driver.py

import requests


class HTTPSWITCHdriver:
    """
    Simple HTTP switch controller.
    Alternation / electric group logic is handled elsewhere.
    """

    def __init__(
        self,
        ip: str,
        electric_group: int | None = None,
        timeout: float = 2.0,
        mock: bool = False,
        track: str | None = None,
    ):
        self.ip = ip
        self.electric_group = electric_group
        self.timeout = timeout
        self.mock = mock
        self.track = track

        self.requested_on = False      # desired MIDI state
        self.current_on = False        # last applied state

        mode = "Mock HTTP" if mock else "Real HTTP"
        label = f" track='{track}'" if track else ""
        print(f"[{mode}] HTTP switch prepared:{label}")
        print(f"  IP: {self.ip}")
        if electric_group is not None:
            print(f"  Electric group: {electric_group}")

    # ─────────────────────────────────────────
    # MIDI
    # ─────────────────────────────────────────
    def note_on(self, note: int, velocity: int) -> None:
        self.requested_on = velocity > 0

    def note_off(self, note: int) -> None:
        self.requested_on = False

    def cleanup(self) -> None:
        self.requested_on = False
        self._apply(False)
        print(f"[HTTP] Cleanup called for {self.ip}")

    # ─────────────────────────────────────────
    # External controller calls this
    # ─────────────────────────────────────────
    def force_state(self, on: bool):
        self._apply(on)

    def _apply(self, on: bool):
        if self.current_on == on:
            return

        self.current_on = on
        self._send("On" if on else "Off")

    # ─────────────────────────────────────────
    # HTTP
    # ─────────────────────────────────────────
    def _send(self, power_state: str) -> None:
        url = f"http://{self.ip}/cm"
        params = {"cmnd": f"Power {power_state}"}

        if self.mock:
            print(f"[Mock HTTP] {self.ip} ← Power {power_state}")
            return

        for attempt in range(2):  # 1 retry
            try:
                r = requests.get(url, params=params, timeout=self.timeout)
                print(f"[HTTP] {self.ip} ← Power {power_state} ({r.status_code})")
                return
            except requests.RequestException as e:
                if attempt == 0:
                    print(f"[HTTP WARN] {self.ip}: retrying after error: {e}")
                    time.sleep(0.1)
                else:
                    print(f"[HTTP ERROR] {self.ip}: {e}")