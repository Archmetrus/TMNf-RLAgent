"""
CarState Sinifi

TMInterface'den gelen CSV verisini ayristirmak ve
kolay kullanilabilir bir nesneye donusturmek icin kullanilir.
"""

import numpy as np

class CarState:
    """
    Panodan gelen CSV verisini yapilandirilmis bir Python nesnesine donusturur.
    Ayrica, bu veri uzerinden aracla ilgili ek hesaplamalar (orn. hareket yonu) yapar.
    """
    def __init__(self, csv_line):
        self.valid = False
        self.direction = "--" # Hareket yonu icin varsayilan deger
        self.forward_speed = 0.0 # YENI: Ileri yon hizi icin

        if not csv_line:
            return

        try:
            parts = csv_line.strip().split(',')
            
            # YENI BASITLESTIRILMIS FORMAT: 11 parca (time, pos(3), vel(3), speed, yaw, cp, lap)
            if len(parts) >= 11:
                self.time = int(float(parts[0]))
                self.pos_x, self.pos_y, self.pos_z = [float(p) for p in parts[1:4]]
                self.vel_x, self.vel_y, self.vel_z = [float(p) for p in parts[4:7]]
                self.speed = float(parts[7])
                # YENI: Sadece stabil yaw'i oku
                self.yaw = float(parts[8])
                self.checkpoint = int(float(parts[9]))
                self.lap = int(float(parts[10]))
                self.valid = True
                
        except (ValueError, IndexError):
            self.valid = False
        
        # Eger veri gecerliyse, hareket yonunu hesapla
        if self.valid:
            self._calculate_direction()

    def _calculate_direction(self):
        """
        Aracin anlik hiz ve yon vektorlerini kullanarak
        "Ileri", "Geri" veya "Durgun" hareket ettigini belirler.
        (Guvenilir YAW degeri ve dogru koordinat sistemi ile)
        """
        try:
            # Y-ekseni etrafindaki donus olan yaw acisindan, XZ duzlemindeki yon vektorunu hesapla.
            # yaw=0 -> Z ekseni yonunde (0,1). yaw=90 -> X ekseni yonunde (1,0).
            forward_vector = np.array([np.sin(self.yaw), np.cos(self.yaw)])
            
            # Arabanin yatay duzlemdeki (XZ) hiz vektorunu al.
            # Y ekseni dikey oldugu icin vel_y kullanilmiyor.
            velocity_vector = np.array([self.vel_x, self.vel_z])
            
            # Ileri yondeki hizi bulmak icin iki vektorun nokta carpimini kullan.
            forward_speed = np.dot(velocity_vector, forward_vector)
            
            # YENI: Hesaplanan degeri sakla
            self.forward_speed = forward_speed

            # Yonu belirle
            if forward_speed > 0.1: # Kucuk hareketleri goz ardi et
                self.direction = "Ileri"
            elif forward_speed < -0.1:
                self.direction = "Geri"
            else:
                self.direction = "Durgun"
        except Exception:
            self.direction = "Hata"

    def to_dict(self):
        """Veriyi sozluk formatina donusturur."""
        if not self.valid:
            return None
        
        return {
            'time': self.time,
            'position': {'x': self.pos_x, 'y': self.pos_y, 'z': self.pos_z},
            'velocity': {'x': self.vel_x, 'y': self.vel_y, 'z': self.vel_z},
            'speed': self.speed,
            'rotation_yaw': self.yaw,
            'forward_speed': self.forward_speed, # YENI
            'checkpoint': self.checkpoint,
            'lap': self.lap
        }
