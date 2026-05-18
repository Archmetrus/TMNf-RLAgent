# TMNF RL Agent - Gercek Zamanli Otonom Surus Egitim Sistemi

Bu proje, TrackMania Nations Forever (TMNF) oyununda bir araci pekistirmeli ogrenme ile otonom surmeyi hedefleyen gercek zamanli bir RL egitim ortamidir. Oyun tarafi TMInterface ve AngelScript ile, egitim/arayuz tarafi Python ile gelistirilmistir.

Proje su an clipboard uzerinden veri okumaz. Eski pano/clipboard-history yaklasimi kullanilmamaktadir. Oyun ile Python arasindaki veri ve komut akisi TCP soket uzerinden yapilir.

## Proje Ozeti

Sistem, TMInterface icinde calisan `RealtimeDataPublisher.as` eklentisi ile oyun motorundan arac durumunu toplar. Bu durum bilgisi Python arayuzune TCP uzerinden aktarilir. Python tarafinda Gymnasium uyumlu `TMNFEnv` ortami, bu veriyi PPO ajaninin kullanabilecegi gozlem formatina cevirir. Ajan direksiyon, gaz ve fren kararlarini uretir; bu kararlar ayni TCP baglantisi uzerinden eklentiye geri gonderilir ve TMInterface komutlari olarak oyuna uygulanir.

Egitim, model izleme ve canli telemetri `tmnf_rl_ui.py` icindeki Tkinter arayuzu ile yonetilir.

## Amac

Projenin amaci, TMNF oyununda araci insan mudahalesi olmadan pist uzerinde ilerletebilen bir RL ajani gelistirmektir. Bu kapsamda:

- Oyun motorundan gercek zamanli yapisal veri almak
- Bu veriyi RL icin anlamli gozlem uzayina cevirmek
- PPO ile surus politikasi egitmek
- Ajan kararlarini oyuna geri iletmek
- Egitim ve test surecini arayuzden izlenebilir hale getirmek
- Egitilmis modelleri tekrar yukleyip davranislarini gozlemlemek hedeflenmistir

## Kapsam

Proje asagidaki parcalari kapsar:

- TMInterface AngelScript eklentisi
- Python TCP istemcisi
- Gymnasium ortam sinifi
- PPO egitim sureci
- Canli telemetri arayuzu
- Gercek zamanli TCP trafik monitoru
- Model kaydetme
- Kayitli modeli yukleyip izleme
- Checkpoint hedefi ve odul fonksiyonu ile surus davranisi sekillendirme

Goruntu tabanli surus yapilmaz. Ajan ekran pikseli islemez. Bunun yerine oyun motorundan alinan hiz, konum, yaw, hiz vektoru ve checkpoint bilgileri kullanilir.

## Guncel Mimari

### Oyun -> Python veri akisi

1. `Plugins/RealtimeDataPublisher.as` TMInterface icinde calisir.
2. Plugin `127.0.0.1:8765` adresinde TCP server olarak dinler.
3. Python UI, `Veri Izlemeyi Baslat` butonuna basildiginda bu porta client olarak baglanir.
4. Plugin her 50 ms'de bir arac verisini CSV satiri olarak Python'a yollar.
5. Python `CarState` sinifi ile CSV verisini parse eder.
6. UI hiz, konum, yaw, checkpoint, hedef checkpoint ve temas bilgisini gosterir.
7. UI icindeki web monitor, gelen/giden TCP trafigini `127.0.0.1:8766` adresinden canli gosterir.

### Python -> Oyun komut akisi

1. PPO ajani veya model izleme dongusu aksiyon uretir.
2. `TMNFEnv` aksiyonu TMInterface komutlarina cevirir.
3. Komutlar TCP soket uzerinden plugin'e gonderilir.
4. Plugin gelen her komut satirini `ExecuteCommand` ile oyuna uygular.

Kullanilan eski yaklasimlar:

- Clipboard/pano uzerinden veri aktarma: artik yok
- `Scripts/action.txt` dosyasini `load action.txt` ile surekli okutma: ana akista artik yok

`action.txt` sadece eski debug/yedek yol olarak kodda durur; normal calismada kullanilmaz.

### TCP trafik monitoru

Python arayuzu acildiginda ek olarak kucuk bir web monitor baslatilir:

```text
http://127.0.0.1:8766
```

Bu sayfa 8765 uzerinden gecen gercek trafigi canli gosterir:

