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

    # Ensure essential keys exist in settings after loading
    if 'settings' not in st.session_state.farm_data:
        st.session_state.farm_data['settings'] = {}
    if 'houses' not in st.session_state.farm_data['settings']:
        st.session_state.farm_data['settings']['houses'] = {}
    if 'feed_transition' not in st.session_state.farm_data['settings']:
        st.session_state.farm_data['settings']['feed_transition'] = {
            'chick_to_grower': 14,
            'grower_to_finisher': 28
        }

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
            
        return result
    except:
        return result

def calculate_water_preparation(current_day: int) -> Tuple[float, float]:
    """Sabah ve akşam hazırlanması gereken su miktarını hesapla"""
    try:
        banvit_day = str(current_day)
        if banvit_day not in st.session_state.banvit_data:
            return 0, 0
        
        water_per_1000_birds = st.session_state.banvit_data[banvit_day].get('su_tüketimi', 300)
        total_live = calculate_total_live_birds(current_day)
        
        total_water = (total_live / 1000) * water_per_1000_birds
        
        # Sabah %60, Akşam %40
        return total_water * 0.6, total_water * 0.4
    except:
        return 0, 0

def get_drug_program_for_day(current_day: int) -> Dict:
    """Belirli bir gün için ilaç programını döndürür"""
    return st.session_state.drug_program.get(str(current_day), {})

# ============ PAGE RENDERING FUNCTIONS ============
def page_dashboard():
    current_day = get_current_day()
    total_live_birds = calculate_total_live_birds(current_day)
    avg_weight = calculate_average_weight(current_day)
    fcr = calculate_fcr(current_day)
    death_rate = calculate_death_rate(current_day)
    render_dashboard(
        st.session_state.farm_data,
        st.session_state.banvit_data,
        current_day,
        total_live_birds,
        avg_weight,
        fcr,
        death_rate
    )

def page_daily_entry():
    st.title("📊 Günlük Veri Girişi")
    current_day = get_current_day()
    st.subheader(f"Bugün: {current_day}. Gün")

    # Ensure daily_data for current day exists
    st.session_state.farm_data.setdefault('daily_data', {}).setdefault(f'day_{current_day}', {})

    for i in range(1, len(st.session_state.farm_data.get('settings', {}).get('houses', {})) + 1):
        house_name = f"Kümes {i}"
        house_settings = st.session_state.farm_data['settings']['houses'].get(house_name, {})
        
        # Ensure house_name exists in daily_data for current day
        st.session_state.farm_data['daily_data'][f'day_{current_day}'].setdefault(house_name, {})

        with st.expander(f"{house_name} Günlük Veri"):
            current_daily_data = st.session_state.farm_data['daily_data'][f'day_{current_day}'][house_name]

            with st.form(f"daily_data_form_{i}"):
                deaths = st.number_input(
                    f"{house_name} Ölüm Sayısı",
                    min_value=0,
                    value=current_daily_data.get('deaths', 0)
                )
                weight = st.number_input(
                    f"{house_name} Ortalama Canlı Ağırlık (gram)",
                    min_value=0.0,
                    value=current_daily_data.get('weight', 0.0)
                )
                water_consumption = st.number_input(
                    f"{house_name} Su Tüketimi (Litre)",
                    min_value=0.0,
                    value=current_daily_data.get('water_consumption', 0.0)
                )
                silo_remaining = st.number_input(
                    f"{house_name} Siloda Kalan Yem (kg)",
                    min_value=0.0,
                    value=current_daily_data.get('silo_remaining', 0.0)
                )

                if st.form_submit_button(f"{house_name} Verilerini Kaydet"):
                    st.session_state.farm_data['daily_data'][f'day_{current_day}'][house_name] = {
                        'deaths': deaths,
                        'weight': weight,
                        'water_consumption': water_consumption,
                        'silo_remaining': silo_remaining
                    }
                    save_json(st.session_state.farm_data, DATA_FILE)
                    log_transaction(st.session_state.farm_data, "Daily Data Entry", f"{house_name} için {current_day}. gün verileri kaydedildi.")
                    st.success(f"✅ {house_name} için {current_day}. gün verileri kaydedildi!")
                    st.rerun()

