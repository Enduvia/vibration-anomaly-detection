#include <Wire.h>
#include <WiFi.h>
#include <PubSubClient.h>

// 🧠 TINYML / EDGE AI KUTUPHANESI
#include <Enduvia_Anomali_inferencing.h>      

// 📌 DONANIM PIN TANIMLAMALARI
const int transistorPin = 14; // BC237 Transistor Base Pin (330 Ohm direnc)
const int MPU_addr = 0x68;    // MPU6050 I2C Adresi (SDA=21, SCL=22)

// 🌐 WIFI VE MQTT AYARLARI (Lutfen kendi bilgilerinizi giriniz)
const char* ssid = "YOUR_WIFI_SSID";             
const char* password = "YOUR_WIFI_PASSWORD";     
const char* mqtt_server = "broker.hivemq.com"; 
const int mqtt_port = 1883;

// 📮 MQTT TOPIC TANIMLAMALARI
const char* topic_durum = "enduvia/sistem/durum";
const char* topic_titresim = "enduvia/sensor/titresim";
const char* topic_uyari = "enduvia/sistem/uyari";

WiFiClient espClient;
PubSubClient client(espClient);

// RAM yukunu sifirlayan statik tampon bellek
static float sample_buf[EI_CLASSIFIER_DSP_INPUT_FRAME_SIZE]; 

// WiFi Baglanti Fonksiyonu
void setup_wifi() {
    delay(10);
    Serial.println();
    Serial.print("Baglaniliyor: ");
    Serial.println(ssid);
    WiFi.begin(ssid, password);

    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\nWiFi baglantisi basarili!");
}

// MQTT Yeniden Baglanma Fonksiyonu
void reconnect() {
    while (!client.connected()) {
        Serial.print("MQTT baglantisi deneniyor...");
        String clientId = "Enduvia-Node-" + String(random(0, 0xffff), HEX);
        if (client.connect(clientId.c_str())) {
            Serial.println("Baglandi!");
            client.publish(topic_durum, "Enduvia Izleme Sistemi Canli");
        } else {
            delay(5000);
        }
    }
}

void setup() {
    Serial.begin(115200);
    
    // Sistem otonom koruma fani aktif
    pinMode(transistorPin, OUTPUT);
    digitalWrite(transistorPin, HIGH); 

    // I2C ve MPU6050 Baslatma
    Wire.begin();
    Wire.beginTransmission(MPU_addr);
    Wire.write(0x6B); 
    Wire.write(0);    
    Wire.endTransmission(true);

    // Baglantilari Baslat
    setup_wifi();
    client.setServer(mqtt_server, mqtt_port);
    
    Serial.println("Enduvia AI Edge Sistemi Aktif...");
}

void loop() {
    if (!client.connected()) {
        reconnect();
    }
    client.loop();

    // -------------------------------------------------------------------------
    // 1. SENSOR VERISI TOPLAMA VE HASSASIYET AYARI (m/s^2 Donusumu)
    // -------------------------------------------------------------------------
    for (size_t i = 0; i < EI_CLASSIFIER_DSP_INPUT_FRAME_SIZE; i += 3) {
        int16_t AcX, AcY, AcZ;
        
        Wire.beginTransmission(MPU_addr);
        Wire.write(0x3B); 
        Wire.endTransmission(false);
        Wire.requestFrom(MPU_addr, 6, true);
        
        AcX = Wire.read() << 8 | Wire.read();
        AcY = Wire.read() << 8 | Wire.read();
        AcZ = Wire.read() << 8 | Wire.read();

        // Yercekimi ivmesi (9.81) ile g hassasiyet donusumu
        if (i < EI_CLASSIFIER_DSP_INPUT_FRAME_SIZE) sample_buf[i] = ((float)AcX / 16384.0) * 9.81;
        if (i + 1 < EI_CLASSIFIER_DSP_INPUT_FRAME_SIZE) sample_buf[i + 1] = ((float)AcY / 16384.0) * 9.81;
        if (i + 2 < EI_CLASSIFIER_DSP_INPUT_FRAME_SIZE) sample_buf[i + 2] = ((float)AcZ / 16384.0) * 9.81;
        
        delayMicroseconds(100); 
    }

    // -------------------------------------------------------------------------
    // 2. EDGE AI CIKARIM (INFERENCE) ASAMASI
    // -------------------------------------------------------------------------
    signal_t signal;
    numpy::signal_from_buffer(sample_buf, EI_CLASSIFIER_DSP_INPUT_FRAME_SIZE, &signal);

    ei_impulse_result_t result = { 0 };
    EI_IMPULSE_ERROR res = run_classifier(&signal, &result, false);
    
    if (res == EI_IMPULSE_OK) {
        Serial.println("\n--- Enduvia AI Analiz Sonuclari ---");
        
        for (size_t ix = 0; ix < EI_CLASSIFIER_LABEL_COUNT; ix++) {
            Serial.printf("%s: %.5f\n", result.classification[ix].label, result.classification[ix].value);

            // Anlik verileri Dashboard'a ilet
            if (strcmp(result.classification[ix].label, "vibration_normal") == 0) {
                char payload[10];
                dtostrf(result.classification[ix].value, 6, 4, payload);
                client.publish(topic_titresim, payload);
            }

            // ANOMALI DURUMUNDA MQTT ALARMI
            if (strcmp(result.classification[ix].label, "vibration_anomaly") == 0 && result.classification[ix].value > 0.80) {
                Serial.println("UYARI: Kritik Yuksek Titresim Algilandi!");
                client.publish(topic_uyari, "KRITIK_HATA: Yuksek_Titresim_Anomalisi");
            }
        }
    } else {
        Serial.printf("AI Motoru Hatasi, Kod: %d\n", res);
    }

    Serial.println("---------------------------------------");
    delay(1000); 
}