- `OYUN -> PY`: pluginden Python'a gelen CSV state satirlari
- `PY -> OYUN`: Python'dan plugine giden input komutlari
- `SISTEM/HATA`: baglanti ve gonderim durumlari

UI'daki web adresi tiklanabilir. Tiklaninca tarayicida monitor acilir.

## Veri Formati

Plugin Python'a 15 alanli CSV yollar:

```text
time,speed,pos_x,pos_y,pos_z,vel_x,vel_y,vel_z,yaw,checkpoint,lap,target_cp_x,target_cp_y,target_cp_z,has_lateral_contact
```

Alanlar:

- `time`: yaris zamani, ms
- `speed`: arac hizi, km/h
- `pos_x,pos_y,pos_z`: arac konumu
- `vel_x,vel_y,vel_z`: hiz vektoru
- `yaw`: arac yonu, radyan
- `checkpoint`: gecilen checkpoint sayisi
- `lap`: tur bilgisi
- `target_cp_x,target_cp_y,target_cp_z`: siradaki hedef checkpoint veya finish koordinati
- `has_lateral_contact`: yan temas/duvar temasi, `0` veya `1`

Checkpoint ve finish hedef koordinati plugin tarafinda blok koordinatindan hesaplanir:

```text
x = grid_x * 32 + 16
y = grid_y * 8 + 8
z = grid_z * 32 + 16
```

`y` degerinde `+8` kullanilir. Ornek: `grid_y = 1` ise hedef yukseklik `16` olur.

## Gozlem Uzayi

Guncel RL gozlem uzayi 5 boyutludur:

```text
[speed/100, sin(yaw), cos(yaw), target_relative_x/100, target_relative_z/100]
```

Aciklama:

- `speed/100`: normalize hiz
- `sin(yaw), cos(yaw)`: yaw acisini sureksizlik olmadan temsil eder
- `target_relative_x`: hedefin araca gore sag/sol konumu
- `target_relative_z`: hedefin araca gore on/arka konumu

Hedefin goreli konumu arac koordinat sistemine cevrilir:

```python
target_relative_z = dx * sin(yaw) + dz * cos(yaw)
target_relative_x = dx * cos(yaw) - dz * sin(yaw)
```

Bu sayede ajan hedefin sadece dunya koordinatini degil, kendi bakis acisina gore nerede oldugunu gorur.

## Aksiyon Uzayi

Aksiyon uzayi 2 boyutlu surekli degerden olusur:

```text
[steer, throttle_brake]
```

Aralik:

```text
[-1.0, 1.0]
```

Donusum:

- `steer`: `[-1, 1]` araligindan TMInterface `[-65536, 65536]` direksiyon degerine cevrilir
- `throttle_brake > 0.15`: gaz
- `throttle_brake < -0.15`: fren
- aradaki bolge: gaz/fren birakilir

## Odul Fonksiyonu

Odul fonksiyonu birden fazla bilesenden olusur:

### Hedefe ilerleme odulu

Ajanin ana odulu aracin baktigi yone gore degil, hedef checkpoint'e yaklasip yaklasmadigina gore hesaplanir.

```python
progress = last_distance_to_target - current_distance
progress_clipped = clip(progress, -3.0, 3.0)
progress_reward = progress_clipped
```

Hedeften uzaklasma daha sert cezalandirilir:

```python
backward_penalty = progress_clipped * 2.0 if progress_clipped < 0 else 0.0
```

Bu sayede ajan sadece hizlanmayi degil, checkpoint'e dogru ilerlemeyi ogrenir.

### Kucuk ileri hiz destegi

Ileri hiz tamamen kaldirilmadi, fakat ana odulu ezmeyecek kadar kucuk tutuldu:

```python
forward_speed_bonus = clip(forward_speed, 0.0, 80.0) * 0.01
```

### Zaman cezasi

Her adimda kucuk zaman cezasi vardir:

```python
time_penalty = -0.03
```

Bu, ajani daha hizli ilerlemeye zorlar.

### Savrulma/tutarlilik cezasi

Aracin baktigi yon ile hareket ettigi yon arasindaki aci buyudukce ceza artar:

```python
cos_angle = forward_speed / horizontal_speed
angle_rad = arccos(cos_angle)
consistency_penalty = -0.3 * (angle_rad / pi) ** 2
```

### Checkpoint bonusu

Checkpoint gecildiginde:

