"""Catálogo de productos de ejemplo y códigos de barras preconfigurados."""

from typing import Dict, List, Optional
from pydantic import BaseModel


class Product(BaseModel):
    code: str
    format: str  # ean13, code128, code39, upca, ean8, qrcode
    name: str
    category: str
    price: float
    stock: int
    description: str
    badge_color: str = "blue"


SAMPLE_PRODUCTS: List[Product] = [
    # EAN-13 (Estándar mundial de retail / supermercado)
    Product(
        code="7501031311309",
        format="ean13",
        name="Refresco Coca-Cola 600ml",
        category="Bebidas",
        price=18.50,
        stock=45,
        description="Bebida carbonatada clásica en botella PET.",
        badge_color="emerald",
    ),
    Product(
        code="7501000111203",
        format="ean13",
        name="Pan Blanco de Caja Bimbo Grande",
        category="Panadería",
        price=42.00,
        stock=28,
        description="Pan de molde enriquecido con vitaminas y minerales.",
        badge_color="emerald",
    ),
    Product(
        code="7501008045612",
        format="ean13",
        name="Leche Entera Alpura 1 Litro",
        category="Lácteos",
        price=26.50,
        stock=60,
        description="Leche 100% pura de vaca pasteurizada.",
        badge_color="emerald",
    ),
    Product(
        code="9780132350884",
        format="ean13",
        name="Libro: Clean Code (Robert C. Martin)",
        category="Libros",
        price=550.00,
        stock=12,
        description="Manual de desarrollo ágil de software y buenas prácticas.",
        badge_color="emerald",
    ),
    # UPC-A (Estándar de 12 dígitos común en EE.UU. y México)
    Product(
        code="012345678905",
        format="upca",
        name="Cereal Cheerios Avena 500g",
        category="Despensa",
        price=65.00,
        stock=30,
        description="Cereal de avena integral en caja familiar.",
        badge_color="amber",
    ),
    Product(
        code="049000000443",
        format="upca",
        name="Bebida Sprite Lima-Limón 355ml",
        category="Bebidas",
        price=16.00,
        stock=52,
        description="Refresco sabor lima limón en lata de aluminio.",
        badge_color="amber",
    ),
    # Code 128 (Alta densidad alfanumérico para logística, seriales e inventario)
    Product(
        code="SKU-LAPTOP-M3",
        format="code128",
        name="Laptop ThinkPad Ultra 16 Pulgadas",
        category="Electrónica",
        price=18499.00,
        stock=8,
        description="Portátil empresarial con procesador de alto rendimiento y 32GB RAM.",
        badge_color="indigo",
    ),
    Product(
        code="SN-SYM-05E0-1200",
        format="code128",
        name="Escáner Láser Symbol Technologies USB",
        category="Hardware POS",
        price=1250.00,
        stock=15,
        description="Lector óptico de código de barras 1D de alta velocidad.",
        badge_color="indigo",
    ),
    Product(
        code="PKG-FEDEX-98214",
        format="code128",
        name="Guía de Envío Courier Prioritario",
        category="Logística",
        price=120.00,
        stock=100,
        description="Etiqueta de despacho nacional con trazabilidad.",
        badge_color="indigo",
    ),
    # Code 39 (Estándar industrial clásico alfanumérico)
    Product(
        code="MOTOR-MOD44",
        format="code39",
        name="Motor a Pasos NEMA 23 Industrial",
        category="Componentes",
        price=450.00,
        stock=20,
        description="Motor paso a paso para actuadores CNC y robótica.",
        badge_color="purple",
    ),
    Product(
        code="LOTE-OCT-2026",
        format="code39",
        name="Materia Prima Polímero Grado A",
        category="Almacén",
        price=3200.00,
        stock=14,
        description="Tambor de 50kg certificado de resina polimérica.",
        badge_color="purple",
    ),
    # EAN-8 (Para productos pequeños)
    Product(
        code="96385074",
        format="ean8",
        name="Goma de Mascar Trident Menta",
        category="Confitería",
        price=12.00,
        stock=75,
        description="Paquete de chicles sin azúcar sabor menta fresca.",
        badge_color="cyan",
    ),
    Product(
        code="12345670",
        format="ean8",
        name="Barra de Chocolate Suizo 30g",
        category="Confitería",
        price=15.00,
        stock=90,
        description="Chocolate con leche de bolsillo.",
        badge_color="cyan",
    ),
    # QR Code (Matriz 2D)
    Product(
        code="https://github.com",
        format="qrcode",
        name="Enlace de Documentación Técnica",
        category="Digital / QR",
        price=0.00,
        stock=999,
        description="Código QR 2D para escáneres con sensor imager matricial.",
        badge_color="rose",
    ),
    Product(
        code="PROD:SYM-SCAN;LOTE:2026;PRECIO:1250",
        format="qrcode",
        name="Ficha Técnica Serializada QR",
        category="Digital / QR",
        price=1250.00,
        stock=1,
        description="Cadena estructurada con parámetros de producto.",
        badge_color="rose",
    ),
]


def find_product_by_code(code: str) -> Optional[Product]:
    """Busca un producto por código exacto o eliminando ceros o espacios iniciales/finales."""
    cleaned = code.strip()
    for prod in SAMPLE_PRODUCTS:
        if prod.code == cleaned:
            return prod

    # Comparación sin ceros a la izquierda (útil para UPC-A vs EAN-13)
    for prod in SAMPLE_PRODUCTS:
        if prod.code.lstrip("0") == cleaned.lstrip("0"):
            return prod

    return None
