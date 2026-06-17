# 🚀 Kestirimci Bakım ve Titreşim Anomali Tespit Sistemi

![Şirket](https://img.shields.io/badge/Girişim-Enduvia-blue?style=for-the-badge)
![Status](https://img.shields.io/badge/Durum-Tamamlandı-success?style=for-the-badge)
![License](https://img.shields.io/badge/Lisans-MIT-green?style=for-the-badge)

Bu depo, **Enduvia** girişimi çatısı altında akıllı fabrikalar (Endüstri 4.0) için geliştirilmiş, makine arızalarını daha yaşanmadan tespit edebilen **Uçta Yapay Zeka (TinyML)** tabanlı kestirimci bakım modülünün uçtan uca kaynak kodlarını içermektedir.

Bulut tabanlı gecikmeleri ve internet kesintisi risklerini ortadan kaldırmak amacıyla, makine öğrenmesi modeli doğrudan mikrodenetleyici üzerinde (Edge AI) çalıştırılmakta ve analiz sonuçları MQTT protokolü ile gerçek zamanlı olarak Enduvia Canlı İzleme Merkezi'ne aktarılmaktadır.

## 🛠️ Sistem Mimarisi ve Teknolojik Katmanlar

Enduvia bünyesinde ürettiğimiz bu teknolojik çözüm, donanımdan arayüze kadar 4 ana katmandan oluşmaktadır:

1. **Gömülü Donanım ve Sensör Füzyonu:**
   * **ESP-32S:** Sistemin ana işlem birimi ve kablosuz haberleşme modülü.
   * **MPU6050:** 6 Eksenli ivmeölçer ve jiroskop. Titreşim verilerini m/s² cinsinden ve 100Hz frekansında yüksek hassasiyetle toplar.
   * **Otonom Donanımsal Müdahale:** BC237 transistör sürücülü akıllı röle/fan devresi ile kritik anomali anında otonom koruma sağlanır.

2. **TinyML / Uçta Yapay Zeka (Edge AI):**
   * Sahadan toplanan sismik veriler **Edge Impulse** mimarisinde işlenerek Sinir Ağı (Neural Network) modeli eğitilmiştir.
   * Eğitilen model tamamen yerelde (offline) çalışacak şekilde C++ kütüphanesine dönüştürülüp ESP32'ye gömülmüştür.

3. **Endüstriyel IoT Haberleşme (MQTT):**
   * Veri transferi, **HiveMQ** broker üzerinden TCP/IP (Port 1883) protokolü ile milisaniyelik gecikmelerle sağlanır.
   * **Hiyerarşik Veri Kanalları (Topics):**
     * `enduvia/sistem/durum`: Cihazın aktiflik bilgisini yayınlar.
     * `enduvia/sensor/titresim`: Sürekli akan normalite ve titreşim verilerini iletir.
     * `enduvia/sistem/uyari`: Sadece anomali eşiği aşıldığında tetiklenen kritik alarm kanalı.

4. **Veri Analitiği ve Dashboard:**
   * **Python** ve **Streamlit** altyapısı kullanılarak geliştirilmiş gerçek zamanlı web arayüzü.
   * `paho-mqtt` kütüphanesi kullanılarak thread-safe (arka plan kilitlenmesiz) veri yakalama mimarisi kurgulanmıştır.

## 👥 Kurucu Ortaklar ve Rol Dağılımı

Bu sistem, Enduvia'nın multidisipliner Ar-Ge vizyonu doğrultusunda geliştirilmiştir:

* **Eren Horasan** *(Kurucu Ortak / Donanım ve Yapay Zeka Lideri - KTO Karatay Üniversitesi, EEE)*
  * Donanım mimarisinin tasarlanması, sensör kalibrasyonları, TinyML modelinin eğitilmesi ve gömülü C++ yazılımlarının kodlanması.
* **Ayşenur** *(Kurucu Ortak / Yazılım ve Sistem Lideri - Necmettin Erbakan Üniversitesi, YBS)*
  * MQTT veri hattının kurgulanması, Python tabanlı veri işleme algoritmalarının yazılması ve Streamlit Dashboard arayüzünün geliştirilmesi.

## ⚙️ Kurulum ve Çalıştırma

### Donanım (C++) Kurulumu
1. `Enduvia_AI_ESP32.ino` dosyasını Arduino IDE ile açın.
2. `YOUR_WIFI_SSID` ve `YOUR_WIFI_PASSWORD` alanlarına yerel ağ bilgilerinizi girin.
3. Kodu ESP32 kartınıza yükleyin (Baud Rate: 115200).

### Yazılım (Python) Kurulumu
1. Gerekli kütüphaneleri terminalden yükleyin:
```bash
pip install -r requirements.txt
```
2. Canlı İzleme Merkezi'ni başlatın:
```bash
streamlit run dashboard.py
```

## 📄 Lisans
Bu proje **MIT Lisansı** ile korunmaktadır. Enduvia teknolojilerini açık kaynak dünyasında inceleyebilir ve geliştirebilirsiniz.









