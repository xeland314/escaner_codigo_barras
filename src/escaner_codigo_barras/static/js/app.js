/**
 * Symbol Barcode Scanner Lab - Frontend Logic
 * - USB HID Keyboard Wedge detector with keystroke timing analysis
 * - Synthetic POS checkout beep via Web Audio API
 * - Real-time WebSocket sync
 * - Interactive modal zoom for scanning off-screen
 */

class SoundEffects {
  constructor() {
    this.ctx = null;
    this.enabled = localStorage.getItem("scanner_sound") !== "false";
  }

  init() {
    if (!this.ctx) {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      if (AudioContextClass) {
        this.ctx = new AudioContextClass();
      }
    }
    if (this.ctx && this.ctx.state === "suspended") {
      this.ctx.resume();
    }
  }

  toggle() {
    this.enabled = !this.enabled;
    localStorage.setItem("scanner_sound", this.enabled ? "true" : "false");
    if (this.enabled) {
      this.playSuccess();
    }
    return this.enabled;
  }

  playSuccess() {
    if (!this.enabled) return;
    this.init();
    if (!this.ctx) return;

    try {
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();

      osc.type = "sine";
      // Típico pitido agudo y limpio de caja registradora / escáner Symbol (1950 Hz)
      osc.frequency.setValueAtTime(1950, this.ctx.currentTime);

      gain.gain.setValueAtTime(0.3, this.ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + 0.08);

      osc.connect(gain);
      gain.connect(this.ctx.destination);

      osc.start();
      osc.stop(this.ctx.currentTime + 0.08);
    } catch (e) {
      console.warn("Error reproduciendo audio:", e);
    }
  }

  playMatch() {
    if (!this.enabled) return;
    this.init();
    if (!this.ctx) return;

    try {
      const now = this.ctx.currentTime;
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();

      osc.type = "sine";
      osc.frequency.setValueAtTime(1800, now);
      osc.frequency.setValueAtTime(2400, now + 0.04);

      gain.gain.setValueAtTime(0.35, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.11);

      osc.connect(gain);
      gain.connect(this.ctx.destination);

      osc.start(now);
      osc.stop(now + 0.11);
    } catch (e) {
      console.warn("Error reproduciendo audio:", e);
    }
  }
}

const sounds = new SoundEffects();

// Wedge Keystroke Buffer Detector
let wedgeBuffer = [];
let lastKeyTime = 0;
let keyIntervals = [];

window.addEventListener("keydown", (e) => {
  // Ignorar si el foco está en un input o select y no es Enter
  const isInput = ["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement?.tagName);
  if (isInput && document.activeElement.id === "manual-code-input" && e.key !== "Enter") {
    return;
  }

  const now = performance.now();
  const timeSinceLastKey = now - lastKeyTime;

  // Si pasaron más de 350ms desde la última tecla, reiniciar buffer
  if (timeSinceLastKey > 350) {
    wedgeBuffer = [];
    keyIntervals = [];
  }

  if (e.key === "Enter") {
    if (wedgeBuffer.length > 0) {
      e.preventDefault();
      const code = wedgeBuffer.join("");
      const totalDuration = keyIntervals.reduce((a, b) => a + b, 0);
      const avgInterval = keyIntervals.length > 0 ? totalDuration / keyIntervals.length : 100;
      const isScannerSpeed = avgInterval < 55; // Escáner físico envía teclas en < 50ms

      sendScanEvent(code, totalDuration, isScannerSpeed ? "usb_scanner_wedge" : "manual_keyboard");

      wedgeBuffer = [];
      keyIntervals = [];
    }
    return;
  }

  // Capturar solo caracteres imprimibles
  if (e.key.length === 1) {
    if (wedgeBuffer.length > 0) {
      keyIntervals.push(timeSinceLastKey);
    }
    wedgeBuffer.push(e.key);
    lastKeyTime = now;
  }
});

// Enviar escaneo al backend FastAPI
async function sendScanEvent(code, durationMs = 25.0, source = "usb_scanner_wedge") {
  try {
    const res = await fetch("/api/scan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        code: code.trim(),
        duration_ms: durationMs,
        source: source,
      }),
    });
    const data = await res.json();
    if (data.data) {
      updateScanUI(data.data);
    }
  } catch (err) {
    console.error("Error al registrar escaneo:", err);
  }
}

