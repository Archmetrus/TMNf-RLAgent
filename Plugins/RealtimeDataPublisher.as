// TMInterface Gercek Zamanli Veri Yayincisi
// OnRunStep callback kullaniyor - Normal race modunda calisir!

const float PI = 3.14159265;

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
    
    // Rotasyon bilgileri (quaternion)
    quat rotation = simManager.Dyna.CurrentState.Quat;
    
    // Quaternion'dan Euler acilarina cevirme
    // Yaw (Z axis)
    float yaw = Math::Atan2(2.0 * (rotation.w * rotation.z + rotation.x * rotation.y),
                            1.0 - 2.0 * (rotation.y * rotation.y + rotation.z * rotation.z));
    
    // Pitch (Y axis)
    float sinp = 2.0 * (rotation.w * rotation.y - rotation.z * rotation.x);
    float pitch;
    if (Math::Abs(sinp) >= 1.0) {
        pitch = (sinp > 0 ? 1.0 : -1.0) * PI / 2.0;  // Math::Sign yerine
    } else {
        pitch = Math::Asin(sinp);
    }
    
    // Roll (X axis)
    float roll = Math::Atan2(2.0 * (rotation.w * rotation.x + rotation.y * rotation.z),
                             1.0 - 2.0 * (rotation.x * rotation.x + rotation.y * rotation.y));
    
    // Checkpoint ve lap bilgisi
    int currentCP = simManager.PlayerInfo.CurCheckpointCount;
    int currentLap = simManager.PlayerInfo.CurLap;
    
    // CSV formatinda veri hazirla
    string csv = raceTime + "," +
                 pos.x + "," + pos.y + "," + pos.z + "," +
                 vel.x + "," + vel.y + "," + vel.z + "," +
                 speed + "," +
                 yaw + "," + pitch + "," + roll + "," +
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
    SetVariable("rt_pitch", pitch);
    SetVariable("rt_roll", roll);
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
        print("Rotasyon: Yaw=" + yaw + " Pitch=" + pitch + " Roll=" + roll);
        print("Checkpoint: " + currentCP + " | Lap: " + currentLap);
        print("CSV: " + csv);
        print("Pano guncelleniyor!");
    }
    
    // DEBUG: Her 5 saniyede bir
    if (raceTime % 5000 == 0 && raceTime > 0) {
        print("OnRunStep! Zaman: " + raceTime + "ms, Hiz: " + speed + " km/h, CP: " + currentCP);
    }
}

void OnSimulationStep(SimulationManager@ simManager, bool userCancelled)
{
    if (userCancelled) {
        return;
    }
    
    // Zaman bilgisi (LowInputBf.as satir 80)
    int raceTime = simManager.RaceTime;
    
    // DEBUG: Her 1 saniyede bir konsola yazdir
    if (raceTime % 1000 == 0 && raceTime > 0) {
        print("OnSimulationStep cagrildi! Zaman: " + raceTime + "ms");
    }
    
    // Pozisyon bilgisi (LowInputBf.as satir 90 - CALISIYOR!)
    vec3 pos = simManager.Dyna.CurrentState.Location.Position;
    
    // LinearSpeed (hiz vektoru)
    vec3 vel = simManager.Dyna.CurrentState.LinearSpeed;
    
    // Hiz hesaplama (km/h)
    float speed = vel.Length() * 3.6;
    
    // DEBUG: Ilk saniyede veriyi goster
    if (raceTime == 1000) {
        print("Pozisyon: " + pos.ToString());
        print("Hiz: " + speed + " km/h");
    }
    
    // CSV formatinda veri hazirla
    string csv = raceTime + "," +
                 pos.x + "," + pos.y + "," + pos.z + "," +
                 vel.x + "," + vel.y + "," + vel.z + "," +
                 speed;
    
    // YONTEM 1: Konsol degiskenlerine yaz
    SetVariable("rt_time", raceTime);
    SetVariable("rt_pos_x", pos.x);
    SetVariable("rt_pos_y", pos.y);
    SetVariable("rt_pos_z", pos.z);
    SetVariable("rt_vel_x", vel.x);
    SetVariable("rt_vel_y", vel.y);
    SetVariable("rt_vel_z", vel.z);
    SetVariable("rt_speed", speed);
    SetVariable("rt_data_csv", csv);
    
    // YONTEM 2: Panoya kopyala (her 100ms'de bir, cok sik olmasin)
    if (raceTime % 100 == 0) {
        IO::SetClipboard(csv);
    }
    
    // DEBUG: Ilk saniyede degiskeni test et
    if (raceTime == 1000) {
        print("CSV degiskeni ayarlandi: " + csv);
        print("Pano guncelleniyor! Python'dan Ctrl+V yapabilirsiniz.");
    }
}

PluginInfo@ GetPluginInfo()
{
    auto info = PluginInfo();
    info.Name = "RealtimeDataPublisher";
    info.Author = "YKK";
    info.Version = "v1.0.0";
    info.Description = "Gercek zamanli arac verilerini konsol degiskenlerine yazar";
    return info;
}

