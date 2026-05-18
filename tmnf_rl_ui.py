"""
TMInterface Reinforcement Learning UI

Bu uygulama, TMInterface'den gelen verileri gorsellestirir ve
bir RL ajaninin egitimini yonetmek icin kontroller sunar.
"""

import os
import time
import sys
import threading
import queue
import math
import socket
import json
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

# Gerekli kutuphaneleri import et
try:
    import tkinter as tk
    from tkinter import ttk
    from tkinter import font, messagebox, filedialog, simpledialog
    from tmnf_env import TMNFEnv
    from car_state import CarState
    from stable_baselines3 import PPO
    from stable_baselines3.common.callbacks import BaseCallback
except ImportError as e:
    print("=" * 80)
    print(f"HATA: Gerekli bir modul bulunamadi! -> {e.name}")
    print("=" * 80)
    print("\nLutfen eksik modulleri yukleyin. Ornegin:")
    print("  pip install stable-baselines3[extra] gymnasium")
    print("=" * 80)
    sys.exit(1)


class StopTrainingCallback(BaseCallback):
    """
    Egitimi disaridan durdurmak ve UI'yi guncellemek icin kullanilan ozel callback.
    """
    def __init__(self, app, verbose=0):
        """Egitim dongusunun UI tarafindaki durdurma bayragini okuyabilmesi icin app referansini saklar."""
        super(StopTrainingCallback, self).__init__(verbose)
        self.app = app

    def _on_rollout_end(self) -> None:
        """
        Her n_steps'de (bizim icin 32) bir cagrilir.
        Adim sayisini guncellemek icin en guvenilir yer burasidir.
        self.num_timesteps, o anki toplam adim sayisini tutar.
        """
        self.app.current_step_count = self.num_timesteps

    def _on_step(self) -> bool:
        """Her PPO adiminda egitimin devam edip etmeyecegini bildirir."""
        # App icindeki bayrak (flag) kontrol edilir.
        # Eger bayrak True ise, egitimi durdur (False dondur).
        return not self.app.training_should_stop


TRAFFIC_MONITOR_HTML = r"""<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>TMNF TCP Trafik Monitoru</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #15181c;
      --panel: #22272e;
      --line: #353c45;
      --text: #eef2f5;
      --muted: #9aa7b4;
      --in: #50d890;
      --out: #69a7ff;
      --sys: #ffc857;
      --bad: #ff6b6b;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font: 14px/1.45 "Segoe UI", system-ui, sans-serif;
    }
    header, main { max-width: 1200px; margin: 0 auto; padding: 18px; }
    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      border-bottom: 1px solid var(--line);
    }
    h1 { margin: 0; font-size: 22px; }
    .status { color: var(--sys); font-family: Consolas, monospace; }
    .grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 14px;
    }
    .card {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
    }
    .label { color: var(--muted); font-size: 12px; }
    .value { margin-top: 4px; font: 20px Consolas, monospace; }
    .toolbar {
      display: flex;
      gap: 8px;
      align-items: center;
      margin: 12px 0;
      flex-wrap: wrap;
    }
    button, input {
      background: #2d333b;
      color: var(--text);
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 8px 10px;
      font: inherit;
    }
    button.active { border-color: var(--out); color: white; }
    input { min-width: 260px; flex: 1; }
    .log {
      height: calc(100vh - 260px);
      min-height: 360px;
      overflow: auto;
      border: 1px solid var(--line);
      background: #101317;
      border-radius: 8px;
    }
    table { width: 100%; border-collapse: collapse; table-layout: fixed; }
    th, td { padding: 8px 10px; border-bottom: 1px solid #252b32; vertical-align: top; }
    th { position: sticky; top: 0; background: #1b2026; color: var(--muted); text-align: left; }
    .time { width: 110px; color: var(--muted); font-family: Consolas, monospace; }
    .dir { width: 120px; font-weight: 700; }
    .payload { font-family: Consolas, monospace; white-space: pre-wrap; overflow-wrap: anywhere; }
    .in { color: var(--in); }
    .out { color: var(--out); }
    .system { color: var(--sys); }
    .error { color: var(--bad); }
    @media (max-width: 760px) {
      header { align-items: flex-start; flex-direction: column; }
      .grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .dir { width: 90px; }
      .time { width: 92px; }
    }
  </style>
</head>
<body>
  <header>
    <div>
      <h1>TMNF TCP Trafik Monitoru</h1>
      <div class="label">Plugin portu: 127.0.0.1:8765 | Web monitor: 127.0.0.1:8766</div>
    </div>
    <div id="status" class="status">baglaniyor</div>
  </header>
  <main>
    <section class="grid">
      <div class="card"><div class="label">Gelen</div><div id="inCount" class="value in">0</div></div>
      <div class="card"><div class="label">Giden</div><div id="outCount" class="value out">0</div></div>
      <div class="card"><div class="label">Toplam</div><div id="totalCount" class="value">0</div></div>
      <div class="card"><div class="label">Son veri</div><div id="lastSeen" class="value">--</div></div>
    </section>
    <div class="toolbar">
      <button data-filter="all" class="active">Hepsi</button>
      <button data-filter="in">Gelen</button>
      <button data-filter="out">Giden</button>
      <button data-filter="system">Sistem</button>
      <button id="clearBtn">Temizle</button>
      <input id="search" placeholder="Filtrele: steer, checkpoint, 1000..." autocomplete="off">
    </div>
    <section class="log">
      <table>
        <thead><tr><th class="time">Saat</th><th class="dir">Yon</th><th>Veri</th></tr></thead>
        <tbody id="rows"></tbody>
      </table>
    </section>
  </main>
  <script>
    const rows = document.getElementById("rows");
    const statusEl = document.getElementById("status");
    const searchEl = document.getElementById("search");
    const counts = { in: 0, out: 0, system: 0, error: 0 };
    let activeFilter = "all";
    let total = 0;
    const maxRows = 500;

    function label(direction) {
      if (direction === "in") return "OYUN -> PY";
      if (direction === "out") return "PY -> OYUN";
      if (direction === "error") return "HATA";
      return "SISTEM";
    }

    function applyFilters() {
      const q = searchEl.value.toLowerCase();
      for (const tr of rows.children) {
        const dirOk = activeFilter === "all" || tr.dataset.direction === activeFilter;
        const textOk = !q || tr.dataset.text.includes(q);
        tr.style.display = dirOk && textOk ? "" : "none";
      }
    }

    function addEvent(item) {
      const tr = document.createElement("tr");
      tr.dataset.direction = item.direction;
      tr.dataset.text = `${item.direction} ${item.payload}`.toLowerCase();
      tr.innerHTML = `<td class="time">${item.time}</td><td class="dir ${item.direction}">${label(item.direction)}</td><td class="payload"></td>`;
      tr.querySelector(".payload").textContent = item.payload;
      rows.prepend(tr);
      while (rows.children.length > maxRows) rows.lastElementChild.remove();

      counts[item.direction] = (counts[item.direction] || 0) + 1;
      if (item.direction === "in") document.getElementById("inCount").textContent = counts.in;
      if (item.direction === "out") document.getElementById("outCount").textContent = counts.out;
      total += 1;
      document.getElementById("totalCount").textContent = total;
      document.getElementById("lastSeen").textContent = item.time;
      applyFilters();
    }

    document.querySelectorAll("button[data-filter]").forEach(btn => {
      btn.addEventListener("click", () => {
        document.querySelectorAll("button[data-filter]").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        activeFilter = btn.dataset.filter;
        applyFilters();
      });
    });
    document.getElementById("clearBtn").addEventListener("click", () => rows.textContent = "");
    searchEl.addEventListener("input", applyFilters);

    const es = new EventSource("/events");
    es.onopen = () => { statusEl.textContent = "canli"; statusEl.style.color = "var(--in)"; };
    es.onerror = () => { statusEl.textContent = "baglanti bekleniyor"; statusEl.style.color = "var(--bad)"; };
    es.addEventListener("traffic", e => addEvent(JSON.parse(e.data)));
  </script>
</body>
</html>
"""


class TrafficMonitorHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        """HTTP server konsol loglarini susturur."""
        return

    def do_GET(self):
        """Ana sayfa ve SSE event endpoint isteklerini ayirir."""
        parsed = urlparse(self.path)
        if parsed.path == "/events":
            self._serve_events()
        else:
            self._serve_page()

    def _serve_page(self):
        """Trafik monitorunun HTML arayuzunu dondurur."""
        body = TRAFFIC_MONITOR_HTML.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_events(self):
        """Kaydedilen trafik olaylarini tarayiciya SSE ile canli yollar."""
        app = self.server.app
        last_id = max(0, app.get_latest_traffic_id() - 200)
        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            while not app.web_monitor_stop.is_set():
                events = app.get_traffic_events_after(last_id)
                if events:
                    for event in events:
                        last_id = event["id"]
                        data = json.dumps(event, ensure_ascii=False)
                        self.wfile.write(f"id: {last_id}\nevent: traffic\ndata: {data}\n\n".encode("utf-8"))
                    self.wfile.flush()
                else:
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
                    time.sleep(0.25)
        except (BrokenPipeError, ConnectionResetError, OSError):
            return


class App(tk.Tk):
    def __init__(self):
        """Tkinter arayuzunu, egitim durumunu ve soket/web monitor durumunu hazirlar."""
        super().__init__()

        self.title("TMNF RL Kontrol Paneli")
        self.geometry("760x820")
        self.minsize(680, 720)
        self.configure(bg="#202225")

        # --- Stil Ayarlari ---
        style = ttk.Style(self)
        style.theme_use('clam')
        # ... (Stil kodlari ayni kaliyor)
        dark_bg = "#202225"
        panel_bg = "#2B2E33"
        panel_border = "#3C4148"
        light_text = "#EAEAEA"
        muted_text = "#AAB2BF"
        value_text = "#48D6C8" # Turkuaz
        header_text = "#FFFFFF"
        status_running_text = "#8AE234" # Yesil
        status_stopped_text = "#EF2929" # Kirmizi
        status_idle_text = "#729FCF" # Mavi

        style.configure("TFrame", background=dark_bg)
        style.configure("Panel.TFrame", background=panel_bg)
        style.configure("TLabel", background=dark_bg, foreground=light_text, font=("Segoe UI", 10))
        style.configure("Panel.TLabel", background=panel_bg, foreground=light_text, font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background=panel_bg, foreground=muted_text, font=("Segoe UI", 9))
        style.configure("Title.TLabel", background=dark_bg, foreground=header_text, font=("Segoe UI", 18, "bold"))
        style.configure("Header.TLabel", background=panel_bg, foreground=header_text, font=("Segoe UI", 12, "bold"))
        style.configure("Value.TLabel", background=panel_bg, foreground=value_text, font=("Consolas", 11, "bold"))
        style.configure("Metric.TLabel", background=panel_bg, foreground=value_text, font=("Consolas", 14, "bold"))
        style.configure("Status.Running.TLabel", background=panel_bg, foreground=status_running_text, font=("Segoe UI", 10, "bold"))
        style.configure("Status.Stopped.TLabel", background=panel_bg, foreground=status_stopped_text, font=("Segoe UI", 10, "bold"))
        style.configure("Status.Idle.TLabel", background=panel_bg, foreground=status_idle_text, font=("Segoe UI", 10, "bold"))
        style.configure("Panel.TLabelframe", background=panel_bg, foreground=header_text, bordercolor=panel_border, relief="solid")
        style.configure("Panel.TLabelframe.Label", background=dark_bg, foreground=header_text, font=("Segoe UI", 11, "bold"))

        style.configure("TButton", background="#42474F", foreground=light_text, font=("Segoe UI", 10, "bold"), borderwidth=0, relief="flat", padding=(10, 7))
        style.map("TButton", background=[('active', '#505761'), ('disabled', '#30343A')], foreground=[('disabled', '#777777')])
        style.configure("Success.TButton", background="#3F7F52", foreground=light_text)
        style.configure("Danger.TButton", background="#8A3A3A", foreground=light_text)
        

        # Veri saklama
        self.data_vars = {
            "time": tk.StringVar(value="0 ms"),
            "pos": tk.StringVar(value="(0.00, 0.00, 0.00)"),
            "speed": tk.StringVar(value="0.00 km/h"),
            "vel": tk.StringVar(value="(0.00, 0.00, 0.00)"),
            "rot_yaw_deg": tk.StringVar(value="0.0"), # YENI: Stabil Yaw (Derece)
            "rot_yaw_rad": tk.StringVar(value="0.00"), # YENI: Stabil Yaw (Radyan)
            "checkpoint": tk.StringVar(value="0"),
            "lap": tk.StringVar(value="0"),
            "target_cp_pos": tk.StringVar(value="(0, 0, 0)"), # YENI: Hedef CP Pozisyonu
            "listener_status": tk.StringVar(value="Durduruldu"),
            "training_status": tk.StringVar(value="Bekliyor"),
            "fps": tk.StringVar(value="0.0 FPS"),
            "reward_current": tk.StringVar(value="0.00"),
            "reward_total": tk.StringVar(value="0.00"),
            "direction": tk.StringVar(value="--"),
            "step_count": tk.StringVar(value="Adim: 0"), # YENI: Adim sayaci
            "contact": tk.StringVar(value="--"), # YENI: Duvara temas icin
            "model_path": tk.StringVar(value="Model yok")
        }

        # Threading ve Egitim Yonetimi
        self.listener_running = False
        self.training_running = False
        self.training_should_stop = False
        self.watch_running = False
        self.watch_should_stop = False
        self.current_step_count = 0 # YENI: Adim sayisini saklamak icin
        self.data_queue = queue.Queue()
        self.status_queue = queue.Queue()
        self.listener_thread = None
        self.training_thread = None
        self.watch_thread = None
        self.frame_count = 0
        self.start_time = 0
        self.model = None
        self.loaded_model_path = None
        self.loaded_model_observation_shape = None
        self.env = None
        self.manual_save_folder_name = None
        self.continue_training_from_loaded_model = False
        self.training_source_model_path = None
        self.latest_car_state = None # En son gecerli araba durumunu saklamak icin
        self.latest_state_wall_time = 0.0
        self.data_poll_interval_ms = 50
        self.socket_host = "127.0.0.1"
        self.socket_port = 8765
        self.client_socket = None
        self.socket_lock = threading.Lock()
        self.web_monitor_host = "127.0.0.1"
        self.web_monitor_port = 8766
        self.web_monitor_server = None
        self.web_monitor_thread = None
        self.web_monitor_stop = threading.Event()
        self.traffic_lock = threading.Lock()
        self.traffic_events = []
        self.traffic_next_id = 1

        self.create_widgets()
        self.start_web_monitor()
        self.update_ui()

    def create_widgets(self):
        """Ana pencere panellerini, butonlari ve canli veri etiketlerini olusturur."""
        main_frame = ttk.Frame(self, padding=18, style="TFrame")
        main_frame.pack(expand=True, fill="both")
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)

        title_row = ttk.Frame(main_frame, style="TFrame")
        title_row.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 14))
        title_row.columnconfigure(0, weight=1)
        ttk.Label(title_row, text="TMNF RL Kontrol Paneli", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(title_row, text="TCP 127.0.0.1:8765", style="TLabel").grid(row=0, column=1, sticky="e")

        connection_frame = ttk.LabelFrame(main_frame, text="Baglanti", padding=12, style="Panel.TLabelframe")
        connection_frame.grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=(0, 12))
        connection_frame.columnconfigure(0, weight=1)
        connection_frame.columnconfigure(1, weight=1)
        self.start_listener_button = ttk.Button(connection_frame, text="Veri Izlemeyi Baslat", command=self.start_listening)
        self.start_listener_button.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.stop_listener_button = ttk.Button(connection_frame, text="Veri Izlemeyi Durdur", command=self.stop_listening, state="disabled")
        self.stop_listener_button.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        ttk.Label(connection_frame, text="Soket:", style="Muted.TLabel").grid(row=1, column=0, sticky="w", pady=(10, 0))
        self.listener_status_label = ttk.Label(connection_frame, textvariable=self.data_vars["listener_status"], style="Status.Idle.TLabel")
        self.listener_status_label.grid(row=1, column=1, sticky="e", pady=(10, 0))
        ttk.Label(connection_frame, text="Web:", style="Muted.TLabel").grid(row=2, column=0, sticky="w", pady=(6, 0))
        self.web_monitor_link = ttk.Label(
            connection_frame,
            text=f"http://127.0.0.1:{self.web_monitor_port}",
            style="Value.TLabel",
            cursor="hand2"
        )
        self.web_monitor_link.grid(row=2, column=1, sticky="e", pady=(6, 0))
        self.web_monitor_link.bind("<Button-1>", lambda _event: self.open_web_monitor())

        run_frame = ttk.LabelFrame(main_frame, text="Calisma", padding=12, style="Panel.TLabelframe")
        run_frame.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(0, 12))
        run_frame.columnconfigure(0, weight=1)
        run_frame.columnconfigure(1, weight=1)
        ttk.Label(run_frame, text="Durum:", style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        self.training_status_label = ttk.Label(run_frame, textvariable=self.data_vars["training_status"], style="Status.Idle.TLabel")
        self.training_status_label.grid(row=0, column=1, sticky="e")
        ttk.Label(run_frame, text="Adim:", style="Muted.TLabel").grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.step_count_label = ttk.Label(run_frame, textvariable=self.data_vars["step_count"], style="Status.Idle.TLabel")
        self.step_count_label.grid(row=1, column=1, sticky="e", pady=(8, 0))
        ttk.Label(run_frame, text="FPS:", style="Muted.TLabel").grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.fps_label = ttk.Label(run_frame, textvariable=self.data_vars["fps"], style="Value.TLabel")
        self.fps_label.grid(row=2, column=1, sticky="e", pady=(8, 0))

        telemetry_frame = ttk.LabelFrame(main_frame, text="Canli Telemetri", padding=12, style="Panel.TLabelframe")
        telemetry_frame.grid(row=2, column=0, sticky="nsew", padx=(0, 8), pady=(0, 12))
        telemetry_frame.columnconfigure(1, weight=1)

        grid_map = [
            ("Zaman", "time"),
            ("Hiz", "speed"),
            ("Hareket", "direction"),
            ("Pozisyon", "pos"),
            ("Temas", "contact"),
            ("Hiz Vektoru", "vel"),
            ("Yaw derece", "rot_yaw_deg"),
            ("Yaw radyan", "rot_yaw_rad"),
            ("Checkpoint", "checkpoint"),
            ("Tur", "lap"),
            ("Hedef", "target_cp_pos"),
        ]

        for row, (label_text, var_key) in enumerate(grid_map):
            ttk.Label(telemetry_frame, text=label_text, style="Muted.TLabel").grid(row=row, column=0, sticky="w", pady=4, padx=(0, 14))
            ttk.Label(telemetry_frame, textvariable=self.data_vars[var_key], style="Value.TLabel").grid(row=row, column=1, sticky="ew", pady=4)

        control_frame = ttk.LabelFrame(main_frame, text="Egitim ve Model", padding=12, style="Panel.TLabelframe")
        control_frame.grid(row=2, column=1, sticky="nsew", padx=(8, 0), pady=(0, 12))
        control_frame.columnconfigure(0, weight=1)
        control_frame.columnconfigure(1, weight=1)

        ttk.Label(control_frame, text="Egitim", style="Header.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))
        self.start_button = ttk.Button(control_frame, text="Egitimi Baslat", command=self.start_training, style="Success.TButton")
        self.start_button.grid(row=1, column=0, padx=(0, 6), pady=4, sticky="ew")
        self.stop_button = ttk.Button(control_frame, text="Egitimi Durdur", command=self.stop_training, state="disabled", style="Danger.TButton")
        self.stop_button.grid(row=1, column=1, padx=(6, 0), pady=4, sticky="ew")

        ttk.Separator(control_frame, orient="horizontal").grid(row=2, column=0, columnspan=2, sticky="ew", pady=14)
        ttk.Label(control_frame, text="Model", style="Header.TLabel").grid(row=3, column=0, columnspan=2, sticky="w", pady=(0, 8))
        self.load_model_button = ttk.Button(control_frame, text="Model Yukle", command=self.load_model)
        self.load_model_button.grid(row=4, column=0, padx=(0, 6), pady=4, sticky="ew")
        self.watch_button = ttk.Button(control_frame, text="Modeli Izle", command=self.start_watch, state="disabled", style="Success.TButton")
        self.watch_button.grid(row=4, column=1, padx=(6, 0), pady=4, sticky="ew")
        self.continue_training_button = ttk.Button(control_frame, text="Egitime Devam Et", command=self.start_continue_training, state="disabled", style="Success.TButton")
        self.continue_training_button.grid(row=5, column=0, padx=(0, 6), pady=4, sticky="ew")
        self.unload_model_button = ttk.Button(control_frame, text="Modeli Kaldir", command=self.unload_model, state="disabled")
        self.unload_model_button.grid(row=5, column=1, padx=(6, 0), pady=4, sticky="ew")
        self.stop_watch_button = ttk.Button(control_frame, text="Izlemeyi Durdur", command=self.stop_watch, state="disabled", style="Danger.TButton")
        self.stop_watch_button.grid(row=6, column=0, columnspan=2, pady=4, sticky="ew")
        model_label = ttk.Label(control_frame, textvariable=self.data_vars["model_path"], style="Value.TLabel", wraplength=300)
        model_label.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(8, 0))

        ttk.Separator(control_frame, orient="horizontal").grid(row=8, column=0, columnspan=2, sticky="ew", pady=14)
        reward_frame = ttk.Frame(control_frame, style="Panel.TFrame")
        reward_frame.grid(row=9, column=0, columnspan=2, sticky="ew")
        reward_frame.columnconfigure(0, weight=1)
        reward_frame.columnconfigure(1, weight=1)
        ttk.Label(reward_frame, text="Anlik Odul", style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(reward_frame, text="Toplam Odul", style="Muted.TLabel").grid(row=0, column=1, sticky="w")
        ttk.Label(reward_frame, textvariable=self.data_vars["reward_current"], style="Metric.TLabel").grid(row=1, column=0, sticky="w", pady=(4, 0))
        ttk.Label(reward_frame, textvariable=self.data_vars["reward_total"], style="Metric.TLabel").grid(row=1, column=1, sticky="w", pady=(4, 0))


    # --- Egitim Fonksiyonlari ---
    def has_live_data(self):
        """Soketten son 1 saniye icinde gecerli arac verisi gelip gelmedigini kontrol eder."""
        if not self.listener_running:
            return False
        if not self.latest_car_state or not self.latest_car_state.valid:
            return False
        with self.socket_lock:
            socket_connected = self.client_socket is not None
        return socket_connected and time.time() - self.latest_state_wall_time <= 1.0

    def ensure_live_data_or_warn(self):
        """Egitim/izleme baslamadan once canli veri yoksa kullaniciyi uyarir."""
        if not self.listener_running:
            messagebox.showwarning("Veri yok", "Once Veri Izlemeyi Baslat'a basin.")
            return False

        if not self.latest_car_state or not self.latest_car_state.valid:
            messagebox.showwarning("Veri yok", "Gecerli araba verisi gelmeden baslatilamaz.")
            return False

        if not self.has_live_data():
            messagebox.showwarning("Veri yok", "Canli soket verisi gelmeden baslatilamaz.")
            return False

        return True

    def training_worker(self):
        """Egitimi ayri bir thread'de calistiran fonksiyon"""
        try:
            self.set_training_status("Ortam baslatiliyor...", "running")
            # Ortami baslatirken arayuzun kendisini referans olarak ver
            self.env = TMNFEnv(ui_app=self)
            
            # Model ve log klasorlerini olustur
            default_models_dir = f"models/PPO-{int(time.time())}"
            logdir = "logs"
            if not os.path.exists(logdir): os.makedirs(logdir)
                
            if self.continue_training_from_loaded_model:
                # Devam egitiminde policy agirliklari korunur, sadece env/log hedefi yenilenir.
                self.set_training_status("Model yukleniyor...", "running")
                self.model = PPO.load(self.training_source_model_path, env=self.env, tensorboard_log=logdir)
                self.loaded_model_observation_shape = self.model.observation_space.shape
            else:
                # YENI: Ince ayar yapilmis hiperparametreler
                # learning_rate: Ajanin ogrenme adimlarinin buyuklugu. Daha dusuk, daha stabil.
                # gamma: Gelecekteki odullere verilen onem. Daha yuksek, daha uzun vadeli planlama.
                self.model = PPO(
                    "MlpPolicy", 
                    self.env, 
                    verbose=1, 
                    tensorboard_log=logdir,
                    learning_rate=0.0003,
                    gamma=0.99,
                    n_steps=256,
                    batch_size=64,
                    n_epochs=10,
                    ent_coef=0.01
                )
            
            self.set_training_status("Egitim basladi...", "running")
            
            # Egitimi baslat, durdurma callback'i ile birlikte
            self.model.learn(
                total_timesteps=100000, 
                reset_num_timesteps=False, 
                tb_log_name=f"PPO-continue-{int(time.time())}" if self.continue_training_from_loaded_model else f"PPO-{int(time.time())}",
                callback=StopTrainingCallback(self)
            )
            
            # Egitim bittiginde (dongu tamamlandiginda veya durduruldugunda)
            if self.training_should_stop:
                self.set_training_status("Egitim kullanici tarafindan durduruldu.", "stopped")
                models_dir = self.get_manual_save_dir(default_models_dir)
                if not os.path.exists(models_dir): os.makedirs(models_dir)
                self.model.save(self.get_manual_save_path(models_dir))
            else:
                self.set_training_status("Egitim tamamlandi.", "idle")
                models_dir = default_models_dir
                if not os.path.exists(models_dir): os.makedirs(models_dir)
                self.model.save(f"{models_dir}/final_model")
                
        except Exception as e:
            self.set_training_status(f"HATA: {e}", "stopped")
        finally:
            if self.env:
                self.env.close()
            self.training_running = False
            self.continue_training_from_loaded_model = False
            self.training_source_model_path = None
            self.update_training_buttons()
            
    def start_training(self):
        """Sifirdan PPO egitimini baslatir."""
        if not self.training_running:
            if self.watch_running:
                messagebox.showwarning("Izleme aktif", "Once model izlemeyi durdurun.")
                return

            if not self.ensure_live_data_or_warn():
                return
            
            # Oyuna baglanmadan once kullaniciyi uyar
            if not messagebox.askyesno("Egitimi Baslat", "Egitimi baslatmak uzeresiniz.\n\nTMInterface'in acik ve bir haritanin yuklu oldugundan emin olun.\n\nDevam edilsin mi?"):
                return
            
            # Odul gostergelerini ve adim sayacini sifirla
            self.data_vars["reward_current"].set("0.00")
            self.data_vars["reward_total"].set("0.00")
            self.data_vars["step_count"].set("Adim: 0")
            self.current_step_count = 0

            self.training_running = True
            self.training_should_stop = False
            self.manual_save_folder_name = None
            self.continue_training_from_loaded_model = False
            self.training_source_model_path = None
            self.update_training_buttons()
            self.training_thread = threading.Thread(target=self.training_worker, daemon=True)
            self.training_thread.start()

    def start_continue_training(self):
        """Secili PPO modelini yukleyip egitime kaldigi agirliklardan devam eder."""
        if self.training_running:
            return
        if self.watch_running:
            messagebox.showwarning("Izleme aktif", "Once model izlemeyi durdurun.")
            return
        if not self.loaded_model_path:
            messagebox.showwarning("Model yok", "Once bir model yukleyin.")
            return
        if not self.ensure_live_data_or_warn():
            return
        if not messagebox.askyesno("Egitime Devam Et", "Yuklu model egitime devam edecek.\n\nObservation/action yapisi ayni olmali.\n\nDevam edilsin mi?"):
            return

        self.data_vars["reward_current"].set("0.00")
        self.data_vars["reward_total"].set("0.00")
        self.data_vars["step_count"].set("Adim: 0")
        self.current_step_count = 0

        self.training_running = True
        self.training_should_stop = False
        self.manual_save_folder_name = None
        self.continue_training_from_loaded_model = True
        self.training_source_model_path = self.loaded_model_path
        self.update_training_buttons()
        self.training_thread = threading.Thread(target=self.training_worker, daemon=True)
        self.training_thread.start()

    def stop_training(self):
        """Egitimi durdurma bayragini kaldirir ve manuel kayit adini alir."""
        if self.training_running and not self.training_should_stop:
            folder_name = simpledialog.askstring(
                "Model klasoru",
                "Model hangi klasore kaydedilsin?\n\nBos birakirsan default isim kullanilir."
            )
            self.manual_save_folder_name = self.sanitize_model_folder_name(folder_name)
            self.training_should_stop = True
            self.set_training_status("Durduruluyor...", "stopped")
            self.stop_button.config(state="disabled")

    def sanitize_model_folder_name(self, folder_name):
        """Kullanici girdisini Windows dosya/klasor adi icin guvenli hale getirir."""
        if not folder_name:
            return None

        cleaned = folder_name.strip()
        if not cleaned:
            return None

        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            cleaned = cleaned.replace(char, "_")
        cleaned = cleaned.rstrip(". ")
        return cleaned or None

    def get_manual_save_dir(self, default_models_dir):
        """Manuel kaydin hangi models/ klasorune yazilacagini belirler."""
        if self.manual_save_folder_name:
            return os.path.join("models", self.manual_save_folder_name)
        return default_models_dir

    def get_manual_save_path(self, models_dir):
        """Manuel model dosya adini uretir ve mevcut dosyayi ezmemek icin gerekirse timestamp ekler."""
        if not self.manual_save_folder_name:
            return os.path.join(models_dir, f"manual_save_{int(time.time())}")

        base_path = os.path.join(models_dir, self.manual_save_folder_name)
        zip_path = f"{base_path}.zip"
        # SB3 .save uzantiyi kendi ekledigi icin varlik kontrolu .zip uzerinden yapilir.
        if not os.path.exists(zip_path):
            return base_path

        return os.path.join(models_dir, f"{self.manual_save_folder_name}_{int(time.time())}")

    def update_training_buttons(self):
        """Egitim durumuna gore egitim/model butonlarini aktif veya pasif yapar."""
        if self.training_running:
            self.start_button.config(state="disabled")
            self.stop_button.config(state="normal" if not self.training_should_stop else "disabled")
        else:
            self.start_button.config(state="disabled" if self.watch_running else "normal")
            self.stop_button.config(state="disabled")

        self.update_watch_buttons()

    def load_model(self):
        """Diskten bir PPO .zip modeli secip UI durumuna yukler."""
        model_path = filedialog.askopenfilename(
            title="PPO model sec",
            initialdir=os.path.abspath("models"),
            filetypes=[("Stable-Baselines3 model", "*.zip"), ("Tum dosyalar", "*.*")]
        )
        if not model_path:
            return

        self.loaded_model_path = model_path
        self.loaded_model_observation_shape = None
        self.data_vars["model_path"].set(os.path.basename(model_path))
        self.set_training_status("Model yuklendi.", "idle")
        self.update_watch_buttons()
        self.update_training_buttons()

    def unload_model(self):
        """Secili modeli UI'dan kaldirir; dosyayi diskten silmez."""
        if self.training_running or self.watch_running:
            return

        # Sadece UI secimini temizler; diskteki .zip model dosyasina dokunmaz.
        self.loaded_model_path = None
        self.loaded_model_observation_shape = None
        self.model = None
        self.data_vars["model_path"].set("Model yok")
        self.set_training_status("Model kaldirildi.", "idle")
        self.update_watch_buttons()
        self.update_training_buttons()

    def adapt_observation_for_model(self, observation):
        """Izleme modunda eski/yeni observation boyut farkini basitce uyarlar."""
        if not self.model:
            return observation

        # Eski modelleri izleyebilmek icin observation boyutu izleme aninda uyarlanir.
        expected_shape = self.model.observation_space.shape
        if observation.shape == expected_shape:
            return observation

        expected_size = expected_shape[0]
        current_size = observation.shape[0]
        if current_size > expected_size:
            return observation[:expected_size]

        if current_size < expected_size:
            import numpy as np
            padded = np.zeros(expected_shape, dtype=observation.dtype)
            padded[:current_size] = observation
            return padded

        return observation

    def watch_worker(self):
        """Yuklu modeli egitim yapmadan oyunda deterministik olarak calistirir."""
        try:
            self.set_training_status("Model yukleniyor...", "running")
            self.env = TMNFEnv(ui_app=self)
            self.model = PPO.load(self.loaded_model_path)
            self.loaded_model_observation_shape = self.model.observation_space.shape

            observation, _info = self.env.reset()
            observation = self.adapt_observation_for_model(observation)
            self.current_step_count = 0
            self.set_training_status("Model izleniyor...", "running")

            while not self.watch_should_stop:
                action, _state = self.model.predict(observation, deterministic=True)
                observation, _reward, terminated, truncated, _info = self.env.step(action)
                observation = self.adapt_observation_for_model(observation)
                self.current_step_count += 1

                if terminated or truncated:
                    observation, _info = self.env.reset()
                    observation = self.adapt_observation_for_model(observation)

            self.set_training_status("Model izleme durduruldu.", "stopped")
        except Exception as e:
            self.set_training_status(f"HATA: {e}", "stopped")
        finally:
            if self.env:
                self.env.close()
            self.watch_running = False
            self.watch_should_stop = False
            self.update_watch_buttons()
            self.update_training_buttons()

    def start_watch(self):
        """Model izleme modunu baslatmadan once gerekli durum kontrollerini yapar."""
        if self.watch_running:
            return
        if self.training_running:
            messagebox.showwarning("Egitim aktif", "Once egitimi durdurun.")
            return
        if not self.loaded_model_path:
            messagebox.showwarning("Model yok", "Once bir model yukleyin.")
            return
        if not self.ensure_live_data_or_warn():
            return
        if not messagebox.askyesno("Modeli Izle", "Yuklu model oyunu kontrol edecek.\n\nDevam edilsin mi?"):
            return

        self.data_vars["reward_current"].set("0.00")
        self.data_vars["reward_total"].set("0.00")
        self.data_vars["step_count"].set("Adim: 0")
        self.current_step_count = 0
        self.watch_running = True
        self.watch_should_stop = False
        self.update_watch_buttons()
        self.update_training_buttons()
        self.watch_thread = threading.Thread(target=self.watch_worker, daemon=True)
        self.watch_thread.start()

    def stop_watch(self):
        """Model izleme dongusunu durdurma bayragini kaldirir."""
        if self.watch_running and not self.watch_should_stop:
            self.watch_should_stop = True
            self.set_training_status("Izleme durduruluyor...", "stopped")
            self.stop_watch_button.config(state="disabled")

    def update_watch_buttons(self):
        """Model secimi ve izleme durumuna gore model butonlarini gunceller."""
        if not hasattr(self, "watch_button"):
            return
        has_model = self.loaded_model_path is not None
        if self.watch_running:
            self.load_model_button.config(state="disabled")
            self.watch_button.config(state="disabled")
            self.continue_training_button.config(state="disabled")
            self.unload_model_button.config(state="disabled")
            self.stop_watch_button.config(state="normal" if not self.watch_should_stop else "disabled")
        else:
            self.load_model_button.config(state="normal" if not self.training_running else "disabled")
            self.watch_button.config(state="normal" if has_model and not self.training_running else "disabled")
            self.continue_training_button.config(state="normal" if has_model and not self.training_running else "disabled")
            self.unload_model_button.config(state="normal" if has_model and not self.training_running else "disabled")
            self.stop_watch_button.config(state="disabled")

    def set_training_status(self, message, status_type):
        """Durum yazisini ve rengini egitim/izleme durumuna gore ayarlar."""
        self.data_vars["training_status"].set(message)
        if status_type == "running":
            self.training_status_label.config(style="Status.Running.TLabel")
            self.step_count_label.config(style="Status.Running.TLabel") # Adim sayaci rengini de guncelle
        elif status_type == "stopped":
            self.training_status_label.config(style="Status.Stopped.TLabel")
            self.step_count_label.config(style="Status.Stopped.TLabel") # Adim sayaci rengini de guncelle
        else: # idle
            self.training_status_label.config(style="Status.Idle.TLabel")
            self.step_count_label.config(style="Status.Idle.TLabel") # Adim sayaci rengini de guncelle

    # --- Web Trafik Monitoru ---
    def start_web_monitor(self):
        """Yerel web trafik monitoru icin HTTP/SSE server baslatir."""
        if self.web_monitor_server is not None:
            return
        try:
            server = ThreadingHTTPServer((self.web_monitor_host, self.web_monitor_port), TrafficMonitorHandler)
            server.app = self
            self.web_monitor_server = server
            self.web_monitor_stop.clear()
            self.web_monitor_thread = threading.Thread(target=server.serve_forever, daemon=True)
            self.web_monitor_thread.start()
            self.record_traffic("system", f"Web monitor hazir: http://{self.web_monitor_host}:{self.web_monitor_port}")
            print(f"[WEB] Trafik monitoru: http://{self.web_monitor_host}:{self.web_monitor_port}")
        except OSError as e:
            self.record_traffic("error", f"Web monitor acilamadi: {e}")
            print(f"[WEB] Trafik monitoru acilamadi: {e}")

    def open_web_monitor(self):
        """Web trafik monitorunu varsayilan tarayicida acar."""
        webbrowser.open(f"http://{self.web_monitor_host}:{self.web_monitor_port}")

    def stop_web_monitor(self):
        """Uygulama kapanirken web monitor serverini durdurur."""
        self.web_monitor_stop.set()
        if self.web_monitor_server is not None:
            self.web_monitor_server.shutdown()
            self.web_monitor_server.server_close()
            self.web_monitor_server = None

    def record_traffic(self, direction, payload):
        """Gelen/giden/sistem trafik satirini web monitor icin bellekte saklar."""
        now = time.strftime("%H:%M:%S")
        with self.traffic_lock:
            event = {
                "id": self.traffic_next_id,
                "time": now,
                "direction": direction,
                "payload": str(payload)
            }
            self.traffic_next_id += 1
            self.traffic_events.append(event)
            if len(self.traffic_events) > 2000:
                self.traffic_events = self.traffic_events[-2000:]

    def get_latest_traffic_id(self):
        """SSE istemcisinin kaldigi yeri bulmasi icin son trafik id'sini verir."""
        with self.traffic_lock:
            return self.traffic_next_id - 1

    def get_traffic_events_after(self, event_id):
        """Verilen id'den sonraki trafik olaylarini kopya olarak dondurur."""
        with self.traffic_lock:
            return [event.copy() for event in self.traffic_events if event["id"] > event_id]

    # --- Soket Dinleyici Fonksiyonlari ---
    def socket_worker(self):
        """Plugin TCP serverina baglanir, gelen CSV satirlarini parse edip UI kuyruguna atar."""
        recv_buffer = ""
        while self.listener_running:
            if self.client_socket is None:
                try:
                    self.queue_listener_status(f"Baglaniyor {self.socket_port}", "running")
                    client = socket.create_connection((self.socket_host, self.socket_port), timeout=0.5)
                    client.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    client.settimeout(0.2)
                    with self.socket_lock:
                        self.client_socket = client
                    recv_buffer = ""
                    self.queue_listener_status("Soket baglandi", "running")
                    self.record_traffic("system", f"8765 baglandi: {self.socket_host}:{self.socket_port}")
                except (OSError, ConnectionError):
                    time.sleep(0.5)
                    continue

            try:
                chunk = self.client_socket.recv(4096)
                if not chunk:
                    self._drop_socket_client()
                    self.queue_listener_status("Soket koptu", "stopped")
                    continue

                recv_buffer += chunk.decode("utf-8", errors="ignore")
                while "\n" in recv_buffer:
                    line, recv_buffer = recv_buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    self.record_traffic("in", line)
                    car_state = CarState(line)
                    if car_state.valid:
                        self.data_queue.put(car_state)
                    else:
                        self.queue_listener_status(f"Gecersiz veri: {line[:60]}", "stopped")
            except socket.timeout:
                continue
            except OSError:
                self._drop_socket_client()
                self.queue_listener_status("Soket koptu", "stopped")

        self._drop_socket_client()

    def _drop_socket_client(self):
        """Aktif TCP client baglantisini kapatir ve UI tarafinda kopus kaydi olusturur."""
        with self.socket_lock:
            client = self.client_socket
            self.client_socket = None
        if client:
            try:
                client.close()
            except OSError:
                pass
            self.record_traffic("system", "8765 baglantisi kapandi")

    def send_socket_command(self, commands):
        """Python tarafindan uretilen TMInterface komutlarini plugine TCP ile yollar."""
        payload = "\n".join(commands) + "\n"
        with self.socket_lock:
            client = self.client_socket
            if client is None:
                self.record_traffic("error", "Komut gonderilemedi: 8765 bagli degil")
                return False
            try:
                client.sendall(payload.encode("utf-8"))
                self.record_traffic("out", payload.strip())
                return True
            except OSError:
                self.client_socket = None
                try:
                    client.close()
                except OSError:
                    pass
                self.record_traffic("error", "Komut gonderilirken soket koptu")
                return False

    def start_listening(self):
        """Veri dinleme thread'ini baslatir ve plugin portuna baglanmayi dener."""
        if not self.listener_running:
            self.listener_running = True
            self.listener_thread = threading.Thread(target=self.socket_worker, daemon=True)
            self.listener_thread.start()
            self.set_listener_status(f"Baglaniyor {self.socket_port}", "running")
            self.start_listener_button.config(state="disabled")
            self.stop_listener_button.config(state="normal")
            self.start_time = time.time()
            self.frame_count = 0

    def stop_listening(self):
        """Veri dinlemeyi durdurur ve mevcut soket baglantisini kapatir."""
        if self.listener_running:
            self.listener_running = False
            self._drop_socket_client()
            self.set_listener_status("Durduruldu", "stopped")
            self.start_listener_button.config(state="normal")
            self.stop_listener_button.config(state="disabled")
            
    def set_listener_status(self, message, status_type):
        """Baglanti durum metnini ve rengini gunceller."""
        self.data_vars["listener_status"].set(message)
        if status_type == "running":
            self.listener_status_label.config(style="Status.Running.TLabel")
        else: # stopped
            self.listener_status_label.config(style="Status.Stopped.TLabel")

    def queue_listener_status(self, message, status_type):
        """Worker thread'den UI thread'ine baglanti durum mesaji tasir."""
        self.status_queue.put((message, status_type))

    def update_ui(self):
        """Arayuzu guncelleyen ana dongu."""
        try:
            while not self.status_queue.empty():
                message, status_type = self.status_queue.get()
                self.set_listener_status(message, status_type)

            while not self.data_queue.empty():
                car_state = self.data_queue.get()
                self.latest_car_state = car_state # En son durumu guncelle
                self.latest_state_wall_time = time.time()
                
                self.frame_count += 1
                self.data_vars["time"].set(f"{car_state.time} ms")
                self.data_vars["pos"].set(f"({car_state.pos_x:.2f}, {car_state.pos_y:.2f}, {car_state.pos_z:.2f})")
                self.data_vars["speed"].set(f"{car_state.speed:.2f} km/h")
                self.data_vars["vel"].set(f"({car_state.vel_x:.2f}, {car_state.vel_y:.2f}, {car_state.vel_z:.2f})")
                
                # YENI: Stabil yaw degerlerini guncelle
                yaw_deg = car_state.yaw * 180 / math.pi
                self.data_vars["rot_yaw_deg"].set(f"{yaw_deg:.1f}")
                self.data_vars["rot_yaw_rad"].set(f"{car_state.yaw:.2f}")

                self.data_vars["checkpoint"].set(str(car_state.checkpoint))
                self.data_vars["lap"].set(str(car_state.lap))
                self.data_vars["direction"].set(car_state.direction)
                # YENI: Hedef checkpoint pozisyonunu guncelle
                self.data_vars["target_cp_pos"].set(f"({int(car_state.target_cp_x)}, {int(car_state.target_cp_y)}, {int(car_state.target_cp_z)})")
                
                # YENI: Duvara temas durumunu guncelle
                contact_status = "Evet" if car_state.has_lateral_contact else "Hayir"
                self.data_vars["contact"].set(contact_status)

            if self.listener_running:
                elapsed = time.time() - self.start_time
                fps = self.frame_count / elapsed if elapsed > 0 else 0
                self.data_vars["fps"].set(f"{fps:.1f} FPS")

            # Egitim veya model izleme calisiyorsa ek bilgileri guncelle
            if (self.training_running or self.watch_running) and self.env:
                self.data_vars["reward_current"].set(f"{self.env.last_reward:.2f}")
                self.data_vars["reward_total"].set(f"{self.env.total_reward:.2f}")
                self.data_vars["step_count"].set(f"Adim: {self.current_step_count}")

        except Exception as e:
            print(f"UI guncelleme hatasi: {e}")
        
        self.after(self.data_poll_interval_ms, self.update_ui)

    def on_closing(self):
        """Pencere kapanirken thread'leri, soketi ve web monitoru temizler."""
        # Tum thread'leri durdur
        self.stop_listening()
        self.stop_web_monitor()
        if self.training_running:
            self.stop_training()
            if self.training_thread:
                self.training_thread.join(timeout=2) # Thread'in bitmesini bekle
        if self.watch_running:
            self.stop_watch()
            if self.watch_thread:
                self.watch_thread.join(timeout=2)
        self.destroy()

if __name__ == "__main__":
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
