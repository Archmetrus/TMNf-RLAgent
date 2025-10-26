import gymnasium as gym
from gymnasium import spaces
import numpy as np
import time
# pyperclip artik burada kullanilmayacak.

from tmnf_controller import TMInterfaceController
from car_state import CarState

class TMNFEnv(gym.Env):
    """
    TrackMania Nations Forever icin ozel Gymnasium ortami.
    """
    metadata = {'render_modes': ['human']}

    def __init__(self, ui_app):
        super(TMNFEnv, self).__init__()
        
        # Arayuz referansini sakla
        self.app = ui_app

        # Odul takibi icin
        self.last_reward = 0.0
        self.total_reward = 0.0
        self.car_direction = "Bilinmiyor" # Arac yonunu saklamak icin yeni degisken

        # --- AKSIYON ALANI (ACTION SPACE) - GELISTIRILDI ---
        # Ajan artik ayni anda iki karar verecek:
        # 1. Direksiyon (5 secenek): Tam Sol, Hafif Sol, Duz, Hafif Sag, Tam Sag
        # 2. Gaz/Fren (3 secenek): Gaz, Bos, Fren
        self.action_space = spaces.MultiDiscrete([5, 3])

        # Aksiyonlari komutlara cevirmek icin haritalar
        self.steer_map = {
            0: "steer -65536",  # Tam Sol
            1: "steer -25000",  # Hafif Sol
            2: "steer 0",       # Duz
            3: "steer 25000",   # Hafif Sag
            4: "steer 65536"    # Tam Sag
        }
        
        # --- Gozlem Alani (Observation Space) ---
        # [hiz, pos_x, pos_y, pos_z, yaw] - pitch ve roll kaldirildi.
        observation_shape = 5 
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(observation_shape,), dtype=np.float32)

        # --- Kontrolcu ---
        self.controller = TMInterfaceController()
        self.current_state = None
        # self.last_action = None # Bu artik dogrudan karsilastirilamaz
        print("[ORTAM] TMNF Ortami baslatildi.")


    def _get_observation(self):
        """
        Gozlem verisini dogrudan arayuzden (app) alir.
        """
        # Arayuzden en son gecerli araba durumunu al
        self.current_state = self.app.latest_car_state

        # Eger veri gecerliyse, gozlem vektorunu olustur ve dondur
        if self.current_state and self.current_state.valid:
            observation = np.array([
                self.current_state.speed,
                self.current_state.pos_x,
                self.current_state.pos_y,
                self.current_state.pos_z,
                self.current_state.yaw,
            ], dtype=np.float32)
            return observation

        # Eger arayuzden henuz gecerli veri gelmediyse, uyari ver ve sifir dondur
        print("[UYARI] Arayuzden gecerli gozlem verisi alinamadi.")
        return np.zeros(self.observation_space.shape, dtype=np.float32)

    def _handle_action(self, action):
        """
        Ajanin [direksiyon, gaz/fren] aksiyonunu TMInterface komutlarina cevirir.
        Her adimda, hem gaz hem de fren durumu acikca belirtilir.
        """
        steer_action, throttle_action = action
        
        commands_to_send = []
        
        # 1. Direksiyon komutunu ekle
        steer_command = self.steer_map.get(steer_action)
        if steer_command:
            commands_to_send.append(steer_command)
            
        # 2. Gaz/Fren komutunu belirle (YENI MANTIK)
        # 0: Gaz, 1: Bos, 2: Fren
        if throttle_action == 0: # Gaz ver
            commands_to_send.append("press up")
            commands_to_send.append("rel down")   # Freni biraktigindan emin ol
        elif throttle_action == 2: # Fren yap
            commands_to_send.append("press down")
            commands_to_send.append("rel up")     # Gazi biraktigindan emin ol
        else: # Bos'ta kal (1)
            commands_to_send.append("rel up")
            commands_to_send.append("rel down")

        self.controller.send_command(commands_to_send)

    def step(self, action):
        """
        Ajanin bir aksiyonunu isler.
        """
        # 1. Aksiyonu oyuna gonder
        self._handle_action(action)

        # AJANIN KARAR SURESI
        # Ajanin verdigi her kararin 0.5 saniye boyunca gecerli olmasini sagla.
        time.sleep(0.2) 

        # 2. Yeni durumu (gozlem) oyundan al
        observation = self._get_observation()

        # 3. ODUL HESAPLAMA (YENIDEN AKTIF)
        # Ajan, sadece ileri yondeki hizina gore odullendirilir.
        reward = 0
        if self.current_state and self.current_state.valid:
            # Ileri yon hizi artik dogrudan CarState nesnesinden okunuyor.
            # Hesaplama tekrari ve tutarsizlik onlendi.
            forward_speed = self.current_state.forward_speed
            
            # YON BILGISINI GUNCELLE
            self.car_direction = self.current_state.direction

            # ODUL MANTIGI:
            # Ileri hareket ussel olarak odullendirilir,
            # Geri hareket ise cok daha siddetli bir sekilde ussel olarak cezalandirilir.
            scaling_factor = 5.0
            if forward_speed > 0:
                # Odul, ileri hizin kupuyle artar.
                reward = (forward_speed / scaling_factor) ** 3
            else:
                # Ceza, geri hizin 6. kuvvetiyle artar (negatif olarak).
                # Bu, en ufak bir geri hareketi bile cok agir cezalandirir.
                reward = -((forward_speed / scaling_factor) ** 6)

        # Takip icin odul degerlerini sakla
        self.last_reward = reward
        self.total_reward += reward

        # 4. Bolumun bitip bitmedigini kontrol et -> KALDIRILDI
        # Ajan artik sadece manuel olarak durduruldugunda bolumu bitirecek.
        terminated = False
        truncated = False 
        info = {}

        return observation, reward, terminated, truncated, info

    def reset(self, seed=None, options=None):
        """
        Ortami ve oyunu sifirlar. Yeni bir bolum baslatir.
        """
        super().reset(seed=seed)

        # Toplam odulu sifirla
        self.total_reward = 0.0
        self.last_reward = 0.0

        # Oyunu yeniden baslat (dogru komut 'press delete')
        print("[ORTAM] Yaris yeniden baslatiliyor...")
        self.controller.send_command(["press delete"])
        
        # Oyunun kendine gelmesi icin kisa bir bekleme
        time.sleep(0.5) 

        # Gaza bas ve basili tut (Artik bu gerekli degil, ajan kendi karar verecek)
        # self.controller.send_command("press up")
        # self.last_action = None # Aksiyon durumunu sifirla

        # Ilk gozlemi al ve dondur
        observation = self._get_observation()
        info = {}

        return observation, info

    def render(self):
        """
        Goruntuleme. Oyun kendisi render ettigi icin bos birakilabilir.
        """
        pass

    def close(self):
        """Ortam kapatildiginda cagrilir ve aracin komutlarini temizler."""
        print("[ORTAM] TMNF Ortami kapatiliyor.")
        if self.controller:
            self.controller.clear_actions()

if __name__ == '__main__':
    # Ortamin Gymnasium standartlarina uygunlugunu test etme
    from stable_baselines3.common.env_checker import check_env

    print("TMNF Ortami Test Ediliyor...")
    # Bu test henuz calismaz cunku `