// WebSocket para actualización en vivo bidireccional
let ws = null;
function initWebSocket() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${window.location.host}/ws`;

  ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    console.log("WebSocket conectado al escáner Symbol.");
    const dot = document.getElementById("ws-status-dot");
    if (dot) dot.style.background = "#22c55e";
  };

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      if (msg.type === "scan_event") {
        updateScanUI(msg.data);
      } else if (msg.type === "history_cleared") {
        clearTableUI();
      }
    } catch (err) {
      console.error("Error procesando mensaje WebSocket:", err);
    }
  };

  ws.onclose = () => {
    const dot = document.getElementById("ws-status-dot");
    if (dot) dot.style.background = "#f43f5e";
    setTimeout(initWebSocket, 2000);
  };
}

// Actualizar elementos visuales cuando ocurre un escaneo
function updateScanUI(scan) {
  // Sonido
  if (scan.product) {
    sounds.playMatch();
  } else {
    sounds.playSuccess();
  }

  // Animación del panel objetivo
  const targetBox = document.getElementById("scan-target-box");
  if (targetBox) {
    targetBox.classList.add("active-scan");
    setTimeout(() => targetBox.classList.remove("active-scan"), 600);
  }

  // Texto del código
  const codeDisplay = document.getElementById("last-scanned-code");
  if (codeDisplay) {
    codeDisplay.textContent = scan.code;
  }

  // Metadatos
  const metaDisplay = document.getElementById("last-scan-meta");
  if (metaDisplay) {
    const hardwareBadge = scan.is_scanner
      ? '<span class="badge badge-connected">Escáner Óptico Hardware</span>'
      : '<span class="badge badge-info">Teclado Manual</span>';
    metaDisplay.innerHTML = `
      <span>Hora: <strong>${scan.timestamp}</strong></span>
      <span>Duración: <strong>${scan.duration_ms} ms</strong></span>
      <span>Origen: <strong>${scan.source}</strong></span>
      ${hardwareBadge}
    `;
  }

  // Tarjeta de producto coincidente
  const productBox = document.getElementById("last-scan-product");
  if (productBox) {
    if (scan.product) {
      productBox.style.display = "flex";
      productBox.innerHTML = `
        <div>
          <div class="product-info-title">${scan.product.name}</div>
          <div class="product-info-meta">
            ${scan.product.category} • Código: ${scan.product.code} • Stock: ${scan.product.stock} un.
          </div>
          <p style="font-size: 0.8rem; color: #cbd5e1; margin-top: 4px;">${scan.product.description}</p>
        </div>
        <div>
          <div class="product-info-price">$${scan.product.price.toFixed(2)}</div>
        </div>
      `;
    } else {
      productBox.style.display = "flex";
      productBox.innerHTML = `
        <div style="color: #cbd5e1;">
          <div style="font-weight: 600; color: #38bdf8;">Código no registrado en catálogo demo</div>
          <div style="font-size: 0.85rem;">Longitud: ${scan.code.length} caracteres. Decodificado correctamente por el Symbol.</div>
        </div>
      `;
    }
  }

  // Agregar fila a la tabla de historial
  appendRowToHistoryTable(scan);
}

function appendRowToHistoryTable(scan) {
  const tbody = document.getElementById("history-table-body");
  if (!tbody) return;

  const emptyRow = document.getElementById("empty-history-row");
  if (emptyRow) emptyRow.remove();

  const tr = document.createElement("tr");
  const prodName = scan.product ? scan.product.name : "<em>No en catálogo</em>";
  const badgeClass = scan.is_scanner ? "badge-connected" : "badge-info";
  const badgeLabel = scan.is_scanner ? "Escáner Óptico" : "Manual";

  tr.innerHTML = `
    <td>${scan.timestamp}</td>
    <td class="code-cell">${scan.code}</td>
    <td>${prodName}</td>
    <td>${scan.duration_ms} ms</td>
    <td><span class="badge ${badgeClass}">${badgeLabel}</span></td>
    <td><span style="font-size: 0.8rem; color: #94a3b8;">${scan.source}</span></td>
  `;

  tbody.insertBefore(tr, tbody.firstChild);
}

function clearTableUI() {
  const tbody = document.getElementById("history-table-body");
  if (tbody) {
    tbody.innerHTML = `
      <tr id="empty-history-row">
        <td colspan="6" style="text-align: center; color: var(--text-muted); padding: 2rem;">
          No hay escaneos en esta sesión. Apunta tu lector a un código de barras.
        </td>
      </tr>
    `;
  }
}

// Modal de Zoom para escanear en pantalla
function openBarcodeModal(code, format, name) {
  const modal = document.getElementById("barcode-modal");
  const modalTitle = document.getElementById("modal-barcode-title");
  const modalCode = document.getElementById("modal-barcode-code");
  const modalImg = document.getElementById("modal-barcode-svg");

  if (modalTitle) modalTitle.textContent = name;
  if (modalCode) modalCode.textContent = `${code} (${format.toUpperCase()})`;
  if (modalImg) {
    modalImg.innerHTML = `<img src="/api/barcode/${format}/${encodeURIComponent(code)}.svg" style="max-height: 220px; width: auto;" alt="Código" />`;
  }

  if (modal) modal.classList.add("active");
}

function closeBarcodeModal() {
  const modal = document.getElementById("barcode-modal");
  if (modal) modal.classList.remove("active");
}

// Inicialización de componentes al cargar la página
document.addEventListener("DOMContentLoaded", () => {
  initWebSocket();

  // Botón de sonido
  const soundBtn = document.getElementById("sound-toggle-btn");
  if (soundBtn) {
    const updateSoundLabel = () => {
      soundBtn.innerHTML = sounds.enabled
        ? `🔊 Sonido POS: ON`
        : `🔇 Sonido POS: OFF`;
      soundBtn.className = sounds.enabled ? "btn btn-success" : "btn btn-secondary";
    };
    updateSoundLabel();
    soundBtn.addEventListener("click", () => {
      sounds.toggle();
      updateSoundLabel();
    });
  }

  // Input manual de escaneo
  const manualInput = document.getElementById("manual-code-input");
  const manualBtn = document.getElementById("manual-code-btn");
  if (manualBtn && manualInput) {
    const triggerManual = () => {
      const code = manualInput.value.trim();
      if (code) {
        sendScanEvent(code, 45.0, "manual_input_button");
        manualInput.value = "";
      }
    };
    manualBtn.addEventListener("click", triggerManual);
    manualInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        triggerManual();
      }
    });
  }

  // Limpiar historial
  const clearBtn = document.getElementById("clear-history-btn");
  if (clearBtn) {
    clearBtn.addEventListener("click", async () => {
      await fetch("/api/scans", { method: "DELETE" });
      clearTableUI();
    });
  }

  // Pestañas (Tabs)
  const tabBtns = document.querySelectorAll(".tab-btn");
  tabBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      tabBtns.forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".tab-pane").forEach((p) => p.classList.remove("active"));

      btn.classList.add("active");
      const targetId = btn.getAttribute("data-tab");
      const targetPane = document.getElementById(targetId);
      if (targetPane) targetPane.classList.add("active");
    });
  });

  // Filtros de categoría de códigos
  const filterChips = document.querySelectorAll(".filter-chip");
  filterChips.forEach((chip) => {
    chip.addEventListener("click", () => {
      filterChips.forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
      const fmt = chip.getAttribute("data-filter");

      document.querySelectorAll(".barcode-card").forEach((card) => {
        const cardFmt = card.getAttribute("data-format");
        if (fmt === "all" || cardFmt === fmt) {
          card.style.display = "flex";
        } else {
          card.style.display = "none";
        }
      });
    });
  });

  // Generador personalizado
  const genForm = document.getElementById("custom-generator-form");
  if (genForm) {
    genForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const codeInput = document.getElementById("gen-code-input").value.trim();
      const formatSelect = document.getElementById("gen-format-select").value;
      const previewBox = document.getElementById("gen-preview-box");
      const dlSvgBtn = document.getElementById("gen-download-svg");
      const dlPngBtn = document.getElementById("gen-download-png");

      if (!codeInput) return;

      const svgUrl = `/api/barcode/${formatSelect}/${encodeURIComponent(codeInput)}.svg`;
      const pngUrl = `/api/barcode/${formatSelect}/${encodeURIComponent(codeInput)}.png`;

      previewBox.innerHTML = `
        <div style="background: #fff; padding: 1.5rem; border-radius: 8px; display: flex; justify-content: center; align-items: center; width: 100%;">
          <img src="${svgUrl}?t=${Date.now()}" style="max-height: 180px; max-width: 100%;" alt="Generado" />
        </div>
      `;

      if (dlSvgBtn) {
        dlSvgBtn.href = svgUrl;
        dlSvgBtn.style.display = "inline-flex";
      }
      if (dlPngBtn) {
        dlPngBtn.href = pngUrl;
        dlPngBtn.style.display = "inline-flex";
      }
    });
  }

  // Modal cerrar al hacer clic afuera
  const modal = document.getElementById("barcode-modal");
  if (modal) {
    modal.addEventListener("click", (e) => {
      if (e.target === modal) closeBarcodeModal();
    });
  }
});
