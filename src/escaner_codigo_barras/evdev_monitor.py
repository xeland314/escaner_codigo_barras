"""Monitor asíncrono de bajo nivel para el escáner de código de barras Symbol usando evdev."""

import asyncio
import logging
import time
from typing import Callable, List, Optional
import evdev
from evdev import ecodes

from escaner_codigo_barras.device_info import find_symbol_scanner_device

logger = logging.getLogger(__name__)

# Mapa de teclas estándar y con shift activo
SCANCODE_MAP = {
    ecodes.KEY_1: ("1", "!"),
    ecodes.KEY_2: ("2", "@"),
    ecodes.KEY_3: ("3", "#"),
    ecodes.KEY_4: ("4", "$"),
    ecodes.KEY_5: ("5", "%"),
    ecodes.KEY_6: ("6", "^"),
    ecodes.KEY_7: ("7", "&"),
    ecodes.KEY_8: ("8", "*"),
    ecodes.KEY_9: ("9", "("),
    ecodes.KEY_0: ("0", ")"),
    ecodes.KEY_MINUS: ("-", "_"),
    ecodes.KEY_EQUAL: ("=", "+"),
    ecodes.KEY_Q: ("q", "Q"),
    ecodes.KEY_W: ("w", "W"),
    ecodes.KEY_E: ("e", "E"),
    ecodes.KEY_R: ("r", "R"),
    ecodes.KEY_T: ("t", "T"),
    ecodes.KEY_Y: ("y", "Y"),
    ecodes.KEY_U: ("u", "U"),
    ecodes.KEY_I: ("i", "I"),
    ecodes.KEY_O: ("o", "O"),
    ecodes.KEY_P: ("p", "P"),
    ecodes.KEY_LEFTBRACE: ("[", "{"),
    ecodes.KEY_RIGHTBRACE: ("]", "}"),
    ecodes.KEY_A: ("a", "A"),
    ecodes.KEY_S: ("s", "S"),
    ecodes.KEY_D: ("d", "D"),
    ecodes.KEY_F: ("f", "F"),
    ecodes.KEY_G: ("g", "G"),
    ecodes.KEY_H: ("h", "H"),
    ecodes.KEY_J: ("j", "J"),
    ecodes.KEY_K: ("k", "K"),
    ecodes.KEY_L: ("l", "L"),
    ecodes.KEY_SEMICOLON: (";", ":"),
    ecodes.KEY_APOSTROPHE: ("'", '"'),
    ecodes.KEY_GRAVE: ("`", "~"),
    ecodes.KEY_BACKSLASH: ("\\", "|"),
    ecodes.KEY_Z: ("z", "Z"),
    ecodes.KEY_X: ("x", "X"),
    ecodes.KEY_C: ("c", "C"),
    ecodes.KEY_V: ("v", "V"),
    ecodes.KEY_B: ("b", "B"),
    ecodes.KEY_N: ("n", "N"),
    ecodes.KEY_M: ("m", "M"),
    ecodes.KEY_COMMA: (",", "<"),
    ecodes.KEY_DOT: (".", ">"),
    ecodes.KEY_SLASH: ("/", "?"),
    ecodes.KEY_SPACE: (" ", " "),
    # Teclado numérico
    ecodes.KEY_KP0: ("0", "0"),
    ecodes.KEY_KP1: ("1", "1"),
    ecodes.KEY_KP2: ("2", "2"),
    ecodes.KEY_KP3: ("3", "3"),
    ecodes.KEY_KP4: ("4", "4"),
    ecodes.KEY_KP5: ("5", "5"),
    ecodes.KEY_KP6: ("6", "6"),
    ecodes.KEY_KP7: ("7", "7"),
    ecodes.KEY_KP8: ("8", "8"),
    ecodes.KEY_KP9: ("9", "9"),
    ecodes.KEY_KPDOT: (".", "."),
    ecodes.KEY_KPSLASH: ("/", "/"),
    ecodes.KEY_KPASTERISK: ("*", "*"),
    ecodes.KEY_KPMINUS: ("-", "-"),
    ecodes.KEY_KPPLUS: ("+", "+"),
}


class EvdevScannerListener:
    """Escucha eventos crudos de pulsación de teclas provenientes directamente del dispositivo /dev/input."""

    def __init__(self, device_path: Optional[str] = None):
        self.device_path = device_path or find_symbol_scanner_device()
        self.callbacks: List[Callable[[str, float, str], None]] = []
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self.device_name = "Desconocido"

    def register_callback(self, cb: Callable[[str, float, str], None]) -> None:
        """Registra un callback que recibe (codigo, duracion_ms, origen)."""
        self.callbacks.append(cb)

    async def start(self) -> bool:
        if not self.device_path:
            logger.warning("No se encontró la ruta del dispositivo escáner Symbol.")
            return False

        try:
            device = evdev.InputDevice(self.device_path)
            self.device_name = device.name
            logger.info(f"Conectado a dispositivo evdev: {device.name} ({self.device_path})")
        except Exception as e:
            logger.warning(
                f"No se pudo abrir el dispositivo {self.device_path}: {e}. "
                "La app continuará en modo Web Keyboard Wedge."
            )
            return False

        self._running = True
        self._task = asyncio.create_task(self._listen_loop(device))
        return True

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _listen_loop(self, device: evdev.InputDevice) -> None:
        shift_pressed = False
        current_buffer: List[str] = []
        start_time: Optional[float] = None

        try:
            async for event in device.async_read_loop():
                if not self._running:
                    break

                if event.type != ecodes.EV_KEY:
                    continue

                key_code = event.code
                key_value = event.value  # 0: release, 1: press, 2: hold

                # Seguimiento del estado Shift
                if key_code in (ecodes.KEY_LEFTSHIFT, ecodes.KEY_RIGHTSHIFT):
                    shift_pressed = (key_value > 0)
                    continue

                # Solo procesar en evento de pulsación (press o repeat)
                if key_value == 0:
                    continue

                now = time.perf_counter()
                if not current_buffer:
                    start_time = now

                # Tecla Enter = fin del escaneo
                if key_code in (ecodes.KEY_ENTER, ecodes.KEY_KPENTER):
                    if current_buffer:
                        duration_ms = (now - (start_time or now)) * 1000.0
                        scanned_code = "".join(current_buffer)
                        logger.info(f"[Evdev] Código escaneado: '{scanned_code}' en {duration_ms:.1f}ms")

                        # Disparar callbacks
                        for cb in self.callbacks:
                            try:
                                if asyncio.iscoroutinefunction(cb):
                                    await cb(scanned_code, duration_ms, "evdev_hardware")
                                else:
                                    cb(scanned_code, duration_ms, "evdev_hardware")
                            except Exception as e:
                                logger.error(f"Error en callback de escaneo: {e}")

                        current_buffer.clear()
                        start_time = None
                    continue

                # Tecla Backspace
                if key_code == ecodes.KEY_BACKSPACE:
                    if current_buffer:
                        current_buffer.pop()
                    continue

                # Mapear tecla
                if key_code in SCANCODE_MAP:
                    normal_char, shifted_char = SCANCODE_MAP[key_code]
                    char = shifted_char if shift_pressed else normal_char
                    current_buffer.append(char)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error en el bucle de lectura evdev: {e}")
        finally:
            try:
                device.close()
            except Exception:
                pass
