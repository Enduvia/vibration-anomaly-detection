import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import paho.mqtt.client as mqtt

st.set_page_config(page_title="Enduvia Cyber Dashboard", page_icon="🌌", layout="wide", initial_sidebar_state="expanded")

if 'aktif_sayfa' not in st.session_state:
    st.session_state.aktif_sayfa = 'Dashboard'

AI_LIMIT = 85.0 

st.markdown("""
<style>
    .block-container { padding-top: 4rem; padding-bottom: 2rem; }
    .grad-card-cyan {
        background: linear-gradient(135deg, #06b6d4 0%, #0369a1 100%);
        border-radius: 15px; padding: 20px; color: white;
        box-shadow: 0 10px 20px rgba(6, 182, 212, 0.2);
        min-height: 120px; display: flex; flex-direction: column; justify-content: center;
    }
    .pill-card {
        background-color: #1e1e2d; border-radius: 20px; padding: 10px 20px;
        display: flex; justify-content: space-between; align-items: center;
        margin-bottom: 10px; border: 1px solid rgba(255,255,255,0.05);
    }
    .card-title { font-size: 14px; opacity: 0.9; margin-bottom: 5px; font-weight: 500;}
    .card-value { font-size: 32px; font-weight: 800; font-family: monospace; letter-spacing: -1px; line-height: 1;}
    .card-unit { font-size: 14px; opacity: 0.8; font-weight: normal; }
</style>
""", unsafe_allow_html=True)

# --- SOL MENÜ ---
st.sidebar.markdown("<h2 style='color: #06b6d4; font-weight: 800;'>Enduvia</h2>", unsafe_allow_html=True)
st.sidebar.caption("👤 KULLANICI PROFİLİ")
st.sidebar.divider()

st.sidebar.caption("📊 ANALİTİK KONTROL")
if st.sidebar.button("⚡ Dashboard", use_container_width=True): st.session_state.aktif_sayfa = 'Dashboard'
if st.sidebar.button("📈 Raporlar", use_container_width=True): st.session_state.aktif_sayfa = 'Raporlar'
if st.sidebar.button("🔔 Alarmlar", use_container_width=True): st.session_state.aktif_sayfa = 'Alarmlar'

# ==========================================
# 1. ARKA PLAN HAFIZASI (KESİNTİSİZ ÇEKİRDEK)
# ==========================================
@st.cache_resource
def get_shared_data():
    class Data:
        anomali_yuzdesi = 0.0 
        uyari_mesaji = "Sorun Yok - Stabil" 
        kayitlar = []  
        sistem_aktif = False
    
    data = Data()
    zamanlar = pd.date_range(end=datetime.now(), periods=100, freq='1s')
    for z in zamanlar:
        data.kayitlar.append({
            'Tarih_Zaman': z,
            'Anomali Riski (%)': 0.0,
            'Durum': '✅ Normal',
            'İhlal Sebebi': '-'
        })
    return data

shared_data = get_shared_data()

# ==========================================
# 2. MQTT VE OTOMATİK VERİTABANI KAYDI
# ==========================================
@st.cache_resource
def get_mqtt_client():
    def veri_geldiginde(client, userdata, message):
        gelen_mesaj = message.payload.decode("utf-8")
        gelen_kanal = message.topic 
        
        try:
            if gelen_kanal == "enduvia/sensor/titresim":
                normal_orani = float(gelen_mesaj)
                hesaplanan_risk = (1.0 - normal_orani) * 100
                shared_data.anomali_yuzdesi = hesaplanan_risk
                
                if hesaplanan_risk < AI_LIMIT:
                    shared_data.uyari_mesaji = "Sorun Yok - Stabil"
                
                son_risk = round(shared_data.anomali_yuzdesi, 1)
                aktif_uyari = shared_data.uyari_mesaji
                
                ai_alarm_var_mi = "TEHLİKE" in aktif_uyari or "Anomali" in aktif_uyari or "Arıza" in aktif_uyari or "KRITIK_HATA" in aktif_uyari
                
                if ai_alarm_var_mi or son_risk >= AI_LIMIT:
                    durum = '🚨 KRİTİK İHLAL'
                    if ai_alarm_var_mi:
                        ihlal_metni = f"Yapay Zeka: {aktif_uyari} (%{son_risk})"
                    else:
                        ihlal_metni = f"Limit Aşımı (%{son_risk})"
                else:
                    durum = '✅ Normal'
                    ihlal_metni = "-"
                    
                shared_data.kayitlar.append({
                    'Tarih_Zaman': datetime.now(),
                    'Anomali Riski (%)': son_risk,
                    'Durum': durum,
                    'İhlal Sebebi': ihlal_metni
                })
                
                if len(shared_data.kayitlar) > 2000:
                    shared_data.kayitlar.pop(0)
                    
            elif gelen_kanal == "enduvia/sistem/uyari":
                shared_data.uyari_mesaji = gelen_mesaj
        except Exception as e:
            pass
            
    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
    except AttributeError:
        client = mqtt.Client() 
        
    client.on_message = veri_geldiginde
    client.connect("broker.hivemq.com", 1883, 60)
    
    client.subscribe("enduvia/sensor/titresim") 
    client.subscribe("enduvia/sistem/uyari") 
    return client

