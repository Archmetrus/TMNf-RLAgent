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
        # YENI: Odul hesaplamasi icin onceki adimin bilgilerini sakla
        self.last_distance_to_target = float('inf')
        self.last_checkpoint_count = 0
        # YENI: Gaz/Fren durumunu takip etmek icin
        self.gas_pressed = False
        self.brake_pressed = False

        # --- AKSIYON ALANI (ACTION SPACE) - GELISTIRILDI ---
        # Ajan artik iki surekli deger uretecek:
        # 1. Direksiyon: [-1.0, 1.0] (tam sol, tam sag)
        # 2. Gaz/Fren: [-1.0, 1.0] (tam fren, tam gaz)
        self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(2,), dtype=np.float32)

        # --- Gozlem Alani (Observation Space) ---
        # [hiz, sin(yaw), cos(yaw), target_relative_x, target_relative_z]
        observation_shape = 5
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(observation_shape,), dtype=np.float32)

        # --- Episode Sonlandirma Degiskenleri ---
        self.step_count = 0
        self.action_interval = 0.05        # TMInterface action.txt'yi 50ms'de bir yukluyor
        self.max_steps_per_episode = 2000  # ~100 saniye (2000 * 0.05s)
        self.low_speed_counter = 0
        self.low_speed_threshold = 60     # 60 adim (~3 sn) boyunca yavas kalirsa bitir
        self.backward_counter = 0
        self.backward_threshold = 40      # 40 adim (~2 sn) boyunca geri giderse bitir

        # --- Kontrolcu ---
        self.controller = TMInterfaceController()
        self.current_state = None
        # self.last_action = None # Bu artik dogrudan karsilastirilamaz
        print("[ORTAM] TMNF Ortami baslatildi.")


    def _get_observation(self):
        """
        Gozlem verisini olusturur ve hedefin goreceli konumunu hesaplar.
        """
        self.current_state = self.app.latest_car_state

        if self.current_state and self.current_state.valid:
            # --- YENI: Hedefin Goreceli Konumunu Hesaplama ---
            car_pos = np.array([self.current_state.pos_x, self.current_state.pos_z])
            car_yaw = self.current_state.yaw
            target_pos = np.array([self.current_state.target_cp_x, self.current_state.target_cp_z])

            # Dunya koordinatlarinda aractan hedefe olan vektor
            world_vec = target_pos - car_pos
            
            cos_yaw = np.cos(car_yaw)
            sin_yaw = np.sin(car_yaw)
            
            # local_z: Hedef onumde/arkamda ne kadar mesafede
            # local_x: Hedef sagimda/solumda ne kadar mesafede
            target_relative_z = world_vec[0] * sin_yaw + world_vec[1] * cos_yaw
            target_relative_x = world_vec[0] * cos_yaw - world_vec[1] * sin_yaw
            
            observation = np.array([
                self.current_state.speed / 100.0,
                np.sin(self.current_state.yaw),
                np.cos(self.current_state.yaw),
                target_relative_x / 100.0,
                target_relative_z / 100.0
            ], dtype=np.float32)
            return observation

        print("[UYARI] Arayuzden gecerli gozlem verisi alinamadi.")
        return np.zeros(self.observation_space.shape, dtype=np.float32)

    def _handle_action(self, action):
        """
        Ajanin surekli aksiyonlarini (direksiyon, gaz/fren) oyun komutlarina donusturur.
        Bu fonksiyon, press/release komutlarini yoneterek durumu takip eder.
        """
        steer_action = action[0]
        throttle_brake_action = action[1]
        
        commands = []

        # 1. Direksiyon Komutu (Her adimda gonderilir)
        # YENI: Ajanin [-1, 1] araligindaki ciktisini oyunun istedigi [-65536, 65536] araligina olcekle
        steer_value = int(steer_action * 65536)
        commands.append(f"steer {steer_value}")

        # 2. Gaz/Fren Mantigi
        # Gaz verilecek durum (deger > 0.15)
        if throttle_brake_action > 0.15:
            if self.brake_pressed:
                commands.append("rel down")
                self.brake_pressed = False
            if not self.gas_pressed:
                commands.append("press up")
                self.gas_pressed = True
        # Fren yapilacak durum (deger < -0.15)
        elif throttle_brake_action < -0.15:
            if self.gas_pressed:
                commands.append("rel up")
                self.gas_pressed = False
            if not self.brake_pressed:
                commands.append("press down")
                self.brake_pressed = True
        # Bosta kalma durumu (aradaki kucuk olu bolge)
        else:
            if self.gas_pressed:
                commands.append("rel up")
                self.gas_pressed = False
            if self.brake_pressed:
                commands.append("rel down")
                self.brake_pressed = False

        if commands:
            self.controller.send_command(commands)

    def step(self, action):
        """
        Ajanin bir aksiyonunu isler.
        """
        # 1. Aksiyonu oyuna gonder
        self._handle_action(action)

        # TMInterface plugin'i action.txt'yi 50ms'de bir yukluyor.
        # Ajan da ayni ritimde karar verirse output dosyada ezilmeden oyuna gider.
        time.sleep(self.action_interval) 
        self.step_count += 1

        # 2. Yeni durumu (gozlem) oyundan al
        observation = self._get_observation()

        # 3. ODUL HESAPLAMA (YENIDEN AKTIF)
        # Ajan, sadece ileri yondeki hizina gore odullendirilir.
        reward = 0
        if self.current_state and self.current_state.valid:
            # Ileri yon hizi artik dogrudan CarState nesnesinden okunuyor.
            forward_speed = self.current_state.forward_speed
            
            # YON BILGISINI GUNCELLE
            self.car_direction = self.current_state.direction

            # --- ODUL MANTIGI (GELISTIRILDI) ---

            # 1. Ana Odul/Ceza: Ileri gitmeye dayali.
            # Ileri hareket ussel olarak odullendirilir,
            # Geri hareket ise cok daha siddetli bir sekilde ussel olarak cezalandirilir.
            reward_forward = 0
            scaling_factor = 5.0
            if forward_speed > 0:
                reward_forward = (forward_speed / scaling_factor) ** 2
            else:
                reward_forward = -((forward_speed / scaling_factor) ** 2)

            # 2. YENI Ceza: Zaman Cezasi
            # Ajanin hedefe hizli ulasmasini tesvik etmek icin her adimda kucuk bir ceza.
            time_penalty = -0.1

            # 3. YENI Ceza: Savrulma (Tutarlilik) Cezasi
            # Arabanin yonu ile hareket yonu arasindaki aciyi cezalandirir.
            consistency_penalty = 0
            # Sadece arac hareket ediyorsa hesapla (sifira bolme hatasini onle)
            horizontal_speed = np.linalg.norm([self.current_state.vel_x, self.current_state.vel_z])
            if horizontal_speed > 1.0:
                # cos_angle = dot_product / (mag1 * mag2)
                # forward_vector'in buyuklugu 1'dir.
                cos_angle = forward_speed / horizontal_speed
                # Aciyi [-1, 1] araliginda tut
                cos_angle = np.clip(cos_angle, -1.0, 1.0)
                # Aci radyan cinsinden (0: ayni yon, pi: ters yon)
                angle_rad = np.arccos(cos_angle)
                # Aci ne kadar buyukse, ceza o kadar artar (0'dan 1'e).
                # Aciyi pi'ye bolerek normalize ediyoruz ve karesini alarak kucuk sapmalari
                # daha az, buyuk sapmalari daha cok cezalandiriyoruz.
                consistency_penalty = - (angle_rad / np.pi) ** 2
            
            # --- YENI ODULLER ---

            # 4. YENI Odul: Checkpoint Bonusu
            checkpoint_bonus = 0
            current_cp_count = self.current_state.checkpoint
            if current_cp_count > self.last_checkpoint_count:
                checkpoint_bonus = 50.0
                print(f"[ODUL] Checkpoint gecildi! +{checkpoint_bonus} bonus!")
            self.last_checkpoint_count = current_cp_count

            # 5. YENI Odul: Hedefe Yaklasma Odulu
            distance_reward = 0
            current_pos = np.array([self.current_state.pos_x, self.current_state.pos_y, self.current_state.pos_z])
            target_pos = np.array([self.current_state.target_cp_x, self.current_state.target_cp_y, self.current_state.target_cp_z])
            current_distance = np.linalg.norm(current_pos - target_pos)
            
            # Ilk adimda self.last_distance_to_target'i ayarla
            if self.last_distance_to_target == float('inf'):
                self.last_distance_to_target = current_distance
            
            distance_diff = self.last_distance_to_target - current_distance
            distance_reward = distance_diff * 0.5
            self.last_distance_to_target = current_distance

            # Tum odul ve cezalari topla
            reward = reward_forward + time_penalty + consistency_penalty + checkpoint_bonus + distance_reward

        # Takip icin odul degerlerini sakla
        self.last_reward = reward
        self.total_reward += reward

        # 4. Episode sonlandirma kontrolleri
        terminated = False
        truncated = False
        info = {}

        if self.current_state and self.current_state.valid:
            # Maksimum adim siniri (zaman asimi)
            if self.step_count >= self.max_steps_per_episode:
                truncated = True

            # Dusuk hiz (takilma) tespiti
            if self.current_state.speed < 2.0:
                self.low_speed_counter += 1
            else:
                self.low_speed_counter = 0
            if self.low_speed_counter >= self.low_speed_threshold:
                terminated = True

            # Geri gitme tespiti
            if self.current_state.forward_speed < -1.0:
                self.backward_counter += 1
            else:
                self.backward_counter = 0
            if self.backward_counter >= self.backward_threshold:
                terminated = True

        return observation, reward, terminated, truncated, info

    def reset(self, seed=None, options=None):
        """
        Ortami ve oyunu sifirlar. Yeni bir bolum baslatir.
        """
        super().reset(seed=seed)

        # Toplam odulu sifirla
        self.total_reward = 0.0
        self.last_reward = 0.0
        self.last_distance_to_target = float('inf')
        self.last_checkpoint_count = 0
        self.gas_pressed = False
        self.brake_pressed = False
        self.step_count = 0
        self.low_speed_counter = 0
        self.backward_counter = 0

        # Oyunu yeniden baslat ve baslangicta tum tuslarin birakildigindan emin ol
        self.controller.send_command(["press delete", "rel up", "rel down"])
        time.sleep(self.action_interval * 1.5)
        self.controller.send_command(["rel delete", "rel up", "rel down", "steer 0"])
        
        time.sleep(0.5) 

        # Ilk gozlemi al ve dondur
        observation = self._get_observation()
        # Sifirlamadan sonra ilk gozlemde CP sayisini guncelle
        if self.current_state and self.current_state.valid:
            self.last_checkpoint_count = self.current_state.checkpoint

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
