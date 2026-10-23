"""Monitor de eventos evdev de bajo nivel para el escáner Symbol."""

import asyncio
import sys
from escaner_codigo_barras.catalog import find_product_by_code
from escaner_codigo_barras.device_info import get_scanner_info
from escaner_codigo_barras.evdev_monitor import EvdevScannerListener

CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"


async def main():
    print(f"\n{BOLD}{CYAN}===================================================={RESET}")
    print(f"{BOLD}{CYAN}   Symbol Technologies - Monitor Hardware evdev     {RESET}")
    print(f"{BOLD}{CYAN}===================================================={RESET}\n")

    info = get_scanner_info()
    if not info["connected"] or not info["is_readable"]:
        print(f"{YELLOW}Aviso:{RESET} Dispositivo no encontrado o sin permisos en {info.get('device_node')}.")
        return

    print(f"Escuchando eventos directamente en: {BOLD}{info['device_node']}{RESET}")
    print(f"Dispositivo: {info['product_name']} (S/N: {info['serial_number']})")
    print("Captura en segundo plano activa (no requiere ventana enfocada).")
    print("Presiona Ctrl+C para detener.\n")

    listener = EvdevScannerListener(info["device_node"])

    def on_scan(code: str, duration_ms: float, source: str):
        prod = find_product_by_code(code)
        print(f"\n{GREEN}{BOLD}⚡ [Hardware evdev] ¡Lectura capturada!{RESET}")
        print(f"  • Código:       {BOLD}{CYAN}{code}{RESET}")
        print(f"  • Ráfaga USB:   {duration_ms:.1f} ms")
        if prod:
            print(f"  • Coincidencia: {BOLD}{prod.name}{RESET} (${prod.price:.2f})")
        else:
            print(f"  • Coincidencia: {YELLOW}Sin producto en catálogo demo{RESET}")
        print("-" * 50)

    listener.register_callback(on_scan)
    success = await listener.start()
    if not success:
        print("No se pudo iniciar el listener.")
        return

    try:
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, asyncio.CancelledError):
        print(f"\n{YELLOW}Cerrando monitor evdev...{RESET}")
        await listener.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
