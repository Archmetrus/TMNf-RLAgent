// TMInterface Gercek Zamanli Veri Yayincisi
// OnRunStep callback kullaniyor - Normal race modunda calisir!

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
    
    // CSV formatinda veri hazirla
    string csv = raceTime + "," +
                 pos.x + "," + pos.y + "," + pos.z + "," +
                 vel.x + "," + vel.y + "," + vel.z + "," +
                 speed;
    
    // Konsol degiskenlerine yaz
    SetVariable("rt_time", raceTime);
    SetVariable("rt_pos_x", pos.x);
    SetVariable("rt_pos_y", pos.y);
    SetVariable("rt_pos_z", pos.z);
    SetVariable("rt_vel_x", vel.x);
    SetVariable("rt_vel_y", vel.y);
    SetVariable("rt_vel_z", vel.z);
    SetVariable("rt_speed", speed);
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
        print("CSV: " + csv);
        print("Pano guncelleniyor!");
    }
    
    // DEBUG: Her 5 saniyede bir
    if (raceTime % 5000 == 0 && raceTime > 0) {
        print("OnRunStep! Zaman: " + raceTime + "ms, Hiz: " + speed + " km/h");
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

