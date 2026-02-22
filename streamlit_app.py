import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import os
from datetime import datetime, timedelta
import google.generativeai as genai
from PIL import Image
import base64
import io

# --- CONFIGURATION ---
st.set_page_config(page_title="Murat Ozkan Kumes Takip Sistemi", layout="wide", initial_sidebar_state="expanded")

# --- CUSTOM CSS ---
st.markdown("""
<style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #1f4e79; color: white; }
    .stTextInput>div>div>input { background-color: #fff9e6; }
    .stNumberInput>div>div>input { background-color: #fff9e6; }
    .stSidebar { background-color: #f0f2f6; }
</style>
""", unsafe_allow_html=True)

# --- DATA PERSISTENCE ---
DATA_FILE = 'farm_data.json'
BANVIT_FILE = 'banvit_data.json'

def load_json(file_path):
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_json(data, file_path):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# Initialize data into session state
if 'data' not in st.session_state:
    st.session_state.data = load_json(DATA_FILE)
if 'banvit_data' not in st.session_state:
    st.session_state.banvit_data = load_json(BANVIT_FILE)

# Initialize data structure if empty
if not st.session_state.data or 'settings' not in st.session_state.data:
    st.session_state.data = {
        "settings": {
            "farm_name": "Cambel Ciftligi",
            "start_date": "2026-02-14",
            "target_slaughter_date": "2026-03-27",
            "houses": {
                f"Kümes {i}": {"chick_count": 10836 if i > 1 else 10248, "silo_capacity": 20.0} for i in range(1, 7)
            },
            "water_tank_capacity": 1000,
            "feed_transition": {"chick_to_grower": 14, "grower_to_finisher": 28},
            "feed_order_rules": [9, 18, 27, 36],
            "min_feed_days": 2,
            "order_lead_time": 1,
            "max_feed_limit": 165,
            "feed_stale_days": 7,
            "withdrawal_periods": {"Neomisin": 5, "Tilosin": 7, "Doksisiklin": 5, "Kolistin": 2}
        },
        "daily_data": {},
        "feed_invoices": [],
        "drug_inventory": {},
        "drug_program": {
            "6": {"sabah": "Neomisin Sülfat", "aksam": "Hepato + Vitamin C", "not": "Tedavi başlangıcı"},
            "7": {"sabah": "Neomisin Sülfat", "aksam": "Hepato + Vitamin C", "not": "Tedavi 2. gün"},
            "8": {"sabah": "Neomisin Sülfat", "aksam": "Hepato + Vitamin C", "not": "Tedavi 3. gün"},
            "9": {"sabah": "Neomisin Sülfat", "aksam": "Hepato + Vitamin C", "not": "Tedavi son gün"}
        },
        "ai_knowledge_base": {"files": [], "observations": {}, "weekly_notes": {}},
        "chat_history": []
    }
    save_json(st.session_state.data, DATA_FILE)

# --- CORE CALCULATIONS ---
def get_current_day():
    try:
        start_dt = datetime.strptime(st.session_state.data['settings']['start_date'], '%Y-%m-%d')
        day = (datetime.now() - start_dt).days + 1
        return max(1, min(42, day))
    except:
        return 1

def calculate_metrics():
    d = st.session_state.data
    current_day = get_current_day()
    total_initial = sum(h['chick_count'] for h in d['settings']['houses'].values() if h['chick_count'] > 0)
    
    total_deaths = 0
    latest_weights = {}
    
    sorted_days = sorted([int(k) for k in d['daily_data'].keys()])
    for day_int in sorted_days:
        day_str = str(day_int)
        day_info = d['daily_data'][day_str]
        total_deaths += sum(day_info.get('deaths', {}).values())
        for house, w in day_info.get('weight', {}).items():
            if w > 0: latest_weights[house] = w

    current_live = total_initial - total_deaths
    avg_weight = sum(latest_weights.values()) / len(latest_weights) if latest_weights else 0
    
    total_received = sum(inv['amount'] for inv in d['feed_invoices'])
    latest_day_str = str(sorted_days[-1]) if sorted_days else "0"
    total_silo_rem = sum(d['daily_data'].get(latest_day_str, {}).get('silo_remaining', {}).values())
    net_feed = total_received - total_silo_rem
    
    total_biomass_kg = (current_live * avg_weight) / 1000 if avg_weight > 0 else 0
    fcr = net_feed / total_biomass_kg if total_biomass_kg > 0 else 0
    
    return {
        "day": current_day,
        "initial": total_initial,
        "live": current_live,
        "deaths": total_deaths,
        "mortalite": (total_deaths / total_initial * 100) if total_initial > 0 else 0,
        "weight": avg_weight,
        "fcr": fcr,
        "silo": total_silo_rem,
        "net_feed": net_feed
    }