def page_drug_program():
    st.title("💊 İlaç Programı")

    current_day = get_current_day()
    st.subheader(f"Bugün: {current_day}. Gün")

    drug_info = get_drug_program_for_day(current_day)

    if drug_info:
        st.markdown("### Bugünün İlaç Programı")
        st.write(f"**Stratejik Odak**: {drug_info.get('Stratejik Odak', 'N/A')}")
        st.write(f"**Sabah İlacı**: {drug_info.get('Sabah İlacı', 'N/A')}")
        st.write(f"**Akşam İlacı**: {drug_info.get('Akşam İlacı', 'N/A')}")
        st.write(f"**Dozaj Notu**: {drug_info.get('Dozaj Notu', 'N/A')}")
        st.write(f"**Veteriner Notu**: {drug_info.get('Veteriner Notu', 'N/A')}")
    else:
        st.info("Bugün için belirlenmiş bir ilaç programı bulunmamaktadır.")

    st.markdown("---")
    st.markdown("### Tüm 42 Günlük Program Özeti")
    if st.session_state.drug_program:
        df_drug = pd.DataFrame.from_dict(st.session_state.drug_program, orient='index')
        df_drug.index.name = 'Gün'
        st.dataframe(df_drug, use_container_width=True)
    else:
        st.warning("İlaç programı verisi yüklenemedi.")

def page_feed_logistics():
    current_day = get_current_day()
    live_birds_per_house = {h: calculate_live_birds_per_house(h, current_day) for h in st.session_state.farm_data.get('settings', {}).get('houses', {}).keys()}
    render_feed_logistics_page(st.session_state.farm_data, st.session_state.banvit_data, current_day, live_birds_per_house)

def page_ai_assistant():
    render_chat_page(st.session_state.farm_data, st.session_state.banvit_data, st.session_state.drug_program, get_current_day())

def page_calculations():
    st.title("🧮 Hesaplamalar")

    current_day = get_current_day()
    st.subheader(f"Bugün: {current_day}. Gün")

    total_live_birds = calculate_total_live_birds(current_day)
    avg_weight = calculate_average_weight(current_day)
    fcr = calculate_fcr(current_day)
    death_rate = calculate_death_rate(current_day)
    feed_days_remaining = calculate_feed_days_remaining(current_day)
    water_sabah, water_aksam = calculate_water_preparation(current_day)

    st.metric("Toplam Canlı Hayvan", f"{total_live_birds:,}")
    st.metric("Ortalama Canlı Ağırlık (gram)", f"{avg_weight:.2f}")
    st.metric("FCR", f"{fcr:.2f}")
    st.metric("Ölüm Oranı (%)", f"{death_rate:.2f}%")

    st.subheader("Kümes Bazında Kalan Yem Günleri")
    if feed_days_remaining:
        for house, days in feed_days_remaining.items():
            st.write(f"**{house}**: {days:.1f} gün")
    else:
        st.info("Yem günleri hesaplanamadı veya kümes verisi eksik.")

    st.subheader("Su Hazırlama Önerisi (Sabah/Akşam)")
    st.write(f"Sabah: {water_sabah:.0f} Litre")
    st.write(f"Akşam: {water_aksam:.0f} Litre")

def page_ai_knowledge_base():
    st.title("🤖 AI Bilgi Bankası")
    st.write("Bu bölümde, yüklenen belgeler ve gözlemler yapay zeka tarafından analiz edilerek size özel bilgiler sunulacaktır.")
    # Placeholder for future functionality

def page_drug_inventory():
    st.title("💉 İlaç Envanteri")
    st.write("Bu bölümde, mevcut ilaç envanteri takip edilecek ve ilaçların karıştırılabilirlik durumları görüntülenecektir.")
    # Placeholder for future functionality

def page_status_analysis():
    st.title("📈 Durum Analizi")
    st.write("Bu bölümde, çiftliğin genel durumu yapay zeka tarafından analiz edilerek kritik görevler ve teşhisler sunulacaktır.")
    # Placeholder for future functionality

def page_financial_analysis():
    st.title("💰 Finansal Analiz")
    st.write("Bu bölümde, çiftliğin finansal performansı detaylı olarak analiz edilecektir.")
    # Placeholder for future functionality

