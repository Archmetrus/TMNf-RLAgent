// TMInterface Gercek Zamanli Veri Yayincisi
// OnRunStep callback kullaniyor - Normal race modunda calisir!

// AngelScript'ten Python'a veri gondermek icin bir kopru kurar.
// RL ajaninin komutlari `Scripts/action.txt` dosyasina yazilir.
// Bu plugin, oyuna periyodik olarak o dosyayi `load` komutuyla yukletir.

// PI sayisi
const float PI = 3.14159256; // Daha hassas PI degeri

void Main()
{
    print("===========================================");
    print("Gercek Zamanli Veri Yayincisi BASLADI!");
    print("===========================================");
    
    // Konsol degiskenlerini kaydet
    RegisterVariable("rt_time", 0);
    RegisterVariable("rt_pos_x", 0.0);
    RegisterVariable("rt_pos_y", 0.0);
    RegisterVariable("rt_pos_z", 0.0);
    RegisterVariable("rt_vel_x", 0.0);
    RegisterVariable("rt_vel_y", 0.0);
    RegisterVariable("rt_vel_z", 0.0);
    RegisterVariable("rt_speed", 0.0);
    RegisterVariable("rt_yaw", 0.0);
    RegisterVariable("rt_pitch", 0.0);
    RegisterVariable("rt_roll", 0.0);
    RegisterVariable("rt_checkpoint", 0);
    RegisterVariable("rt_lap", 0);
    RegisterVariable("rt_data_csv", "");
    
    print("Konsol degiskenleri kaydedildi!");
    print("UYARI: Sadece yaris modunda calisir!");
    print("Normal race modunda map yukleyip ENTER basin");
    print("===========================================");
}

// Yaris basladiginda cagrilir
void OnSimulationBegin(SimulationManager@ simManager)
{
    print(">>> YARIS BASLADI! OnSimulationBegin cagrildi <<<");
}

// Yaris bittiginde cagrilir
void OnSimulationEnd(SimulationManager@ simManager, SimulationResult result)
{
    print(">>> YARIS BITTI! OnSimulationEnd cagrildi <<<");
}

// NORMAL YARIS MODUNDA HER ADIMDA CAGRILIR!
void OnRunStep(SimulationManager@ simManager)
{
    // --- KOMUT YUKLEME (YENI - DOSYA LOAD SISTEMI) ---
    // Her 100ms'de bir, Python'un yazdigi action.txt dosyasini oyuna yukle.
    // Bu, AngelScript'in dosya okumasina gerek kalmadan komutlari calistirir.
    if (simManager.RaceTime % 100 == 0)
    {
        ExecuteCommand("load action.txt");
    }

    // Yaris baslamadiysa veya bittiyse gec
    if (simManager.RaceTime < 0) return;
    
    // Zaman bilgisi (LowInputBf.as satir 80)
    int raceTime = simManager.RaceTime;
    
    // Pozisyon bilgisi (LowInputBf.as satir 90 - CALISIYOR!)
    vec3 pos = simManager.Dyna.CurrentState.Location.Position;
    
    // LinearSpeed (hiz vektoru)
    vec3 vel = simManager.Dyna.CurrentState.LinearSpeed;
    
    // Hiz hesaplama (km/h)
    float speed = vel.Length() * 3.6;
    
    // YENI ve KESIN YONTEM: iso4 -> mat3 -> GetYawPitchRoll()
    // iso4, hem pozisyon (translation) hem de rotasyon (mat3) bilgisi icerir.
    iso4 location = simManager.Dyna.CurrentState.Location;
    
    // location.Rotation, 3x3'luk bir rotasyon matrisidir (mat3).
    mat3 rotationMatrix = location.Rotation;

    // Cikti degiskenlerini tanimla
    float yaw, pitch, roll;

    // Matris'ten dogrudan yaw, pitch, roll degerlerini (radyan) al.
    // Bu, TMInterface'in kendi, stabil cevirme fonksiyonudur.
    rotationMatrix.GetYawPitchRoll(yaw, pitch, roll);

    // Checkpoint ve lap bilgisi
    int currentCP = simManager.PlayerInfo.CurCheckpointCount;
    int currentLap = simManager.PlayerInfo.CurLap;
    
    // CSV formatinda veri hazirla
    string csv = raceTime + "," +
                 pos.x + "," + pos.y + "," + pos.z + "," +
                 vel.x + "," + vel.y + "," + vel.z + "," +
                 speed + "," +
                 yaw + "," + // Sadece stabil yaw gonderiliyor
                 currentCP + "," + currentLap;
    
    // Konsol degiskenlerine yaz
    SetVariable("rt_time", raceTime);
    SetVariable("rt_pos_x", pos.x);
    SetVariable("rt_pos_y", pos.y);
    SetVariable("rt_pos_z", pos.z);
    SetVariable("rt_vel_x", vel.x);
    SetVariable("rt_vel_y", vel.y);
    SetVariable("rt_vel_z", vel.z);
    SetVariable("rt_speed", speed);
    SetVariable("rt_yaw", yaw);
    SetVariable("rt_pitch", pitch); // Debug icin hala yazdiriliyor ama CSV'de yok
    SetVariable("rt_roll", roll);  // Debug icin hala yazdiriliyor ama CSV'de yok
    SetVariable("rt_checkpoint", currentCP);
    SetVariable("rt_lap", currentLap);
    SetVariable("rt_data_csv", csv);
    
    // Panoya kopyala (her 100ms'de bir, cok sik olmasin)
    if (raceTime % 100 == 0) {
        IO::SetClipboard(csv);
    }
    
    // DEBUG: Ilk saniyede veriyi goster
    if (raceTime == 1000) {
        print("OnRunStep CALISIYOR!");
        print("Pozisyon: " + pos.ToString());
        print("Hiz: " + speed + " km/h");
        print("KESIN YAW (Radyan): " + yaw);
        print("Checkpoint: " + currentCP + " | Lap: " + currentLap);
        print("CSV: " + csv);
        print("Pano guncelleniyor!");
    }
    
    // DEBUG: Her 5 saniyede bir
    if (raceTime % 5000 == 0 && raceTime > 0) {
        print("OnRunStep! Zaman: " + raceTime + "ms, Hiz: " + speed + " km/h, CP: " + currentCP);
    }
}

// BU FONKSIYONLAR ARTIK KULLANILMIYOR
// void CheckForCommands() {}
// void OnSimulationStep(SimulationManager@ simManager, bool userCancelled) {}


PluginInfo@ GetPluginInfo()
{
    auto info = PluginInfo();
    info.Name = "RealtimeDataPublisher";
    info.Author = "YKK";
    info.Version = "v1.0.0";
    info.Description = "Gercek zamanli arac verilerini konsol degiskenlerine yazar";
    return info;
}

