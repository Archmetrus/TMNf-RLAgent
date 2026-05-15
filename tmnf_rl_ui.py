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

# Gerekli kutuphaneleri import et
try:
    import tkinter as tk
    from tkinter import ttk
    from tkinter import font, messagebox, filedialog
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
        # App icindeki bayrak (flag) kontrol edilir.
        # Eger bayrak True ise, egitimi durdur (False dondur).
        return not self.app.training_should_stop


class App(tk.Tk):
    def __init__(self):
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
        self.latest_car_state = None # En son gecerli araba durumunu saklamak icin
        self.latest_state_wall_time = 0.0
        self.data_poll_interval_ms = 50
        self.socket_host = "127.0.0.1"
        self.socket_port = 8765
        self.client_socket = None
        self.socket_lock = threading.Lock()

        self.create_widgets()
        self.update_ui()

    def create_widgets(self):
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
        self.stop_watch_button = ttk.Button(control_frame, text="Izlemeyi Durdur", command=self.stop_watch, state="disabled", style="Danger.TButton")
        self.stop_watch_button.grid(row=5, column=0, columnspan=2, pady=4, sticky="ew")
        model_label = ttk.Label(control_frame, textvariable=self.data_vars["model_path"], style="Value.TLabel", wraplength=300)
        model_label.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(8, 0))

        ttk.Separator(control_frame, orient="horizontal").grid(row=7, column=0, columnspan=2, sticky="ew", pady=14)
        reward_frame = ttk.Frame(control_frame, style="Panel.TFrame")
        reward_frame.grid(row=8, column=0, columnspan=2, sticky="ew")
        reward_frame.columnconfigure(0, weight=1)
        reward_frame.columnconfigure(1, weight=1)
        ttk.Label(reward_frame, text="Anlik Odul", style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(reward_frame, text="Toplam Odul", style="Muted.TLabel").grid(row=0, column=1, sticky="w")
        ttk.Label(reward_frame, textvariable=self.data_vars["reward_current"], style="Metric.TLabel").grid(row=1, column=0, sticky="w", pady=(4, 0))
        ttk.Label(reward_frame, textvariable=self.data_vars["reward_total"], style="Metric.TLabel").grid(row=1, column=1, sticky="w", pady=(4, 0))


    # --- Egitim Fonksiyonlari ---
    def has_live_data(self):
        if not self.listener_running:
            return False
        if not self.latest_car_state or not self.latest_car_state.valid:
            return False
        with self.socket_lock:
            socket_connected = self.client_socket is not None
        return socket_connected and time.time() - self.latest_state_wall_time <= 1.0

    def ensure_live_data_or_warn(self):
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
            models_dir = f"models/PPO-{int(time.time())}"
            logdir = "logs"
            if not os.path.exists(models_dir): os.makedirs(models_dir)
            if not os.path.exists(logdir): os.makedirs(logdir)
                
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
                tb_log_name=f"PPO-{int(time.time())}",
                callback=StopTrainingCallback(self)
            )
            
            # Egitim bittiginde (dongu tamamlandiginda veya durduruldugunda)
            if self.training_should_stop:
                self.set_training_status("Egitim kullanici tarafindan durduruldu.", "stopped")
                self.model.save(f"{models_dir}/manual_save_{int(time.time())}")
            else:
                self.set_training_status("Egitim tamamlandi.", "idle")
                self.model.save(f"{models_dir}/final_model")
                
        except Exception as e:
            self.set_training_status(f"HATA: {e}", "stopped")
        finally:
            if self.env:
                self.env.close()
            self.training_running = False
            self.update_training_buttons()
            
    def start_training(self):
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
            self.update_training_buttons()
            self.training_thread = threading.Thread(target=self.training_worker, daemon=True)
            self.training_thread.start()

    def stop_training(self):
        if self.training_running and not self.training_should_stop:
            self.training_should_stop = True
            self.set_training_status("Durduruluyor...", "stopped")
            self.stop_button.config(state="disabled")

    def update_training_buttons(self):
        if self.training_running:
            self.start_button.config(state="disabled")
            self.stop_button.config(state="normal" if not self.training_should_stop else "disabled")
        else:
            self.start_button.config(state="disabled" if self.watch_running else "normal")
            self.stop_button.config(state="disabled")

        self.update_watch_buttons()

    def load_model(self):
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

    def adapt_observation_for_model(self, observation):
        if not self.model:
            return observation

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
        if self.watch_running and not self.watch_should_stop:
            self.watch_should_stop = True
            self.set_training_status("Izleme durduruluyor...", "stopped")
            self.stop_watch_button.config(state="disabled")

    def update_watch_buttons(self):
        if not hasattr(self, "watch_button"):
            return
        has_model = self.loaded_model_path is not None
        if self.watch_running:
            self.load_model_button.config(state="disabled")
            self.watch_button.config(state="disabled")
            self.stop_watch_button.config(state="normal" if not self.watch_should_stop else "disabled")
        else:
            self.load_model_button.config(state="normal" if not self.training_running else "disabled")
            self.watch_button.config(state="normal" if has_model and not self.training_running else "disabled")
            self.stop_watch_button.config(state="disabled")

    def set_training_status(self, message, status_type):
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


    # --- Soket Dinleyici Fonksiyonlari ---
    def socket_worker(self):
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
        with self.socket_lock:
            client = self.client_socket
            self.client_socket = None
        if client:
            try:
                client.close()
            except OSError:
                pass

    def send_socket_command(self, commands):
        payload = "\n".join(commands) + "\n"
        with self.socket_lock:
            client = self.client_socket
            if client is None:
                return False
            try:
                client.sendall(payload.encode("utf-8"))
                return True
            except OSError:
                self.client_socket = None
                try:
                    client.close()
                except OSError:
                    pass
                return False

    def start_listening(self):
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
        if self.listener_running:
            self.listener_running = False
            self._drop_socket_client()
            self.set_listener_status("Durduruldu", "stopped")
            self.start_listener_button.config(state="normal")
            self.stop_listener_button.config(state="disabled")
            
    def set_listener_status(self, message, status_type):
        self.data_vars["listener_status"].set(message)
        if status_type == "running":
            self.listener_status_label.config(style="Status.Running.TLabel")
        else: # stopped
            self.listener_status_label.config(style="Status.Stopped.TLabel")

    def queue_listener_status(self, message, status_type):
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
        # Tum thread'leri durdur
        self.stop_listening()
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
