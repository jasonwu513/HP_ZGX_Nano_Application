import enum
import logging
import threading

logger = logging.getLogger(__name__)


class LEDColor(enum.Enum):
    GREEN = "green"    # 就緒
    BLUE = "blue"      # 聆聽中
    YELLOW = "yellow"  # 處理中
    RED = "red"        # 錯誤
    OFF = "off"


class Controller:
    def __init__(self):
        self._gpio_available = False
        self._mode_callback = None
        self._action_callback = None
        self._init_gpio()

    def _init_gpio(self):
        try:
            import RPi.GPIO as GPIO
            GPIO.setmode(GPIO.BCM)

            self._mode_pin = 17  # 模式切換按鈕
            self._action_pin = 27  # 動作按鈕 (開始/停止)
            self._led_pins = {
                LEDColor.GREEN: 22,
                LEDColor.BLUE: 23,
                LEDColor.YELLOW: 24,
                LEDColor.RED: 25,
            }

            GPIO.setup(self._mode_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(self._action_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

            for pin in self._led_pins.values():
                GPIO.setup(pin, GPIO.OUT)
                GPIO.output(pin, GPIO.LOW)

            GPIO.add_event_detect(
                self._mode_pin, GPIO.FALLING,
                callback=self._on_mode_press, bouncetime=300,
            )
            GPIO.add_event_detect(
                self._action_pin, GPIO.FALLING,
                callback=self._on_action_press, bouncetime=300,
            )

            self._gpio_available = True
            logger.info("GPIO 已初始化")
        except (ImportError, RuntimeError):
            logger.info("GPIO 不可用，使用 CLI 選單")

    def set_led(self, color: LEDColor):
        if not self._gpio_available:
            return

        import RPi.GPIO as GPIO
        for c, pin in self._led_pins.items():
            GPIO.output(pin, GPIO.HIGH if c == color else GPIO.LOW)

    def on_mode_change(self, callback):
        self._mode_callback = callback

    def on_action(self, callback):
        self._action_callback = callback

    def _on_mode_press(self, channel):
        if self._mode_callback:
            self._mode_callback()

    def _on_action_press(self, channel):
        if self._action_callback:
            self._action_callback()

    def cli_menu(self) -> str:
        print("\n=== 中英學習工具 ===")
        print("1. 即時翻譯模式 (Mode 1)")
        print("2. 批次錄音模式 (Mode 2)")
        print("q. 離開")
        return input("請選擇: ").strip()

    def cleanup(self):
        if self._gpio_available:
            import RPi.GPIO as GPIO
            GPIO.cleanup()
