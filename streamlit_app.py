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

# Import modular components
from dashboard_analytics import render_dashboard
from enhanced_chat import render_chat_page
from feed_logistics import render_feed_logistics_page

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
DRUG_PROGRAM_FILE = 'complete_drug_program.json'

def initialize_data_file(file_path, default_data):
    """If a data file doesn't exist, create it with default data."""
    if not os.path.exists(file_path):
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(default_data, f, indent=2, ensure_ascii=False)
            return default_data
        except Exception as e:
            st.error(f"{file_path} oluşturulurken hata: {e}")
            st.stop()
    return None

def load_json(file_path):
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            st.error(f"{file_path} okunurken hata oluştu: {e}. Dosya bozuk veya bulunamıyor.")
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

# ============ INITIALIZATION & ERROR HANDLING ============
# Check for API Key first
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=GEMINI_API_KEY)
except (KeyError, Exception) as e:
    st.error("🔴 KRİTİK HATA: Gemini API anahtarı bulunamadı veya geçersiz. Lütfen Streamlit Cloud > Settings > Secrets bölümüne `GEMINI_API_KEY = '...'` olarak ekleyin.")
    st.stop()

# Initialize and load data files
if 'farm_data' not in st.session_state:
    initialize_data_file(DATA_FILE, {"settings": {"houses": {}}, "daily_data": {}})
    st.session_state.farm_data = load_json(DATA_FILE)
    if not st.session_state.farm_data:
        st.error("farm_data.json yüklenemedi veya boş. Uygulama başlatılamıyor.")
        st.stop()

if 'banvit_data' not in st.session_state:
    st.session_state.banvit_data = load_json(BANVIT_FILE)
    if not st.session_state.banvit_data:
        st.warning("banvit_data.json bulunamadı. Hedef değerler olmadan çalışılacak.")
        st.session_state.banvit_data = {}

if 'drug_program' not in st.session_state:
    st.session_state.drug_program = load_json(DRUG_PROGRAM_FILE)
    if not st.session_state.drug_program:
        st.warning("complete_drug_program.json bulunamadı. İlaç programı boş olacak.")
        st.session_state.drug_program = {}

# ============ CORE CALCULATIONS ============
def get_current_day():
    try:
        start_date_str = st.session_state.farm_data.get('settings', {}).get('start_date')
        if not start_date_str:
            return 1
        start_dt = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        day = (datetime.now().date() - start_dt).days + 1
        return max(1, min(42, day))
    except (ValueError, TypeError):
        return 1

def calculate_live_birds_per_house(house_name: str, current_day: int) -> int:
    try:
        initial = st.session_state.farm_data['settings']['houses'][house_name]['chick_count']
        deaths = sum(
            st.session_state.farm_data.get('daily_data', {}).get(f'day_{day}', {}).get(house_name, {}).get('deaths', 0)
            for day in range(1, current_day + 1)
        )
        return max(0, initial - deaths)
    except (KeyError, TypeError):
        return 0

def calculate_total_live_birds(current_day: int) -> int:
    try:
        return sum(calculate_live_birds_per_house(h, current_day) for h in st.session_state.farm_data.get('settings', {}).get('houses', {}).keys())
    except (KeyError, TypeError):
        return 0

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
                if house_name in day_data and 'water_consumption' in day_data[house_name]:
                    total_water += day_data[house_name]['water_consumption']
        
        target_water_consumption = st.session_state.banvit_data[banvit_day].get('su_tüketimi', 100) * calculate_total_live_birds(current_day) / 1000
        water_deviation = 0
        if target_water_consumption > 0:
            water_deviation = ((total_water - target_water_consumption) / target_water_consumption) * 100

        # FCR sapması
        fcr = calculate_fcr(current_day)
        target_fcr = st.session_state.banvit_data[banvit_day].get('fcr', 1.5)
        fcr_deviation = 0
        if target_fcr > 0:
            fcr_deviation = ((fcr - target_fcr) / target_fcr) * 100

        score = 100
        # Ölüm oranı
        if death_rate > 2:
            score -= 30
        elif death_rate > 1:
            score -= 15
        
        # Ağırlık sapması
        if weight_deviation < -10:
            score -= 25
        elif weight_deviation < -5:
            score -= 10
        
        # FCR sapması
        if fcr_deviation > 10:
            score -= 20
        elif fcr_deviation > 5:
            score -= 10

        # Su tüketimi sapması
        if water_deviation < -15 or water_deviation > 15:
            score -= 10
        
        return max(0, score)
    except Exception as e:
        st.error(f"Sağlık puanı hesaplama hatası: {e}")
        return 50 # Default health score in case of error

