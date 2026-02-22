import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

# Import FCR calculations
from fcr_calculations import calculate_fcr, calculate_mortality_rate, calculate_feed_order_alert

# ============= PAGE CONFIG =============
st.set_page_config(
    page_title="Murat Özkan Kümes Takip Sistemi",
    page_icon="🐔",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============= DATA MANAGEMENT =============
@st.cache_resource
def load_farm_data():
    """Load or create farm data"""
    if os.path.exists('farm_data.json'):
        with open('farm_data.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        return {}

def save_farm_data(data):
    """Save farm data to JSON"""
    with open('farm_data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@st.cache_resource
def load_drug_program():
    """Load drug program"""
    if os.path.exists('drug_program.json'):
        with open('drug_program.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

# ============= INITIALIZE SESSION STATE =============
def init_session_state():
    if 'farm_data' not in st.session_state:
        st.session_state.farm_data = load_farm_data()
    
    if 'drug_program' not in st.session_state:
        st.session_state.drug_program = load_drug_program()
    
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []

init_session_state()

# ============= HELPER FUNCTIONS =============
def get_current_day():
    """Calculate current day based on start date"""
    farm_data = st.session_state.farm_data
    if not farm_data or 'settings' not in farm_data:
        return 1
    
    start_date = datetime.strptime(farm_data['settings']['start_date'], '%Y-%m-%d')
    current_date = datetime.now()
    days_passed = (current_date - start_date).days + 1
    return min(days_passed, 42)

def get_live_chicken_count(day, deaths_data):
    """Calculate live chicken count"""
    total_deaths = sum(deaths_data.values())
    initial_count = 42756
    return initial_count - total_deaths

# ============= PAGE: DASHBOARD =============
def page_dashboard():
    st.title("Dashboard")
    
    farm_data = st.session_state.farm_data
    if not farm_data or 'settings' not in farm_data:
        st.error("Çiftlik verisi yüklenmedi. Lütfen Ayarlar sayfasını kontrol edin.")
        return
    
    current_day = get_current_day()
    
    # KPI Cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Çiftlik Adı", farm_data['settings']['farm_name'])
    with col2:
        st.metric("Gün", current_day)
    with col3:
        st.metric("Başlangıç Tarihi", farm_data['settings']['start_date'])
    with col4:
        st.metric("Tahmini Kesim", "27.03.2026")
    
    st.markdown("---")
    
    # Kümes Özeti
    st.subheader("Kümes Özeti")
    
    if str(current_day) in farm_data.get('daily_data', {}):
        current_data = farm_data['daily_data'][str(current_day)]
        
        kumes_data = []
        for kumes_id in ["1", "2", "3", "4"]:
            deaths = current_data.get('deaths', {}).get(kumes_id, 0)
            weight = current_data.get('weight', {}).get(kumes_id, 0)
            capacity = farm_data['settings']['kumes'][kumes_id]['capacity']
            
            kumes_data.append({
                'Kümes': f'Kümes {kumes_id}',
                'Kapasite': capacity,
                'Ölüm': deaths,
                'Canlı': capacity - deaths,
                'Ağırlık (g)': weight
            })
        
        df = pd.DataFrame(kumes_data)
        st.dataframe(df, use_container_width=True)
    
    st.markdown("---")
    
    # Performance Metrics
    st.subheader("Performans Metrikleri")
    
    if str(current_day) in farm_data.get('daily_data', {}):
        current_data = farm_data['daily_data'][str(current_day)]
        
        # Total deaths
        total_deaths = sum(current_data.get('deaths', {}).values())
        mortality_rate = (total_deaths / 42756 * 100) if 42756 > 0 else 0
        
        # Average weight
        weights = [w for w in current_data.get('weight', {}).values() if w > 0]
        avg_weight = sum(weights) / len(weights) if weights else 0
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Toplam Canlı Hayvan", 42756 - total_deaths)
        with col2:
            st.metric("Mortalite Oranı (%)", f"{mortality_rate:.2f}%")
        with col3:
            st.metric("Ortalama Ağırlık (g)", f"{avg_weight:.0f}")

# ============= PAGE: AYARLAR =============
def page_ayarlar():
    st.title("Sistem Ayarları")
    
    farm_data = st.session_state.farm_data
    settings = farm_data.get('settings', {})
    
    st.subheader("Çiftlik Bilgileri")
    
    col1, col2 = st.columns(2)
    with col1:
        farm_name = st.text_input("Çiftlik Adı", value=settings.get('farm_name', 'Cambel Ciftligi'))
    with col2:
        start_date = st.date_input("Başlangıç Tarihi", value=datetime.strptime(settings.get('start_date', '2026-02-14'), '%Y-%m-%d'))
    
    st.subheader("Kümes Kapasiteleri")
    
    for kumes_id in ["1", "2", "3", "4"]:
        col1, col2 = st.columns(2)
        with col1:
            capacity = st.number_input(
                f"Kümes {kumes_id} Civciv Sayısı",
                value=settings.get('kumes', {}).get(kumes_id, {}).get('capacity', 10836),
                key=f"capacity_{kumes_id}"
            )
        with col2:
            silo_cap = st.number_input(
                f"Kümes {kumes_id} Silo Kapasitesi (Ton)",
                value=settings.get('kumes', {}).get(kumes_id, {}).get('silo_capacity', 5.0),
                key=f"silo_{kumes_id}"
            )
    
    if st.button("Ayarları Kaydet", type="primary"):
        farm_data['settings']['farm_name'] = farm_name
        farm_data['settings']['start_date'] = start_date.strftime('%Y-%m-%d')
        
        for kumes_id in ["1", "2", "3", "4"]:
            farm_data['settings']['kumes'][kumes_id]['capacity'] = st.session_state[f"capacity_{kumes_id}"]
            farm_data['settings']['kumes'][kumes_id]['silo_capacity'] = st.session_state[f"silo_{kumes_id}"]
        
        save_farm_data(farm_data)
        st.success("Ayarlar kaydedildi!")

# ============= PAGE: GÜNLÜK VERİLER =============
def page_gunluk_veriler():
    st.title("Günlük Veri Girişi")
    
    farm_data = st.session_state.farm_data
    current_day = get_current_day()
    
    day = st.slider("Gün Seç", 1, 42, current_day)
    
    st.subheader(f"Gün {day} - Veri Girişi")
    
    if str(day) not in farm_data['daily_data']:
        farm_data['daily_data'][str(day)] = {
            "date": "",
            "deaths": {"1": 0, "2": 0, "3": 0, "4": 0},
            "weight": {"1": 0, "2": 0, "3": 0, "4": 0},
            "water_consumption": {"1": 0, "2": 0, "3": 0, "4": 0},
            "feed_consumption": {"1": 0, "2": 0, "3": 0, "4": 0},
            "silo_remaining": {"1": 0, "2": 0, "3": 0, "4": 0},
            "notes": ""
        }
    
    day_data = farm_data['daily_data'][str(day)]
    
    # Date input
    date_input = st.date_input("Tarih", value=datetime.now())
    day_data['date'] = date_input.strftime('%Y-%m-%d')
    
    # Deaths and Weight
    st.subheader("Ölüm ve Ağırlık Verileri")
    
    col1, col2, col3, col4 = st.columns(4)
    
    for idx, kumes_id in enumerate(["1", "2", "3", "4"]):
        with [col1, col2, col3, col4][idx]:
            st.write(f"**Kümes {kumes_id}**")
            
            deaths = st.number_input(
                f"K{kumes_id} Ölüm",
                value=int(day_data['deaths'].get(kumes_id, 0)),
                min_value=0,
                key=f"deaths_{day}_{kumes_id}"
            )
            day_data['deaths'][kumes_id] = int(deaths)
            
            weight = st.number_input(
                f"K{kumes_id} Ağırlık (g)",
                value=int(day_data['weight'].get(kumes_id, 0)),
                min_value=0,
                step=1,
                key=f"weight_{day}_{kumes_id}"
            )
            day_data['weight'][kumes_id] = int(weight)
    
    # Water and Feed
    st.subheader("Su ve Yem Verileri")
    
    col1, col2, col3, col4 = st.columns(4)
    
    for idx, kumes_id in enumerate(["1", "2", "3", "4"]):
        with [col1, col2, col3, col4][idx]:
            water = st.number_input(
                f"K{kumes_id} Su (L)",
                value=float(day_data['water_consumption'].get(kumes_id, 0)),
                min_value=0.0,
                key=f"water_{day}_{kumes_id}"
            )
            day_data['water_consumption'][kumes_id] = float(water)
            
            feed = st.number_input(
                f"K{kumes_id} Yem (kg)",
                value=float(day_data['feed_consumption'].get(kumes_id, 0)),
                min_value=0.0,
                step=0.1,
                key=f"feed_{day}_{kumes_id}"
            )
            day_data['feed_consumption'][kumes_id] = float(feed)
            
            silo = st.number_input(
                f"K{kumes_id} Silo Kalan (kg)",
                value=float(day_data['silo_remaining'].get(kumes_id, 0)),
                min_value=0.0,
                step=10.0,
                key=f"silo_{day}_{kumes_id}"
            )
            day_data['silo_remaining'][kumes_id] = float(silo)
    
    # Notes
    st.subheader("Notlar")
    notes = st.text_area("Gün Notları", value=day_data.get('notes', ''), height=100)
    day_data['notes'] = notes
    
    # Save button
    if st.button("Günlük Verileri Kaydet", type="primary"):
        save_farm_data(farm_data)
        st.success(f"Gün {day} verileri kaydedildi!")
        st.rerun()

# ============= PAGE: YEM TAKIBI =============
def page_yem_takibi():
    st.title("Yem Takibi ve Siparişi")
    
    farm_data = st.session_state.farm_data
    
    st.subheader("Yem Geliş Kayıtları")
    
    # Add new feed delivery
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        delivery_date = st.date_input("Teslimat Tarihi", value=datetime.now(), key="feed_date")
    with col2:
        feed_type = st.selectbox("Yem Türü", ["Starter", "Grower", "Finisher"], key="feed_type")
    with col3:
        quantity = st.number_input("Miktar (kg)", min_value=0, step=100, key="feed_qty")
    with col4:
        supplier = st.text_input("Tedarikçi", value="", key="feed_supplier")
    
    if st.button("Yem Geliş Kaydet", type="primary"):
        farm_data['feed_deliveries'].append({
            'date': delivery_date.strftime('%Y-%m-%d'),
            'type': feed_type,
            'quantity': quantity,
            'supplier': supplier
        })
        save_farm_data(farm_data)
        st.success("Yem geliş kaydedildi!")
    
    # Display feed deliveries
    if farm_data.get('feed_deliveries'):
        st.subheader("Geçmiş Yem Geliş Kayıtları")
        df = pd.DataFrame(farm_data['feed_deliveries'])
        st.dataframe(df, use_container_width=True)
    
    st.markdown("---")
    
    # Feed order alerts
    st.subheader("Yem Siparişi Uyarıları")
    
    current_day = get_current_day()
    if str(current_day) in farm_data.get('daily_data', {}):
        current_data = farm_data['daily_data'][str(current_day)]
        silo_status = farm_data.get('silo_status', {})
        
        # Calculate daily consumption
        daily_consumption = {}
        for kumes_id in ["1", "2", "3", "4"]:
            daily_consumption[kumes_id] = current_data.get('feed_consumption', {}).get(kumes_id, 0)
        
        # Get alerts
        alerts = calculate_feed_order_alert(silo_status, daily_consumption, 42 - current_day)
        
        for kumes_id in ["1", "2", "3", "4"]:
            alert = alerts[kumes_id]
            
            if alert['status'] == 'UYARI':
                st.warning(f"🚨 {alert['message']}")
                st.info(f"Mevcut Silo: {alert['current_silo']} kg | 3 Günlük İhtiyaç: {alert['three_day_need']:.0f} kg")
            else:
                st.success(f"✓ {alert['message']}")

# ============= PAGE: FCR HESAPLAMALARI =============
def page_fcr_hesaplamalari():
    st.title("FCR Hesaplamaları ve Performans")
    
    farm_data = st.session_state.farm_data
    current_day = get_current_day()
    
    day = st.slider("Gün Seç", 1, 42, current_day, key="fcr_day")
    
    if str(day) in farm_data.get('daily_data', {}):
        day_data = farm_data['daily_data'][str(day)]
        
        # Calculate FCR
        fcr_results = calculate_fcr(day_data, farm_data['settings'])
        
        st.subheader(f"Gün {day} - FCR Analizi")
        
        fcr_data = []
        for kumes_id in ["1", "2", "3", "4"]:
            result = fcr_results[kumes_id]
            fcr_data.append({
                'Kümes': f'Kümes {kumes_id}',
                'Tüketilen Yem (kg)': result['consumed_feed'],
                'Canlı Ağırlık (kg)': result['live_weight'] / 1000,
                'FCR': result['fcr']
            })
        
        df = pd.DataFrame(fcr_data)
        st.dataframe(df, use_container_width=True)
        
        # Calculate mortality
        st.subheader("Mortalite Analizi")
        
        mortality_results = calculate_mortality_rate(day_data, farm_data['settings'])
        
        mortality_data = []
        for kumes_id in ["1", "2", "3", "4"]:
            result = mortality_results[kumes_id]
            mortality_data.append({
                'Kümes': f'Kümes {kumes_id}',
                'Ölüm Sayısı': result['deaths'],
                'Kapasite': result['capacity'],
                'Mortalite (%)': result['mortality_rate']
            })
        
        df_mortality = pd.DataFrame(mortality_data)
        st.dataframe(df_mortality, use_container_width=True)
    else:
        st.info(f"Gün {day} için veri girilmemiş.")

# ============= PAGE: İLAÇ PROGRAMI =============
def page_ilac_programi():
    st.title("İlaç Programı")
    
    drug_program = st.session_state.drug_program
    current_day = get_current_day()
    
    day = st.slider("Gün Seç", 6, 42, current_day, key="drug_day")
    
    if str(day) in drug_program:
        program = drug_program[str(day)]
        
        st.header(f"Gün {day} - {program.get('tarih', '')}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("SABAH (08:00-14:00)")
            st.success(program.get('sabah', 'Bilgi yok'))
        
        with col2:
            st.subheader("AKŞAM (16:00-22:00)")
            st.info(program.get('aksam', 'Bilgi yok'))
        
        st.markdown("---")
        st.subheader("Veteriner Hekim Notu")
        st.warning(program.get('not', 'Not yok'))
    else:
        st.error(f"Gün {day} için program bilgisi bulunamadi. Program 6-42. gunler arasinda gecerlidir.")

# ============= PAGE: SOHBET =============
def page_sohbet():
    st.title("AI Asistan Sohbeti")
    
    st.info("AI Asistan ile canli sohbet")
    
    # Display chat history
    for msg in st.session_state.chat_history:
        if msg['role'] == 'user':
            st.markdown(f"**Siz:** {msg['content']}")
        else:
            st.markdown(f"**AI:** {msg['content']}")
    
    st.markdown("---")
    
    # Input
    user_input = st.text_input("Mesajiniz:", key="chat_input")
    
    if st.button("Gonder"):
        if user_input:
            st.session_state.chat_history.append({'role': 'user', 'content': user_input})
            
            # Simulate AI response
            ai_response = f"Mesajiniz alindi: '{user_input}'. Size yardimci olmak icin buradayim."
            st.session_state.chat_history.append({'role': 'assistant', 'content': ai_response})
            
            st.rerun()

# ============= MAIN APP =============
def main():
    st.sidebar.title("Murat Özkan Kümes Takip Sistemi")
    
    sayfa = st.sidebar.radio(
        "Sayfalar",
        [
            "Dashboard",
            "Ayarlar",
            "Günlük Veriler",
            "Yem Takibi",
            "FCR Hesaplamaları",
            "İlaç Programı",
            "Sohbet"
        ]
    )
    
    if sayfa == "Dashboard":
        page_dashboard()
    elif sayfa == "Ayarlar":
        page_ayarlar()
    elif sayfa == "Günlük Veriler":
        page_gunluk_veriler()
    elif sayfa == "Yem Takibi":
        page_yem_takibi()
    elif sayfa == "FCR Hesaplamaları":
        page_fcr_hesaplamalari()
    elif sayfa == "İlaç Programı":
        page_ilac_programi()
    elif sayfa == "Sohbet":
        page_sohbet()

if __name__ == "__main__":
    main()
