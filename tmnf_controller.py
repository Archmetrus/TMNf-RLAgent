"""
TMInterface Kontrolcusu

Bu sinif, TMInterface komut satiri araci (CLI) uzerinden oyunla
etkilesime gecer. Komut gonderme ve veri okuma islemlerini yonetir.
"""
import os
import time

# RL ajaninin komutlarinin yazilacagi dosyanin yolu
# TMInterface'in `load` komutu bu dosyayi `Scripts` klasorunde arar.
ACTION_FILE_PATH = "Scripts/action.txt"

class TMInterfaceController:
    def __init__(self):
        """
        Kontrolcu baslatildiginda Scripts klasorunun ve action.txt'nin
        var oldugundan emin olur.
        """
        scripts_dir = os.path.dirname(ACTION_FILE_PATH)
        if not os.path.exists(scripts_dir):
            os.makedirs(scripts_dir)
        # Komut dosyasini baslangicta temizle
        with open(ACTION_FILE_PATH, "w") as f:
            f.write("steer 0") # Oyuna ilk komut olarak duz gitmeyi ver
        print("[KONTROLCU] 'load' komutu tabanli kontrolcu baslatildi.")
        print(f"[KONTROLCU] Komutlar '{ACTION_FILE_PATH}' dosyasina yazilacak.")

    def send_command(self, commands):
        """
        Verilen komut listesini action.txt dosyasina yazar.
        Her komut kendi satirina yazilir.
        """
        try:
            # Komutlarin basina bir zaman damgasi eklemek, `load` komutunun
            # her seferinde calismasini saglayabilir.
            # Not: Bu sistemde ayni anda birden fazla komut gonderildigi icin
            # zaman damgasi (prefix) kullanmak sorun yaratabilir. Simdilik kaldirildi.
            full_command = "\n".join(commands)
            with open(ACTION_FILE_PATH, "w") as f:
                f.write(full_command)
            return True
        except Exception as e:
            print(f"[HATA] Komutlar dosyaya yazilamadi: {commands} - {e}")
            return False

    def clear_actions(self):
        """Egitim durdugunda aracin son komutta takili kalmamasi icin action.txt'yi temizler."""
        try:
            # action.txt dosyasini acip icerigini tamamen sil.
            with open(ACTION_FILE_PATH, "w") as f:
                f.write("")
            print("[KONTROLCU] Egitim durdu, action.txt temizlendi.")
            return True
        except Exception as e:
            print(f"[HATA] action.txt temizlenemedi: {e}")
            return False

if __name__ == '__main__':
    # Basit test
    print("TMInterface Kontrolcusu Test Ediliyor...")
    controller = TMInterfaceController()
    
    print("\n'restart' komutu gonderiliyor... (Bu komut 'load' ile calismayabilir, direksiyon test ediliyor)")
    controller.send_command(["restart"])
    time.sleep(2)
    
    print("\n'steer 65536' (tam sag) ve 'press up' komutlari gonderiliyor...")
    controller.send_command(["steer 65536", "press up"])
    print("Komutlar gonderildi. Lutfen aracin direksiyonunu ve hareketini gozlemleyin.")
    time.sleep(2)
    
    print("\n'steer -65536' (tam sol) ve 'press down' komutlari gonderiliyor...")
    controller.send_command(["steer -65536", "press down"])
    print("Komutlar gonderildi.")
    time.sleep(2)
    
    print("\n'steer 0' (duz) komutu gonderiliyor...")
    controller.send_command(["steer 0"])
    print("Komut gonderildi.")
    
    print("\n[TEST TAMAMLANDI]")