# ============ PAGE RENDERING FUNCTIONS ============
def page_dashboard():
    """Ana Dashboard Sayfası"""
    current_day = get_current_day()
    render_dashboard(st.session_state.farm_data, st.session_state.banvit_data, current_day)

def page_settings():
    st.title("⚙️ Çiftlik Ayarları")

    st.subheader("Genel Ayarlar")
    with st.form("general_settings_form"):
        farm_name = st.text_input("Çiftlik Adı", st.session_state.farm_data.get('settings', {}).get('farm_name', 'Yeni Çiftlik'))
        start_date = st.date_input("Dönem Başlangıç Tarihi", value=datetime.strptime(st.session_state.farm_data.get('settings', {}).get('start_date', str(datetime.now().date())), '%Y-%m-%d').date())
        target_slaughter_date = st.date_input("Hedef Kesim Tarihi", value=datetime.strptime(st.session_state.farm_data.get('settings', {}).get('target_slaughter_date', str((datetime.now() + timedelta(days=42)).date())), '%Y-%m-%d').date())
        
        if st.form_submit_button("Ayarları Kaydet"):
            st.session_state.farm_data['settings']['farm_name'] = farm_name
            st.session_state.farm_data['settings']['start_date'] = str(start_date)
            st.session_state.farm_data['settings']['target_slaughter_date'] = str(target_slaughter_date)
            save_json(st.session_state.farm_data, DATA_FILE)
            st.success("Genel ayarlar kaydedildi!")
            st.rerun()

    st.subheader("Kümes Ayarları")
    num_houses = st.number_input("Kümes Sayısı", min_value=1, max_value=6, value=len(st.session_state.farm_data.get('settings', {}).get('houses', {})) or 1)

    if 'houses' not in st.session_state.farm_data['settings']:
        st.session_state.farm_data['settings']['houses'] = {}

    for i in range(num_houses):
        house_name = f"Kümes {i+1}"
        current_house_settings = st.session_state.farm_data['settings']['houses'].get(house_name, {})
        
        with st.expander(f"{house_name} Ayarları"):
            with st.form(f"house_settings_form_{i}"):
                chick_count = st.number_input(f"{house_name} Başlangıç Hayvan Sayısı", min_value=0, value=current_house_settings.get('chick_count', 10000))
                silo_capacity = st.number_input(f"{house_name} Silo Kapasitesi (ton)", min_value=0.0, value=current_house_settings.get('silo_capacity', 20.0))
                
                if st.form_submit_button(f"{house_name} Ayarlarını Kaydet"):
                    st.session_state.farm_data['settings']['houses'][house_name] = {
                        'chick_count': chick_count,
                        'silo_capacity': silo_capacity
                    }
                    save_json(st.session_state.farm_data, DATA_FILE)
                    st.success(f"✅ {house_name} ayarları kaydedildi!")
                    st.rerun()

