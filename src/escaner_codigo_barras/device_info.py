"""Módulo para inspeccionar el escáner de código de barras Symbol Technologies conectado vía USB."""

import glob
import os
import re
import subprocess
from typing import Any, Dict, List, Optional


def find_symbol_scanner_device() -> Optional[str]:
    """Busca el archivo de dispositivo /dev/input/event* o by-id correspondiente al escáner Symbol."""
    by_id_dir = "/dev/input/by-id"
    if os.path.exists(by_id_dir):
        for entry in os.listdir(by_id_dir):
            if "symbol" in entry.lower() and "event-kbd" in entry.lower():
                return os.path.join(by_id_dir, entry)

    # Si no está en by-id, buscar en /sys/class/input/event*
    for sys_path in glob.glob("/sys/class/input/event*/device/name"):
        try:
            with open(sys_path, "r", encoding="utf-8", errors="ignore") as f:
                name = f.read().strip()
                if "symbol" in name.lower() or "bar code" in name.lower():
                    event_dir = os.path.dirname(os.path.dirname(sys_path))
                    event_name = os.path.basename(event_dir)
                    dev_node = f"/dev/input/{event_name}"
                    if os.path.exists(dev_node):
                        return dev_node
        except Exception:
            continue
    return None


def get_scanner_info() -> Dict[str, Any]:
    """Recopila información detallada del hardware, driver, protocolo y permisos del escáner."""
    device_path = find_symbol_scanner_device()
    resolved_path = os.path.realpath(device_path) if device_path else None

    # Permisos de lectura
    is_readable = False
    if resolved_path and os.path.exists(resolved_path):
        is_readable = os.access(resolved_path, os.R_OK)

    # Obtener información mediante udevadm si está disponible
    udev_props: Dict[str, str] = {}
    if resolved_path:
        try:
            out = subprocess.check_output(
                ["udevadm", "info", resolved_path],
                text=True,
                stderr=subprocess.DEVNULL,
            )
            for line in out.splitlines():
                if "=" in line and line.startswith("E: "):
                    key, val = line[3:].split("=", 1)
                    udev_props[key] = val
        except Exception:
            pass

    # Obtener información mediante lsusb
    lsusb_raw = ""
    try:
        lsusb_raw = subprocess.check_output(
            ["lsusb", "-d", "05e0:1200", "-v"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass

    return {
        "connected": device_path is not None,
        "vendor_id": "05e0",
        "product_id": "1200",
        "vendor_name": "Symbol Technologies, Inc.",
        "product_name": udev_props.get("ID_MODEL", "Symbol Bar Code Scanner"),
        "serial_number": udev_props.get("ID_SERIAL_SHORT", "N/A"),
        "device_symlink": device_path,
        "device_node": resolved_path,
        "is_readable": is_readable,
        "driver": udev_props.get("ID_USB_DRIVER", "usbhid"),
        "bus_type": udev_props.get("ID_BUS", "usb"),
        "interface_class": "03 (Human Interface Device - HID)",
        "interface_subclass": "01 (Boot Interface)",
        "interface_protocol": "01 (Keyboard)",
        "operation_mode": "USB HID Keyboard Wedge (Emulación de Teclado)",
        "explanation": (
            "El escáner funciona como un teclado USB estándar ('Keyboard Wedge'). "
            "Cuando se presiona el gatillo sobre un código de barras, su procesador óptico "
            "decodifica las barras a texto y envía cada caracter como pulsación de tecla rápida, "
            "seguido por una tecla Enter (Carriage Return). "
            "Esto permite usarlo en cualquier aplicación sin drivers especiales."
        ),
    }
