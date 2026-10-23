"""Utilidad CLI interactiva para probar el escáner Symbol directamente desde la terminal."""

import sys
import time
from escaner_codigo_barras.catalog import find_product_by_code
from escaner_codigo_barras.device_info import get_scanner_info

CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"


def run_cli():
    print(f"\n{BOLD}{CYAN}===================================================={RESET}")
    print(f"{BOLD}{CYAN}   Symbol Technologies Barcode Scanner - Modo CLI   {RESET}")
    print(f"{BOLD}{CYAN}===================================================={RESET}\n")

    info = get_scanner_info()
    status_str = f"{GREEN}CONECTADO{RESET}" if info["connected"] else f"{YELLOW}NO DETECTADO{RESET}"
    print(f"Estado USB: {status_str} ({info['vendor_id']}:{info['product_id']} - {info['product_name']})")
    print(f"Modo: {info['operation_mode']}")
    print(f"Dispositivo: {info['device_node'] or 'N/A'}\n")
    print("👉 Apunta el lector a cualquier código de barras y presiona el gatillo.")
    print("   (Presiona Ctrl+C para salir)\n")

    count = 0
    try:
        while True:
            # Dado que el escáner emula un teclado y envía Enter al final,
            # input() captura el código instantáneamente
            sys.stdout.write(f"{BOLD}[Listo para escanear]{RESET} > ")
            sys.stdout.flush()

            t0 = time.perf_counter()
            scanned = sys.stdin.readline()
            if not scanned:
                break
            t1 = time.perf_counter()

            code = scanned.strip()
            if not code:
                continue

            count += 1
            duration_ms = (t1 - t0) * 1000.0
            prod = find_product_by_code(code)

            print(f"\n{GREEN}{BOLD}✓ ¡Código Recibido! (#{count}){RESET}")
            print(f"  • Cadena:    {BOLD}{CYAN}{code}{RESET}")
            print(f"  • Longitud:  {len(code)} caracteres")
            if prod:
                print(f"  • Producto:  {BOLD}{prod.name}{RESET} (${prod.price:.2f})")
                print(f"  • Categoría: {prod.category} (Formato: {prod.format.upper()})")
            else:
                print(f"  • Catálogo:  {YELLOW}Código nuevo / No registrado en demo{RESET}")
            print()

    except KeyboardInterrupt:
        print(f"\n{YELLOW}Finalizando prueba CLI. ¡Hasta luego!{RESET}\n")


if __name__ == "__main__":
    run_cli()
