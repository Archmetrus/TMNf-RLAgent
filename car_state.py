"""
CarState Sinifi

TMInterface'den gelen CSV verisini ayristirmak ve
kolay kullanilabilir bir nesneye donusturmek icin kullanilir.
"""

class CarState:
    """Arac durumunu temsil eden sinif"""
    def __init__(self, csv_line):
        """CSV satirindan veri ayristir"""
        self.valid = False
        if not csv_line:
            return

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
                
        except (ValueError, IndexError):
            self.valid = False

    def to_dict(self):
        """Veriyi sozluk formatina donusturur."""
        if not self.valid:
            return None
        
        return {
            'time': self.time,
            'position': {'x': self.pos_x, 'y': self.pos_y, 'z': self.pos_z},
            'velocity': {'x': self.vel_x, 'y': self.vel_y, 'z': self.vel_z},
            'speed': self.speed,
            'rotation': {'yaw': self.yaw, 'pitch': self.pitch, 'roll': self.roll},
            'checkpoint': self.checkpoint,
            'lap': self.lap
        }
