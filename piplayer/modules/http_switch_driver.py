# modules/http_switch_driver.py

import requests


class HTTPSWITCHdriver:
    """
    Controls an HTTP-enabled switch (e.g. Tasmota) for a whole MIDI track.

    - All MIDI notes trigger the same device
    - Velocity > 0  → Power ON
    - Note off or velocity = 0 → Power OFF

    Extra metadata (electric_group, etc.) is stored for future logic.
    """

    def __init__(
        self,
        ip: str,
        electric_group: int | None = None,
        timeout: float = 1.0,
        mock: bool = False,
        track: str | None = None,
    ):
        self.ip = ip
        self.electric_group = electric_group
        self.timeout = timeout
        self.mock = mock
        self.track = track

        mode = "Mock HTTP" if mock else "Real HTTP"
        label = f" track='{track}'" if track else ""
        print(f"[{mode}] HTTP switch prepared:{label}")
        print(f"  IP: {self.ip}")
        if electric_group is not None:
            print(f"  Electric group: {electric_group}")

    # ────────────────────────────────────────────────────────
    def note_on(self, note: int, velocity: int) -> None:
        """
        Turn device ON if velocity > 0, otherwise OFF.
        """
        if velocity > 0:
            self._send("On")
        else:
            self._send("Off")

    def note_off(self, note: int) -> None:
        """
        Turn device OFF.
        """
        self._send("Off")

    def cleanup(self) -> None:
        """
        No persistent state, kept for API symmetry.
        """
        print(f"[HTTP] Cleanup called for {self.ip}")

    # ────────────────────────────────────────────────────────
    def _send(self, power_state: str) -> None:
        url = f"http://{self.ip}/cm"
        params = {"cmnd": f"Power {power_state}"}

        if self.mock:
            print(f"[Mock HTTP] {self.ip} ← Power {power_state}")
            return

        try:
            r = requests.get(url, params=params, timeout=self.timeout)
            print(f"[HTTP] {self.ip} ← Power {power_state} ({r.status_code})")
        except requests.RequestException as e:
            print(f"[HTTP ERROR] {self.ip}: {e}")
