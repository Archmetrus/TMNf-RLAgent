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

class CarState:
    """Araç durumunu temsil eden sınıf"""
    
    def __init__(self, csv_line):
        """CSV satırından veri ayrıştır"""
        try:
            parts = csv_line.strip().split(',')
            
            if len(parts) >= 8:
                self.time = int(float(parts[0]))  # ms
                self.pos_x = float(parts[1])
                self.pos_y = float(parts[2])
                self.pos_z = float(parts[3])
                self.vel_x = float(parts[4])
                self.vel_y = float(parts[5])
                self.vel_z = float(parts[6])
                self.speed = float(parts[7])
                self.valid = True
            else:
                self.valid = False
                
        except (ValueError, IndexError):
            self.valid = False
    
    def __str__(self):
        """Okunabilir format"""
        if not self.valid:
            return "Gecersiz veri"
        
        return (
            f"Zaman: {self.time:6d}ms | "
            f"Pozisyon: ({self.pos_x:7.2f}, {self.pos_y:7.2f}, {self.pos_z:7.2f}) | "
            f"Hiz: {self.speed:6.2f} km/h"
        )
    
    def to_dict(self):
        """Sözlük formatı (ML/AI için)"""
        if not self.valid:
            return None
        
        return {
            'time': self.time,
            'position': {'x': self.pos_x, 'y': self.pos_y, 'z': self.pos_z},
            'velocity': {'x': self.vel_x, 'y': self.vel_y, 'z': self.vel_z},
            'speed': self.speed
        }


def main():
    """Ana dinleyici döngüsü"""
    print("=" * 80)
    print("TMInterface Gercek Zamanli Veri Dinleyicisi")
    print("=" * 80)
    print("\n[OK] pyperclip modulu yuklu!")
    print("\n[PANO] Pano izleniyor... (Durdurmak icin Ctrl+C)\n")
    print("[BILGI] TMInterface'de bir harita yukleyip yarisi baslatin.")
    print("        Eklenti otomatik olarak verileri panoya yazacak.\n")
    print("=" * 80 + "\n")
    
    last_clipboard = ""
    frame_count = 0
    start_time = time.time()
    
    try:
        while True:
            try:
                # Panodan veriyi oku
                current_clipboard = pyperclip.paste()
                
                # Yeni veri mi?
                if current_clipboard != last_clipboard and current_clipboard:
                    # CSV formatında mı kontrol et
                    if ',' in current_clipboard and current_clipboard[0].isdigit():
                        last_clipboard = current_clipboard
                        
                        car_state = CarState(current_clipboard)
                        
                        if car_state.valid:
                            frame_count += 1
                            print(f"\r{car_state}", end='', flush=True)
                            
                            # --- KENDİ İŞLEMLERİNİZİ BURAYA EKLEYİN ---
                            # data_dict = car_state.to_dict()
                            # your_ml_model.predict(data_dict)
                            
                            # Ornek: Yuksek hiz uyarisi
                            if car_state.speed > 200:
                                print(f"\n[UYARI] YUKSEK HIZ: {car_state.speed:.2f} km/h!")
                
                time.sleep(0.05)  # 50ms bekle
                
            except Exception as e:
                # Pano okuma hatası (nadiren olur)
                pass
    
    except KeyboardInterrupt:
        print("\n\n" + "=" * 80)
        elapsed = time.time() - start_time
        fps = frame_count / elapsed if elapsed > 0 else 0
        print(f"Dinleyici durduruldu.")
        print(f"Toplam frame: {frame_count}")
        print(f"Calisma suresi: {elapsed:.2f} saniye")
        print(f"Ortalama FPS: {fps:.2f}")
        print("=" * 80)


if __name__ == "__main__":
    main()