```python
checkpoint_bonus = 50.0
```

Checkpoint degistigi anda hedef mesafesi resetlenir. Boylece ajan yeni checkpoint daha uzakta diye yanlis negatif distance cezasi yemez.

### Temas cezasi

Arac yan temas/duvar temasi yaparsa ceza alir:

```python
contact_penalty = -2.0
```

### Aksiyon yumusakligi cezasi

Ajanin direksiyon/gaz kararlarini asiri sert degistirmesi kucuk ceza alir:

```python
action_smoothness_penalty = -0.02 * norm(action - last_action)
```

Toplam odul bu bilesenlerin toplami olarak hesaplanir:

```python
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
```

## Episode Sonlandirma

Bir episode su durumlarda biter:

- Maksimum adim siniri: `2000` adim, yaklasik 100 saniye
- Dusuk hiz: 60 adim boyunca hiz `< 2.0`
- Hedeften uzaklasma: 40 adim boyunca checkpoint mesafesi artarsa
- Ilerleme yok: 80 adim boyunca checkpoint'e anlamli yaklasma olmazsa

Bu kurallar ajanin uzun sure takili kalmasini veya geri gitme davranisini surdurmesini engeller.

## Model Egitimi

Egitim algoritmasi:

```text
PPO - Proximal Policy Optimization
```

Guncel temel hiperparametreler:

```python
learning_rate = 0.0003
gamma = 0.99
n_steps = 256
batch_size = 64
n_epochs = 10
ent_coef = 0.01
total_timesteps = 100000
```

Egitim normal tamamlanirsa model su klasore kaydedilir:

```text
models/PPO-<timestamp>/final_model.zip
```

Egitim `Egitimi Durdur` butonu ile durdurulursa UI model klasoru icin isim sorar.

- Isim yazilirsa: `models/<girilen_isim>/<girilen_isim>.zip`
- Ayni dosya zaten varsa: `models/<girilen_isim>/<girilen_isim>_<timestamp>.zip`
- Bos birakilip Tamam'a basilirsa: `models/PPO-<timestamp>/manual_save_<timestamp>.zip`
- Iptal edilirse: default klasor kullanilir

### TensorBoard loglari

Egitim loglari `logs/` klasorune yazilir. Bu klasor model degildir; egitim grafigi icindir.

Bakmak icin:

```powershell
tensorboard --logdir logs
```

Sonra:

```text
http://localhost:6006
```

En onemli grafikler:

- `rollout/ep_rew_mean`: odul artiyor mu?
- `rollout/ep_len_mean`: episode suresi uzuyor mu?
- `train/value_loss`: deger agi patliyor mu?
- `train/entropy_loss`: kesif cok erken bitiyor mu?
- `train/approx_kl`: PPO fazla agresif mi?

## Model Yukleme ve Izleme

Arayuzde model izleme destegi vardir.

Kullanim:

1. `Veri Izlemeyi Baslat`
2. Soket baglantisinin kurulmasini bekle
3. `Model Yukle` ile `models/.../*.zip` dosyasi sec
4. `Modeli Izle` butonuna bas
5. Model oyunu kontrol eder
6. `Izlemeyi Durdur` ile kontrol birakilir

Izleme modu egitim yapmaz. Model `deterministic=True` ile tahmin uretir.

Eski modeller 4 boyutlu observation ile egitildiyse UI observation'i modelin bekledigi boyuta otomatik uyarlar. Bu uyumluluk sadece izleme icindir; yeni egitimler guncel 5 boyutlu gozlemle yapilir.

## Egitime Devam Etme

Daha once egitilmis bir PPO modeli ayni observation/action yapisi korunuyorsa tekrar yuklenip egitime devam ettirilebilir.

Arayuzden:

1. `Veri Izlemeyi Baslat`
2. `Model Yukle` ile `.zip` model sec
3. `Egitime Devam Et` butonuna bas
4. Egitimi normal sekilde durdur veya tamamlanmasini bekle

Devam egitimi eski model dosyasini ezmez. Yeni kayit yine `models/` altina yazilir.

Notlar:

- Eski 4 observation'li model yeni 5 observation ortaminda egitime devam edemez.
- Reward fonksiyonu degistiyse model devam edebilir ama davranis gecici olarak sarsilabilir.
- Devam egitimi TensorBoard'da `PPO-continue-<timestamp>` adi ile gorunur.

## Arayuz

Ana arayuz dosyasi:

