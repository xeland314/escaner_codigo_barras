"""Generador de códigos de barras en formato SVG vectorial y PNG para pruebas de escaneo."""

import io
from typing import Optional, Tuple
import barcode
from barcode.errors import BarcodeError, IllegalCharacterError, NumberOfDigitsError
from barcode.writer import ImageWriter, SVGWriter
import qrcode
import qrcode.image.svg


SUPPORTED_FORMATS = {
    "ean13": "EAN-13 (Retail / Supermercado)",
    "code128": "Code 128 (Alfanumérico / Logística)",
    "code39": "Code 39 (Alfanumérico Industrial)",
    "upca": "UPC-A (Retail USA / 12 dígitos)",
    "ean8": "EAN-8 (Empaques compactos)",
    "qrcode": "Código QR (2D / Matricial)",
}


def normalize_format(format_name: str) -> str:
    fmt = format_name.lower().replace("-", "").replace("_", "")
    if fmt in ("qr", "qrcode"):
        return "qrcode"
    if fmt in ("ean13", "ean"):
        return "ean13"
    if fmt in ("code128", "c128"):
        return "code128"
    if fmt in ("code39", "c39"):
        return "code39"
    if fmt in ("upca", "upc"):
        return "upca"
    if fmt in ("ean8",):
        return "ean8"
    return "code128"


def generate_svg(format_name: str, code: str) -> Tuple[str, Optional[str]]:
    """Genera el contenido XML/SVG del código de barras.

    Retorna una tupla (svg_xml, error_message).
    """
    fmt = normalize_format(format_name)
    cleaned_code = code.strip()

    if not cleaned_code:
        return "", "El código no puede estar vacío."

    if fmt == "qrcode":
        try:
            factory = qrcode.image.svg.SvgPathImage
            img = qrcode.make(cleaned_code, image_factory=factory, box_size=10, border=3)
            svg_bytes = img.to_string()
            return svg_bytes.decode("utf-8"), None
        except Exception as e:
            return "", f"Error al generar QR: {str(e)}"

    # Mapeo a python-barcode
    bc_name = fmt
    try:
        bc_cls = barcode.get_barcode_class(bc_name)
    except Exception:
        bc_cls = barcode.get_barcode_class("code128")

    writer = SVGWriter()
    options = {
        "write_text": True,
        "font_size": 11,
        "text_distance": 4.0,
        "quiet_zone": 4.0,
        "module_width": 0.32,
        "module_height": 16.0,
    }

    try:
        bc = bc_cls(cleaned_code, writer=writer)
        svg_bytes = bc.render(writer_options=options)
        return svg_bytes.decode("utf-8"), None
    except NumberOfDigitsError:
        # Intento de corrección para EAN13 o UPC si faltó o sobró dígito
        if fmt == "ean13" and len(cleaned_code) == 13:
            # Quizás el último dígito verificador era erróneo, reintentar con los primeros 12
            try:
                bc = bc_cls(cleaned_code[:12], writer=writer)
                svg_bytes = bc.render(writer_options=options)
                return svg_bytes.decode("utf-8"), None
            except Exception:
                pass
        return "", f"Número de dígitos inválido para {format_name.upper()}."
    except IllegalCharacterError as e:
        return "", f"Caracteres no válidos para {format_name.upper()}: {str(e)}"
    except BarcodeError as e:
        return "", f"Error de formato en {format_name.upper()}: {str(e)}"
    except Exception as e:
        return "", f"Error inesperado al generar código: {str(e)}"


def generate_png_bytes(format_name: str, code: str) -> Tuple[Optional[bytes], Optional[str]]:
    """Genera una imagen PNG del código para descargar o visualizar."""
    fmt = normalize_format(format_name)
    cleaned_code = code.strip()

    if fmt == "qrcode":
        try:
            img = qrcode.make(cleaned_code, box_size=10, border=3)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return buf.getvalue(), None
        except Exception as e:
            return None, str(e)

    try:
        bc_cls = barcode.get_barcode_class(fmt)
        writer = ImageWriter()
        buf = io.BytesIO()
        bc = bc_cls(cleaned_code, writer=writer)
        bc.write(buf, options={"write_text": True, "font_size": 11, "module_width": 0.35, "module_height": 18.0})
        return buf.getvalue(), None
    except Exception as e:
        return None, str(e)