def page_settings():
    st.title("⚙️ Ayarlar")

    st.subheader("Genel Ayarlar")
    with st.form("general_settings_form"):
        farm_name = st.text_input("Çiftlik Adı", value=st.session_state.farm_data.get('settings', {}).get('farm_name', 'Yeni Çiftlik'))
        start_date = st.date_input("Başlangıç Tarihi", value=datetime.strptime(st.session_state.farm_data.get('settings', {}).get('start_date', datetime.now().strftime('%Y-%m-%d')), '%Y-%m-%d').date())
        
        if st.form_submit_button("Genel Ayarları Kaydet"):
            st.session_state.farm_data.setdefault('settings', {})['farm_name'] = farm_name
            st.session_state.farm_data['settings']['start_date'] = start_date.strftime('%Y-%m-%d')
            save_json(st.session_state.farm_data, DATA_FILE)
            log_transaction(st.session_state.farm_data, "General Settings Update", "Genel ayarlar güncellendi.")
            st.success("Genel ayarlar kaydedildi!")
            st.rerun()

    st.subheader("Kümes Ayarları")
    num_houses = st.number_input("Kümes Sayısı", min_value=1, max_value=6, value=len(st.session_state.farm_data.get('settings', {}).get('houses', {})) or 1)

    # Ensure 'houses' key exists in settings
    if 'houses' not in st.session_state.farm_data['settings']:
        st.session_state.farm_data['settings']['houses'] = {}

    for i in range(num_houses):
        house_name = f"Kümes {i+1}"
        current_house_settings = st.session_state.farm_data['settings'].get('houses', {}).get(house_name, {})
        
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
                    log_transaction(st.session_state.farm_data, "House Settings Update", f"{house_name} ayarları güncellendi.")
                    st.success(f"✅ {house_name} ayarları kaydedildi!")
                    st.rerun()

    st.subheader("Yem Geçiş Ayarları")
    with st.form("feed_transition_settings_form"):
        chick_to_grower = st.number_input("Civciv Yeminden Büyütme Yemine Geçiş Günü", min_value=1, max_value=42, value=st.session_state.farm_data.get('settings', {}).get('feed_transition', {}).get('chick_to_grower', 14))
        grower_to_finisher = st.number_input("Büyütme Yeminden Bitirme Yemine Geçiş Günü", min_value=1, max_value=42, value=st.session_state.farm_data.get('settings', {}).get('grower_to_finisher', 28))
        
        if st.form_submit_button("Yem Geçiş Ayarlarını Kaydet"):
            st.session_state.farm_data.setdefault('settings', {})['feed_transition'] = {
                'chick_to_grower': chick_to_grower,
                'grower_to_finisher': grower_to_finisher
            }
            save_json(st.session_state.farm_data, DATA_FILE)
            log_transaction(st.session_state.farm_data, "Feed Transition Settings Update", "Yem geçiş ayarları güncellendi.")
            st.success("✅ Yem geçiş ayarları kaydedildi!")
            st.rerun()

    st.subheader("Diğer Ayarlar")
    with st.form("other_settings_form"):
        min_feed_days = st.number_input("Minimum Yem Kalma Günü (Sipariş Tetikleyici)", min_value=1, value=st.session_state.farm_data.get('settings', {}).get('min_feed_days', 2))
        feed_stale_days = st.number_input("Yem Bayatlama Eşiği (Gün)", min_value=1, value=st.session_state.farm_data.get('settings', {}).get('feed_stale_days', 7))

        if st.form_submit_button("Diğer Ayarları Kaydet"):
            st.session_state.farm_data.setdefault('settings', {})['min_feed_days'] = min_feed_days
            st.session_state.farm_data.setdefault('settings', {})['feed_stale_days'] = feed_stale_days
            save_json(st.session_state.farm_data, DATA_FILE)
            log_transaction(st.session_state.farm_data, "Other Settings Update", "Diğer ayarlar güncellendi.")
            st.success("✅ Diğer ayarlar kaydedildi!")
            st.rerun()

# ============ MAIN APP LOGIC ============
def main():
    st.sidebar.title("Murat Özkan Kümes IS")
    
    pages = {
        "🏠 Dashboard": page_dashboard,
        "📊 Günlük Veri Girişi": page_daily_entry,
        "💊 İlaç Programı": page_drug_program,
        "🚚 Yem Lojistiği": page_feed_logistics,
        "💬 AI Asistan": page_ai_assistant,
        "🧮 Hesaplamalar": page_calculations,
        "🤖 AI Bilgi Bankası": page_ai_knowledge_base,
        "💉 İlaç Envanteri": page_drug_inventory,
        "📈 Durum Analizi": page_status_analysis,
        "💰 Finansal Analiz": page_financial_analysis,
        "⚙️ Ayarlar": page_settings,
    }

    selection = st.sidebar.radio("Gezinme", list(pages.keys()))
    page = pages[selection]
    page()

if __name__ == "__main__":
    main()
