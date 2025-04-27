# modules/gpio_driver.py
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    print("⚠️  RPi.GPIO not available — using mock mode.")

class GPIODriver:
    """
    Controls Raspberry Pi GPIO pins based on MIDI note events.

    - Note number = GPIO pin
    - Velocity > 0 = ON (HIGH)
    - Note off or velocity = 0 = OFF (LOW)
    """

    def __init__(self, pin_list: list[int]):
        self.pins = sorted(set(pin_list))
        self.mock = not GPIO_AVAILABLE

        if not self.mock:
            GPIO.setmode(GPIO.BCM)
            for pin in self.pins:
                GPIO.setup(pin, GPIO.OUT)
                GPIO.output(pin, GPIO.LOW)
            print(f"[Real GPIO] Prepared pins: {self.pins}")
        else:
            print(f"[Mock GPIO] Prepared pins: {self.pins}")

    def note_on(self, note: int, velocity: int) -> None:
        """Turn pin ON if velocity > 0, otherwise OFF."""
        if note not in self.pins:
            print(f"[Warning] Note {note} not prepared")
            return

        if velocity > 0:
            self._write(note, True)
        else:
            self._write(note, False)

    def note_off(self, note: int) -> None:
        """Turn pin OFF."""
        if note not in self.pins:
            print(f"[Warning] Note {note} not prepared")
            return
        self._write(note, False)

    def cleanup(self) -> None:
        """Cleanup GPIO state."""
        if not self.mock:
            GPIO.cleanup()
        else:
            print("[Mock GPIO] Cleanup called.")

    def _write(self, pin: int, state: bool) -> None:
        if not self.mock:
            GPIO.output(pin, GPIO.HIGH if state else GPIO.LOW)
        else:
            print(f"[Mock GPIO] Pin {pin}: {'HIGH' if state else 'LOW'}")
