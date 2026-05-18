// TMInterface Gercek Zamanli Veri Yayincisi
// OnRunStep callback kullaniyor - Normal race modunda calisir!

// AngelScript'ten Python'a veri gondermek ve Python'dan input almak icin
// TCP soket koprusu kurar.

// PI sayisi
const float PI = 3.14159256; // Daha hassas PI degeri

// YENI: Checkpoint'leri siralamak icin yardimci sinif ve fonksiyonlar
class CheckpointInfo {
    int Order = 999;
    vec3 Position = vec3(0,0,0);
};

// CheckpointInfo dizisini Order'a gore siralayan basit bir bubble sort
void SortCheckpoints(array<CheckpointInfo@>& checkpoints) {
    if (checkpoints.get_Length() <= 1) return;
    for (uint i = 0; i < checkpoints.get_Length() - 1; i++) {
        for (uint j = 0; j < checkpoints.get_Length() - i - 1; j++) {
            if (checkpoints[j].Order > checkpoints[j + 1].Order) {
                CheckpointInfo@ temp = checkpoints[j];
                checkpoints[j] = checkpoints[j + 1];
                checkpoints[j + 1] = temp;
            }
        }
    }
}

// Bir string'in sonundan sayi ayiklayan basit bir fonksiyon
int ParseIntFromEnd(const string& in str) {
    if (str.IsEmpty()) return 999;
    int result = 0;
    int multiplier = 1;
    bool foundDigit = false;
    for (int i = int(str.get_Length()) - 1; i >= 0; i--) {
        uint8 char_code = str[i];
        if (char_code >= 48 && char_code <= 57) { // '0'-'9' arasi
            result += (char_code - 48) * multiplier;
            multiplier *= 10;
            foundDigit = true;
        } else {
            if (foundDigit) break; // Sayi bitti
        }
    }
    return foundDigit ? result : 999;
}


// YENI: Checkpoint ve finish koordinatlarini saklamak icin global degiskenler
array<vec3> g_checkpointWorldCoords;
vec3 g_finishWorldCoord;
bool g_mapInfoLoaded = false;
int g_lastRaceTime = -1; // YENI: Yarışın yeniden baslatildigini anlamak icin
Net::Socket@ g_serverSocket = null;
Net::Socket@ g_clientSocket = null;
string g_socketReadBuffer = "";
const string SOCKET_HOST = "127.0.0.1";
const uint16 SOCKET_PORT = 8765;

// TCP client koptugunda referansi ve yarim kalan komut bufferini temizler.
void DropSocket()
{
    @g_clientSocket = null;
    g_socketReadBuffer = "";
}

// Plugin tarafinda Python'in baglanacagi TCP serveri tek kez acar.
void EnsureSocketServer()
{
    if (g_serverSocket !is null) return;

    @g_serverSocket = Net::Socket();
    if (g_serverSocket.Listen(SOCKET_HOST, SOCKET_PORT)) {
        print("TCP koprusu dinliyor: " + SOCKET_HOST + ":" + SOCKET_PORT);
    } else {
        print("HATA: TCP koprusu portu acilamadi: " + SOCKET_HOST + ":" + SOCKET_PORT);
        @g_serverSocket = null;
    }
}

// Python'dan gelen tek komut satirini TMInterface konsol komutu olarak calistirir.
void ExecuteSocketCommandLine(string command)
{
    if (command.get_Length() > 0 && command[command.get_Length() - 1] == 13) {
        command.Erase(command.get_Length() - 1, 1);
    }
    if (command.IsEmpty()) return;
    ExecuteCommand(command, ExecuteCommandFlags::SuppressOutput);
}

// TCP bufferinda biriken komutlari newline'a gore ayirip sirasiyla uygular.
void ProcessSocketCommands()
{
    if (g_clientSocket is null) return;

    uint available = g_clientSocket.get_Available();
    if (available == 0) return;

    string chunk = g_clientSocket.ReadString(available);
    if (chunk.IsEmpty()) {
        DropSocket();
        return;
    }

    g_socketReadBuffer += chunk;
    int newlineIndex = g_socketReadBuffer.FindFirst("\n");
    while (newlineIndex >= 0) {
        string command = g_socketReadBuffer.Substr(0, newlineIndex);
        g_socketReadBuffer.Erase(0, newlineIndex + 1);
        ExecuteSocketCommandLine(command);
        newlineIndex = g_socketReadBuffer.FindFirst("\n");
    }
}

// Tek state CSV satirini Python client'a yollar; hata olursa soketi dusurur.
bool SendSocketState(const string&in data)
{
    if (g_clientSocket is null) return false;
    if (!g_clientSocket.Write(data + "\n")) {
        DropSocket();
        return false;
    }
    return true;
}

