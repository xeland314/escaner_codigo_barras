# 🏷️ Suite de Pruebas y Uso para Escáner de Código de Barras Symbol Technologies (05e0:1200)

Mini aplicación interactiva construida en **Python**, administrada con **uv** y con interfaz web en tiempo real desarrollada en **FastAPI**. Diseñada para probar, diagnosticar y aprender a integrar el lector de códigos de barras USB **Symbol Technologies Bar Code Scanner (`ID 05e0:1200`)**.

---

## 🔬 ¿Cómo funciona el escáner Symbol USB?

El escáner conectado tiene las siguientes características en el sistema Linux:
* **Vendor ID / Product ID:** `05e0:1200` (Symbol Technologies / Zebra Enterprise).
* **Clase USB:** `bInterfaceClass 3` (Human Interface Device - HID).
* **Protocolo:** `bInterfaceProtocol 1` (Keyboard / Boot Interface).
* **Driver en Linux:** `usbhid` / `hid-generic`.
* **Nodo en Linux:** `/dev/input/event13` (o `/dev/input/by-id/usb-*Symbol*-event-kbd`).

### Mecanismo de Funcionamiento (USB HID Keyboard Wedge)
1. **Decodificación Óptica:** Al presionar el gatillo, el sensor óptico / láser lee la reflectividad de las barras y espacios (o matriz 2D). El microprocesador interno decodifica la simbología según los estándares (EAN-13, Code 128, Code 39, etc.) y verifica el dígito de control o checksum.
2. **Emulación de Teclado:** El lector **emula un teclado USB estándar**. No requiere ningún driver propietario.
3. **Ráfaga de Teclas de Alta Velocidad:** Cada carácter decodificado se envía a la computadora como eventos de teclado estándar (`KeyDown` y `KeyUp`).
   * A diferencia de un humano (que escribe con intervalos de 80ms a 300ms), el escáner transmite cada carácter en **5ms a 20ms**, completando un código de 13 dígitos en **20ms a 60ms**.
4. **Sufijo Automático:** Por defecto de fábrica, el escáner añade automáticamente la pulsación de la tecla **`Enter` (`KEY_ENTER` / `\r` / `\n`)** al final de la lectura.
5. **Doble Método de Integración:**
   * **Modo A (Wedge en Navegador / GUI):** Cualquier campo de texto enfocado o listener global de teclado en JavaScript recibe la cadena sin requerir privilegios de superusuario.
   * **Modo B (Hardware evdev en Segundo Plano):** El backend en Python puede conectarse directamente a `/dev/input/event13` mediante `evdev` para recibir escaneos incluso si el navegador o la aplicación no están en primer plano.

---

## 🚀 Requisitos y Puesta en Marcha con `uv`

