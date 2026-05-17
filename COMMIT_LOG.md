# Commit Log

Bu dosya proje commit gecmisinin kisa ozetidir.

## Son Commitler

```text
22fb8e9 readme guncellendi.
c8937db odul ceza mekanizmasi duzeltildi; gelen/giden TCP komutlari icin canli web izleme eklendi; manuel model klasor ismi eklendi; checkpoint offset hatasi duzeltildi.
2e82401 readme guncellendi ve anlatim dili duzeltildi.
493c70a arayuz guncellendi; CP sonrasi haksiz ceza kaldirildi; daha adil odul/ceza mekanizmasi eklendi.
695e00d veri iletisimi clipboard yerine TCP server uzerinden yapildi; egitilen modelleri izlemek icin butonlar eklendi.
6a9cd0b agentin checkpoint'e gore konumu duzenlendi; matematiksel hatalar giderildi.
11b2202 gitignore guncellendi.
b5d7dcc ogrenme ve termination islemleri optimize edildi.
e89a31b ufak denemeler.
e8b0022 training start/stop buton adlari tutarli hale getirildi.
cb24e12 duvar temas kontrolu eklendi.
838944c ufak degisiklikler.
86a66d7 checkpointlerin UI'da gorunmesi saglandi.
c562d1b agent egitim modeli guncellendi.
61ac7a7 GUI calisir hale getirildi; yaw dogrudan oyundan alindi; ileri/geri/durgun hesaplari duzeltildi.
1f0bfa7 GUI ve agent egitim programi eklendi; vektor hesaplama sorunu not edildi.
0b29ad9 GUI arayuzu eklendi; konum, hiz, hiz vektorleri ve aci verileri gosterildi.
4909a0f ilk commit: TMInterface gercek zamanli veri cekme altyapisi.
```

## Guncel Durum Ozeti

- Haberlesme clipboard degil TCP uzerinden yapiliyor.
- Plugin `127.0.0.1:8765` uzerinden state yollar ve komut alir.
- UI `127.0.0.1:8766` uzerinden canli TCP trafik monitoru sunar.
- Reward sistemi checkpoint'e ilerleme odakli hale getirildi.
- Checkpoint Y offset hesabi `grid_y * 8 + 8` olarak duzeltildi.
- Egitim durdurulurken model klasor ismi kullanicidan alinabilir.
- README guncel proje durumuna gore yenilendi.
