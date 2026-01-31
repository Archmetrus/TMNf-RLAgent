# TMInterface RL Agent - Gerçek Zamanlı Eğitim Sistemi

Bu proje, TrackMania Nations Forever (TMNF) oyunu için TMInterface kullanarak geliştirilmiş bir Reinforcement Learning (RL) eğitim ortamıdır.

## 🏗️ Mimari

Proje, oyun ve Python arasında çift yönlü bir iletişim kurar:

1.  **Veri Akışı (Oyun -> Python):**
    *   `Plugins/RealtimeDataPublisher.as` eklentisi, oyun içi verileri (hız, pozisyon, rotasyon, vb.) her karede toplar.
    *   Bu verileri CSV formatında **PC Panosuna (Clipboard)** kopyalar.
    *   Python tarafındaki arayüz panoyu dinler ve veriyi işler.

2.  **Komut Akışı (Python -> Oyun):**
    *   RL Ajanı (veya manuel test), aksiyonları (gaz, fren, direksiyon) belirler.
    *   Bu komutlar `Scripts/action.txt` dosyasına yazılır.
    *   Oyun eklentisi, her 100ms'de bir bu dosyayı okuyarak (`load action.txt`) komutları uygular.

## 📦 Kurulum

### 1. Gereksinimler
*   **TrackMania Nations Forever** + **TMInterface** (En güncel sürüm)
*   **Python 3.x**
*   Gerekli Kütüphaneler:
    ```bash
    pip install gymnasium stable-baselines3[extra] pyperclip
    ```
    *(Tkinter Python ile kurulu gelir, gelmezse ayrıca kurmanız gerekebilir)*

### 2. Plugin Kurulumu
*   `TMInterface/Plugins/RealtimeDataPublisher.as` dosyasını, TMInterface'in `Plugins` klasörüne taşıyın veya kopyalayın.
    *   Genellikle: `C:\Users\<Kullanıcı>\Documents\TMInterface\Plugins\`
*   Oyunu başlatın, TMInterface menüsünden **Plugins** kısmına gidin ve **RealtimeDataPublisher** eklentisini aktif edin.

## 🚀 Kullanım

1.  **Oyunu Başlatın:**
    *   TMInterface üzerinden TMNF'yi açın.
    *   Eklentinin aktif olduğundan emin olun (Konsolda "Gerçek Zamanlı Veri Yayincisi BASLADI!" yazmalı).
    *   Bir yarış haritası açın (örn: A01) ve başlatın.

2.  **Arayüzü Başlatın:**
    *   Proje dizininde terminal açın:
    ```bash
    python tmnf_rl_ui.py
    ```

3.  **Eğitimi Yönetin:**
    *   Açılan pencerede **"Veri İzlemeyi Başlat"** butonuna basarak verilerin doğru geldiğini teyit edin.
    *   **"Eğitimi Başlat"** butonuna basarak RL ajanını devreye sokun.
    *   Ajan, `models/` klasörüne düzenli olarak kaydedilecektir.

## 📂 Dosya Yapısı

*   `tmnf_rl_ui.py`: Ana uygulama. Arayüzü, veri dinlemeyi ve eğitimi yönetir.
*   `tmnf_env.py`: Gymnasium uyumlu RL ortamı (Ödül fonksiyonu, gözlem uzayı burada tanımlıdır).
*   `tmnf_controller.py`: Oyuna komut gönderme mekanizması.
*   `car_state.py`: Pano verisini işleyen sınıf.
*   `Plugins/RealtimeDataPublisher.as`: Oyun içi veri toplayıcı plugin scripti.

## ⚠️ Önemli Notlar
*   Yarışın başlamış olması gerekir (`Race Time > 0`).
*   Oyun penceresi odaklanmış olmasa bile veri akışı devam eder, ancak oyunun minimize edilmemesi önerilir.
