# TMInterface RL Ajanı - Detaylı Kullanım Talimatları

Bu belge, TMInterface ve Python tabanlı RL ajanını çalıştırmak için adım adım talimatları içerir.

## 📋 Ön Gereksinimler

*   **Oyun:** TrackMania Nations Forever (TMNF)
*   **Mod:** TMInterface (En güncel sürüm)
*   **Dil:** Python 3.10 veya üzeri
*   **Kütüphaneler:**
    ```powershell
    pip install gymnasium stable-baselines3[extra]
    ```

---

## 🚀 Adım Adım Kurulum ve Çalıştırma

### Adım 1: AngelScript Eklentisini Hazırlama
*Oyunun veriyi dışarı aktarması için gereklidir.*

1.  Proje klasöründeki `Plugins/RealtimeDataPublisher.as` dosyasını bulun.
2.  Bu dosyayı TMInterface Plugin klasörüne kopyalayın:
    *   `C:\Users\KULLANICI_ADI\Documents\TMInterface\Plugins\`
3.  Oyunu başlatın.
4.  TMInterface menüsünden (Ekranın üstünde veya `F3`/`~` tuşu ile) **Plugins** sekmesine gidin.
5.  **"RealtimeDataPublisher"** kutucuğunu işaretleyerek aktifleştirin.
6.  Konsolda (Console) "Gerçek Zamanlı Veri Yayincisi BASLADI!" mesajını görmelisiniz.

### Adım 2: Python Arayüzünü Başlatma
*Ajanı eğitmek ve verileri izlemek için gereklidir.*

1.  Bir terminal (PowerShell) açın.
2.  Proje klasörüne gidin:
    ```powershell
    Set-Location (Join-Path $env:USERPROFILE 'Documents\TMInterface')
    ```
3.  Ana uygulamayı çalıştırın:
    ```powershell
    python tmnf_rl_ui.py
    ```
4.  Karşınıza "TMNF RL Eğitim Arayüzü" başlıklı bir pencere gelecektir.

### Adım 3: Oyunu Hazırlama
1.  Oyunda **Single Player -> Race** menüsünden basit bir harita (örn: A01) açın.
2.  **ÖNEMLİ:** Yarışın başlamış olması (sayacın ilerliyor olması) gerekir. Sadece menüde dururken veri akışı olmaz.

### Adım 4: Sistemi Test Etme (Veri Akışı)
1.  Python uygulamasında en alttaki **"Veri İzlemeyi Başlat"** butonuna tıklayın.
2.  Eğer her şey doğruysa, arayüzdeki "Hız", "Pozisyon" ve "Checkpoint" değerlerinin oyunla eş zamanlı değiştiğini görmelisiniz.
    *   *Veri gelmiyorsa:* Oyunda eklentinin açık olduğunu ve yarışın başladığını kontrol edin.

### Adım 5: Eğitimi Başlatma
1.  Veri akışı sorunsuzsa, arayüzdeki **"Eğitimi Başlat"** butonuna tıklayın.
2.  Durum çubuğunda "Eğitim başladı..." yazısını göreceksiniz.
3.  Aracın kontrolü RL ajanına geçecek ve araç kendi kendine hareket etmeye başlayacaktır (veya öğrenmeye çalışacaktır).

---

## 🔧 Sorun Giderme

### "Gerekli bir modül bulunamadı" Hatası
Python kütüphaneleri eksiktir. Terminalde şu komutu çalıştırın:
`pip install gymnasium stable-baselines3[extra]`

### Veriler 0 Gözüküyor / Değişmiyor
1.  Oyunda `RealtimeDataPublisher` plugininin aktif olduğundan emin olun.
2.  Yarışın `Pause` modunda olmadığından emin olun.
3.  Oyun penceresine bir kez tıklayıp odaklanın, sonra tekrar Python penceresine bakın.

### Model Nereye Kaydediliyor?
Eğitim sırasında ve sonunda modeller `models/` klasörüne kaydedilir. Her eğitim seansı için tarih/saat damgalı yeni bir klasör oluşturulur.
