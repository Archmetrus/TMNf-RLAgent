import gymnasium as gym
from gymnasium import spaces
import numpy as np
import time

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
        self.action_interval = 0.05        # TCP koprusu 50ms ritminde calisiyor
        self.max_steps_per_episode = 2000  # ~100 saniye (2000 * 0.05s)
        self.low_speed_counter = 0
        self.low_speed_threshold = 60     # 60 adim (~3 sn) boyunca yavas kalirsa bitir
        self.backward_counter = 0
        self.backward_threshold = 40      # 40 adim (~2 sn) boyunca geri giderse bitir
        self.no_progress_counter = 0
        self.no_progress_threshold = 80   # 80 adim (~4 sn) hedefe yaklasamazsa bitir
        self.no_progress_epsilon = 0.05

        # --- Kontrolcu ---
        self.controller = TMInterfaceController(command_sender=self.app.send_socket_command)
        self.current_state = None
        self.last_action = np.zeros(self.action_space.shape, dtype=np.float32)
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
        action_array = np.asarray(action, dtype=np.float32)

        # 1. Aksiyonu oyuna gonder
        self._handle_action(action_array)

        # TMInterface plugin'i TCP komutlarini 50ms ritminde isliyor.
        # Ajan da ayni ritimde karar verirse output dosyada ezilmeden oyuna gider.
        time.sleep(self.action_interval) 
        self.step_count += 1

        # 2. Yeni durumu (gozlem) oyundan al
        observation = self._get_observation()

        # 3. ODUL HESAPLAMA
        # Ana hedef: arabayi sadece kendi onune gitmeye degil, checkpoint'e yaklasmaya zorlamak.
        reward = 0.0
        progress = 0.0
        checkpoint_changed = False
        if self.current_state and self.current_state.valid:
            forward_speed = self.current_state.forward_speed
            
            # YON BILGISINI GUNCELLE
            self.car_direction = self.current_state.direction

            # 1. Checkpoint bonusu
            checkpoint_bonus = 0.0
            current_cp_count = self.current_state.checkpoint
            checkpoint_changed = current_cp_count > self.last_checkpoint_count
            if checkpoint_changed:
                checkpoint_bonus = 50.0
                print(f"[ODUL] Checkpoint gecildi! +{checkpoint_bonus} bonus!")
            self.last_checkpoint_count = current_cp_count

            # 2. Ana odul: hedef checkpoint'e yaklasma
            current_pos = np.array([self.current_state.pos_x, self.current_state.pos_y, self.current_state.pos_z])
            target_pos = np.array([self.current_state.target_cp_x, self.current_state.target_cp_y, self.current_state.target_cp_z])
            current_distance = np.linalg.norm(current_pos - target_pos)
            
            if self.last_distance_to_target == float('inf') or checkpoint_changed:
                progress = 0.0
            else:
                progress = self.last_distance_to_target - current_distance
            self.last_distance_to_target = current_distance

            progress_clipped = float(np.clip(progress, -3.0, 3.0))
            progress_reward = progress_clipped
            backward_penalty = progress_clipped * 2.0 if progress_clipped < 0.0 else 0.0

            # 3. Kucuk hiz destegi: checkpoint ilerlemesinin onune gecmeyecek kadar sinirli.
            forward_speed_bonus = float(np.clip(forward_speed, 0.0, 80.0) * 0.01)

            # 4. Zaman cezasi
            time_penalty = -0.03

            # 5. Savrulma (Tutarlilik) Cezasi
            # Arabanin yonu ile hareket yonu arasindaki aciyi cezalandirir.
            consistency_penalty = 0.0
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
                consistency_penalty = -0.3 * (angle_rad / np.pi) ** 2

            # 6. Duvar/yan temas cezasi
            contact_penalty = -2.0 if self.current_state.has_lateral_contact else 0.0

            # 7. Aksiyon yumusakligi cezasi
            action_smoothness_penalty = -0.02 * float(np.linalg.norm(action_array - self.last_action))

            # Tum odul ve cezalari topla
            reward = (
                progress_reward
                + backward_penalty
                + forward_speed_bonus
                + time_penalty
                + consistency_penalty
                + checkpoint_bonus
                + contact_penalty
                + action_smoothness_penalty
            )

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
            if progress < -self.no_progress_epsilon:
                self.backward_counter += 1
            else:
                self.backward_counter = 0
            if self.backward_counter >= self.backward_threshold:
                terminated = True

            # Hedefe ilerleyememe tespiti
            if checkpoint_changed or progress > self.no_progress_epsilon:
                self.no_progress_counter = 0
            else:
                self.no_progress_counter += 1
            if self.no_progress_counter >= self.no_progress_threshold:
                terminated = True

        self.last_action = action_array.copy()
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
        self.no_progress_counter = 0
        self.last_action = np.zeros(self.action_space.shape, dtype=np.float32)

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
