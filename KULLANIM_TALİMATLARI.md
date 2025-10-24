# TMInterface Gerçek Zamanlı Veri Çekme - Kullanım Talimatları

## 📋 Gereksinimler

✅ TrackMania ModLoader kurulu  
✅ TMInterface kurulu ve çalışır durumda  
✅ Python 3.x yüklü  

---

## 🚀 Kurulum ve Kullanım

### Adım 1: AngelScript Eklentisini Etkinleştirin

1. **TrackMania'yı ModLoader ile başlatın**
2. Oyun açıldığında **TMInterface konsolunu** açın (genellikle ekranın sol tarafında)
3. Konsola şu komutu yazın:
   ```
   help
   ```
   TMInterface'in çalıştığını doğrulayın.

4. **Eklentiyi etkinleştirin:**
   - TMInterface penceresinde üstteki menüden **"Ayarlar"** (Settings) veya **"Eklentiler"** (Plugins) sekmesine gidin
   - Listede **"RealtimeDataPublisher"** eklentisini bulun
   - Yanındaki onay kutusunu işaretleyin
   - Konsola "Gerçek Zamanlı Veri Yayıncısı Başlatıldı!" mesajı gelmelidir

> **Not:** Eklenti `.as` dosyası `Documents/TMInterface/Plugins/` klasöründe olmalıdır (zaten orada).

---

### Adım 2: Python Dinleyiciyi Başlatın

1. **Yeni bir terminal/PowerShell penceresi açın**

2. Proje klasörüne gidin:
   ```powershell
   cd "C:\Users\YKK\Documents\TMInterface"
   ```

3. Python betiğini çalıştırın:
   ```powershell
   python Scripts/realtime_listener.py
   ```

4. Şu mesajı görmelisiniz:
   ```
   TMInterface Gerçek Zamanlı Veri Dinleyicisi
   Başlatıldı. Veri bekleniyor...
   ```

---

### Adım 3: Bir Harita Yükleyin ve Sürün

1. **TMInterface konsoluna** dönün
2. Bir harita yükleyin (örnek):
   ```
   map A01-Race.Challenge.Gbx
   ```
3. **Yarışı başlatın** (Enter tuşu veya oyun içi başlat butonu)

4. **Python terminalinde** gerçek zamanlı verileri görmelisiniz:
   ```
   ⏱️  1500ms | 📍 Pos: ( 245.32,  15.67, 128.90) | 🏎️ Speed: 185.45 km/h | ...
   ```

---

## 📊 Veri Formatı

Her frame'de şu veriler gelir:

| Veri | Açıklama | Birim |
|------|----------|-------|
| `time` | Simülasyon zamanı | ms |
| `pos_x, pos_y, pos_z` | Araç pozisyonu | metre |
| `vel_x, vel_y, vel_z` | Hız vektörü | m/s |
| `speed` | Görünen hız | km/h |
| `yaw, pitch, roll` | Rotasyon | radyan |
| `ang_vel_x, ang_vel_y, ang_vel_z` | Açısal hız | rad/s |
| `steer` | Direksiyon açısı | -65536 ile 65536 arası |
| `gas` | Gaz pedalı | True/False |
| `brake` | Fren pedalı | True/False |

---

## 🔧 Özelleştirme

### Kendi Analizinizi Ekleyin

`Scripts/realtime_listener.py` dosyasında, **satır 126-135** arasındaki yorumlu bölümde kendi işlemlerinizi yapabilirsiniz:

```python
# --- BU KISIMDA KENDİ İŞLEMLERİNİZİ YAPABİLİRSİNİZ ---
# Örneğin:
data_dict = car_state.to_dict()  # Sözlük formatında al

# Bir dosyaya kaydet
# import json
# with open('race_log.json', 'a') as f:
#     json.dump(data_dict, f)
#     f.write('\n')

# ML modeline gönder
# your_model.predict(data_dict)

# Gerçek zamanlı kontrol
# if car_state.speed < 100:
#     # Girdi dosyası oluştur ve load et
```

### Daha Fazla Veri Çekmek

`Plugins/RealtimeDataPublisher.as` dosyasını düzenleyerek daha fazla veri ekleyebilirsiniz:

- `state.FrontSpeed` - Önden hız
- `state.LeftSpeed` - Soldan hız  
- `state.WheelContactCount` - Kaç tekerlek yerde
- `simManager.CurrentCheckpoint` - Geçilen checkpoint
- ve daha fazlası...

TMInterface API dökümantasyonu: https://donadigo.com/tminterface/plugins/api

---

## ❓ Sorun Giderme

### "Veri bekleniyor..." mesajı kalıyor

✅ **Çözüm:**
- TMInterface'de eklentinin **etkin** olduğunu kontrol edin
- Bir harita yükleyip yarışı **başlattığınızdan** emin olun
- `C:/Users/YKK/Documents/TMInterface/realtime_data.tmp` dosyasının oluşup oluşmadığını kontrol edin

### Python "No module" hatası veriyor

✅ **Çözüm:**
- Python 3.x kurulu olduğunu doğrulayın: `python --version`
- Standart kütüphaneler kullanılıyor, ekstra paket kurulumuna gerek yok

### Veri gelmiyor ama dosya var

✅ **Çözüm:**
- Eklentiyi devre dışı bırakıp tekrar etkinleştirin
- TMInterface'i yeniden başlatın (ModLoader'dan oyunu kapatıp tekrar açın)

---

## 🎯 Sonraki Adımlar

1. **Veri Kaydetme:** JSON veya CSV formatında kayıt sistemi ekleyin
2. **Makine Öğrenmesi:** Verileri bir RL modeline besleyin
3. **Girdi Kontrolü:** Dökümanın Bölüm 5.1'deki gibi programatik girdi dosyaları oluşturun
4. **Görselleştirme:** matplotlib ile gerçek zamanlı grafikler çizin

---

## 📚 Ek Kaynaklar

- TMInterface Resmi Dokümantasyon: https://donadigo.com/tminterface/
- AngelScript API: https://donadigo.com/tminterface/plugins/api
- Ana Döküman: `TMNF Veri Çekme Dokümantasyonu Oluşturma.txt`

---

**İyi sürüşler! 🏁**