// Plugin acildiginda degiskenleri kaydeder ve TCP serveri hazirlar.
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
    
    EnsureSocketServer();
    print("Konsol degiskenleri kaydedildi!");
    print("TCP koprusu: Python client bekleniyor.");
    print("UYARI: Sadece yaris modunda calisir!");
    print("Normal race modunda map yukleyip ENTER basin");
    print("===========================================");
}

// Render dongusu servera baglanmaya calisan Python client'i kabul eder.
void Render()
{
    EnsureSocketServer();
    if (g_serverSocket is null || g_clientSocket !is null) return;

    Net::Socket@ newSocket = g_serverSocket.Accept(0);
    if (newSocket !is null) {
        @g_clientSocket = newSocket;
        g_clientSocket.set_NoDelay(true);
        g_socketReadBuffer = "";
        print("TCP koprusu baglandi: " + g_clientSocket.get_RemoteIP());
    }
}

// Yaris basladiginda cagrilir - GUVENILIR DEGIL, KULLANILMIYOR
void OnSimulationBegin(SimulationManager@ simManager)
{
    print(">>> OnSimulationBegin cagrildi (ama bu guvenilir degil) <<<");
    // Bu fonksiyonun icini bosaltiyoruz, tum mantik OnRunStep'e tasindi.
}

// Yaris bittiginde cagrilir
void OnSimulationEnd(SimulationManager@ simManager, SimulationResult result)
{
    print(">>> YARIS BITTI! OnSimulationEnd cagrildi <<<");
}

