"""Aplicación FastAPI principal para probar y usar el escáner Symbol USB."""

from contextlib import asynccontextmanager
from datetime import datetime
import json
import logging
from typing import Any, Dict, List, Optional
import uuid

from fastapi import FastAPI, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from escaner_codigo_barras.barcode_generator import (
    SUPPORTED_FORMATS,
    generate_png_bytes,
    generate_svg,
    normalize_format,
)
from escaner_codigo_barras.catalog import SAMPLE_PRODUCTS, Product, find_product_by_code
from escaner_codigo_barras.device_info import get_scanner_info
from escaner_codigo_barras.evdev_monitor import EvdevScannerListener

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Almacén de escaneos recientes en memoria (máximo 100)
scan_history: List[Dict[str, Any]] = []
last_scan_dedup: Dict[str, float] = {}

evdev_listener: Optional[EvdevScannerListener] = None


class ConnectionManager:
    """Administra conexiones WebSocket activas."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.append(connection)
        for dead in dead_connections:
            self.disconnect(dead)


ws_manager = ConnectionManager()


async def process_and_record_scan(code: str, duration_ms: float, source: str) -> Optional[Dict[str, Any]]:
    """Procesa un código escaneado, deduplica si ocurrió en los últimos 400ms, y lo registra."""
    now_ts = datetime.now().timestamp()
    clean_code = code.strip()

    if not clean_code:
        return None

    # Deduplicación rápida (útil cuando tanto evdev como el navegador capturan el mismo escaneo)
    last_time = last_scan_dedup.get(clean_code, 0.0)
    if (now_ts - last_time) < 0.40:
        logger.debug(f"Escaneo duplicado ignorado: {clean_code} ({source})")
        return None
    last_scan_dedup[clean_code] = now_ts

    product = find_product_by_code(clean_code)
    is_scanner = duration_ms < 90.0 or source == "evdev_hardware"

    record = {
        "id": str(uuid.uuid4())[:8],
        "code": clean_code,
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "duration_ms": round(duration_ms, 1),
        "source": source,
        "is_scanner": is_scanner,
        "product": product.model_dump() if product else None,
    }

    scan_history.insert(0, record)
    if len(scan_history) > 100:
        scan_history.pop()

    # Difundir a clientes WebSocket conectados
    await ws_manager.broadcast({"type": "scan_event", "data": record})
    return record


@asynccontextmanager
async def lifespan(app: FastAPI):
    global evdev_listener
    logger.info("Iniciando aplicación de escáner Symbol...")
    evdev_listener = EvdevScannerListener()

    async def evdev_callback(code: str, duration_ms: float, source: str):
        await process_and_record_scan(code, duration_ms, source)

    evdev_listener.register_callback(evdev_callback)
    started = await evdev_listener.start()
    if started:
        logger.info("Monitor de hardware evdev iniciado exitosamente.")
    else:
        logger.info("Monitor evdev no disponible. El escaneo funcionará vía Web Keyboard Wedge.")

    yield

    logger.info("Cerrando aplicación...")
    if evdev_listener:
        await evdev_listener.stop()


app = FastAPI(
    title="Symbol Barcode Scanner Testbench",
    description="Mini app para probar el lector de código de barras Symbol Technologies USB",
    version="1.0.0",
    lifespan=lifespan,
)

# Montar estáticos y plantillas
import os
base_dir = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(base_dir, "static")
templates_dir = os.path.join(base_dir, "templates")

app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)


class ScanInput(BaseModel):
    code: str
    duration_ms: float = 25.0
    source: str = "web_wedge"


@app.get("/", response_class=HTMLResponse)
async def home_page(request: Request):
    device_info = get_scanner_info()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "device": device_info,
            "sample_products": SAMPLE_PRODUCTS,
            "supported_formats": SUPPORTED_FORMATS,
            "scans": scan_history[:15],
        },
    )


@app.get("/printable", response_class=HTMLResponse)
async def printable_page(request: Request):
    """Página con códigos en alta resolución optimizada para imprimir o escanear en pantalla."""
    return templates.TemplateResponse(
        request=request,
        name="printable.html",
        context={
            "sample_products": SAMPLE_PRODUCTS,
        },
    )


@app.get("/api/device")
async def api_device_info():
    """Retorna información técnica y estado del dispositivo USB conectado."""
    info = get_scanner_info()
    info["evdev_active"] = evdev_listener._running if evdev_listener else False
    return JSONResponse(info)


@app.get("/api/catalog")
async def api_catalog():
    """Retorna la lista de productos de ejemplo y sus códigos."""
    return JSONResponse([p.model_dump() for p in SAMPLE_PRODUCTS])


@app.get("/api/barcode/{format_name}/{code}.svg")
async def api_barcode_svg(format_name: str, code: str):
    """Genera y retorna un código de barras en formato SVG dinámico."""
    svg_content, error = generate_svg(format_name, code)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return Response(content=svg_content, media_type="image/svg+xml")


@app.get("/api/barcode/{format_name}/{code}.png")
async def api_barcode_png(format_name: str, code: str):
    """Genera y retorna un código de barras en imagen PNG descargable."""
    png_bytes, error = generate_png_bytes(format_name, code)
    if error or not png_bytes:
        raise HTTPException(status_code=400, detail=error or "No se pudo generar PNG")
    return Response(content=png_bytes, media_type="image/png")


@app.post("/api/scan")
async def api_record_scan(scan: ScanInput):
    """Registra un escaneo manual o capturado por el wedge web."""
    record = await process_and_record_scan(scan.code, scan.duration_ms, scan.source)
    if not record:
        return JSONResponse({"status": "ignored_or_empty"})
    return JSONResponse({"status": "success", "data": record})


@app.get("/api/scans")
async def api_get_scans():
    """Retorna el historial de escaneos de la sesión."""
    return JSONResponse(scan_history)


@app.delete("/api/scans")
async def api_clear_scans():
    """Limpia el historial de escaneos."""
    scan_history.clear()
    await ws_manager.broadcast({"type": "history_cleared"})
    return JSONResponse({"status": "cleared"})


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket para eventos de escaneo en tiempo real."""
    await ws_manager.connect(websocket)
    try:
        while True:
            # Mantener conexión abierta y recibir mensajes de control o pings del cliente
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except Exception:
                pass
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
