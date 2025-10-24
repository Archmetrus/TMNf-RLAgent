# TMInterface Real-Time Data Extraction for RL Agent

TrackMania Nations Forever'dan TMInterface kullanarak gerçek zamanlı veri çıkarma projesi. Reinforcement Learning ajanları için tasarlanmıştır.

## 🎯 Proje Amacı

Bu proje, TrackMania Nations Forever oyunundan gerçek zamanlı araç verilerini (pozisyon, hız, rotasyon) çıkararak Reinforcement Learning modellerine beslemeyi amaçlar.

## 🛠️ Gereksinimler

### Yazılımlar
- **TrackMania Nations Forever** (TMNF)
- **TrackMania ModLoader** (en güncel versiyon)
- **TMInterface 2.1.1+** (ModLoader üzerinden)
- **Python 3.x**

### Python Kütüphaneleri
```bash
pip install pyperclip
```

## 📦 Kurulum

### 1. TMInterface Kurulumu

1. TrackMania ModLoader'ı indirin ve kurun
2. ModLoader'dan TMInterface'i yükleyin
3. Steam kullanıyorsanız, oyunu 2.11.26 sürümüne güncelleyin (Steam TMNF Fix)

### 2. Plugin Kurulumu

`Plugins/RealtimeDataPublisher.as` dosyasını şu klasöre kopyalayın:
```
C:\Users\<KullaniciAdi>\Documents\TMInterface\Plugins\
```

TMInterface'de Ayarlar → Plugins → "RealtimeDataPublisher" kutucuğunu işaretleyin.

### 3. Python Listener Kurulumu

```bash
cd TMInterface
pip install pyperclip
python clipboard_listener.py
```

## 🚀 Kullanım

### 1. TMInterface'i Başlatın
- ModLoader üzerinden TrackMania'yı başlatın
- TMInterface konsolunu açın

### 2. Python Listener'ı Çalıştırın
```bash
python clipboard_listener.py
```

### 3. Oyunda Yarış Başlatın
```
map A01-Race.Challenge.Gbx
```
Normal race modunda yarışı başlatın (ENTER).

### 4. Veri Akışını İzleyin

Python terminalinde gerçek zamanlı veri göreceksiniz:
```
Zaman:   1500ms | Pozisyon: (245.32, 15.67, 128.90) | Hiz: 185.45 km/h
```

## 📊 Veri Formatı

Her 100ms'de bir güncellenen CSV formatında veri:

```csv
zaman,pos_x,pos_y,pos_z,vel_x,vel_y,vel_z,hiz
```

| Alan | Açıklama | Birim |
|------|----------|-------|
| `zaman` | Simülasyon zamanı | ms |
| `pos_x, pos_y, pos_z` | Araç pozisyonu | metre |
| `vel_x, vel_y, vel_z` | Hız vektörü | m/s |
| `hiz` | Toplam hız | km/h |

## 🏗️ Mimari

```
┌─────────────────────────────────────────┐
│   TrackMania Nations Forever (Oyun)     │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│        TMInterface (AngelScript)        │
│  • OnRunStep callback (her frame)      │
│  • Veri toplama ve serileştirme        │
│  • IO::SetClipboard (panoya kopyalama) │
└─────────────────┬───────────────────────┘
                  │ Clipboard IPC
┌─────────────────▼───────────────────────┐
│     clipboard_listener.py (Python)      │
│  • Panoyu izleme (50ms polling)        │
│  • CSV parse etme                       │
│  • CarState nesnesi oluşturma          │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│      RL Model / Veri İşleme Katmanı     │
│  • car_state.to_dict() → model input   │
│  • Karar verme ve aksiyon seçimi       │
│  • Eğitim döngüsü                       │
└─────────────────────────────────────────┘
```

## 📁 Dosya Yapısı

```
TMInterface/
├── Plugins/
│   └── RealtimeDataPublisher.as    # AngelScript plugin
├── clipboard_listener.py            # Python veri dinleyicisi
├── README.md                        # Bu dosya
└── TMNF Veri Çekme Dokümantasyonu.txt  # Detaylı Türkçe dokümantasyon
```

## 🔧 Özelleştirme

### Python Tarafında Veri İşleme

`clipboard_listener.py` dosyasında 111-117. satırlar arası:

```python
# Kendi işlemlerinizi buraya ekleyin
data_dict = car_state.to_dict()

# Örnek: ML modeline gönderme
# your_rl_model.predict(data_dict)

# Örnek: Veriyi kaydetme
# with open('race_data.json', 'a') as f:
#     json.dump(data_dict, f)
```

### AngelScript Tarafında Veri Ekleme

`Plugins/RealtimeDataPublisher.as` dosyasında daha fazla veri ekleyebilirsiniz:

- `state.Quat` - Rotasyon quaternion
- `simManager.PlayerInfo.RaceFinished` - Yarış durumu
- `simManager.PlayerInfo.CheckpointStates` - Checkpoint bilgileri

## 🐛 Sorun Giderme

### Plugin yüklenmedi
- `OnRunStep` fonksiyonu sadece normal race modunda çalışır
- Validation mode değil, **normal oyun modunda** test edin

### Python veri almıyor
- `pyperclip` modülünün kurulu olduğundan emin olun
- TMInterface konsolunda "OnRunStep CALISIYOR!" mesajını görüyor musunuz?
- Yarışı **başlattınız** mı? (sadece harita yüklemek yeterli değil)

### Türkçe karakter sorunları
- Tüm çıktılar İngilizce karakterlerle (ç→c, ş→s, ğ→g) yazılmıştır

## 📚 Detaylı Dokümantasyon

Proje hakkında kapsamlı Türkçe dokümantasyon için:
- `TMNF Veri Çekme Dokümantasyonu Oluşturma.txt`

## 🤝 Katkıda Bulunma

1. Fork edin
2. Feature branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Commit edin (`git commit -m 'Add amazing feature'`)
4. Push edin (`git push origin feature/amazing-feature`)
5. Pull Request açın

## 📄 Lisans

Bu proje eğitim amaçlıdır. TMInterface, TrackMania Nations Forever ve ilgili tüm markalar sahiplerinin mülkiyetindedir.

## 🙏 Teşekkürler

- **donadigo** - TMInterface geliştiricisi
- **Shweetz** - LowInputBf.as örnek plugin
- TMInterface topluluğu

## 📞 İletişim

- GitHub Issues: [TMNf-RLAgent/issues](https://github.com/Archmetrus/TMNf-RLAgent/issues)

---

**Not:** Bu proje aktif geliştirme aşamasındadır. Geri bildirimlerinizi bekliyoruz!