```bash
python .\tmnf_rl_ui.py
```

Arayuz bolumleri:

- `Baglanti`: TCP baglantisini baslatir/durdurur
- `Calisma`: soket durumu, egitim/izleme durumu, adim sayisi, FPS
- `Canli Telemetri`: oyun verilerini gosterir
- `Egitim ve Model`: egitim baslat/durdur, model yukle/izle, odul bilgileri
- `Web` linki: canli TCP trafik monitorunu acar

## Kurulum

### Gereksinimler

- TrackMania Nations Forever
- TMInterface
- Python 3.10 veya uzeri
- Python kutuphaneleri:

```bash
pip install gymnasium stable-baselines3[extra]
```

Tkinter genellikle Python ile birlikte gelir.

### Plugin kurulumu

`Plugins/RealtimeDataPublisher.as` dosyasini TMInterface plugin klasorune koyun:

```text
C:\Users\<KULLANICI_ADI>\Documents\TMInterface\Plugins\
```

TMInterface icinden `RealtimeDataPublisher` pluginini aktif edin.

Plugin konsolunda su mesajlari beklenir:

```text
Gercek Zamanli Veri Yayincisi BASLADI!
TCP koprusu dinliyor: 127.0.0.1:8765
TCP koprusu: Python client bekleniyor.
```

Python arayuzu baglaninca:

```text
TCP koprusu baglandi
```

## Calistirma Sirasi

1. TMInterface ile oyunu acin.
2. `RealtimeDataPublisher` pluginini aktif edin.
3. Python arayuzunu baslatin:

```powershell
python .\tmnf_rl_ui.py
```

4. Arayuzden `Veri Izlemeyi Baslat` butonuna basin.
5. Soket durumu `Soket baglandi` olana kadar bekleyin.
6. Oyunda bir race baslatin.
7. Telemetri degerlerinin aktigini kontrol edin.
8. Egitim icin `Egitimi Baslat`, model izlemek icin `Model Yukle` + `Modeli Izle` kullanin.
9. TCP trafigini izlemek icin UI'daki web linkine tiklayin veya `http://127.0.0.1:8766` adresini acin.

## Egitim Pisti Tavsiyesi

Ilk egitim icin checkpoint araliklari kisa tutulmalidir. CP arasi cok uzunsa ajan odulu seyrek alir ve yon bulmakta zorlanir.

Baslangic icin:

```text
CP arasi: 20-30 metre
```

Biraz daha genel aralik:

```text
CP arasi: 20-60 metre
```

Once duz veya az virajli pistte su davranis ogretilmelidir:

```text
gaz ver -> hedefe yaklas -> checkpoint gec
```

Ajan bunu ogrendikten sonra CP araligi ve pist zorlugu artirilabilir.

## Dosya Yapisi

```text
TMInterface/
├─ tmnf_rl_ui.py                  # Ana Tkinter arayuzu, TCP client, egitim ve model izleme
├─ tmnf_env.py                    # Gymnasium ortami, observation/action/reward mantigi
├─ tmnf_controller.py             # Python -> oyun komut gonderimi
├─ car_state.py                   # TCP'den gelen CSV durum verisini parse eder
├─ Plugins/
│  └─ RealtimeDataPublisher.as    # TMInterface AngelScript TCP server ve veri yayinci
├─ Scripts/
│  └─ action.txt                  # Eski/debug yedek dosya, normal akista kullanilmaz
├─ models/                        # Kaydedilen PPO modelleri
├─ logs/                          # TensorBoard/PPO loglari
└─ README.md
```

## Rapor Sablonundaki Ozelliklerin Guncel Karsiligi

### Yapısal veri kullanimi

Rapor sablonunda belirtilen yapisal veri yaklasimi guncel projede korunmaktadir. Ajan ekran goruntusu yerine dogrudan oyun motorundan gelen sayisal telemetriyi kullanir.

Kullanilan veriler:

- hiz
- konum
- hiz vektoru
- yaw
- checkpoint sayisi
- hedef checkpoint koordinati
- duvar/yan temas bilgisi

### Gercek zamanli egitim

Sistem halen gercek zamanli race modunda calisir. Ajan karar frekansi 50 ms ritmine gore ayarlanmistir. Plugin de 50 ms'de bir state yollar.

### Iletisim mimarisi

Rapor sablonundaki eski "clipboard/pano" ve "dosya tabanli action.txt + load" anlatimi artik guncel degildir.