// NORMAL YARIS MODUNDA HER ADIMDA CAGRILIR!
void OnRunStep(SimulationManager@ simManager)
{
    // YENI: Yarışın yeniden baslatilip baslatilmadigini kontrol et
    int raceTime = simManager.RaceTime;
    ProcessSocketCommands();

    if (raceTime < g_lastRaceTime) {
        print(">>> YARIS YENIDEN BASLATILDI! Harita tekrar taranacak. <<<");
        g_mapInfoLoaded = false; // Harita tarama bayragini sifirla
    }
    g_lastRaceTime = raceTime;

    // YENI: Harita bilgilerini sadece bir kez, yarisin basinda yukle
    if (!g_mapInfoLoaded && raceTime > 0) {
        print(">>> YARIS BASLADI! Checkpoint'ler siralanarak araniyor...");
        g_checkpointWorldCoords.Resize(0);
        g_finishWorldCoord = vec3(0,0,0);
        
        TM::GameCtnChallenge@ challenge = GetCurrentChallenge();
        if (@challenge !is null) {
            const array<TM::GameCtnBlock@>@ blocks = challenge.get_Blocks();
            array<CheckpointInfo@> tempCheckpoints; // YENI: Siralamak icin gecici liste
            
            for (uint i = 0; i < blocks.get_Length(); i++) {
                TM::GameCtnBlock@ block = blocks[i];
                if (block is null) continue;

                if (block.get_WayPointType() == TM::WayPointType::Checkpoint) {
                    CheckpointInfo@ cpInfo = CheckpointInfo();
                    nat3 gridCoord = block.Coord;
                    // TMNF blok olcegi: X/Z 32 birim, Y 8 birim.
                    // X/Z blok ortasi, Y ise yol/CP yuzey yuksekligi.
                    cpInfo.Position = vec3((gridCoord.x * 32.0) + 16.0, 
                                           (gridCoord.y * 8.0) + 8.0, 
                                           (gridCoord.z * 32.0) + 16.0);
                    cpInfo.Order = ParseIntFromEnd(block.get_Name());
                    tempCheckpoints.Add(cpInfo);
                }
                else if (block.get_WayPointType() == TM::WayPointType::Finish) {
                    nat3 gridCoord = block.Coord;
                    // X/Z blok ortasi, Y ise yol/finish yuzey yuksekligi.
                    g_finishWorldCoord = vec3((gridCoord.x * 32.0) + 16.0, 
                                              (gridCoord.y * 8.0) + 8.0, 
                                              (gridCoord.z * 32.0) + 16.0);
                }
            }

            // Gecici listeyi sirala
            SortCheckpoints(tempCheckpoints);

            // Siralanmis listeden global listeyi doldur
            for (uint i = 0; i < tempCheckpoints.get_Length(); i++) {
                g_checkpointWorldCoords.Add(tempCheckpoints[i].Position);
            }

            print("Listenin Boyutu (siralanmis): " + g_checkpointWorldCoords.get_Length());
            g_mapInfoLoaded = true;
        } else {
            print("HATA: Harita bilgisi alinamadi!");
        }
    }

    // Yaris baslamadiysa veya bittiyse gec
    if (simManager.RaceTime < 0) return;
    
    // --- Veri Toplama ---
    TM::PlayerInfo@ playerInfo = simManager.get_PlayerInfo();
    TM::HmsDyna@ dyna = simManager.get_Dyna();
    TM::SceneVehicleCar@ car = simManager.get_SceneVehicleCar(); // YENI: Arac bilgilerini almak icin

    if (playerInfo is null || dyna is null || car is null) return;

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

    // YENI: Sonraki hedefi belirle
    vec3 targetPos = vec3(0,0,0);
    if (g_mapInfoLoaded) {
        // HATA DUZELTILDI: CurCheckpoint yerine CurCheckpointCount kullaniyoruz.
        // CurCheckpointCount, gecilen CP sayisini verir ve bu bizim listemizin index'iyle uyumludur.
        uint nextCpIndex = simManager.PlayerInfo.CurCheckpointCount;
        if (nextCpIndex < g_checkpointWorldCoords.get_Length()) {
            // Bir sonraki checkpoint hedeftir
            targetPos = g_checkpointWorldCoords[nextCpIndex];
        } else if (g_finishWorldCoord.LengthSquared() > 0.1) {
            // Tum checkpointler bitti, hedef bitis cizgisi
            targetPos = g_finishWorldCoord;
        }
    }

    // Checkpoint ve lap bilgisi
    int currentCP = simManager.PlayerInfo.CurCheckpointCount;
    int currentLap = simManager.PlayerInfo.CurLap;
    
    // YENI: Yandan temas bilgisini al (1 = Evet, 0 = Hayir)
    int hasLateralContact = car.HasAnyLateralContact ? 1 : 0;

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

    // Veriyi TCP soketten 50ms'de bir Python'a gonder.
    // Ajan step suresi de 50ms oldugu icin iki taraf ayni ritimde kalir.
    if (raceTime % 50 == 0)
    {
        string data = ""
            + raceTime + ","
            + speed + ","
            + pos.x + "," + pos.y + "," + pos.z + ","
            + vel.x + "," + vel.y + "," + vel.z + ","
            + yaw + ","
            + playerInfo.CurCheckpointCount + ","
            + playerInfo.CurLap + ","
            + targetPos.x + "," + targetPos.y + "," + targetPos.z + ","
            + hasLateralContact;

        SetVariable("rt_data_csv", data);
        SendSocketState(data);
    }
    
    // DEBUG: Ilk saniyede veriyi goster
    if (raceTime == 1000) {
        string data = ""
            + raceTime + ","
            + speed + ","
            + pos.x + "," + pos.y + "," + pos.z + ","
            + vel.x + "," + vel.y + "," + vel.z + ","
            + yaw + ","
            + playerInfo.CurCheckpointCount + ","
            + playerInfo.CurLap + ","
            + targetPos.x + "," + targetPos.y + "," + targetPos.z + ","
            + hasLateralContact;
        print("OnRunStep CALISIYOR!");
        print("Pozisyon: " + pos.ToString());
        print("Hiz: " + speed + " km/h");
        print("KESIN YAW (Radyan): " + yaw);
        print("Checkpoint: " + currentCP + " | Lap: " + currentLap);
        print("CSV: " + data);
        if (g_clientSocket !is null) {
            print("TCP client bagli, veri gonderiliyor!");
        } else {
            print("TCP client yok, veri gonderilemiyor!");
        }
    }
    
    // DEBUG: Her 5 saniyede bir
    if (raceTime % 5000 == 0 && raceTime > 0) {
        print("OnRunStep! Zaman: " + raceTime + "ms, Hiz: " + speed + " km/h, CP: " + currentCP);
    }
    
    // YENI DEBUG: Her saniye anlik hedefi konsola yazdir
    if (raceTime % 1000 == 0 && raceTime > 0) {
        print("ANLIK HEDEF (Debug): " + targetPos.ToString());
    }
}

// BU FONKSIYONLAR ARTIK KULLANILMIYOR
// void CheckForCommands() {}
// void OnSimulationStep(SimulationManager@ simManager, bool userCancelled) {}

// TMInterface plugin listesindeki ad, surum ve aciklama bilgisini dondurur.
PluginInfo@ GetPluginInfo()
{
    auto info = PluginInfo();
    info.Name = "RealtimeDataPublisher";
    info.Author = "YKK";
    info.Version = "v1.0.0";
    info.Description = "Gercek zamanli arac verilerini konsol degiskenlerine yazar";
    return info;
}