client = get_mqtt_client()

# ==========================================
# 3. SAYFA 1: HAREKETLİ DASHBOARD EKRANI
# ==========================================
if st.session_state.aktif_sayfa == 'Dashboard':
    
    buton_alani = st.empty()
    bilgi_alani = st.empty()
    
    if not shared_data.sistem_aktif:
        bilgi_alani.info("Sistem cihaz bağlantısı bekliyor. Veri akışını başlatmak için butona tıklayın.")
        if buton_alani.button("📡 SİSTEME BAĞLAN VE CANLI AKIŞI BAŞLAT", type="primary", use_container_width=True):
            client.loop_start() 
            shared_data.sistem_aktif = True
            st.rerun() 
            
    else:
        st.success("📡 Sistem aktif. Arka planda kesintisiz kayıt alınıyor...")
        dashboard_alani = st.empty()
        grafik_alarm_sayaci = 0  
        
        for i in range(1000): 
            df_gecmis = pd.DataFrame(shared_data.kayitlar)
            ekran_df = df_gecmis.iloc[-60:]
            
            son_risk = round(shared_data.anomali_yuzdesi, 1)
            aktif_uyari = shared_data.uyari_mesaji
            ai_alarm_var_mi = "TEHLİKE" in aktif_uyari or "Anomali" in aktif_uyari or "Arıza" in aktif_uyari or "KRITIK_HATA" in aktif_uyari
            
            with dashboard_alani.container():
                col1, col2, col3 = st.columns([1.5, 1, 1.5])
                
                with col1:
                    st.markdown(f"<div class='grad-card-cyan'><div class='card-title'>Yapay Zeka Anomali Riski</div><div class='card-value'>{son_risk}<span class='card-unit'> %</span></div></div>", unsafe_allow_html=True)
                with col2:
                    ag_yuku = np.random.randint(95, 100)
                    st.markdown(f"<div style='padding-top: 5px;'><div class='pill-card'><span style='color:#ef4444;'>🔴</span> <span style='color:#94a3b8; font-size:12px;'>Sistem</span> <span style='color:white; font-size:12px; font-weight:bold;'>%98</span></div><div class='pill-card'><span style='color:#06b6d4;'>🔵</span> <span style='color:#94a3b8; font-size:12px;'>Ağ Akışı</span> <span style='color:white; font-size:12px; font-weight:bold;'>%{ag_yuku}</span></div></div>", unsafe_allow_html=True)
                with col3:
                    fig_mini = go.Figure(go.Scatter(x=ekran_df['Tarih_Zaman'][-20:], y=ekran_df['Anomali Riski (%)'][-20:], mode='lines', line=dict(color='#06b6d4', width=2, shape='spline'), fill='tozeroy', fillcolor='rgba(6,182,212,0.2)'))
                    fig_mini.update_layout(height=110, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis=dict(visible=False), yaxis=dict(visible=False, range=[0, 100]))
                    st.plotly_chart(fig_mini, width="stretch", key=f"mini_{i}", config={'displayModeBar': False})

                if son_risk >= AI_LIMIT and not ai_alarm_var_mi:
                    st.warning(f"⚠️ **DİKKAT:** Risk Skoru %{son_risk}'e ulaştı, yapay zeka kararı bekleniyor...", icon="⚠️")
                    
                if ai_alarm_var_mi:
                    st.error(f"🤖 **EDGE IMPULSE UYARISI:** {aktif_uyari}", icon="🚨")

                st.markdown("<h4 style='color: white; margin-top: 10px; font-size: 16px;'>Risk Skoru Geçmişi (CANLI)</h4>", unsafe_allow_html=True)
                fig_main = go.Figure()
                fig_main.add_trace(go.Scatter(x=ekran_df['Tarih_Zaman'], y=ekran_df['Anomali Riski (%)'], name='Risk (%)', mode='lines', line=dict(color='#06b6d4', width=3, shape='spline'), fill='tozeroy', fillcolor='rgba(6, 182, 212, 0.1)'))
                
                fig_main.update_layout(
                    template="plotly_dark", height=320, margin=dict(l=0, r=0, t=10, b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(30,30,45,0.4)',
                    hovermode="x unified",
                    xaxis=dict(showgrid=False, zeroline=False, tickfont=dict(color='#64748b')),
                    yaxis=dict(range=[0, 100], showgrid=True, gridcolor='rgba(255,255,255,0.05)', tickfont=dict(color='#06b6d4'))
                )
                fig_main.add_hline(y=AI_LIMIT, line_dash="dash", line_color="#ef4444", opacity=0.6)
                
                st.plotly_chart(fig_main, width="stretch", key=f"main_{i}", config={'displayModeBar': False})

                col_donut, col_bar = st.columns(2)
                with col_donut:
                    st.markdown("<h4 style='color: white; font-size: 15px;'>Risk Dağılımı</h4>", unsafe_allow_html=True)
                    krt_yuzde = len(ekran_df[ekran_df['Durum'] == '🚨 KRİTİK İHLAL']) 
                    uyr_yuzde = len(ekran_df[(ekran_df['Anomali Riski (%)'] >= 40.0) & (ekran_df['Anomali Riski (%)'] < AI_LIMIT)])
                    nrm_yuzde = len(ekran_df) - (krt_yuzde + uyr_yuzde)
                    
                    if nrm_yuzde + uyr_yuzde + krt_yuzde == 0: nrm_yuzde = 1
                    
                    fig_donut = go.Figure(data=[go.Pie(labels=['Normal', 'Uyarı', 'Kritik'], values=[nrm_yuzde, uyr_yuzde, krt_yuzde], hole=0.7, marker_colors=['#06b6d4', '#3b82f6', '#ef4444'])])
                    fig_donut.update_layout(height=260, margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig_donut, width="stretch", key=f"donut_{i}", config={'displayModeBar': False})
                with col_bar:
                    st.markdown("<h4 style='color: white; font-size: 15px;'>Haftalık Ortalama Riskler</h4>", unsafe_allow_html=True)
                    fig_bar = go.Figure(data=[go.Bar(x=['Pzt','Sal','Çar','Per','Cum','Cmt','Paz'], y=[5, 8, 12, 65, 14, 7, 9], marker_color='#06b6d4', width=0.4)])
                    fig_bar.update_layout(template="plotly_dark", height=260, margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', yaxis=dict(showgrid=True, range=[0, 100], gridcolor='rgba(255,255,255,0.05)'))
                    st.plotly_chart(fig_bar, width="stretch", key=f"bar_{i}", config={'displayModeBar': False})
            
            time.sleep(0.5)

# ==========================================
# 4. SAYFA 2 & 3: RAPORLAR VE ALARMLAR
# ==========================================
elif st.session_state.aktif_sayfa == 'Raporlar':
    col_baslik, col_buton = st.columns([4, 1])
    with col_baslik:
        st.markdown("<h2 style='color: #06b6d4;'>📈 Sistem Raporları (Tüm Veriler)</h2>", unsafe_allow_html=True)
    with col_buton:
        if st.button("🔄 Tabloyu Yenile", use_container_width=True):
            st.rerun()
            
    st.divider()
    
    df_rapor = pd.DataFrame(shared_data.kayitlar)
    
    col_r1, col_r2 = st.columns(2)
    col_r1.metric("Kayıtlı Veri Sayısı", f"{len(df_rapor)} Adet")
    col_r2.metric("Sistem Çalışma Süresi", "Arka Planda Kesintisiz" if shared_data.sistem_aktif else "Bekliyor")
    
    def satir_vurgula(row):
        if row['Durum'] == '🚨 KRİTİK İHLAL':
            return ['background-color: rgba(220, 38, 38, 0.2); color: #ef4444; font-weight: bold;'] * len(row)
        else:
            return [''] * len(row)
            
    sirali_df = df_rapor.sort_values(by='Tarih_Zaman', ascending=False).reset_index(drop=True)
    renkli_tablo = sirali_df.style.apply(satir_vurgula, axis=1)
    st.dataframe(renkli_tablo, use_container_width=True, height=500)

elif st.session_state.aktif_sayfa == 'Alarmlar':
    st.markdown("<h2 style='color: #ef4444;'>🔔 Kritik Alarm Geçmişi</h2>", unsafe_allow_html=True)
    st.divider()
    
    df_rapor = pd.DataFrame(shared_data.kayitlar)
    df_alarmlar = df_rapor[df_rapor['Durum'] == '🚨 KRİTİK İHLAL'].sort_values(by='Tarih_Zaman', ascending=False).reset_index(drop=True)
    
    if len(df_alarmlar) > 0:
        st.error(f"Sistem geçmişinde toplam **{len(df_alarmlar)} adet** kritik ihlal tespit edildi!")
        def alarm_vurgula(row):
            return ['background-color: rgba(220, 38, 38, 0.2); color: #ef4444; font-weight: bold;'] * len(row)
        renkli_alarm_tablosu = df_alarmlar.style.apply(alarm_vurgula, axis=1)
        st.dataframe(renkli_alarm_tablosu, use_container_width=True)
    else:
        st.success("Tebrikler! Sistem geçmişinde hiçbir alarm veya limit ihlali bulunmuyor.")
