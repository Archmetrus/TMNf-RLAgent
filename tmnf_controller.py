"""
TMInterface Kontrolcusu

Bu sinif, Python tarafindaki soket koprusu uzerinden oyuna komut gonderir.
"""
import os
import time

# Soket yokken debug icin kullanilan eski yedek dosya yolu.
ACTION_FILE_PATH = "Scripts/action.txt"

class TMInterfaceController:
    def __init__(self, command_sender=None):
        """
        Kontrolcu baslatildiginda komut gonderme arayuzunu saklar.
        Eski dosya tabanli yol sadece yedek olarak tutulur.
        """
        self.command_sender = command_sender
        scripts_dir = os.path.dirname(ACTION_FILE_PATH)
        if not os.path.exists(scripts_dir):
            os.makedirs(scripts_dir)
        # Komut dosyasini baslangicta temizle
        with open(ACTION_FILE_PATH, "w") as f:
            f.write("steer 0") # Oyuna ilk komut olarak duz gitmeyi ver
        print("[KONTROLCU] Soket tabanli kontrolcu baslatildi.")

    def send_command(self, commands):
        """
        Verilen komut listesini oyuna gonderir.
        """
        try:
            if self.command_sender:
                return self.command_sender(commands)

            # Debug/manuel test icin eski dosya yoluna dus.
            full_command = "\n".join(commands)
            with open(ACTION_FILE_PATH, "w") as f:
                f.write(full_command)
            return True
        except Exception as e:
            print(f"[HATA] Komutlar dosyaya yazilamadi: {commands} - {e}")
            return False

    def clear_actions(self):
        """Egitim durdugunda aracin son komutta takili kalmamasi icin inputlari birakir."""
        try:
            commands = ["steer 0", "rel up", "rel down", "rel delete"]
            if self.command_sender:
                sent = self.command_sender(commands)
                if sent:
                    print("[KONTROLCU] Egitim durdu, inputlar soketten birakildi.")
                return sent

            # Basili kalabilecek tuslari acikca birak.
            with open(ACTION_FILE_PATH, "w") as f:
                f.write("\n".join(commands))
            print("[KONTROLCU] Egitim durdu, inputlar birakildi.")
            return True
        except Exception as e:
            print(f"[HATA] inputlar birakilamadi: {e}")
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