def page_daily_entry():
    st.title("📝 Günlük Veri Girişi")
    current_day = get_current_day()
    st.write(f"**Bugün: {current_day}. Gün**")

    if 'daily_data' not in st.session_state.farm_data:
        st.session_state.farm_data['daily_data'] = {}

    day_key = f"day_{current_day}"
    if day_key not in st.session_state.farm_data['daily_data']:
        st.session_state.farm_data['daily_data'][day_key] = {}

    for house_name in st.session_state.farm_data['settings']['houses'].keys():
        with st.expander(f"{house_name} Günlük Veri"):
            current_house_data = st.session_state.farm_data['daily_data'][day_key].get(house_name, {})
            with st.form(f"daily_entry_form_{house_name}"):
                deaths = st.number_input(f"{house_name} Ölüm Sayısı", min_value=0, value=current_house_data.get('deaths', 0))
                weight = st.number_input(f"{house_name} Ortalama Canlı Ağırlık (gram)", min_value=0.0, value=current_house_data.get('weight', 0.0))
                water_consumption = st.number_input(f"{house_name} Su Tüketimi (Litre)", min_value=0.0, value=current_house_data.get('water_consumption', 0.0))
                silo_remaining = st.number_input(f"{house_name} Siloda Kalan Yem (kg)", min_value=0.0, value=current_house_data.get('silo_remaining', 0.0))

                if st.form_submit_button(f"{house_name} Verilerini Kaydet"):
                    st.session_state.farm_data['daily_data'][day_key][house_name] = {
                        'deaths': deaths,
                        'weight': weight,
                        'water_consumption': water_consumption,
                        'silo_remaining': silo_remaining
                    }
                    log_transaction(st.session_state.farm_data, "DAILY_DATA_ENTRY", {"day": current_day, "house": house_name})
                    save_json(st.session_state.farm_data, DATA_FILE)
                    st.success(f"✅ {house_name} günlük verileri kaydedildi!")
                    st.rerun()

def page_drug_program():
    st.title("💊 İlaç Programı")
    current_day = get_current_day()
    st.write(f"**Bugün: {current_day}. Gün**")

    drug_program = st.session_state.drug_program.get('drug_program_complete', {})

    if not drug_program:
        st.warning("İlaç programı yüklenemedi veya boş. Lütfen `complete_drug_program.json` dosyasını kontrol edin.")
        return

    st.subheader("🗓️ Bugünün İlaç Programı")
    today_program = drug_program.get(str(current_day), {})
    if today_program:
        st.markdown(f"**Stratejik Odak**: {today_program.get('strategic_focus', 'N/A')}")
        st.markdown(f"**Sabah İlaçı**: {today_program.get('sabah', 'Yok')}")
        st.markdown(f"**Akşam İlaçı**: {today_program.get('aksam', 'Yok')}")
        st.markdown(f"**Dozaj Notu**: {today_program.get('dozaj_notu', 'N/A')}")
        st.markdown(f"**Veteriner Notu**: {today_program.get('veteriner_notu', 'N/A')}")
    else:
        st.info("Bugün için tanımlanmış bir ilaç programı bulunmamaktadır.")

    st.markdown("---")

    # Display all 42 days program
    st.subheader("📋 Tüm 42 Günlük Program Özeti")
    
    program_data = []
    for day in range(1, 43):
        day_str = str(day)
        program_day_data = drug_program.get(day_str, {})
        program_data.append({
            "Gün": day,
            "Yaş": program_day_data.get('age', ''),
            "Stratejik Odak": program_day_data.get('strategic_focus', ''),
            "Sabah İlaçı": program_day_data.get('sabah', ''),
            "Akşam İlaçı": program_day_data.get('aksam', ''),
            "Dozaj Notu": program_day_data.get('dozaj_notu', ''),
            "Veteriner Notu": program_day_data.get('veteriner_notu', '')
        })
    
    df_program = pd.DataFrame(program_data)
    st.dataframe(df_program, use_container_width=True)

def page_feed_logistics():
    """Yem Lojistiği Sayfası"""
    current_day = get_current_day()
    live_birds_per_house = {house_name: calculate_live_birds_per_house(house_name, current_day) for house_name in st.session_state.farm_data['settings']['houses'].keys()}
    render_feed_logistics_page(st.session_state.farm_data, st.session_state.banvit_data, current_day, live_birds_per_house)

def page_chat():
    """AI Asistan Sayfası"""
    current_day = get_current_day()
    total_live = calculate_total_live_birds(current_day)
    death_rate = calculate_death_rate(current_day)
    avg_weight = calculate_average_weight(current_day)
    fcr = calculate_fcr(current_day)
    health_score = calculate_health_score(current_day)

    calculations = {
        'total_live': total_live,
        'death_rate': death_rate,
        'avg_weight': avg_weight,
        'fcr': fcr,
        'health_score': health_score,
        'feed_days': calculate_feed_days_remaining(current_day),
        'morning_water': calculate_water_preparation(current_day)[0],
        'evening_water': calculate_water_preparation(current_day)[1]
    }
    render_chat_page(st.session_state.farm_data, st.session_state.banvit_data, current_day, calculations)

