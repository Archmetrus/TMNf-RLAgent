"""
TMInterface Clipboard Dinleyicisi

AngelScript eklentisi verileri panoya yazıyor,
bu betik panondan okuyup gösteriyor.

Kurulum:
    pip install pyperclip

Kullanım:
    python clipboard_listener.py
"""

import time
import sys
import threading
import queue
import math

try:
    import pyperclip
except ImportError:
    print("=" * 80)
    print("HATA: pyperclip modulu bulunamadi!")
    print("=" * 80)
    print("\nLutfen yukleyin:")
    print("  pip install pyperclip")
    print("\nVeya:")
    print("  python -m pip install pyperclip")
    print("=" * 80)
    sys.exit(1)

try:
    import tkinter as tk
    from tkinter import ttk
    from tkinter import font
except ImportError:
    print("=" * 80)
    print("HATA: tkinter modulu bulunamadi!")
    print("=" * 80)
    print("\nPython kurulumunuzda tkinter eksik.")
    print("Genellikle Python ile birlikte gelir.")
    print("Lutfen Python kurulumunuzu kontrol edin.")
    print("=" * 80)
    sys.exit(1)


class CarState:
    """Arac durumunu temsil eden sinif"""
    def __init__(self, csv_line):
        """CSV satirindan veri ayristir"""
        try:
            parts = csv_line.strip().split(',')
            
            if len(parts) >= 13:
                self.time = int(float(parts[0]))
                self.pos_x, self.pos_y, self.pos_z = [float(p) for p in parts[1:4]]
                self.vel_x, self.vel_y, self.vel_z = [float(p) for p in parts[4:7]]
                self.speed = float(parts[7])
                self.yaw, self.pitch, self.roll = [float(p) for p in parts[8:11]]
                self.checkpoint = int(float(parts[11]))
                self.lap = int(float(parts[12]))
                self.valid = True
            else:
                self.valid = False
                
        except (ValueError, IndexError):
            self.valid = False

