import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import os
from datetime import datetime, timedelta
import numpy as np
from typing import Dict, List, Tuple, Optional
import google.generativeai as genai

# ============ CONFIGURATION ============
st.set_page_config(
    page_title="Murat Özkan Kümes İşletim Sistemi",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border-left: 5px solid #1f4e79; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #1f4e79; color: white; font-weight: bold; }
    .stTextInput>div>div>input, .stNumberInput>div>div>input { background-color: #fff9e6 !important; }
    .stSidebar { background-color: #f0f2f6; }
    h1, h2, h3 { color: #1f4e79; font-family: 'Georgia', serif; }
    .alert-red { background-color: #ffcccc; padding: 15px; border-radius: 5px; border-left: 5px solid #dc3545; }
    .alert-yellow { background-color: #fff3cd; padding: 15px; border-radius: 5px; border-left: 5px solid #ffc107; }
    .alert-green { background-color: #d4edda; padding: 15px; border-radius: 5px; border-left: 5px solid #28a745; }
</style>
""", unsafe_allow_html=True)

# ============ DATA MANAGEMENT ============
DATA_FILE = 'farm_data.json'
BANVIT_FILE = 'banvit_data.json'

def load_json(file_path):
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Dosya okuma hatası: {e}")
            return {}
    return {}

def save_json(data, file_path):
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"Dosya kaydetme hatası: {e}")
        return False

def log_transaction(data, action, details):
    """Her veri değişikliğini kaydet"""
    transaction = {
        "timestamp": str(datetime.now()),
        "action": action,
        "details": details
    }
    if "metadata" not in data:
        data["metadata"] = {"transaction_log": []}
    if "transaction_log" not in data["metadata"]:
        data["metadata"]["transaction_log"] = []
    data["metadata"]["transaction_log"].append(transaction)
    data["metadata"]["last_updated"] = str(datetime.now())

# ============ INITIALIZATION ============
if 'farm_data' not in st.session_state:
    st.session_state.farm_data = load_json(DATA_FILE)
if 'banvit_data' not in st.session_state:
    st.session_state.banvit_data = load_json(BANVIT_FILE)

# ============ CORE CALCULATIONS ============
def get_current_day():
    """Mevcut programın kaçıncı günü olduğunu hesapla"""
    try:
        start_dt = datetime.strptime(
            st.session_state.farm_data['settings']['start_date'], 
            '%Y-%m-%d'
        ).date()
        day = (datetime.now().date() - start_dt).days + 1
        return max(1, min(42, day))
    except:
        return 1

def calculate_live_birds_per_house(house_name: str, current_day: int) -> int:
    """Her kümesteki canlı hayvan sayısını hesapla (başlangıç - toplam ölüm)"""
    try:
        initial = st.session_state.farm_data['settings']['houses'][house_name]['chick_count']
        deaths = 0
        
        # Tüm günlerdeki ölümleri topla
        for day in range(1, current_day + 1):
            day_key = f"day_{day}"
            if day_key in st.session_state.farm_data['daily_data']:
                day_data = st.session_state.farm_data['daily_data'][day_key]
                if house_name in day_data and 'deaths' in day_data[house_name]:
                    deaths += day_data[house_name]['deaths']
        
        return max(0, initial - deaths)
    except:
        return 0

def calculate_total_live_birds(current_day: int) -> int:
    """Tüm kümeslerdeki toplam canlı hayvan sayısı"""
    total = 0
    for house_name in st.session_state.farm_data['settings']['houses'].keys():
        total += calculate_live_birds_per_house(house_name, current_day)
    return total

def calculate_average_weight(current_day: int) -> float:
    """Çiftlik ortalaması canlı ağırlık (gram)"""
    try:
        total_weight = 0
        total_birds = 0
        
        for house_name in st.session_state.farm_data['settings']['houses'].keys():
            day_key = f"day_{current_day}"
            if day_key in st.session_state.farm_data['daily_data']:
                day_data = st.session_state.farm_data['daily_data'][day_key]
                if house_name in day_data and 'weight' in day_data[house_name]:
                    weight = day_data[house_name]['weight']
                    live_birds = calculate_live_birds_per_house(house_name, current_day)
                    total_weight += weight * live_birds
                    total_birds += live_birds
        
        if total_birds > 0:
            return total_weight / total_birds
        return 0
    except:
        return 0

def calculate_fcr(current_day: int) -> float:
    """Çiftlik FCR hesapla: (Toplam Gelen Yem - Siloda Kalan) / Toplam Canlı Hayvan"""
    try:
        # Toplam gelen yem
        total_feed_received = 0
        for invoice in st.session_state.farm_data.get('feed_invoices', []):
            total_feed_received += invoice.get('quantity', 0)
        
        # Toplam siloda kalan yem
        total_silo_remaining = 0
        day_key = f"day_{current_day}"
        if day_key in st.session_state.farm_data['daily_data']:
            day_data = st.session_state.farm_data['daily_data'][day_key]
            for house_name in st.session_state.farm_data['settings']['houses'].keys():
                if house_name in day_data and 'silo_remaining' in day_data[house_name]:
                    total_silo_remaining += day_data[house_name]['silo_remaining']
        
        # Net tüketilen yem
        net_consumed = total_feed_received - total_silo_remaining
        total_live = calculate_total_live_birds(current_day)
        
        if total_live > 0 and net_consumed > 0:
            return net_consumed / total_live
        return 0
    except:
        return 0

def calculate_death_rate(current_day: int) -> float:
    """Ölüm oranı (%) hesapla"""
    try:
        total_deaths = 0
        total_initial = 0
        
        for house_name, house_info in st.session_state.farm_data['settings']['houses'].items():
            total_initial += house_info['chick_count']
            
            for day in range(1, current_day + 1):
                day_key = f"day_{day}"
                if day_key in st.session_state.farm_data['daily_data']:
                    day_data = st.session_state.farm_data['daily_data'][day_key]
                    if house_name in day_data and 'deaths' in day_data[house_name]:
                        total_deaths += day_data[house_name]['deaths']
        
        if total_initial > 0:
            return (total_deaths / total_initial) * 100
        return 0
    except:
        return 0

def calculate_feed_days_remaining(current_day: int) -> Dict[str, float]:
    """Her kümes için siloda kaç günlük yem kaldığını hesapla"""
    result = {}
    
    try:
        day_data_key = f"day_{current_day}"
        banvit_day = str(current_day)
        
        if banvit_day not in st.session_state.banvit_data:
            return result
        
        daily_consumption_per_bird = st.session_state.banvit_data[banvit_day].get('yem_tüketimi', 150) / 1000  # gram to kg
        
        for house_name in st.session_state.farm_data['settings']['houses'].keys():
            live_birds = calculate_live_birds_per_house(house_name, current_day)
            daily_need = live_birds * daily_consumption_per_bird
            
            silo_remaining = 0
            if day_data_key in st.session_state.farm_data['daily_data']:
                day_data = st.session_state.farm_data['daily_data'][day_data_key]
                if house_name in day_data and 'silo_remaining' in day_data[house_name]:
                    silo_remaining = day_data[house_name]['silo_remaining']
            
            if daily_need > 0:
                days_remaining = silo_remaining / daily_need
            else:
                days_remaining = 0
            
            result[house_name] = days_remaining
    except Exception as e:
        st.error(f"Yem gün hesabı hatası: {e}")
    
    return result

def calculate_water_preparation(current_day: int) -> Tuple[float, float]:
    """Sabah ve akşam su hazırlama miktarını hesapla (400-1000L arasında)"""
    try:
        banvit_day = str(current_day)
        if banvit_day not in st.session_state.banvit_data:
            return 400, 400
        
        daily_water_target = st.session_state.banvit_data[banvit_day].get('su_tüketimi', 100)
        total_live = calculate_total_live_birds(current_day)
        total_daily_water = (daily_water_target * total_live) / 1000  # ml to liters
        
        # Sabah ve akşam 50-50 bölüş
        morning_water = (total_daily_water * 0.5)
        evening_water = (total_daily_water * 0.5)
        
        # Min/Max sınırları uygula
        morning_water = max(400, min(1000, morning_water))
        evening_water = max(400, min(1000, evening_water))
        
        return morning_water, evening_water
    except:
        return 400, 400

def calculate_health_score(current_day: int) -> float:
    """Sağlık puanı hesapla (0-100)"""
    try:
        death_rate = calculate_death_rate(current_day)
        avg_weight = calculate_average_weight(current_day)
        
        # Ross hedef ağırlık
        banvit_day = str(current_day)
        if banvit_day in st.session_state.banvit_data:
            target_weight = st.session_state.banvit_data[banvit_day].get('ross_ağırlık', 1000)
        else:
            target_weight = 1000
        
        # Sapma oranı
        if target_weight > 0:
            weight_deviation = ((avg_weight - target_weight) / target_weight) * 100
        else:
            weight_deviation = 0
        
        # Su tüketimi sapması
        day_key = f"day_{current_day}"
        total_water = 0
        if day_key in st.session_state.farm_data['daily_data']:
            day_data = st.session_state.farm_data['daily_data'][day_key]
            for house_name in st.session_state.farm_data['settings']['houses'].keys():
                if house_name in day_data and 'water' in day_data[house_name]:
                    total_water += day_data[house_name]['water']
        
        banvit_day_str = str(current_day)
        if banvit_day_str in st.session_state.banvit_data:
            target_water = st.session_state.banvit_data[banvit_day_str].get('su_tüketimi', 100)
            total_live = calculate_total_live_birds(current_day)
            expected_water = (target_water * total_live) / 1000
            if expected_water > 0:
                water_deviation = ((total_water - expected_water) / expected_water) * 100
            else:
                water_deviation = 0
        else:
            water_deviation = 0
        
        # Sağlık puanı formülü
        death_score = 100 - (death_rate * 5)
        weight_score = 100 - (abs(weight_deviation) * 2)
        water_score = 100 if water_deviation > -10 else 70
        
        health_score = (death_score + weight_score + water_score) / 3
        return max(0, min(100, health_score))
    except Exception as e:
        st.error(f"Sağlık puanı hesabı hatası: {e}")
        return 0

# ============ PAGE NAVIGATION ============
def create_sidebar():
    """Sidebar navigasyon menüsü"""
    st.sidebar.title("📋 Murat Özkan Kümes İşletim Sistemi")
    st.sidebar.markdown("---")
    
    page = st.sidebar.radio(
        "Sayfayı Seç",
        [
            "🏠 Dashboard",
            "⚙️ Ayarlar",
            "📊 Günlük Veri Girişi",
            "🔬 Hesaplamalar",
            "💊 İlaç Programı",
            "🤖 AI Bilgi Bankası",
            "💉 İlaç Envanteri",
            "📈 Durum Analizi",
            "💬 Chat",
            "📉 Finansal Analiz"
        ]
    )
    
    return page

# ============ PAGES ============

def page_dashboard():
    """Dashboard - Ana Sayfa"""
    st.title("🏠 Dashboard - Çiftlik Özeti")
    
    current_day = get_current_day()
    
    # Üst bilgi
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Çiftlik Adı", st.session_state.farm_data['settings'].get('farm_name', 'N/A'))
    with col2:
        st.metric("Program Günü", f"{current_day}/42")
    with col3:
        st.metric("Başlangıç Tarihi", st.session_state.farm_data['settings'].get('start_date', 'N/A'))
    with col4:
        st.metric("Kesim Tarihi", st.session_state.farm_data['settings'].get('target_slaughter_date', 'N/A'))
    
    st.markdown("---")
    
    # KPI Kartları (12 Kart)
    col1, col2, col3, col4 = st.columns(4)
    
    total_live = calculate_total_live_birds(current_day)
    death_rate = calculate_death_rate(current_day)
    avg_weight = calculate_average_weight(current_day)
    health_score = calculate_health_score(current_day)
    fcr = calculate_fcr(current_day)
    
    with col1:
        st.metric("Toplam Canlı Hayvan", f"{total_live:,}")
    with col2:
        st.metric("Ölüm Oranı (%)", f"{death_rate:.2f}%")
    with col3:
        st.metric("Ort. Canlı Ağırlık (g)", f"{avg_weight:.0f}")
    with col4:
        st.metric("Sağlık Puanı", f"{health_score:.1f}/100")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # Kalan yem
    feed_days = calculate_feed_days_remaining(current_day)
    min_feed_days = min(feed_days.values()) if feed_days else 0
    
    with col1:
        st.metric("Çiftlik FCR", f"{fcr:.2f}")
    with col2:
        st.metric("Siloda Kaç Gün Yem", f"{min_feed_days:.1f} gün")
    with col3:
        morning_water, evening_water = calculate_water_preparation(current_day)
        st.metric("Günlük Su Tüketimi (L)", f"{morning_water + evening_water:.0f}")
    with col4:
        banvit_day = str(current_day)
        if banvit_day in st.session_state.banvit_data:
            target_weight = st.session_state.banvit_data[banvit_day].get('ross_ağırlık', 0)
            st.metric("Ross Hedef Ağırlık (g)", f"{target_weight}")
        else:
            st.metric("Ross Hedef Ağırlık (g)", "N/A")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if avg_weight > 0 and target_weight > 0:
            deviation = ((avg_weight - target_weight) / target_weight) * 100
            st.metric("Sapma Oranı (%)", f"{deviation:.2f}%")
        else:
            st.metric("Sapma Oranı (%)", "N/A")
    with col2:
        st.metric("Sürü Yaşı (Gün)", f"{current_day}")
    with col3:
        pass
    with col4:
        pass
    
    st.markdown("---")
    
    # Kümes Özeti
    st.subheader("📦 Kümes Özeti")
    
    house_summary = []
    for house_name in st.session_state.farm_data['settings']['houses'].keys():
        live_birds = calculate_live_birds_per_house(house_name, current_day)
        
        # Ölüm sayısı
        deaths = 0
        day_key = f"day_{current_day}"
        if day_key in st.session_state.farm_data['daily_data']:
            day_data = st.session_state.farm_data['daily_data'][day_key]
            if house_name in day_data and 'deaths' in day_data[house_name]:
                deaths = day_data[house_name]['deaths']
        
        # Ağırlık
        weight = 0
        if day_key in st.session_state.farm_data['daily_data']:
            day_data = st.session_state.farm_data['daily_data'][day_key]
            if house_name in day_data and 'weight' in day_data[house_name]:
                weight = day_data[house_name]['weight']
        
        # Su tüketimi
        water = 0
        if day_key in st.session_state.farm_data['daily_data']:
            day_data = st.session_state.farm_data['daily_data'][day_key]
            if house_name in day_data and 'water' in day_data[house_name]:
                water = day_data[house_name]['water']
        
        # Silo kalan
        silo = 0
        if day_key in st.session_state.farm_data['daily_data']:
            day_data = st.session_state.farm_data['daily_data'][day_key]
            if house_name in day_data and 'silo_remaining' in day_data[house_name]:
                silo = day_data[house_name]['silo_remaining']
        
        days_feed = silo / (weight * live_birds / 1000) if weight > 0 and live_birds > 0 else 0
        
        house_summary.append({
            "Kümes": house_name,
            "Canlı Hayvan": f"{live_birds:,}",
            "Ölüm (Gün)": deaths,
            "Ort. Ağırlık (g)": f"{weight:.0f}",
            "Su (L)": f"{water:.1f}",
            "Silo (kg)": f"{silo:.1f}",
            "Silo Gün": f"{days_feed:.1f}"
        })
    
    df_houses = pd.DataFrame(house_summary)
    st.dataframe(df_houses, use_container_width=True)
    
    st.markdown("---")
    
    # Uyarı Sistemi
    st.subheader("⚠️ Önemli Uyarılar")
    
    warnings = []
    
    # Siloda yem bitme uyarısı
    if min_feed_days < 2:
        warnings.append(("🔴 KRİTİK", f"Siloda {min_feed_days:.1f} günlük yem kaldı! Acil sipariş ver!"))
    elif min_feed_days < 3:
        warnings.append(("🟡 UYARI", f"Siloda {min_feed_days:.1f} günlük yem kaldı. Yakında sipariş ver."))
    
    # Ölüm oranı uyarısı
    if death_rate > 2:
        warnings.append(("🔴 KRİTİK", f"Ölüm oranı %{death_rate:.2f} - Acil veteriner müdahalesi gerekli!"))
    elif death_rate > 1:
        warnings.append(("🟡 UYARI", f"Ölüm oranı %{death_rate:.2f} - Gözlemle ve tedavi et."))
    
    # FCR uyarısı
    banvit_day = str(current_day)
    if banvit_day in st.session_state.banvit_data:
        target_fcr = st.session_state.banvit_data[banvit_day].get('fcr', 2.0)
        if fcr > target_fcr + 0.1:
            warnings.append(("🔴 KRİTİK", f"FCR {fcr:.2f} - Hedef {target_fcr:.2f} - Yem kalitesini kontrol et!"))
        elif fcr > target_fcr + 0.05:
            warnings.append(("🟡 UYARI", f"FCR {fcr:.2f} - Hedef {target_fcr:.2f} - Gözlemle."))
    
    # Su tüketimi uyarısı
    total_water = 0
    day_key = f"day_{current_day}"
    if day_key in st.session_state.farm_data['daily_data']:
        day_data = st.session_state.farm_data['daily_data'][day_key]
        for house_name in st.session_state.farm_data['settings']['houses'].keys():
            if house_name in day_data and 'water' in day_data[house_name]:
                total_water += day_data[house_name]['water']
    
    if banvit_day in st.session_state.banvit_data:
        target_water = st.session_state.banvit_data[banvit_day].get('su_tüketimi', 100)
        expected_water = (target_water * total_live) / 1000
        if total_water < expected_water * 0.7:
            warnings.append(("🔴 KRİTİK", f"Su tüketimi çok düşük! Nipel basıncını kontrol et!"))
        elif total_water < expected_water * 0.9:
            warnings.append(("🟡 UYARI", f"Su tüketimi düşük. Nipel basıncını kontrol et."))
    
    if warnings:
        for level, message in warnings:
            if "KRİTİK" in level:
                st.markdown(f'<div class="alert-red">{level}: {message}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="alert-yellow">{level}: {message}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="alert-green">✅ Tüm parametreler normal!</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Grafikler
    st.subheader("📊 Trendler")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Ağırlık grafiği
        weight_data = []
        for day in range(1, current_day + 1):
            day_key = f"day_{day}"
            if day_key in st.session_state.farm_data['daily_data']:
                day_data = st.session_state.farm_data['daily_data'][day_key]
                total_weight = 0
                count = 0
                for house_name in st.session_state.farm_data['settings']['houses'].keys():
                    if house_name in day_data and 'weight' in day_data[house_name]:
                        total_weight += day_data[house_name]['weight']
                        count += 1
                if count > 0:
                    avg_w = total_weight / count
                    weight_data.append({"Gün": day, "Ağırlık (g)": avg_w})
            
            # Ross hedef
            if str(day) in st.session_state.banvit_data:
                target = st.session_state.banvit_data[str(day)].get('ross_ağırlık', 0)
                weight_data.append({"Gün": day, "Ross Hedef (g)": target})
        
        if weight_data:
            df_weight = pd.DataFrame(weight_data)
            fig_weight = px.line(df_weight, x="Gün", y=["Ağırlık (g)", "Ross Hedef (g)"], 
                                 title="Ağırlık Trendi vs Ross Hedef")
            st.plotly_chart(fig_weight, use_container_width=True)
    
    with col2:
        # FCR grafiği
        fcr_data = []
        for day in range(1, current_day + 1):
            fcr_day = calculate_fcr(day)
            fcr_data.append({"Gün": day, "FCR": fcr_day})
            
            if str(day) in st.session_state.banvit_data:
                target_fcr = st.session_state.banvit_data[str(day)].get('fcr', 0)
                fcr_data.append({"Gün": day, "FCR Hedef": target_fcr})
        
        if fcr_data:
            df_fcr = pd.DataFrame(fcr_data)
            fig_fcr = px.line(df_fcr, x="Gün", y=["FCR", "FCR Hedef"], 
                             title="FCR Trendi vs Hedef")
            st.plotly_chart(fig_fcr, use_container_width=True)

def page_settings():
    """Ayarlar Sayfası"""
    st.title("⚙️ Sistem Ayarları")
    
    with st.form("settings_form"):
        st.subheader("A. Sistem Konfigürasyonu")
        
        col1, col2 = st.columns(2)
        with col1:
            farm_name = st.text_input(
                "Çiftlik Adı",
                value=st.session_state.farm_data['settings'].get('farm_name', '')
            )
            start_date = st.date_input(
                "Başlangıç Tarihi",
                value=datetime.strptime(
                    st.session_state.farm_data['settings'].get('start_date', '2026-02-14'),
                    '%Y-%m-%d'
                ).date()
            )
        
        with col2:
            target_slaughter = st.date_input(
                "Tahmini Kesim Tarihi",
                value=datetime.strptime(
                    st.session_state.farm_data['settings'].get('target_slaughter_date', '2026-03-27'),
                    '%Y-%m-%d'
                ).date()
            )
            water_tank_capacity = st.number_input(
                "Su Deposu Kapasitesi (1000L)",
                value=st.session_state.farm_data['settings'].get('water_tank_capacity', 1000),
                min_value=500,
                max_value=5000
            )
        
        st.subheader("B. Kümes Konfigürasyonu")
        
        for i, (house_name, house_info) in enumerate(st.session_state.farm_data['settings']['houses'].items()):
            col1, col2 = st.columns(2)
            with col1:
                chick_count = st.number_input(
                    f"{house_name} - Civciv Sayısı",
                    value=int(house_info['chick_count']),
                    min_value=1000,
                    max_value=50000,
                    key=f"chick_{i}"
                )
            with col2:
                silo_capacity = st.number_input(
                    f"{house_name} - Silo Kapasitesi (Ton)",
                    value=float(house_info['silo_capacity']),
                    min_value=5.0,
                    max_value=100.0,
                    key=f"silo_{i}"
                )
            
            st.session_state.farm_data['settings']['houses'][house_name]['chick_count'] = chick_count
            st.session_state.farm_data['settings']['houses'][house_name]['silo_capacity'] = silo_capacity
        
        st.subheader("C. Yem Yönetimi")
        
        col1, col2 = st.columns(2)
        with col1:
            chick_to_grower = st.number_input(
                "Civciv → Büyütme Geçişi (Gün)",
                value=st.session_state.farm_data['settings']['feed_transition'].get('chick_to_grower', 14),
                min_value=1,
                max_value=42
            )
            min_feed_days = st.number_input(
                "Minimum Siloda Kalan Yem (Gün)",
                value=st.session_state.farm_data['settings'].get('min_feed_days', 2),
                min_value=1,
                max_value=10
            )
        
        with col2:
            grower_to_finisher = st.number_input(
                "Büyütme → Bitirme Geçişi (Gün)",
                value=st.session_state.farm_data['settings']['feed_transition'].get('grower_to_finisher', 28),
                min_value=1,
                max_value=42
            )
            order_lead_time = st.number_input(
                "Siparişi Verme Öncesi (Gün)",
                value=st.session_state.farm_data['settings'].get('order_lead_time', 1),
                min_value=0,
                max_value=7
            )
        
        st.subheader("D. Su Yönetimi")
        
        col1, col2 = st.columns(2)
        with col1:
            min_water = st.number_input(
                "Minimum Su Hazırlama (L)",
                value=400,
                min_value=100,
                max_value=1000
            )
            water_flush_period = st.number_input(
                "Su Hattı Flushing Periyodu (Gün)",
                value=3,
                min_value=1,
                max_value=30
            )
        
        with col2:
            max_water = st.number_input(
                "Maksimum Su Hazırlama (L)",
                value=1000,
                min_value=500,
                max_value=5000
            )
            pipe_drain_time = st.number_input(
                "Boru Hattı Tahliye Süresi (Dakika)",
                value=5,
                min_value=1,
                max_value=60
            )
        
        st.subheader("E. Sağlık Eşikleri")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.write("**Yaşa Bağlı Normal Ölüm Oranı (%)**")
            death_1_7 = st.number_input("Gün 1-7", value=1.0, min_value=0.1, max_value=5.0, step=0.1)
            death_8_14 = st.number_input("Gün 8-14", value=0.5, min_value=0.1, max_value=5.0, step=0.1)
            death_15_21 = st.number_input("Gün 15-21", value=0.5, min_value=0.1, max_value=5.0, step=0.1)
        
        with col2:
            st.write("**Devam (Gün 22-42)**")
            death_22_28 = st.number_input("Gün 22-28", value=0.5, min_value=0.1, max_value=5.0, step=0.1)
            death_29_35 = st.number_input("Gün 29-35", value=0.5, min_value=0.1, max_value=5.0, step=0.1)
            death_36_42 = st.number_input("Gün 36-42", value=0.5, min_value=0.1, max_value=5.0, step=0.1)
        
        with col3:
            st.write("**Uyarı Eşikleri**")
            death_red_threshold = st.number_input("Ölüm Kırmızı Eşiği (%)", value=2.0, min_value=0.5, max_value=10.0, step=0.1)
            death_yellow_threshold = st.number_input("Ölüm Sarı Eşiği (%)", value=1.0, min_value=0.5, max_value=10.0, step=0.1)
            water_red_threshold = st.number_input("Su Kırmızı Eşiği (%)", value=70.0, min_value=10.0, max_value=100.0, step=1.0)
        
        st.subheader("F. İlaç Arınma Süreleri (Kesim Öncesi)")
        
        col1, col2 = st.columns(2)
        with col1:
            neomisin_withdrawal = st.number_input("Neomisin (Gün)", value=5, min_value=0, max_value=14)
            tilosin_withdrawal = st.number_input("Tilosin (Gün)", value=7, min_value=0, max_value=14)
        
        with col2:
            doksisiklin_withdrawal = st.number_input("Doksisiklin (Gün)", value=5, min_value=0, max_value=14)
            kolistin_withdrawal = st.number_input("Kolistin (Gün)", value=2, min_value=0, max_value=14)
        
        # Update session state
        st.session_state.farm_data['settings']['farm_name'] = farm_name
        st.session_state.farm_data['settings']['start_date'] = start_date.strftime('%Y-%m-%d')
        st.session_state.farm_data['settings']['target_slaughter_date'] = target_slaughter.strftime('%Y-%m-%d')
        st.session_state.farm_data['settings']['water_tank_capacity'] = water_tank_capacity
        st.session_state.farm_data['settings']['feed_transition']['chick_to_grower'] = chick_to_grower
        st.session_state.farm_data['settings']['feed_transition']['grower_to_finisher'] = grower_to_finisher
        st.session_state.farm_data['settings']['min_feed_days'] = min_feed_days
        st.session_state.farm_data['settings']['order_lead_time'] = order_lead_time
        st.session_state.farm_data['settings']['withdrawal_periods'] = {
            'Neomisin': neomisin_withdrawal,
            'Tilosin': tilosin_withdrawal,
            'Doksisiklin': doksisiklin_withdrawal,
            'Kolistin': kolistin_withdrawal
        }
        st.session_state.farm_data['settings']['death_thresholds'] = {
            '1-7': death_1_7,
            '8-14': death_8_14,
            '15-21': death_15_21,
            '22-28': death_22_28,
            '29-35': death_29_35,
            '36-42': death_36_42
        }
        
        if st.form_submit_button("💾 Ayarları Kaydet", use_container_width=True):
            log_transaction(st.session_state.farm_data, "UPDATE_SETTINGS", {
                "farm_name": farm_name,
                "start_date": start_date.strftime('%Y-%m-%d'),
                "target_slaughter_date": target_slaughter.strftime('%Y-%m-%d')
            })
            if save_json(st.session_state.farm_data, DATA_FILE):
                st.success("✅ Ayarlar başarıyla kaydedildi!")
            else:
                st.error("❌ Ayarlar kaydedilemedi!")

def page_daily_data_entry():
    """Günlük Veri Girişi Sayfası"""
    st.title("📊 Günlük Veri Girişi")
    
    current_day = get_current_day()
    
    st.info(f"📅 Bugün: Gün {current_day}/42")
    
    day_key = f"day_{current_day}"
    
    # Initialize day data if not exists
    if day_key not in st.session_state.farm_data['daily_data']:
        st.session_state.farm_data['daily_data'][day_key] = {}
    
    day_data = st.session_state.farm_data['daily_data'][day_key]
    
    with st.form("daily_data_form"):
        st.subheader("A. Kümes Verileri")
        
        for house_name in st.session_state.farm_data['settings']['houses'].keys():
            st.write(f"**{house_name}**")
            
            col1, col2, col3, col4 = st.columns(4)
            
            # Initialize house data if not exists
            if house_name not in day_data:
                day_data[house_name] = {}
            
            with col1:
                deaths = st.number_input(
                    f"{house_name} - Ölüm Sayısı",
                    value=day_data[house_name].get('deaths', 0),
                    min_value=0,
                    max_value=50000,
                    key=f"deaths_{house_name}"
                )
                day_data[house_name]['deaths'] = deaths
            
            with col2:
                weight = st.number_input(
                    f"{house_name} - Ağırlık (g)",
                    value=day_data[house_name].get('weight', 0.0),
                    min_value=0.0,
                    max_value=10000.0,
                    step=0.1,
                    key=f"weight_{house_name}"
                )
                day_data[house_name]['weight'] = weight
            
            with col3:
                water = st.number_input(
                    f"{house_name} - Su Tüketimi (L)",
                    value=day_data[house_name].get('water', 0.0),
                    min_value=0.0,
                    max_value=100000.0,
                    step=0.1,
                    key=f"water_{house_name}"
                )
                day_data[house_name]['water'] = water
            
            with col4:
                silo = st.number_input(
                    f"{house_name} - Siloda Kalan (kg)",
                    value=day_data[house_name].get('silo_remaining', 0.0),
                    min_value=0.0,
                    max_value=100000.0,
                    step=0.1,
                    key=f"silo_{house_name}"
                )
                day_data[house_name]['silo_remaining'] = silo
        
        st.subheader("B. Fiziksel Ortam Verileri")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            max_temp = st.number_input(
                "Max Sıcaklık (°C)",
                value=day_data.get('max_temp', 0.0),
                min_value=-10.0,
                max_value=50.0,
                step=0.1
            )
            day_data['max_temp'] = max_temp
        
        with col2:
            min_temp = st.number_input(
                "Min Sıcaklık (°C)",
                value=day_data.get('min_temp', 0.0),
                min_value=-10.0,
                max_value=50.0,
                step=0.1
            )
            day_data['min_temp'] = min_temp
        
        with col3:
            humidity = st.number_input(
                "Nem (%)",
                value=day_data.get('humidity', 0.0),
                min_value=0.0,
                max_value=100.0,
                step=0.1
            )
            day_data['humidity'] = humidity
        
        with col4:
            ammonia = st.number_input(
                "Amonyak Seviyesi (ppm)",
                value=day_data.get('ammonia', 0.0),
                min_value=0.0,
                max_value=100.0,
                step=0.1
            )
            day_data['ammonia'] = ammonia
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            ventilation = st.selectbox(
                "Havalandırma Durumu",
                ["Normal", "Kötü", "Arızalı"],
                index=["Normal", "Kötü", "Arızalı"].index(day_data.get('ventilation', 'Normal'))
            )
            day_data['ventilation'] = ventilation
        
        with col2:
            power_cut = st.selectbox(
                "Elektrik Kesintisi",
                ["Yok", "Var"],
                index=["Yok", "Var"].index(day_data.get('power_cut', 'Yok'))
            )
            day_data['power_cut'] = power_cut
        
        with col3:
            if power_cut == "Var":
                power_cut_hours = st.number_input(
                    "Kesinti Süresi (Saat)",
                    value=day_data.get('power_cut_hours', 0),
                    min_value=0,
                    max_value=24
                )
                day_data['power_cut_hours'] = power_cut_hours
        
        st.subheader("C. Sürü Gözlem Notları")
        
        general_note = st.text_area(
            "Genel Durum Notu",
            value=day_data.get('general_note', ''),
            height=100
        )
        day_data['general_note'] = general_note
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            diarrhea = st.selectbox(
                "Dışkı Durumu",
                ["Normal", "İshal", "Kan"],
                index=["Normal", "İshal", "Kan"].index(day_data.get('diarrhea', 'Normal'))
            )
            day_data['diarrhea'] = diarrhea
        
        with col2:
            sneezing = st.selectbox(
                "Pıskırma",
                ["Yok", "Az", "Çok"],
                index=["Yok", "Az", "Çok"].index(day_data.get('sneezing', 'Yok'))
            )
            day_data['sneezing'] = sneezing
        
        with col3:
            lameness = st.selectbox(
                "Hareketlilik",
                ["Normal", "Azalmış", "Yok"],
                index=["Normal", "Azalmış", "Yok"].index(day_data.get('lameness', 'Normal'))
            )
            day_data['lameness'] = lameness
        
        if st.form_submit_button("💾 Günlük Verileri Kaydet", use_container_width=True):
            log_transaction(st.session_state.farm_data, "DAILY_DATA_ENTRY", {
                "day": current_day,
                "houses": len(st.session_state.farm_data['settings']['houses'])
            })
            if save_json(st.session_state.farm_data, DATA_FILE):
                st.success(f"✅ Gün {current_day} verileri başarıyla kaydedildi!")
                st.rerun()
            else:
                st.error("❌ Veriler kaydedilemedi!")

def page_calculations():
    """Hesaplamalar Sayfası"""
    st.title("🔬 Otomatik Hesaplamalar")
    
    current_day = get_current_day()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("A. Canlı Hayvan Hesaplamaları")
        
        total_live = calculate_total_live_birds(current_day)
        st.metric("Toplam Canlı Hayvan", f"{total_live:,}")
        
        for house_name in st.session_state.farm_data['settings']['houses'].keys():
            live = calculate_live_birds_per_house(house_name, current_day)
            st.metric(f"{house_name} - Canlı", f"{live:,}")
    
    with col2:
        st.subheader("B. Ölüm Hesaplamaları")
        
        death_rate = calculate_death_rate(current_day)
        st.metric("Ölüm Oranı (%)", f"{death_rate:.2f}%")
        
        # Toplam ölüm
        total_deaths = 0
        for day in range(1, current_day + 1):
            day_key = f"day_{day}"
            if day_key in st.session_state.farm_data['daily_data']:
                day_data = st.session_state.farm_data['daily_data'][day_key]
                for house_name in st.session_state.farm_data['settings']['houses'].keys():
                    if house_name in day_data and 'deaths' in day_data[house_name]:
                        total_deaths += day_data[house_name]['deaths']
        
        st.metric("Toplam Ölüm (Kümülatif)", f"{total_deaths:,}")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("C. Ağırlık Hesaplamaları")
        
        avg_weight = calculate_average_weight(current_day)
        st.metric("Çiftlik Ort. Ağırlık (g)", f"{avg_weight:.0f}")
        
        banvit_day = str(current_day)
        if banvit_day in st.session_state.banvit_data:
            target_weight = st.session_state.banvit_data[banvit_day].get('ross_ağırlık', 0)
            st.metric("Ross Hedef Ağırlık (g)", f"{target_weight}")
            
            if target_weight > 0:
                deviation = ((avg_weight - target_weight) / target_weight) * 100
                st.metric("Sapma Oranı (%)", f"{deviation:.2f}%")
    
    with col2:
        st.subheader("D. Su Hesaplamaları")
        
        morning_water, evening_water = calculate_water_preparation(current_day)
        st.metric("Sabah Su Hazırlama (L)", f"{morning_water:.0f}")
        st.metric("Akşam Su Hazırlama (L)", f"{evening_water:.0f}")
        st.metric("Toplam Günlük Su (L)", f"{morning_water + evening_water:.0f}")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("E. Yem Hesaplamaları")
        
        total_feed_received = 0
        for invoice in st.session_state.farm_data.get('feed_invoices', []):
            total_feed_received += invoice.get('quantity', 0)
        
        st.metric("Toplam Gelen Yem (kg)", f"{total_feed_received:,.0f}")
        
        total_silo = 0
        day_key = f"day_{current_day}"
        if day_key in st.session_state.farm_data['daily_data']:
            day_data = st.session_state.farm_data['daily_data'][day_key]
            for house_name in st.session_state.farm_data['settings']['houses'].keys():
                if house_name in day_data and 'silo_remaining' in day_data[house_name]:
                    total_silo += day_data[house_name]['silo_remaining']
        
        st.metric("Toplam Siloda Kalan (kg)", f"{total_silo:,.0f}")
        st.metric("Net Tüketilen Yem (kg)", f"{total_feed_received - total_silo:,.0f}")
    
    with col2:
        st.subheader("F. FCR Hesaplamaları")
        
        fcr = calculate_fcr(current_day)
        st.metric("Çiftlik FCR", f"{fcr:.2f}")
        
        if banvit_day in st.session_state.banvit_data:
            target_fcr = st.session_state.banvit_data[banvit_day].get('fcr', 0)
            st.metric("FCR Hedefi", f"{target_fcr:.2f}")
            st.metric("FCR Sapması", f"{fcr - target_fcr:.2f}")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("G. Silo Yönetimi")
        
        feed_days = calculate_feed_days_remaining(current_day)
        for house_name, days in feed_days.items():
            st.metric(f"{house_name} - Siloda Kaç Gün", f"{days:.1f} gün")
    
    with col2:
        st.subheader("H. Sağlık Puanı")
        
        health_score = calculate_health_score(current_day)
        st.metric("Genel Sağlık Puanı (0-100)", f"{health_score:.1f}")
        
        if health_score >= 90:
            st.success("✅ Mükemmel")
        elif health_score >= 70:
            st.info("ℹ️ İyi")
        elif health_score >= 50:
            st.warning("⚠️ Dikkat")
        else:
            st.error("❌ Kritik")

def page_drug_program():
    """İlaç Programı Sayfası"""
    st.title("💊 İlaç Programı (Gün 1-42)")
    
    current_day = get_current_day()
    
    st.info(f"📅 Bugün: Gün {current_day}/42")
    
    # Drug program data structure
    if 'drug_program' not in st.session_state.farm_data:
        st.session_state.farm_data['drug_program'] = {}
    
    drug_program = st.session_state.farm_data['drug_program']
    
    # Initialize all 42 days if not exists
    for day in range(1, 43):
        day_str = str(day)
        if day_str not in drug_program:
            drug_program[day_str] = {
                "sabah": "",
                "aksam": "",
                "dozaj_notu": "",
                "veteriner_notu": ""
            }
    
    with st.form("drug_program_form"):
        st.subheader(f"Gün {current_day} - İlaç Takvimi")
        
        day_str = str(current_day)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**SABAH (08:00-14:00)**")
            morning_drug = st.selectbox(
                "Sabah İlaçı",
                [
                    "",
                    "Neomisin Sülfat",
                    "Tilosin Tartrat",
                    "Doksisiklin",
                    "Kolistin",
                    "Wellpro",
                    "Segropass",
                    "Hepato",
                    "Avicid",
                    "Sodyum Bütirat",
                    "Vitamin C + Elektrolit",
                    "Nane Yağı",
                    "Probiyotik"
                ],
                index=0 if drug_program[day_str].get('sabah', '') == "" else [
                    "",
                    "Neomisin Sülfat",
                    "Tilosin Tartrat",
                    "Doksisiklin",
                    "Kolistin",
                    "Wellpro",
                    "Segropass",
                    "Hepato",
                    "Avicid",
                    "Sodyum Bütirat",
                    "Vitamin C + Elektrolit",
                    "Nane Yağı",
                    "Probiyotik"
                ].index(drug_program[day_str].get('sabah', '')),
                key=f"morning_drug_{current_day}"
            )
            drug_program[day_str]['sabah'] = morning_drug
            
            # Calculate dosage
            if morning_drug and morning_drug in st.session_state.farm_data['drug_inventory']:
                drug_info = st.session_state.farm_data['drug_inventory'][morning_drug]
                morning_water, _ = calculate_water_preparation(current_day)
                morning_dosage = (drug_info['dose'] / 1000) * morning_water / 6  # Per house
                st.metric("Sabah Dozajı (Kümes Başına)", f"{morning_dosage:.1f}g")
        
        with col2:
            st.write("**AKŞAM (16:00-22:00)**")
            evening_drug = st.selectbox(
                "Akşam İlaçı",
                [
                    "",
                    "Neomisin Sülfat",
                    "Tilosin Tartrat",
                    "Doksisiklin",
                    "Kolistin",
                    "Wellpro",
                    "Segropass",
                    "Hepato",
                    "Avicid",
                    "Sodyum Bütirat",
                    "Vitamin C + Elektrolit",
                    "Nane Yağı",
                    "Probiyotik"
                ],
                index=0 if drug_program[day_str].get('aksam', '') == "" else [
                    "",
                    "Neomisin Sülfat",
                    "Tilosin Tartrat",
                    "Doksisiklin",
                    "Kolistin",
                    "Wellpro",
                    "Segropass",
                    "Hepato",
                    "Avicid",
                    "Sodyum Bütirat",
                    "Vitamin C + Elektrolit",
                    "Nane Yağı",
                    "Probiyotik"
                ].index(drug_program[day_str].get('aksam', '')),
                key=f"evening_drug_{current_day}"
            )
            drug_program[day_str]['aksam'] = evening_drug
            
            # Calculate dosage
            if evening_drug and evening_drug in st.session_state.farm_data['drug_inventory']:
                drug_info = st.session_state.farm_data['drug_inventory'][evening_drug]
                _, evening_water = calculate_water_preparation(current_day)
                evening_dosage = (drug_info['dose'] / 1000) * evening_water / 6  # Per house
                st.metric("Akşam Dozajı (Kümes Başına)", f"{evening_dosage:.1f}g")
        
        st.subheader("Notlar")
        
        col1, col2 = st.columns(2)
        
        with col1:
            dosage_note = st.text_area(
                "Dozaj Notu",
                value=drug_program[day_str].get('dozaj_notu', ''),
                height=80,
                key=f"dosage_note_{current_day}"
            )
            drug_program[day_str]['dozaj_notu'] = dosage_note
        
        with col2:
            vet_note = st.text_area(
                "Veteriner Notu",
                value=drug_program[day_str].get('veteriner_notu', ''),
                height=80,
                key=f"vet_note_{current_day}"
            )
            drug_program[day_str]['veteriner_notu'] = vet_note
        
        if st.form_submit_button("💾 İlaç Programını Kaydet", use_container_width=True):
            log_transaction(st.session_state.farm_data, "DRUG_PROGRAM_UPDATE", {
                "day": current_day,
                "morning_drug": morning_drug,
                "evening_drug": evening_drug
            })
            if save_json(st.session_state.farm_data, DATA_FILE):
                st.success(f"✅ Gün {current_day} ilaç programı kaydedildi!")
            else:
                st.error("❌ Kaydedilemedi!")
    
    st.markdown("---")
    
    # Display all 42 days program
    st.subheader("📋 Tüm 42 Günlük Program Özeti")
    
    program_data = []
    for day in range(1, 43):
        day_str = str(day)
        program_data.append({
            "Gün": day,
            "Sabah İlaçı": drug_program[day_str].get('sabah', ''),
            "Akşam İlaçı": drug_program[day_str].get('aksam', '')
        })
    
    df_program = pd.DataFrame(program_data)
    st.dataframe(df_program, use_container_width=True)

def page_ai_knowledge_bank():
    """AI Bilgi Bankası Sayfası"""
    st.title("🤖 AI Bilgi Bankası")
    
    st.subheader("A. Dosya Arşivi")
    
    uploaded_file = st.file_uploader(
        "Dosya Yükle (FAL, Antibiyogram, Otopsi, vb.)",
        type=['pdf', 'jpg', 'png', 'xlsx', 'docx', 'txt']
    )
    
    file_type = st.selectbox(
        "Dosya Türü",
        ["FAL Raporu", "Antibiyogram", "Laboratuvar Sonuçları", "Otopsi Fotoğrafı", 
         "Dışkı Fotoğrafı", "Su Analizi", "Aşı Takvimi"]
    )
    
    file_notes = st.text_area("Dosya Notları", height=100)
    
    if st.button("📤 Dosyayı Yükle"):
        if uploaded_file is not None:
            file_info = {
                "filename": uploaded_file.name,
                "type": file_type,
                "uploaded_date": str(datetime.now()),
                "notes": file_notes,
                "size_kb": uploaded_file.size / 1024
            }
            
            if 'files' not in st.session_state.farm_data['ai_knowledge_base']:
                st.session_state.farm_data['ai_knowledge_base']['files'] = []
            
            st.session_state.farm_data['ai_knowledge_base']['files'].append(file_info)
            
            log_transaction(st.session_state.farm_data, "FILE_UPLOAD", {
                "filename": uploaded_file.name,
                "type": file_type
            })
            
            if save_json(st.session_state.farm_data, DATA_FILE):
                st.success(f"✅ {uploaded_file.name} başarıyla yüklendi!")
            else:
                st.error("❌ Dosya yüklenemedi!")
    
    st.markdown("---")
    
    st.subheader("B. Sürü Gözlem Notları (42 Gün)")
    
    current_day = get_current_day()
    
    day_str = str(current_day)
    
    if 'observations' not in st.session_state.farm_data['ai_knowledge_base']:
        st.session_state.farm_data['ai_knowledge_base']['observations'] = {}
    
    observations = st.session_state.farm_data['ai_knowledge_base']['observations']
    
    if day_str not in observations:
        observations[day_str] = {"status": "Normal", "note": ""}
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        status = st.selectbox(
            f"Gün {current_day} - Durum",
            ["Normal", "Dikkat", "Kritik"],
            index=["Normal", "Dikkat", "Kritik"].index(observations[day_str].get('status', 'Normal'))
        )
        observations[day_str]['status'] = status
    
    with col2:
        note = st.text_area(
            f"Gün {current_day} - Not",
            value=observations[day_str].get('note', ''),
            height=100
        )
        observations[day_str]['note'] = note
    
    if st.button("💾 Gözlem Notunu Kaydet"):
        log_transaction(st.session_state.farm_data, "OBSERVATION_UPDATE", {
            "day": current_day,
            "status": status
        })
        if save_json(st.session_state.farm_data, DATA_FILE):
            st.success(f"✅ Gün {current_day} notu kaydedildi!")
        else:
            st.error("❌ Kaydedilemedi!")
    
    st.markdown("---")
    
    st.subheader("C. Haftalık Dikkat Notları")
    
    if 'weekly_notes' not in st.session_state.farm_data['ai_knowledge_base']:
        st.session_state.farm_data['ai_knowledge_base']['weekly_notes'] = {}
    
    weekly_notes = st.session_state.farm_data['ai_knowledge_base']['weekly_notes']
    
    weeks = [
        ("Hafta 1", "1-7", "1"),
        ("Hafta 2", "8-14", "2"),
        ("Hafta 3", "15-21", "3"),
        ("Hafta 4", "22-28", "4"),
        ("Hafta 5", "29-35", "5"),
        ("Hafta 6", "36-42", "6")
    ]
    
    for week_name, day_range, week_num in weeks:
        if week_num not in weekly_notes:
            weekly_notes[week_num] = ""
        
        note = st.text_area(
            f"{week_name} ({day_range}) Notu",
            value=weekly_notes[week_num],
            height=80,
            key=f"week_{week_num}"
        )
        weekly_notes[week_num] = note
    
    if st.button("💾 Haftalık Notları Kaydet"):
        log_transaction(st.session_state.farm_data, "WEEKLY_NOTES_UPDATE", {
            "weeks": 6
        })
        if save_json(st.session_state.farm_data, DATA_FILE):
            st.success("✅ Haftalık notlar kaydedildi!")
        else:
            st.error("❌ Kaydedilemedi!")

def page_drug_inventory():
    """İlaç Envanteri Sayfası"""
    st.title("💉 İlaç Envanteri")
    
    st.subheader("A. 11 İlaç Prospektüs Bilgileri")
    
    drugs = st.session_state.farm_data['drug_inventory']
    
    drug_data = []
    for drug_name, drug_info in drugs.items():
        drug_data.append({
            "İlaç Adı": drug_name,
            "Dozu (g/1000L)": drug_info.get('dose', 0),
            "Arınma Süresi (Gün)": drug_info.get('withdrawal', 0),
            "Stok (g)": drug_info.get('stock', 0),
            "Maliyet (₺)": drug_info.get('cost', 0)
        })
    
    df_drugs = pd.DataFrame(drug_data)
    st.dataframe(df_drugs, use_container_width=True)
    
    st.markdown("---")
    
    st.subheader("B. Karıştırılabilirlik Matrisi")
    
    compatibility_matrix = st.session_state.farm_data.get('drug_compatibility_matrix', {})
    
    compat_data = []
    for drug1, compatible_drugs in compatibility_matrix.items():
        for drug2 in compatible_drugs:
            compat_data.append({
                "İlaç 1": drug1,
                "İlaç 2": drug2,
                "Uyumlu": "✅ Evet"
            })
    
    if compat_data:
        df_compat = pd.DataFrame(compat_data)
        st.dataframe(df_compat, use_container_width=True)
    else:
        st.info("Henüz karıştırılabilirlik matrisi tanımlanmamış.")

def page_status_analysis():
    """Durum Analizi Sayfası"""
    st.title("📈 Durum Analizi - AI Rapor")
    
    current_day = get_current_day()
    
    st.subheader("A. Sağlık Puanı (0-100)")
    
    health_score = calculate_health_score(current_day)
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Progress bar
        progress = health_score / 100
        st.progress(progress)
    
    with col2:
        if health_score >= 90:
            st.success(f"✅ {health_score:.1f}")
        elif health_score >= 70:
            st.info(f"ℹ️ {health_score:.1f}")
        elif health_score >= 50:
            st.warning(f"⚠️ {health_score:.1f}")
        else:
            st.error(f"❌ {health_score:.1f}")
    
    st.markdown("---")
    
    st.subheader("B. AI Teşhis")
    
    # Generate AI diagnosis
    death_rate = calculate_death_rate(current_day)
    avg_weight = calculate_average_weight(current_day)
    fcr = calculate_fcr(current_day)
    
    diagnosis = []
    
    # Ölüm oranı analizi
    if death_rate > 2:
        diagnosis.append(f"🔴 **Ölüm Oranı Kritik**: %{death_rate:.2f} - Acil veteriner müdahalesi gerekli!")
    elif death_rate > 1:
        diagnosis.append(f"🟡 **Ölüm Oranı Yüksek**: %{death_rate:.2f} - Enfeksiyon riski var, tedavi başla.")
    else:
        diagnosis.append(f"🟢 **Ölüm Oranı Normal**: %{death_rate:.2f}")
    
    # Ağırlık analizi
    banvit_day = str(current_day)
    if banvit_day in st.session_state.banvit_data:
        target_weight = st.session_state.banvit_data[banvit_day].get('ross_ağırlık', 0)
        if target_weight > 0:
            deviation = ((avg_weight - target_weight) / target_weight) * 100
            if deviation < -10:
                diagnosis.append(f"🔴 **Ağırlık Gerisinde**: %{deviation:.1f} - Yem kalitesi ve tüketimini kontrol et.")
            elif deviation < -5:
                diagnosis.append(f"🟡 **Ağırlık Biraz Gerisinde**: %{deviation:.1f} - Beslenmeyi optimize et.")
            else:
                diagnosis.append(f"🟢 **Ağırlık Normal**: %{deviation:.1f}")
    
    # FCR analizi
    if banvit_day in st.session_state.banvit_data:
        target_fcr = st.session_state.banvit_data[banvit_day].get('fcr', 0)
        if fcr > target_fcr + 0.1:
            diagnosis.append(f"🔴 **FCR Kötü**: {fcr:.2f} vs Hedef {target_fcr:.2f} - Yem dönüşümü düşük!")
        elif fcr > target_fcr + 0.05:
            diagnosis.append(f"🟡 **FCR Sapması**: {fcr:.2f} vs Hedef {target_fcr:.2f} - Gözlemle.")
        else:
            diagnosis.append(f"🟢 **FCR İyi**: {fcr:.2f}")
    
    for diag in diagnosis:
        st.write(diag)
    
    st.markdown("---")
    
    st.subheader("C. Kritik Görevler (Top 3)")
    
    tasks = []
    
    # Task 1: Feed ordering
    feed_days = calculate_feed_days_remaining(current_day)
    min_feed_days = min(feed_days.values()) if feed_days else 999
    if min_feed_days < 3:
        tasks.append(f"🔴 **Yem Sipariş Et**: Siloda {min_feed_days:.1f} günlük yem kaldı!")
    
    # Task 2: Health check
    if death_rate > 1:
        tasks.append(f"🔴 **Otopsi Yap**: Ölüm oranı %{death_rate:.2f} - Hastalık teşhisi gerekli!")
    
    # Task 3: Weight check
    if banvit_day in st.session_state.banvit_data:
        target_weight = st.session_state.banvit_data[banvit_day].get('ross_ağırlık', 0)
        if target_weight > 0:
            deviation = ((avg_weight - target_weight) / target_weight) * 100
            if deviation < -10:
                tasks.append(f"🔴 **Beslenmeyi Kontrol Et**: Ağırlık %{deviation:.1f} gerisinde!")
    
    for i, task in enumerate(tasks[:3], 1):
        st.write(f"{i}. {task}")

def page_chat():
    """Chat Sayfası"""
    st.title("💬 AI Asistan")
    
    # Initialize Gemini API
    try:
        api_key = os.getenv('GEMINI_API_KEY')
        if api_key:
            genai.configure(api_key=api_key)
    except Exception as e:
        st.error(f"Gemini API yapılandırma hatası: {e}")
    
    st.info("🤖 Çiftlik hakkında sorular sorun, AI asistan size yardımcı olacak.")
    
    # Chat history
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = st.session_state.farm_data.get('chat_history', [])
    
    # Display chat history
    for message in st.session_state.chat_history:
        if message['role'] == 'user':
            st.write(f"👤 **Siz**: {message['content']}")
        else:
            st.write(f"🤖 **AI**: {message['content']}")
    
    st.markdown("---")
    
    # User input
    user_input = st.text_area("Sorunuzu yazın:", height=100)
    
    if st.button("📤 Gönder"):
        if user_input.strip():
            # Prepare context
            current_day = get_current_day()
            total_live = calculate_total_live_birds(current_day)
            death_rate = calculate_death_rate(current_day)
            avg_weight = calculate_average_weight(current_day)
            fcr = calculate_fcr(current_day)
            health_score = calculate_health_score(current_day)
            
            context = f"""
            Çiftlik Durumu (Gün {current_day}/42):
            - Toplam Canlı Hayvan: {total_live:,}
            - Ölüm Oranı: %{death_rate:.2f}
            - Ort. Ağırlık: {avg_weight:.0f}g
            - FCR: {fcr:.2f}
            - Sağlık Puanı: {health_score:.1f}/100
            
            Soru: {user_input}
            """
            
            try:
                model = genai.GenerativeModel('gemini-2.5-flash')
                response = model.generate_content(context)
                ai_response = response.text
            except Exception as e:
                ai_response = f"Gemini API hatası: {str(e)}. Lütfen daha sonra tekrar deneyin."
            
            # Add to chat history
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            st.session_state.chat_history.append({"role": "assistant", "content": ai_response})
            
            # Save to farm data
            st.session_state.farm_data['chat_history'] = st.session_state.chat_history
            log_transaction(st.session_state.farm_data, "CHAT_MESSAGE", {
                "question": user_input[:100],
                "day": current_day
            })
            save_json(st.session_state.farm_data, DATA_FILE)
            
            st.rerun()

def page_financial_analysis():
    """Finansal Analiz Sayfası"""
    st.title("💰 Finansal Analiz")
    
    st.subheader("A. Yem Maliyeti")
    
    total_feed_received = 0
    for invoice in st.session_state.farm_data.get('feed_invoices', []):
        total_feed_received += invoice.get('quantity', 0)
    
    # Estimate cost based on feed type
    feed_costs = st.session_state.farm_data['settings'].get('feed_costs', {})
    
    st.metric("Toplam Gelen Yem (kg)", f"{total_feed_received:,.0f}")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        chick_cost = feed_costs.get('Civciv', 2.5) * total_feed_received * 0.3  # 30% chick feed
        st.metric("Civciv Yemi Maliyeti (₺)", f"{chick_cost:,.0f}")
    
    with col2:
        grower_cost = feed_costs.get('Büyütme', 2.0) * total_feed_received * 0.4  # 40% grower feed
        st.metric("Büyütme Yemi Maliyeti (₺)", f"{grower_cost:,.0f}")
    
    with col3:
        finisher_cost = feed_costs.get('Bitirme', 1.8) * total_feed_received * 0.3  # 30% finisher feed
        st.metric("Bitirme Yemi Maliyeti (₺)", f"{finisher_cost:,.0f}")
    
    st.markdown("---")
    
    st.subheader("B. İlaç Maliyeti")
    
    total_drug_cost = 0
    for drug_name, drug_info in st.session_state.farm_data['drug_inventory'].items():
        cost = drug_info.get('cost', 0) * (drug_info.get('stock', 0) / 1000)
        total_drug_cost += cost
    
    st.metric("Toplam İlaç Maliyeti (₺)", f"{total_drug_cost:,.0f}")
    
    st.markdown("---")
    
    st.subheader("C. Özet")
    
    total_expenses = chick_cost + grower_cost + finisher_cost + total_drug_cost
    st.metric("Tahmini Toplam Masraf (₺)", f"{total_expenses:,.0f}")

# ============ MAIN APP ============
def main():
    page = create_sidebar()
    
    if page == "🏠 Dashboard":
        page_dashboard()
    elif page == "⚙️ Ayarlar":
        page_settings()
    elif page == "📊 Günlük Veri Girişi":
        page_daily_data_entry()
    elif page == "🔬 Hesaplamalar":
        page_calculations()
    elif page == "💊 İlaç Programı":
        page_drug_program()
    elif page == "🤖 AI Bilgi Bankası":
        page_ai_knowledge_bank()
    elif page == "💉 İlaç Envanteri":
        page_drug_inventory()
    elif page == "📈 Durum Analizi":
        page_status_analysis()
    elif page == "💬 Chat":
        page_chat()
    elif page == "📉 Finansal Analiz":
        page_financial_analysis()

if __name__ == "__main__":
    main()