Guncel mimari:

- Veri: AngelScript TCP server -> Python TCP client
- Komut: Python TCP client -> AngelScript TCP server
- Komut uygulama: `ExecuteCommand`

Bu yapi clipboard gecmisini bozmaz, kopyalama panosunu kullanmaz ve komut/state hattini ayni TCP baglantisinda toplar.

### PPO tabanli egitim

Rapor sablonunda belirtilen PPO yaklasimi guncel projede devam etmektedir. Egitim `stable-baselines3` PPO sinifi ile yapilir.

### Gozlem uzayi iyilestirmesi

Yaw ham radyan olarak tek basina verilmez. Aci sureksizligini azaltmak icin:

```text
sin(yaw), cos(yaw)
```

kullanilir.

### Hedef checkpoint yonlendirmesi

Guncel sistem hedef checkpoint'in dunya koordinatini alir, sonra bunu aracin yerel koordinat sistemine cevirir. Bu sayede ajan hedefin sagda, solda, onde veya arkada oldugunu anlayabilir.

### Odul fonksiyonu dengelemesi

Rapor sablonunda belirtilen odul bilesenleri guncel projede vardir:

- hedef checkpoint'e ilerleme odulu
- hedeften uzaklasma cezasi
- kucuk ileri hiz destegi
- checkpoint bonusu
- savrulma cezasi
- zaman cezasi
- temas cezasi
- aksiyon yumusakligi cezasi

Checkpoint bonusu `50.0` olarak tutulur. Ana yonlendirme artik `last_distance_to_target - current_distance` ilerleme farki ile yapilir. Checkpoint gecildiginde distance baseline resetlenir.

### Model izleme

Guncel projede rapor sablonundaki egitim izleme fikrine ek olarak kayitli model yukleme ve davranis izleme ozelligi vardir.

## Bulgular ve Mevcut Durum

Guncel sistemde:

- TMInterface ile Python arasinda TCP tabanli cift yonlu haberlesme kurulmustur.
- Oyun motorundan canli veri alinabilmektedir.
- PPO modeli egitilebilmektedir.
- Egitilen modeller `models/` altina kaydedilebilmektedir.
- Egitim durdurulurken model klasor adi kullanicidan alinabilmektedir.
- Kayitli modeller arayuzden secilip izlenebilmektedir.
- Eski 4 observation'li modeller izleme modunda uyumluluk icin desteklenmektedir.
- Web trafik monitoru ile gelen/giden TCP satirlari canli izlenebilmektedir.

Bilinen nokta:

- Checkpoint'e gitme davranisi tamamen garanti degildir; bu halen odul tasarimi, hedef temsili ve egitim suresine baglidir.
- Ajanin daha iyi pist takibi icin ileride yol/trajectory tabanli ek oduller veya taklit ogrenme eklenebilir.

## Sorun Giderme

### UI'da veri akmiyor

Kontrol edin:

- Plugin aktif mi?
- Plugin konsolunda `TCP koprusu dinliyor` yaziyor mu?
- Python UI'da `Veri Izlemeyi Baslat` basildi mi?
- UI soket durumu `Soket baglandi` oldu mu?
- Yarista race time ilerliyor mu?

### Plugin portu acamiyor

`127.0.0.1:8765` portu baska bir surec tarafindan kullaniliyor olabilir. Python UI ve TMInterface'i kapatip tekrar acin.

### Model yukleniyor ama hata veriyor

Model eski observation uzayi ile egitilmis olabilir. Izleme modu eski 4 boyutlu modelleri uyarlamaya calisir; fakat davranis kalitesi yeni 5 boyutlu modeller kadar iyi olmayabilir.

### Ajan checkpoint'e gitmiyor

Olası nedenler:

- Model yeterince egitilmemis olabilir
- Eski 4 observation'li model izleniyor olabilir
- Odul agirliklari piste gore yetersiz olabilir
- Hedef checkpoint koordinati pistte fiziksel ideal surus cizgisini temsil etmiyor olabilir

## Kaynaklar

- Schulman, J. vd. (2017). Proximal Policy Optimization Algorithms. arXiv:1707.06347
- Stable-Baselines3 PPO dokumantasyonu
- Gymnasium dokumantasyonu
- TMInterface dokumantasyonu: https://donadigo.com/tminterface
- TMRL projesi: https://github.com/trackmania-rl/tmrl