class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("TMInterface Veri Dinleyici")
        self.geometry("600x450")
        self.configure(bg="#2E2E2E")

        # --- YENI STIL AYARLARI ---
        style = ttk.Style(self)
        style.theme_use('clam')

        dark_bg = "#2E2E2E"
        light_text = "#EAEAEA"
        value_text = "#40E0D0" # Turkuaz
        header_text = "#FFFFFF"

        style.configure("TFrame", background=dark_bg)
        style.configure("TLabel", background=dark_bg, foreground=light_text, font=("Segoe UI", 11))
        style.configure("Header.TLabel", background=dark_bg, foreground=header_text, font=("Segoe UI", 16, "bold"))
        style.configure("Value.TLabel", background=dark_bg, foreground=value_text, font=("Consolas", 12, "bold"))

        # Button stili
        style.configure("TButton", 
                        background="#4A4A4A", 
                        foreground=light_text, 
                        font=("Segoe UI", 10, "bold"),
                        borderwidth=0,
                        relief="flat",
                        padding=6)
        style.map("TButton",
                  background=[('active', '#5A5A5A'), ('disabled', '#3A3A3A')],
                  foreground=[('disabled', '#777777')])

        # Veri saklama
        self.data_vars = {
            "time": tk.StringVar(value="0 ms"),
            "pos": tk.StringVar(value="(0.00, 0.00, 0.00)"),
            "speed": tk.StringVar(value="0.00 km/h"),
            "vel": tk.StringVar(value="(0.00, 0.00, 0.00)"),
            "rot_deg": tk.StringVar(value="(0.0, 0.0, 0.0)"),
            "rot_rad": tk.StringVar(value="(0.00, 0.00, 0.00)"),
            "checkpoint": tk.StringVar(value="0"),
            "lap": tk.StringVar(value="0"),
            "status": tk.StringVar(value="Durduruldu"),
            "fps": tk.StringVar(value="0.0 FPS")
        }

        self.create_widgets()

        # Threading icin
        self.running = False
        self.data_queue = queue.Queue()
        self.listener_thread = None
        self.last_clipboard = ""

        self.frame_count = 0
        self.start_time = time.time()
        
        self.update_ui()

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="20", style="TFrame")
        main_frame.pack(expand=True, fill="both")
        main_frame.columnconfigure(1, weight=1)

        # Baslik
        ttk.Label(main_frame, text="TMInterface Gercek Zamanli Veri", style="Header.TLabel").grid(row=0, column=0, columnspan=2, pady=(0, 20), sticky="w")

        # Veri etiketleri ve degerleri
        grid_map = {
            "Zaman:": ("time", 1),
            "Hiz:": ("speed", 2),
            "Pozisyon (x,y,z):": ("pos", 3),
            "Hiz Vektoru (x,y,z):": ("vel", 4),
            "Rotasyon (derece):": ("rot_deg", 5),
            "Rotasyon (radyan):": ("rot_rad", 6),
            "Checkpoint:": ("checkpoint", 7),
            "Tur:": ("lap", 8),
        }

        for i, (label_text, (var_key, row)) in enumerate(grid_map.items()):
            ttk.Label(main_frame, text=label_text).grid(row=row, column=0, sticky="w", padx=(0, 10), pady=5)
            ttk.Label(main_frame, textvariable=self.data_vars[var_key], style="Value.TLabel").grid(row=row, column=1, sticky="w")
        
        # Durum Cubugu (alta tasindi)
        status_bar = ttk.Frame(self, padding="5", style="TFrame")
        status_bar.pack(side="bottom", fill="x")
        ttk.Label(status_bar, textvariable=self.data_vars["status"]).pack(side="left")
        ttk.Label(status_bar, textvariable=self.data_vars["fps"]).pack(side="right")

        # Kontrol Butonlari (en alta tasindi)
        control_frame = ttk.Frame(self, padding="10", style="TFrame")
        control_frame.pack(fill="x", side="bottom")
        
        self.start_button = ttk.Button(control_frame, text="Baslat", command=self.start_listening)
        self.start_button.pack(side="left", padx=5, pady=5)
        
        self.stop_button = ttk.Button(control_frame, text="Durdur", command=self.stop_listening, state="disabled")
        self.stop_button.pack(side="left", padx=5, pady=5)

    def clipboard_worker(self):
        while self.running:
            try:
                current_clipboard = pyperclip.paste()
                if current_clipboard and current_clipboard != self.last_clipboard and ',' in current_clipboard:
                    self.last_clipboard = current_clipboard
                    car_state = CarState(current_clipboard)
                    if car_state.valid:
                        self.data_queue.put(car_state)
            except Exception as e:
                pass
            time.sleep(0.05) # 50ms polling

    def start_listening(self):
        if not self.running:
            self.running = True
            self.listener_thread = threading.Thread(target=self.clipboard_worker, daemon=True)
            self.listener_thread.start()
            self.data_vars["status"].set("Dinleniyor...")
            self.start_button.config(state="disabled")
            self.stop_button.config(state="normal")
            self.start_time = time.time()
            self.frame_count = 0

    def stop_listening(self):
        if self.running:
            self.running = False
            if self.listener_thread:
                self.listener_thread.join(timeout=0.1)
            self.data_vars["status"].set("Durduruldu")
            self.start_button.config(state="normal")
            self.stop_button.config(state="disabled")

    def update_ui(self):
        try:
            while not self.data_queue.empty():
                car_state = self.data_queue.get()
                
                self.frame_count += 1
                
                self.data_vars["time"].set(f"{car_state.time} ms")
                self.data_vars["pos"].set(f"({car_state.pos_x:.2f}, {car_state.pos_y:.2f}, {car_state.pos_z:.2f})")
                self.data_vars["speed"].set(f"{car_state.speed:.2f} km/h")
                self.data_vars["vel"].set(f"({car_state.vel_x:.2f}, {car_state.vel_y:.2f}, {car_state.vel_z:.2f})")
                
                yaw_deg = car_state.yaw * 180 / math.pi
                pitch_deg = car_state.pitch * 180 / math.pi
                roll_deg = car_state.roll * 180 / math.pi
                
                self.data_vars["rot_deg"].set(f"({yaw_deg:.1f}, {pitch_deg:.1f}, {roll_deg:.1f})")
                self.data_vars["rot_rad"].set(f"({car_state.yaw:.2f}, {car_state.pitch:.2f}, {car_state.roll:.2f})")
                self.data_vars["checkpoint"].set(str(car_state.checkpoint))
                self.data_vars["lap"].set(str(car_state.lap))

            if self.running:
                elapsed = time.time() - self.start_time
                fps = self.frame_count / elapsed if elapsed > 0 else 0
                self.data_vars["fps"].set(f"{fps:.1f} FPS")

        except Exception as e:
            print(f"UI guncelleme hatasi: {e}")
        
        self.after(100, self.update_ui)

    def on_closing(self):
        self.stop_listening()
        self.destroy()

if __name__ == "__main__":
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()