def page_calculations():
    st.title("🧮 Hesaplamalar")
    current_day = get_current_day()
    st.write(f"**Bugün: {current_day}. Gün**")

    st.subheader("Canlı Hayvan Sayısı")
    for house_name in st.session_state.farm_data['settings']['houses'].keys():
        live_birds = calculate_live_birds_per_house(house_name, current_day)
        st.write(f"- {house_name}: {live_birds:,} adet")
    st.write(f"**Toplam Canlı Hayvan**: {calculate_total_live_birds(current_day):,} adet")

    st.subheader("Ölüm Oranı")
    death_rate = calculate_death_rate(current_day)
    st.write(f"- Çiftlik Ölüm Oranı: %{death_rate:.2f}")

    st.subheader("Ortalama Ağırlık")
    avg_weight = calculate_average_weight(current_day)
    st.write(f"- Çiftlik Ortalama Ağırlık: {avg_weight:.0f} gram")

    st.subheader("FCR (Yem Dönüşüm Oranı)")
    fcr = calculate_fcr(current_day)
    st.write(f"- Çiftlik FCR: {fcr:.2f}")

    st.subheader("Sağlık Puanı")
    health_score = calculate_health_score(current_day)
    st.write(f"- Çiftlik Sağlık Puanı: {health_score:.1f}/100")

def page_ai_knowledge_base():
    st.title("🤖 AI Bilgi Bankası")
    st.info("Burada çiftliğe özel dokümanları yükleyebilir ve AI'ın analiz etmesini sağlayabilirsiniz.")
    st.warning("Bu özellik henüz geliştirme aşamasındadır.")

def page_drug_inventory():
    st.title("💉 İlaç Envanteri")
    st.info("Burada ilaç envanterinizi takip edebilir ve karıştırılabilirlik matrisini görüntüleyebilirsiniz.")
    st.warning("Bu özellik henüz geliştirme aşamasındadır.")

def page_status_analysis():
    st.title("📈 Durum Analizi")
    st.info("Burada AI tarafından yapılan detaylı durum analizlerini ve kritik görevleri görebilirsiniz.")
    st.warning("Bu özellik henüz geliştirme aşamasındadır.")

def page_financial_analysis():
    st.title("💰 Finansal Analiz")
    st.info("Burada çiftliğinizin finansal performansını takip edebilirsiniz.")
    st.warning("Bu özellik henüz geliştirme aşamasındadır.")

# ============ MAIN APP LOGIC ============
def main():
    st.sidebar.title("Murat Özkan Kümes IS")
    st.sidebar.markdown("--- ")
    
    # Check if settings are complete
    if not st.session_state.farm_data.get('settings', {}).get('farm_name') or not st.session_state.farm_data.get('settings', {}).get('houses'):
        st.warning("Lütfen önce Ayarlar sayfasından çiftlik ve kümes bilgilerinizi girin.")
        page_settings()
        return

    pages = {
        "📊 Dashboard": page_dashboard,
        "📝 Günlük Veri Girişi": page_daily_entry,
        "💊 İlaç Programı": page_drug_program,
        "🚛 Yem Lojistiği": page_feed_logistics,
        "💬 AI Asistan": page_chat,
        "🧮 Hesaplamalar": page_calculations,
        "🤖 AI Bilgi Bankası": page_ai_knowledge_base,
        "💉 İlaç Envanteri": page_drug_inventory,
        "📈 Durum Analizi": page_status_analysis,
        "💰 Finansal Analiz": page_financial_analysis,
        "⚙️ Ayarlar": page_settings,
    }

    selection = st.sidebar.radio("Sayfa Seçimi", list(pages.keys()))
    
    page = pages[selection]
    page()

if __name__ == "__main__":
    main()