El proyecto se gestiona completamente con **[uv](https://github.com/astral-sh/uv)**.

### 1. Iniciar la Interfaz Web (FastAPI)
```bash
uv run escaner-codigo-barras
# o explícitamente:
uv run escaner-codigo-barras server --port 8000
```
Luego abre tu navegador en:
👉 **[http://localhost:8000](http://localhost:8000)**

### 2. Probar en Terminal (Modo CLI Stdin)
Si solo deseas capturar escaneos en la terminal sin interfaz gráfica:
```bash
uv run escaner-codigo-barras cli
```
Apunta el lector a cualquier código y presiona el gatillo. Verás la salida instantánea con información del producto y longitud.

### 3. Monitor Directo de Hardware (`evdev`)
Para ver eventos crudos capturados a nivel de kernel en segundo plano:
```bash
uv run escaner-codigo-barras evdev
```

---

## 📦 Códigos de Barras de Ejemplo Incluidos

La aplicación incluye un catálogo interactivo con generación vectorial **SVG** de alta nitidez y descarga **PNG**:

| Simbología | Formato | Código de Ejemplo | Nombre / Uso Demo |
| :--- | :--- | :--- | :--- |
| **EAN-13** | Retail Global | `7501031311309` | Refresco Coca-Cola 600ml |
| **EAN-13** | Retail Global | `7501000111203` | Pan de Caja Bimbo Grande |
| **EAN-13** | Retail Global | `7501008045612` | Leche Alpura 1L |
| **EAN-13** | Libros (ISBN) | `9780132350884` | Libro Clean Code (R. Martin) |
| **UPC-A** | Retail EE.UU. (12 dígitos) | `012345678905` | Cereal Cheerios Avena |
| **UPC-A** | Retail EE.UU. (12 dígitos) | `049000000443` | Bebida Sprite 355ml |
| **Code 128** | Alfanumérico Logística | `SKU-LAPTOP-M3` | Laptop ThinkPad Ultra 16" |
| **Code 128** | Serial de Fábrica | `SN-SYM-05E0-1200` | Escáner Symbol USB |
| **Code 128** | Guía de Envío | `PKG-FEDEX-98214` | Etiqueta Despacho Prioritario |
| **Code 39** | Industrial / Almacén | `MOTOR-MOD44` | Motor NEMA 23 Industrial |
| **Code 39** | Lote de Fabricación | `LOTE-OCT-2026` | Materia Prima Polímero Grado A |
| **EAN-8** | Empaques Compactos | `96385074` | Pastillas Trident Menta |
| **EAN-8** | Empaques Compactos | `12345670` | Barra de Chocolate 30g |
| **QR Code** | Matriz 2D | `https://github.com` | Enlace Documentación Técnica |
| **QR Code** | Matriz 2D Serializada | `PROD:SYM-SCAN;LOTE:2026;PRECIO:1250` | Ficha Técnica Estructurada |

> **💡 Consejo para escanear en pantalla:** Puedes hacer clic en el botón **"🔍 Ampliar"** de cualquier tarjeta en la interfaz web para abrir el código en un modal a pantalla completa con fondo blanco de alto contraste. Para mejores resultados, coloca el lector a una distancia de **10 a 20 cm** de la pantalla.

---

## 🖨️ Hoja Imprimible
Si el reflejo de la pantalla dificulta la lectura con el haz láser, accede a la ruta de impresión:
👉 **[http://localhost:8000/printable](http://localhost:8000/printable)**
Presiona `Ctrl + P` para imprimir la hoja optimizada en papel con márgenes y guías de corte.

---

## 🛠️ Estructura del Proyecto

```
escaner_codigo_barras/
├── pyproject.toml                     # Configuración del proyecto y dependencias uv
├── 99-symbol-barcode.rules            # Regla udev para permisos Linux
├── README.md                          # Documentación completa
└── src/escaner_codigo_barras/
    ├── __init__.py
    ├── main.py                        # Punto de entrada unificado (server, cli, evdev)
    ├── app.py                         # Servidor FastAPI, WebSockets y rutas API
    ├── device_info.py                 # Inspección de hardware USB y sysfs
    ├── evdev_monitor.py               # Listener asíncrono evdev de bajo nivel
    ├── catalog.py                     # Base de datos simulada de productos y códigos
    ├── barcode_generator.py           # Generador vectorial SVG y PNG (python-barcode & qrcode)
    ├── cli.py                         # Interfaz interactiva de terminal stdin
    ├── evdev_cli.py                   # Monitor de terminal directo sobre /dev/input
    ├── static/
    │   ├── css/style.css              # Estilos responsivos con tema oscuro
    │   └── js/app.js                  # Algoritmo Keyboard Wedge + Sonido POS Web Audio
    └── templates/
        ├── index.html                 # Dashboard interactivo principal
        └── printable.html             # Hoja de códigos para impresión física
```

---

## ⚙️ Reglas Udev (Permisos en Linux)

Para permitir que usuarios sin privilegios `sudo` lean directamente el nodo `/dev/input/event*`:
```bash
sudo cp 99-symbol-barcode.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger
```
*(Ya configurado y activado en este sistema).*