m = calculate_metrics()

# --- SIDEBAR NAVIGATION ---
st.sidebar.title("Murat Özkan Kümes")
st.sidebar.markdown(f"**Gün:** {m['day']} | **Canlı:** {m['live']}")

menu = st.sidebar.radio("Menü", [
    "📊 Dashboard", "⚙️ Ayarlar", "📝 Günlük Veriler", "🚚 Yem Takibi", 
    "🧮 FCR Hesaplamaları", "💊 İlaç Programı", "🏥 AI Bilgi Bankası", 
    "📋 İlaç Envanteri", "📈 Durum Analizi", "💬 Sohbet"
])

# --- PAGE: DASHBOARD ---
if menu == "📊 Dashboard":
    st.title("Dashboard")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Canlı Hayvan", f"{m['live']}")
    c2.metric("Mortalite (%)", f"{m['mortalite']:.2f}%")
    c3.metric("Ort. Ağırlık (g)", f"{m['weight']:.1f}g")
    c4.metric("Çiftlik FCR", f"{m['fcr']:.3f}")
    
    st.subheader("Kümes Özeti")
    house_data = []
    for h_name, h_info in st.session_state.data['settings']['houses'].items():
        if h_info['chick_count'] > 0:
            h_deaths = 0
            h_weight = 0
            for d_info in st.session_state.data['daily_data'].values():
                h_deaths += d_info.get('deaths', {}).get(h_name, 0)
                if d_info.get('weight', {}).get(h_name, 0) > 0:
                    h_weight = d_info['weight'][h_name]
            
            house_data.append({
                "Kümes": h_name,
                "Kapasite": h_info['chick_count'],
                "Ölüm": h_deaths,
                "Canlı": h_info['chick_count'] - h_deaths,
                "Ağırlık (g)": h_weight
            })
    st.table(pd.DataFrame(house_data))

# --- PAGE: AYARLAR ---
elif menu == "⚙️ Ayarlar":
    st.title("Sistem Ayarları")
    with st.form("settings"):
        st.session_state.data['settings']['farm_name'] = st.text_input("Çiftlik Adı", st.session_state.data['settings']['farm_name'])
        st.session_state.data['settings']['start_date'] = st.text_input("Başlangıç Tarihi (YYYY-MM-DD)", st.session_state.data['settings']['start_date'])
        
        st.subheader("Kümes Bilgileri")
        cols = st.columns(3)
        for i, (h_name, h_info) in enumerate(st.session_state.data['settings']['houses'].items()):
            with cols[i % 3]:
                h_info['chick_count'] = st.number_input(f"{h_name} Civciv", value=h_info['chick_count'])
                h_info['silo_capacity'] = st.number_input(f"{h_name} Silo (Ton)", value=h_info['silo_capacity'])
        
        if st.form_submit_button("Ayarları Güncelle"):
            save_json(st.session_state.data, DATA_FILE)
            st.success("Ayarlar kaydedildi!")
            st.rerun()

