"""Punto de entrada principal para ejecutar la aplicación web o CLI."""

import argparse
import sys
import uvicorn


def main():
    parser = argparse.ArgumentParser(
        description="Suite de pruebas para escáner de código de barras Symbol Technologies USB"
    )
    parser.add_argument(
        "mode",
        nargs="?",
        default="server",
        choices=["server", "cli", "evdev"],
        help="Modo de ejecución: 'server' (Web Dashboard FastAPI), 'cli' (Terminal stdin), 'evdev' (Hardware listener)",
    )
    parser.add_argument("--host", default="0.0.0.0", help="Dirección host del servidor web (por defecto: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Puerto del servidor web (por defecto: 8000)")
    parser.add_argument("--reload", action="store_true", help="Habilitar autoreload para desarrollo")

    args = parser.parse_args()

    if args.mode == "cli":
        from escaner_codigo_barras.cli import run_cli
        run_cli()
    elif args.mode == "evdev":
        import asyncio
        from escaner_codigo_barras.evdev_cli import main as evdev_main
        asyncio.run(evdev_main())
    else:
        print(f"\n🚀 Iniciando servidor FastAPI en http://localhost:{args.port} ...\n")
        uvicorn.run(
            "escaner_codigo_barras.app:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
        )


if __name__ == "__main__":
    main()
