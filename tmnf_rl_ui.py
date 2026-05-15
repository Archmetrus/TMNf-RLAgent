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

# Gerekli kutuphaneleri import et
try:
    import pyperclip
    import tkinter as tk
    from tkinter import ttk
    from tkinter import font, messagebox
    from tmnf_env import TMNFEnv
    from car_state import CarState
    from stable_baselines3 import PPO
    from stable_baselines3.common.callbacks import BaseCallback
except ImportError as e:
    print("=" * 80)
    print(f"HATA: Gerekli bir modul bulunamadi! -> {e.name}")
    print("=" * 80)
    print("\nLutfen eksik modulleri yukleyin. Ornegin:")
    print("  pip install pyperclip stable-baselines3[extra] gymnasium")
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

        self.title("TMNF RL Egitim Arayuzu")
        self.geometry("550x850") # Pencere boyutu genisletildi
        self.configure(bg="#2E2E2E")

        # --- Stil Ayarlari ---
        style = ttk.Style(self)
        style.theme_use('clam')
        # ... (Stil kodlari ayni kaliyor)
        dark_bg = "#2E2E2E"
        light_text = "#EAEAEA"
        value_text = "#40E0D0" # Turkuaz
        header_text = "#FFFFFF"
        status_running_text = "#8AE234" # Yesil
        status_stopped_text = "#EF2929" # Kirmizi
        status_idle_text = "#729FCF" # Mavi

        style.configure("TFrame", background=dark_bg)
        style.configure("TLabel", background=dark_bg, foreground=light_text, font=("Segoe UI", 11))
        style.configure("Header.TLabel", background=dark_bg, foreground=header_text, font=("Segoe UI", 16, "bold"))
        style.configure("Value.TLabel", background=dark_bg, foreground=value_text, font=("Consolas", 12, "bold"))
        style.configure("Status.Running.TLabel", background=dark_bg, foreground=status_running_text, font=("Segoe UI", 10, "bold"))
        style.configure("Status.Stopped.TLabel", background=dark_bg, foreground=status_stopped_text, font=("Segoe UI", 10, "bold"))
        style.configure("Status.Idle.TLabel", background=dark_bg, foreground=status_idle_text, font=("Segoe UI", 10, "bold"))

        style.configure("TButton", background="#4A4A4A", foreground=light_text, font=("Segoe UI", 10, "bold"), borderwidth=0, relief="flat", padding=6)
        style.map("TButton", background=[('active', '#5A5A5A'), ('disabled', '#3A3A3A')], foreground=[('disabled', '#777777')])
        style.configure("Success.TButton", background="#4E9A06") # Yesil
        style.configure("Danger.TButton", background="#A40000") # Kirmizi
        

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
            "contact": tk.StringVar(value="--") # YENI: Duvara temas icin
        }

        # Threading ve Egitim Yonetimi
        self.listener_running = False
        self.training_running = False
        self.training_should_stop = False
        self.current_step_count = 0 # YENI: Adim sayisini saklamak icin
        self.data_queue = queue.Queue()
        self.listener_thread = None
        self.training_thread = None
        self.last_clipboard = ""
        self.frame_count = 0
        self.start_time = 0
        self.model = None
        self.env = None
        self.latest_car_state = None # En son gecerli araba durumunu saklamak icin
        self.data_poll_interval_ms = 50

        self.create_widgets()
        self.update_ui()

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="20", style="TFrame")
        main_frame.pack(expand=True, fill="both")
        main_frame.columnconfigure(1, weight=1)

        # Baslik
        ttk.Label(main_frame, text="TMInterface Gercek Zamanli Veri", style="Header.TLabel").grid(row=0, column=0, columnspan=2, pady=(0, 20), sticky="w")
        
        # --- Veri Gorsellestirme Paneli ---
        grid_map = [
            ("Zaman:", "time", 1),
            ("Hiz:", "speed", 2),
            ("Hareket Yonu:", "direction", 3),
            ("Pozisyon (x,y,z):", "pos", 4),
            ("Duvara Temas:", "contact", 5),
            ("Hiz Vektoru (x,y,z):", "vel", 6),
            ("Yaw Acisi (derece):", "rot_yaw_deg", 7),
            ("Yaw Acisi (radyan):", "rot_yaw_rad", 8),
            ("Checkpoint:", "checkpoint", 9),
            ("Tur:", "lap", 10),
            ("Sonraki Hedef (X,Y,Z):", "target_cp_pos", 11),
        ]

        for label_text, var_key, row in grid_map:
            ttk.Label(main_frame, text=label_text).grid(row=row, column=0, sticky="w", padx=(0, 10), pady=2)
            ttk.Label(main_frame, textvariable=self.data_vars[var_key], style="Value.TLabel").grid(row=row, column=1, sticky="w")
        
        # Ayirici cizgi
        separator = ttk.Separator(main_frame, orient='horizontal')
        separator.grid(row=12, column=0, columnspan=2, sticky='ew', pady=10)

        # --- Egitim Kontrol Paneli (main_frame icine tasindi ve yeniden duzenlendi) ---
        ttk.Label(main_frame, text="RL Egitim Kontrolu", style="Header.TLabel").grid(row=13, column=0, columnspan=2, sticky="w", pady=(0, 5))

        # Butonlar
        self.start_button = ttk.Button(main_frame, text="Egitimi Baslat", command=self.start_training)
        self.start_button.grid(row=14, column=0, padx=5, pady=5, sticky="ew")
        self.stop_button = ttk.Button(main_frame, text="Egitimi Durdur", command=self.stop_training, state="disabled")
        self.stop_button.grid(row=14, column=1, padx=5, pady=5, sticky="ew")

        # Odul Gostergeleri (Kendi satirlarina alindi)
        ttk.Label(main_frame, text="Anlik Odul/Ceza:").grid(row=15, column=0, sticky="w")
        ttk.Label(main_frame, textvariable=self.data_vars["reward_current"]).grid(row=15, column=1, sticky="w")

        ttk.Label(main_frame, text="Bolum Toplam Odulu:").grid(row=16, column=0, sticky="w")
        ttk.Label(main_frame, textvariable=self.data_vars["reward_total"]).grid(row=16, column=1, sticky="w")

        # --- Alt Durum Cubugu ---
        status_frame = ttk.Frame(self, padding=(10, 5))
        status_frame.pack(side="bottom", fill="x")
        self.listener_status_label = ttk.Label(status_frame, textvariable=self.data_vars["listener_status"])
        self.listener_status_label.pack(side="left")
        
        self.training_status_label = ttk.Label(status_frame, textvariable=self.data_vars["training_status"])
        self.training_status_label.pack(side="left", padx=20)
        
        # YENI: Adim sayaci etiketi
        self.step_count_label = ttk.Label(status_frame, textvariable=self.data_vars["step_count"], style="Status.Idle.TLabel")
        self.step_count_label.pack(side="left", padx=20)

        self.fps_label = ttk.Label(status_frame, textvariable=self.data_vars["fps"])
        self.fps_label.pack(side="right")
        
        # Veri Dinleyici Butonlari (en altta)
        control_frame = ttk.Frame(self, padding="10", style="TFrame")
        control_frame.pack(fill="x", side="bottom")
        self.start_listener_button = ttk.Button(control_frame, text="Veri Izlemeyi Baslat", command=self.start_listening)
        self.start_listener_button.pack(side="left", padx=5, pady=5)
        self.stop_listener_button = ttk.Button(control_frame, text="Veri Izlemeyi Durdur", command=self.stop_listening, state="disabled")
        self.stop_listener_button.pack(side="left", padx=5, pady=5)


    # --- Egitim Fonksiyonlari ---
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
            if not self.listener_running:
                messagebox.showwarning("Veri yok", "Once Veri Izlemeyi Baslat'a basin.")
                return

            if not self.latest_car_state or not self.latest_car_state.valid:
                messagebox.showwarning("Veri yok", "Gecerli araba verisi gelmeden egitim baslatilamaz.")
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
            self.start_button.config(state="normal")
            self.stop_button.config(state="disabled")

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


    # --- Pano Dinleyici Fonksiyonlari ---
    def clipboard_worker(self):
        # ... (Bu fonksiyon ayni kaliyor)
        while self.listener_running:
            try:
                current_clipboard = pyperclip.paste()
                if current_clipboard and current_clipboard != self.last_clipboard and ',' in current_clipboard:
                    self.last_clipboard = current_clipboard
                    car_state = CarState(current_clipboard)
                    if car_state.valid:
                        self.data_queue.put(car_state)
            except Exception:
                pass
            time.sleep(self.data_poll_interval_ms / 1000.0)

    def start_listening(self):
        if not self.listener_running:
            self.listener_running = True
            self.listener_thread = threading.Thread(target=self.clipboard_worker, daemon=True)
            self.listener_thread.start()
            self.set_listener_status("Dinleniyor...", "running")
            self.start_listener_button.config(state="disabled")
            self.stop_listener_button.config(state="normal")
            self.start_time = time.time()
            self.frame_count = 0

    def stop_listening(self):
        if self.listener_running:
            self.listener_running = False
            self.set_listener_status("Durduruldu", "stopped")
            self.start_listener_button.config(state="normal")
            self.stop_listener_button.config(state="disabled")
            
    def set_listener_status(self, message, status_type):
        self.data_vars["listener_status"].set(message)
        if status_type == "running":
            self.listener_status_label.config(style="Status.Running.TLabel")
        else: # stopped
            self.listener_status_label.config(style="Status.Stopped.TLabel")

    def update_ui(self):
        """Arayuzu guncelleyen ana dongu."""
        try:
            while not self.data_queue.empty():
                car_state = self.data_queue.get()
                self.latest_car_state = car_state # En son durumu guncelle
                
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

            # Egitim calisiyorsa ek bilgileri guncelle
            if self.training_running and self.env:
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
        self.destroy()

if __name__ == "__main__":
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