# --- PAGE: GÜNLÜK VERİLER ---
elif menu == "📝 Günlük Veriler":
    st.title("Günlük Veri Girişi")
    day_sel = st.number_input("Gün", 1, 42, m['day'])
    ds = str(day_sel)
    
    if ds not in st.session_state.data['daily_data']:
        st.session_state.data['daily_data'][ds] = {
            "deaths": {h: 0 for h in st.session_state.data['settings']['houses']},
            "weight": {h: 0 for h in st.session_state.data['settings']['houses']},
            "silo_remaining": {h: 0 for h in st.session_state.data['settings']['houses']},
            "water": {h: 0 for h in st.session_state.data['settings']['houses']}
        }
    
    with st.form("daily_form"):
        for h_name, h_info in st.session_state.data['settings']['houses'].items():
            if h_info['chick_count'] > 0:
                st.write(f"### {h_name}")
                c1, c2, c3, c4 = st.columns(4)
                st.session_state.data['daily_data'][ds]['deaths'][h_name] = c1.number_input(f"Ölüm", value=st.session_state.data['daily_data'][ds]['deaths'].get(h_name, 0), key=f"d_{ds}_{h_name}")
                st.session_state.data['daily_data'][ds]['weight'][h_name] = c2.number_input(f"Ağırlık (g)", value=st.session_state.data['daily_data'][ds]['weight'].get(h_name, 0), key=f"w_{ds}_{h_name}")
                st.session_state.data['daily_data'][ds]['silo_remaining'][h_name] = c3.number_input(f"Silo (kg)", value=st.session_state.data['daily_data'][ds]['silo_remaining'].get(h_name, 0), key=f"s_{ds}_{h_name}")
                st.session_state.data['daily_data'][ds]['water'][h_name] = c4.number_input(f"Su (L)", value=st.session_state.data['daily_data'][ds]['water'].get(h_name, 0), key=f"wa_{ds}_{h_name}")
        
        if st.form_submit_button("Verileri Kaydet"):
            save_json(st.session_state.data, DATA_FILE)
            st.success(f"Gün {day_sel} verileri kaydedildi!")
            st.rerun()

# --- PAGE: YEM TAKIBI ---
elif menu == "🚚 Yem Takibi":
    st.title("Yem Takibi ve Sipariş")
    with st.form("invoice"):
        st.subheader("Yeni Yem İrsaliyesi")
        c1, c2, c3 = st.columns(3)
        date = c1.date_input("Tarih")
        typ = c2.selectbox("Tip", ["Civciv", "Büyütme", "Bitirme"])
        amt = c3.number_input("Miktar (kg)", min_value=0)
        if st.form_submit_button("İrsaliye Ekle"):
            st.session_state.data['feed_invoices'].append({"date": str(date), "type": typ, "amount": amt})
            save_json(st.session_state.data, DATA_FILE)
            st.success("İrsaliye eklendi!")
            st.rerun()
    
    st.subheader("Sipariş Uyarıları")
    for h_name, h_info in st.session_state.data['settings']['houses'].items():
        if h_info['chick_count'] > 0:
            latest_day = str(max([int(k) for k in st.session_state.data['daily_data'].keys()] + [0]))
            rem = st.session_state.data['daily_data'].get(latest_day, {}).get('silo_remaining', {}).get(h_name, 0)
            target_feed = st.session_state.banvit_data.get(str(m['day']), {}).get('yem_tüketimi', 100)
            daily_need = (target_feed * h_info['chick_count']) / 1000
            days_left = rem / daily_need if daily_need > 0 else 10
            
            if days_left < 2:
                st.error(f"🚨 {h_name}: KRİTİK! {days_left:.1f} gün yem kaldı. Hemen sipariş ver!")
            elif days_left < 4:
                st.warning(f"⚠️ {h_name}: DİKKAT! {days_left:.1f} gün yem kaldı.")
            else:
                st.success(f"✅ {h_name}: Yeterli ({days_left:.1f} gün)")

# --- PAGE: SOHBET ---
elif menu == "💬 Sohbet":
    st.title("AI Asistan")
    for msg in st.session_state.data['chat_history']:
        with st.chat_message(msg['role']): st.write(msg['content'])
    
    if prompt := st.chat_input("Sorunuzu yazın..."):
        st.session_state.data['chat_history'].append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.write(prompt)
        
        # Simple Logic for AI response
        resp = f"Merhaba Yağız, mevcut durumunu analiz ettim. Gün: {m['day']}, FCR: {m['fcr']:.3f}. '{prompt}' talebinle ilgili yardımcı oluyorum."
        st.session_state.data['chat_history'].append({"role": "assistant", "content": resp})
        with st.chat_message("assistant"): st.write(resp)
        save_json(st.session_state.data, DATA_FILE)

# --- FALLBACK ---
else:
    st.title(menu)
    st.info("Bu sayfa güncelleniyor...")
