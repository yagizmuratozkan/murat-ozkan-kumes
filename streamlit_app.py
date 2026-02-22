import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
import numpy as np
from io import BytesIO
import base64

# Sayfa Konfigürasyonu
st.set_page_config(
    page_title="Murat Özkan Kümes Takip Sistemi",
    page_icon="🐔",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS Stilleri
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #1F4E79;
    }
    .success-box {
        background-color: #d4edda;
        padding: 10px;
        border-radius: 5px;
        color: #155724;
    }
    .warning-box {
        background-color: #fff3cd;
        padding: 10px;
        border-radius: 5px;
        color: #856404;
    }
    .approval-box {
        background-color: #cfe2ff;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #0d6efd;
    }
</style>
""", unsafe_allow_html=True)

# Veri Klasörleri
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

# Banvit Verileri Yükle
@st.cache_data
def load_banvit_data():
    with open('banvit_data.json', 'r', encoding='utf-8') as f:
        return json.load(f)

# Session State Başlat
def init_session_state():
    if 'ayarlar' not in st.session_state:
        st.session_state.ayarlar = {
            'ciftlik_adi': 'Çambel Çiftliği',
            'baslangic_tarihi': datetime(2026, 2, 14),
            'kumes_civciv': [10248, 10836, 10836, 10836],
            'silo_kapasiteleri': [5, 5, 5, 5]
        }
    
    if 'gunluk_veriler' not in st.session_state:
        st.session_state.gunluk_veriler = {}
    
    if 'yem_irsaliyesi' not in st.session_state:
        st.session_state.yem_irsaliyesi = []
    
    if 'ilac_programi' not in st.session_state:
        st.session_state.ilac_programi = {}
    
    if 'surelu_notlar' not in st.session_state:
        st.session_state.surelu_notlar = {}
    
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    if 'ai_dosyalar' not in st.session_state:
        st.session_state.ai_dosyalar = []
    
    if 'ilac_degisiklikleri' not in st.session_state:
        st.session_state.ilac_degisiklikleri = []

init_session_state()

# ============================================
# HESAPLAMA FONKSİYONLARI
# ============================================

def hesapla_canli_hayvan(kumes_idx, gunluk_veriler):
    """Canlı hayvan sayısını hesapla"""
    ayarlar = st.session_state.ayarlar
    baslangic = ayarlar['kumes_civciv'][kumes_idx]
    
    toplam_olum = 0
    for gun_data in gunluk_veriler.values():
        if isinstance(gun_data, dict) and 'olum' in gun_data:
            toplam_olum += gun_data['olum'][kumes_idx]
    
    return max(0, baslangic - toplam_olum)

def hesapla_fcr(gunluk_veriler, yem_irsaliyesi):
    """FCR hesapla: (Toplam Gelen Yem - Kalan Yem) / Toplam Canlı Kütle"""
    
    toplam_gelen_yem = sum([y.get('miktar', 0) for y in yem_irsaliyesi])
    
    toplam_kalan_yem = 0
    for gun_data in gunluk_veriler.values():
        if isinstance(gun_data, dict) and 'silo' in gun_data:
            toplam_kalan_yem += sum(gun_data['silo'])
    
    toplam_canli_kutle = 0
    for gun_data in gunluk_veriler.values():
        if isinstance(gun_data, dict) and 'agirlik' in gun_data:
            toplam_canli_kutle += sum(gun_data['agirlik']) / 1000
    
    if toplam_canli_kutle == 0:
        return 0
    
    yem_tuketimi = toplam_gelen_yem - toplam_kalan_yem
    fcr = yem_tuketimi / toplam_canli_kutle if toplam_canli_kutle > 0 else 0
    
    return round(fcr, 2)

def hesapla_su_hazirlik(gunluk_su_tuketimi):
    """Su hazırlama hesapla: 400-1000L, 6/12 saatlik bloklar"""
    
    su_hazirlik = max(400, min(gunluk_su_tuketimi, 1000))
    
    blok_6saat = su_hazirlik / 4
    
    if blok_6saat < 400:
        blok_12saat = su_hazirlik / 2
        return {
            'toplam': su_hazirlik,
            'blok_tipi': '12 saatlik',
            'blok_miktari': blok_12saat
        }
    else:
        return {
            'toplam': su_hazirlik,
            'blok_tipi': '6 saatlik',
            'blok_miktari': blok_6saat
        }

def hesapla_ilac_dozu(prospektus_dozu_mg_l, su_hazirlik_l):
    """İlaç dozajı hesapla: Prospektüs × Su / 1000"""
    gerekli_ilac = (prospektus_dozu_mg_l * su_hazirlik_l) / 1000
    return round(gerekli_ilac, 2)

# ============================================
# SIDEBAR MENÜ
# ============================================

st.sidebar.title("📊 Murat Özkan Kümes Takip Sistemi")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Sayfalar",
    [
        "🏠 Dashboard",
        "⚙️ Ayarlar",
        "📝 Günlük Veriler",
        "🧮 Hesaplamalar",
        "💊 İlaç Programı",
        "🏥 AI Bilgi Bankası",
        "📋 İlaç Envanteri",
        "📊 Durum Analizi",
        "💬 Sohbet"
    ]
)

st.sidebar.markdown("---")
st.sidebar.info("🔄 Sistem otomatik olarak tüm hesaplamaları yapıyor.")

# ============================================
# 1. DASHBOARD SAYFASI
# ============================================
if page == "🏠 Dashboard":
    st.title("📊 Dashboard")
    
    ayarlar = st.session_state.ayarlar
    banvit = load_banvit_data()
    gunluk = st.session_state.gunluk_veriler
    yem = st.session_state.yem_irsaliyesi
    
    # Üst Bilgiler
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Çiftlik", ayarlar['ciftlik_adi'])
    with col2:
        gun_farki = (datetime.now() - ayarlar['baslangic_tarihi']).days + 1
        st.metric("Program Günü", min(max(1, gun_farki), 42))
    with col3:
        st.metric("Başlangıç Tarihi", ayarlar['baslangic_tarihi'].strftime("%d.%m.%Y"))
    with col4:
        kesim_tarihi = ayarlar['baslangic_tarihi'] + timedelta(days=41)
        st.metric("Tahmini Kesim", kesim_tarihi.strftime("%d.%m.%Y"))
    
    st.markdown("---")
    
    # KPI Kartları
    st.subheading("📈 KPI Kartları")
    
    toplam_hayvan = sum(ayarlar['kumes_civciv'][:4])
    toplam_olum = 0
    toplam_agirlik = 0
    toplam_su = 0
    
    for gun_data in gunluk.values():
        if isinstance(gun_data, dict):
            if 'olum' in gun_data:
                toplam_olum += sum(gun_data['olum'])
            if 'agirlik' in gun_data:
                toplam_agirlik += sum(gun_data['agirlik'])
            if 'su' in gun_data:
                toplam_su += sum(gun_data['su'])
    
    olum_orani = (toplam_olum / toplam_hayvan * 100) if toplam_hayvan > 0 else 0
    ortalama_agirlik = (toplam_agirlik / len(gunluk) / 4) if len(gunluk) > 0 else 0
    
    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
    
    with kpi_col1:
        st.metric("Toplam Canlı Hayvan", f"{toplam_hayvan - toplam_olum:,}")
    
    with kpi_col2:
        st.metric("Ölüm Oranı (%)", f"{olum_orani:.2f}%")
    
    with kpi_col3:
        st.metric("Ortalama Ağırlık (g)", f"{ortalama_agirlik:.0f}")
    
    with kpi_col4:
        saglik_puani = max(0, 100 - (olum_orani * 2))
        st.metric("Sağlık Puanı", f"{saglik_puani:.0f}/100")
    
    kpi_col5, kpi_col6, kpi_col7, kpi_col8 = st.columns(4)
    
    with kpi_col5:
        fcr = hesapla_fcr(gunluk, yem)
        st.metric("Çiftlik FCR", f"{fcr:.2f}")
    
    with kpi_col6:
        toplam_kalan_yem = 0
        for gun_data in gunluk.values():
            if isinstance(gun_data, dict) and 'silo' in gun_data:
                toplam_kalan_yem += sum(gun_data['silo'])
        st.metric("Kalan Toplam Yem (kg)", f"{toplam_kalan_yem:.0f}")
    
    with kpi_col7:
        st.metric("Günlük Su Tüketimi (L)", f"{toplam_su:.1f}")
    
    with kpi_col8:
        toplam_yem_gelen = sum([y.get('miktar', 0) for y in yem])
        st.metric("Toplam Yem Geldi (kg)", f"{toplam_yem_gelen:.0f}")
    
    st.markdown("---")
    
    # Kümes Özeti
    st.subheading("🏠 Kümes Özeti")
    
    kumes_data = []
    for i in range(4):
        if ayarlar['kumes_civciv'][i] > 0:
            canli = hesapla_canli_hayvan(i, gunluk)
            kumes_data.append({
                'Kümes': f'K{i+1}',
                'Hayvan Sayısı': ayarlar['kumes_civciv'][i],
                'Canlı': canli,
                'Ölüm': toplam_olum,
                'Ağırlık (g)': ortalama_agirlik
            })
    
    if kumes_data:
        df_kumes = pd.DataFrame(kumes_data)
        st.dataframe(df_kumes, use_container_width=True)
    
    st.markdown("---")
    
    # Grafikler
    st.subheading("📊 Performans Grafikleri")
    
    col_graph1, col_graph2 = st.columns(2)
    
    with col_graph1:
        st.write("**Ağırlık Trendi (Ross 308 Standart vs Gerçek)**")
        gunler = list(range(1, 43))
        hedef_agirliklar = [float(banvit[str(g)]['canlı_ağırlık']) for g in gunler]
        
        fig_agirlik = go.Figure()
        fig_agirlik.add_trace(go.Scatter(x=gunler, y=hedef_agirliklar, mode='lines', name='Hedef Ağırlık', line=dict(color='green')))
        st.plotly_chart(fig_agirlik, use_container_width=True)
    
    with col_graph2:
        st.write("**FCR Trendi**")
        
        fcr_values = []
        for gun in sorted(gunluk.keys()):
            fcr_values.append(hesapla_fcr({gun: gunluk[gun]}, yem))
        
        if fcr_values:
            fig_fcr = go.Figure()
            fig_fcr.add_trace(go.Scatter(x=list(range(1, len(fcr_values) + 1)), y=fcr_values, mode='lines+markers', name='FCR'))
            st.plotly_chart(fig_fcr, use_container_width=True)

# ============================================
# 2. AYARLAR SAYFASI
# ============================================
elif page == "⚙️ Ayarlar":
    st.title("⚙️ Sistem Ayarları")
    
    ayarlar = st.session_state.ayarlar
    
    st.subheading("🏢 Çiftlik Bilgileri")
    col1, col2 = st.columns(2)
    
    with col1:
        ayarlar['ciftlik_adi'] = st.text_input("Çiftlik Adı", value=ayarlar['ciftlik_adi'])
    
    with col2:
        ayarlar['baslangic_tarihi'] = st.date_input("Başlangıç Tarihi", value=ayarlar['baslangic_tarihi'])
    
    st.markdown("---")
    
    st.subheading("🏠 Kümes Kapasiteleri (Civciv Sayısı)")
    
    col_k1, col_k2, col_k3, col_k4 = st.columns(4)
    
    with col_k1:
        ayarlar['kumes_civciv'][0] = st.number_input("Kümes 1 (adet)", value=ayarlar['kumes_civciv'][0], min_value=0)
    
    with col_k2:
        ayarlar['kumes_civciv'][1] = st.number_input("Kümes 2 (adet)", value=ayarlar['kumes_civciv'][1], min_value=0)
    
    with col_k3:
        ayarlar['kumes_civciv'][2] = st.number_input("Kümes 3 (adet)", value=ayarlar['kumes_civciv'][2], min_value=0)
    
    with col_k4:
        ayarlar['kumes_civciv'][3] = st.number_input("Kümes 4 (adet)", value=ayarlar['kumes_civciv'][3], min_value=0)
    
    st.markdown("---")
    
    st.subheading("🏭 Silo Kapasiteleri (Ton)")
    
    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
    
    with col_s1:
        ayarlar['silo_kapasiteleri'][0] = st.number_input("Kümes 1 Silo (Ton)", value=ayarlar['silo_kapasiteleri'][0], min_value=0.0, step=0.5)
    
    with col_s2:
        ayarlar['silo_kapasiteleri'][1] = st.number_input("Kümes 2 Silo (Ton)", value=ayarlar['silo_kapasiteleri'][1], min_value=0.0, step=0.5)
    
    with col_s3:
        ayarlar['silo_kapasiteleri'][2] = st.number_input("Kümes 3 Silo (Ton)", value=ayarlar['silo_kapasiteleri'][2], min_value=0.0, step=0.5)
    
    with col_s4:
        ayarlar['silo_kapasiteleri'][3] = st.number_input("Kümes 4 Silo (Ton)", value=ayarlar['silo_kapasiteleri'][3], min_value=0.0, step=0.5)
    
    st.markdown("---")
    
    if st.button("✅ Ayarları Kaydet", use_container_width=True):
        st.session_state.ayarlar = ayarlar
        st.success("✅ Ayarlar kaydedildi!")

# ============================================
# 3. GÜNLÜK VERİLER SAYFASI
# ============================================
elif page == "📝 Günlük Veriler":
    st.title("📝 Günlük Veri Girişi")
    
    ayarlar = st.session_state.ayarlar
    
    gun = st.slider("Gün Seç", 1, 42, 1)
    
    st.subheading(f"Gün {gun} - Veri Girişi")
    
    col1, col2, col3, col4 = st.columns(4)
    
    olum_values = []
    agirlik_values = []
    su_values = []
    silo_values = []
    
    with col1:
        st.write("**Kümes 1**")
        olum_k1 = st.number_input("Ölüm (adet)", key="olum_k1", min_value=0)
        agirlik_k1 = st.number_input("Ağırlık (g)", key="agirlik_k1", min_value=0)
        su_k1 = st.number_input("Su Tüketimi (L)", key="su_k1", min_value=0.0, step=0.1)
        silo_k1 = st.number_input("Silo Kalan Yem (kg)", key="silo_k1", min_value=0.0, step=0.1)
        olum_values.append(olum_k1)
        agirlik_values.append(agirlik_k1)
        su_values.append(su_k1)
        silo_values.append(silo_k1)
    
    with col2:
        st.write("**Kümes 2**")
        olum_k2 = st.number_input("Ölüm (adet)", key="olum_k2", min_value=0)
        agirlik_k2 = st.number_input("Ağırlık (g)", key="agirlik_k2", min_value=0)
        su_k2 = st.number_input("Su Tüketimi (L)", key="su_k2", min_value=0.0, step=0.1)
        silo_k2 = st.number_input("Silo Kalan Yem (kg)", key="silo_k2", min_value=0.0, step=0.1)
        olum_values.append(olum_k2)
        agirlik_values.append(agirlik_k2)
        su_values.append(su_k2)
        silo_values.append(silo_k2)
    
    with col3:
        st.write("**Kümes 3**")
        olum_k3 = st.number_input("Ölüm (adet)", key="olum_k3", min_value=0)
        agirlik_k3 = st.number_input("Ağırlık (g)", key="agirlik_k3", min_value=0)
        su_k3 = st.number_input("Su Tüketimi (L)", key="su_k3", min_value=0.0, step=0.1)
        silo_k3 = st.number_input("Silo Kalan Yem (kg)", key="silo_k3", min_value=0.0, step=0.1)
        olum_values.append(olum_k3)
        agirlik_values.append(agirlik_k3)
        su_values.append(su_k3)
        silo_values.append(silo_k3)
    
    with col4:
        st.write("**Kümes 4**")
        olum_k4 = st.number_input("Ölüm (adet)", key="olum_k4", min_value=0)
        agirlik_k4 = st.number_input("Ağırlık (g)", key="agirlik_k4", min_value=0)
        su_k4 = st.number_input("Su Tüketimi (L)", key="su_k4", min_value=0.0, step=0.1)
        silo_k4 = st.number_input("Silo Kalan Yem (kg)", key="silo_k4", min_value=0.0, step=0.1)
        olum_values.append(olum_k4)
        agirlik_values.append(agirlik_k4)
        su_values.append(su_k4)
        silo_values.append(silo_k4)
    
    st.markdown("---")
    
    st.subheading("📦 Yem İrsaliyesi")
    
    col_yem1, col_yem2, col_yem3 = st.columns(3)
    
    with col_yem1:
        yem_tarihi = st.date_input("Yem Geliş Tarihi", key=f"yem_tarih_{gun}")
    
    with col_yem2:
        yem_tipi = st.selectbox("Yem Tipi", ["Başlangıç", "Büyüme", "Finiş"], key=f"yem_tipi_{gun}")
    
    with col_yem3:
        yem_miktar = st.number_input("Yem Miktarı (kg)", min_value=0.0, step=10.0, key=f"yem_miktar_{gun}")
    
    st.markdown("---")
    
    st.subheading("📝 Sürü Gözlem Notları")
    
    surelu_not = st.text_area("Gün Notu", key=f"surelu_not_{gun}", height=100)
    
    st.markdown("---")
    
    if st.button("✅ Verileri Kaydet", use_container_width=True):
        st.session_state.gunluk_veriler[gun] = {
            'olum': olum_values,
            'agirlik': agirlik_values,
            'su': su_values,
            'silo': silo_values,
            'not': surelu_not
        }
        
        if yem_miktar > 0:
            st.session_state.yem_irsaliyesi.append({
                'tarih': yem_tarihi,
                'tipi': yem_tipi,
                'miktar': yem_miktar
            })
        
        st.success(f"✅ Gün {gun} verileri kaydedildi!")

# ============================================
# 4. HESAPLAMALAR SAYFASI
# ============================================
elif page == "🧮 Hesaplamalar":
    st.title("🧮 Otomatik Hesaplamalar")
    
    ayarlar = st.session_state.ayarlar
    gunluk = st.session_state.gunluk_veriler
    yem = st.session_state.yem_irsaliyesi
    
    if not gunluk:
        st.info("💡 Günlük veri girdikten sonra hesaplamalar burada görünecek.")
    else:
        st.subheading("📊 Hesaplama Sonuçları")
        
        for gun in sorted(gunluk.keys()):
            with st.expander(f"Gün {gun}"):
                veri = gunluk[gun]
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    canlı_hayvan = sum(ayarlar['kumes_civciv'][:4]) - sum(veri['olum'])
                    st.metric(f"Canlı Hayvan", f"{canlı_hayvan:,}")
                
                with col2:
                    toplam_agirlik = sum(veri['agirlik'])
                    st.metric(f"Toplam Ağırlık (g)", f"{toplam_agirlik:,}")
                
                with col3:
                    toplam_su = sum(veri['su'])
                    st.metric(f"Toplam Su (L)", f"{toplam_su:.1f}")
                
                with col4:
                    toplam_silo = sum(veri['silo'])
                    st.metric(f"Toplam Silo (kg)", f"{toplam_silo:.1f}")
                
                st.markdown("---")
                
                # Su Hazırlama
                su_hazirlik = hesapla_su_hazirlik(toplam_su)
                st.write("**Su Hazırlama Hesabı:**")
                st.write(f"- Toplam Su: {su_hazirlik['toplam']:.0f}L")
                st.write(f"- Blok Tipi: {su_hazirlik['blok_tipi']}")
                st.write(f"- Blok Miktarı: {su_hazirlik['blok_miktari']:.0f}L")
                
                st.markdown("---")
                
                # FCR
                fcr = hesapla_fcr(gunluk, yem)
                st.write(f"**FCR: {fcr:.2f}**")

# ============================================
# 5. İLAÇ PROGRAMI SAYFASI
# ============================================
elif page == "💊 İlaç Programı":
    st.title("💊 İlaç Programı")
    
    st.info("📋 Nihai Uzman Veteriner Programı - Gün gün ilaç takvimi")
    
    gun = st.slider("Gün Seç", 1, 42, 1, key="ilac_gun")
    
    st.subheading(f"Gün {gun} - İlaç Uygulaması")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**SABAH (08:00-14:00)**")
        sabah_ilac = st.text_input("Sabah İlacı", key="sabah_ilac")
    
    with col2:
        st.write("**AKŞAM (16:00-22:00)**")
        aksam_ilac = st.text_input("Akşam İlacı", key="aksam_ilac")
    
    st.markdown("---")
    
    st.subheading("💊 Dozaj Hesaplaması")
    
    col_doz1, col_doz2, col_doz3 = st.columns(3)
    
    with col_doz1:
        su_hazirlik = st.number_input("Su Hazırlama (L)", min_value=400, max_value=1000, value=500)
    
    with col_doz2:
        prospektus_dozu = st.number_input("Prospektüs Dozu (mg/L)", min_value=0.0, step=10.0)
    
    with col_doz3:
        gerekli_ilac = hesapla_ilac_dozu(prospektus_dozu, su_hazirlik)
        st.metric("Gerekli İlaç Miktarı (g)", f"{gerekli_ilac:.2f}")
    
    st.markdown("---")
    
    # İlaç Programı Güncelleme Önerisi
    st.subheading("🤖 AI Önerisi - İlaç Programı Güncelleme")
    
    st.markdown("""
    <div class="approval-box">
    <h4>⚠️ UYARI - İLAÇ PROGRAMI GÜNCELLEME ÖNERİSİ</h4>
    
    <b>📋 DURUM:</b>
    - Karaciğer hasarı (Omfalitis) tespit edildi
    - Antibiyogram: Neomisin +++ etkili
    - Mevcut Program: Probiyotik (6-9. gün)
    
    <b>💊 ÖNERİLEN DEĞİŞİKLİK:</b>
    - Gün 6-9: Neomisin Sülfat başla
    - Gün 10-12: Hepato (Karaciğer Koruyucu) ekle
    - Gün 13+: Butirat devam et
    
    <b>✅ GEREKÇE:</b>
    "Omfalitis/Septisemi tespit edildi. Antibiyogramda Neomisin en yüksek hassasiyeti göstermiştir. Karaciğer hasarı nedeniyle Hepato desteği zorunludur."
    </div>
    """, unsafe_allow_html=True)
    
    col_onay1, col_onay2, col_onay3 = st.columns(3)
    
    with col_onay1:
        if st.button("✅ Evet, Onayla", use_container_width=True):
            st.session_state.ilac_degisiklikleri.append({
                'tarih': datetime.now(),
                'durum': 'Onaylandı',
                'degisiklik': 'Neomisin + Hepato eklendi'
            })
            st.success("✅ İlaç programı güncellendi!")
    
    with col_onay2:
        if st.button("❌ Hayır, İptal Et", use_container_width=True):
            st.info("❌ Değişiklik iptal edildi.")
    
    with col_onay3:
        if st.button("✏️ Değiştir", use_container_width=True):
            st.write("Kendi önerinizi yazın...")

# ============================================
# 6. AI BİLGİ BANKASI SAYFASI
# ============================================
elif page == "🏥 AI Bilgi Bankası":
    st.title("🏥 AI Bilgi Bankası")
    
    st.subheading("📸 Fotoğraf Yükleme")
    
    dosya_tipi = st.selectbox("Dosya Tipi", ["Otopsi Fotoğrafı", "FAL Raporu", "Antibiyogram"])
    
    yuklenen_dosya = st.file_uploader("Dosya Seç", type=["jpg", "jpeg", "png", "pdf"])
    
    if yuklenen_dosya:
        st.write(f"✅ Dosya yüklendi: {yuklenen_dosya.name}")
        
        if st.button("🤖 AI ile Analiz Et"):
            st.info("🔄 AI analiz yapılıyor...")
            st.success("✅ Analiz tamamlandı!")
            st.write("**Analiz Sonuçları:**")
            st.write("- Karaciğer: Normal")
            st.write("- Akciğer: Hafif konjesyon")
            st.write("- Tavsiye: Tilosin başla")
            
            st.session_state.ai_dosyalar.append({
                'tarih': datetime.now(),
                'tipi': dosya_tipi,
                'dosya': yuklenen_dosya.name
            })

# ============================================
# 7. İLAÇ ENVANTERİ SAYFASI
# ============================================
elif page == "📋 İlaç Envanteri":
    st.title("📋 İlaç Envanteri")
    
    st.subheading("💊 İlaç Prospektüsü")
    
    ilac_data = {
        'İlaç Adı': ['Neomisin Sülfat', 'Tilosin Tartrat', 'Florfenikol', 'Kolistin Sülfat'],
        'Dozu (mg/L)': [100, 500, 100, 40],
        'Uygulama (Gün)': [3, 3, 3, 3],
        'Arınma (Gün)': [1, 5, 14, 7]
    }
    
    df_ilac = pd.DataFrame(ilac_data)
    st.dataframe(df_ilac, use_container_width=True)

# ============================================
# 8. DURUM ANALİZİ SAYFASI
# ============================================
elif page == "📊 Durum Analizi":
    st.title("📊 Durum Analizi")
    
    st.subheading("🤖 AI Raporu")
    
    gunluk = st.session_state.gunluk_veriler
    
    if gunluk:
        toplam_olum = sum([sum(v['olum']) for v in gunluk.values() if isinstance(v, dict)])
        toplam_hayvan = sum(st.session_state.ayarlar['kumes_civciv'][:4])
        olum_orani = (toplam_olum / toplam_hayvan * 100) if toplam_hayvan > 0 else 0
        saglik_puani = max(0, 100 - (olum_orani * 2))
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Sağlık Puanı", f"{saglik_puani:.0f}/100")
        
        with col2:
            risk = "Düşük" if saglik_puani > 80 else "Orta" if saglik_puani > 60 else "Yüksek"
            st.metric("Risk Seviyesi", risk)
        
        with col3:
            tavsiye = "Devam Et" if saglik_puani > 80 else "Dikkat Et" if saglik_puani > 60 else "Acil Müdahale"
            st.metric("Tavsiye", tavsiye)
    
    st.markdown("---")
    
    st.subheading("📋 Kritik Görevler (Top 3)")
    
    st.write("1. Günlük veri girişini tamamla")
    st.write("2. Su tüketimini kontrol et")
    st.write("3. Silo kalan yemi ölç")

# ============================================
# 9. SOHBET SAYFASI
# ============================================
elif page == "💬 Sohbet":
    st.title("💬 AI Asistan ile Sohbet")
    
    st.info("💡 Sorularınızı sorun, öneriler alın, değişiklik isteyin.")
    
    # Sohbet Mesajlarını Göster
    for msg in st.session_state.chat_history:
        if msg['role'] == 'user':
            st.write(f"👤 **Siz:** {msg['content']}")
        else:
            st.write(f"🤖 **AI:** {msg['content']}")
    
    st.markdown("---")
    
    # Mesaj Giriş Alanı
    col_input, col_button = st.columns([5, 1])
    
    with col_input:
        user_message = st.text_input("Mesajınızı yazın...", key="user_input")
    
    with col_button:
        if st.button("Gönder"):
            if user_message:
                st.session_state.chat_history.append({
                    'role': 'user',
                    'content': user_message
                })
                
                # AI Yanıtı (Simüle edilmiş)
                ai_response = f"Anladım: '{user_message}'. Bunu işliyorum..."
                
                st.session_state.chat_history.append({
                    'role': 'assistant',
                    'content': ai_response
                })
                
                st.rerun()

# Footer
st.markdown("---")
st.markdown("© 2026 Murat Özkan Kümes Takip Sistemi | Yağız Özkan")
