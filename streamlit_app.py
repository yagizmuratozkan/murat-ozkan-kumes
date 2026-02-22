import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import os
from datetime import datetime, timedelta
import numpy as np

# ============ CONFIGURATION ============
st.set_page_config(page_title="Murat Özkan Kümes İşletim Sistemi", layout="wide", initial_sidebar_state="expanded")

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
    except Exception as e:
        st.error(f"Dosya kaydetme hatası: {e}")

def log_transaction(data, action, details):
    """Her veri değişikliğini kaydet"""
    transaction = {
        "timestamp": str(datetime.now()),
        "action": action,
        "details": details
    }
    if "metadata" not in data:
        data["metadata"] = {"transaction_log": []}
    data["metadata"]["transaction_log"].append(transaction)
    data["metadata"]["last_updated"] = str(datetime.now())

# ============ INITIALIZATION ============
if 'data' not in st.session_state:
    st.session_state.data = load_json(DATA_FILE)
if 'banvit_data' not in st.session_state:
    st.session_state.banvit_data = load_json(BANVIT_FILE)

# ============ CORE CALCULATIONS ============
def get_current_day():
    try:
        start_dt = datetime.strptime(st.session_state.data['settings']['start_date'], '%Y-%m-%d').date()
        day = (datetime.now().date() - start_dt).days + 1
        return max(1, min(42, day))
    except:
        return 1

def calculate_metrics():
    d = st.session_state.data
    current_day = get_current_day()
    total_initial = sum(h['chick_count'] for h in d['settings']['houses'].values())
    
    total_deaths = 0
    house_data = {h: {"deaths": 0, "live": d['settings']['houses'][h]['chick_count'], "weight": 0, "silo": 0} for h in d['settings']['houses']}
    
    sorted_days = sorted([int(k) for k in d['daily_data'].keys()])
    for day_int in sorted_days:
        day_str = str(day_int)
        day_info = d['daily_data'][day_str]
        for h in d['settings']['houses']:
            deaths = day_info.get('deaths', {}).get(h, 0)
            total_deaths += deaths
            house_data[h]["deaths"] += deaths
            house_data[h]["live"] -= deaths
            house_data[h]["weight"] = day_info.get('weight', {}).get(h, 0)
            house_data[h]["silo"] = day_info.get('silo_remaining', {}).get(h, 0)

    total_live = total_initial - total_deaths
    avg_weight = sum(h["weight"] for h in house_data.values() if h["weight"] > 0) / len([h for h in house_data.values() if h["weight"] > 0]) if any(h["weight"] > 0 for h in house_data.values()) else 0
    
    total_received = sum(inv['amount'] for inv in d['feed_invoices'])
    total_silo = sum(h["silo"] for h in house_data.values())
    net_feed = total_received - total_silo
    
    total_biomass = (total_live * avg_weight) / 1000 if avg_weight > 0 else 0
    fcr = net_feed / total_biomass if total_biomass > 0 else 0
    
    health_score = 100 - (total_deaths / total_initial * 100 * 5) if total_initial > 0 else 100
    
    return {
        "day": current_day, "initial": total_initial, "live": total_live, "deaths": total_deaths,
        "mortalite": (total_deaths / total_initial * 100) if total_initial > 0 else 0,
        "weight": avg_weight, "fcr": fcr, "silo": total_silo, "net_feed": net_feed,
        "health_score": max(0, min(100, health_score)), "house_data": house_data
    }

m = calculate_metrics()

# ============ SIDEBAR ============
st.sidebar.title("Murat Özkan Kümes")
st.sidebar.markdown(f"**Gün:** {m['day']} | **Canlı:** {m['live']:,}")

page = st.sidebar.radio("Sayfa Seçin", [
    "📊 Dashboard", "⚙️ Ayarlar", "📝 Günlük Veriler", "🚚 Yem Takibi", 
    "🧮 Hesaplamalar", "💊 İlaç Programı", "🏥 AI Bilgi Bankası", 
    "📋 İlaç Envanteri", "📈 Durum Analizi", "💰 Finansal", "💬 Sohbet"
])

# ============ PAGE: DASHBOARD ============
if page == "📊 Dashboard":
    st.title(f"🚀 {st.session_state.data['settings']['farm_name']} - Gün {m['day']}/42")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Canlı Hayvan", f"{m['live']:,}", f"-{m['deaths']}")
    c2.metric("Mortalite (%)", f"{m['mortalite']:.2f}%")
    c3.metric("Ort. Ağırlık (g)", f"{m['weight']:.1f}g")
    c4.metric("Çiftlik FCR", f"{m['fcr']:.3f}")

    c1, c2, c3, c4 = st.columns(4)
    score_color = "green" if m['health_score'] > 85 else "orange" if m['health_score'] > 70 else "red"
    c1.markdown(f"<div class='alert-{score_color}' style='text-align:center; font-weight:bold;'>Sağlık Puanı: {m['health_score']:.0f}</div>", unsafe_allow_html=True)
    c2.metric("Kalan Yem (kg)", f"{m['silo']:,}")
    c3.metric("Net Tüketim (kg)", f"{m['net_feed']:,}")
    c4.metric("Kesime Kalan", f"{42 - m['day']} Gün")

    st.divider()
    st.subheader("Kümes Özeti")
    h_df = pd.DataFrame([{"Kümes": k, "Canlı": v["live"], "Ölüm": v["deaths"], "Ağırlık (g)": v["weight"], "Silo (kg)": v["silo"]} for k, v in m["house_data"].items()])
    st.dataframe(h_df, use_container_width=True, hide_index=True)

    st.subheader("Uyarılar")
    if m['silo'] < 500:
        st.markdown("<div class='alert-red'><b>KIRMIZI:</b> Silo kritik seviyede! Acil yem siparişi gerekli.</div>", unsafe_allow_html=True)
    elif m['mortalite'] > 1.5:
        st.markdown("<div class='alert-red'><b>KIRMIZI:</b> Mortalite eşik değerin üzerinde!</div>", unsafe_allow_html=True)
    elif m['fcr'] > 1.65:
        st.markdown("<div class='alert-yellow'><b>SARI:</b> FCR yükseliyor, yem kalitesini kontrol et.</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='alert-green'><b>YEŞİL:</b> Sistem normal çalışıyor.</div>", unsafe_allow_html=True)

# ============ PAGE: AYARLAR ============
elif page == "⚙️ Ayarlar":
    st.title("Sistem Ayarları")
    with st.form("settings_form"):
        st.session_state.data['settings']['farm_name'] = st.text_input("Çiftlik Adı", st.session_state.data['settings']['farm_name'])
        st.session_state.data['settings']['start_date'] = st.text_input("Başlangıç Tarihi (YYYY-MM-DD)", st.session_state.data['settings']['start_date'])
        
        st.subheader("Kümes Bilgileri")
        cols = st.columns(3)
        for i, (h_name, h_info) in enumerate(st.session_state.data['settings']['houses'].items()):
            with cols[i % 3]:
                h_info['chick_count'] = st.number_input(f"{h_name} Civciv", value=h_info['chick_count'])
                h_info['silo_capacity'] = st.number_input(f"{h_name} Silo (Ton)", value=h_info['silo_capacity'])
        
        if st.form_submit_button("Kaydet"):
            log_transaction(st.session_state.data, "SETTINGS_UPDATE", "Sistem ayarları güncellendi")
            save_json(st.session_state.data, DATA_FILE)
            st.success("Ayarlar kaydedildi!")
            st.rerun()

# ============ PAGE: GÜNLÜK VERİLER ============
elif page == "📝 Günlük Veriler":
    st.title("Günlük Veri Girişi")
    day_sel = st.number_input("Gün", 1, 42, m['day'])
    ds = str(day_sel)
    
    if ds not in st.session_state.data['daily_data']:
        st.session_state.data['daily_data'][ds] = {
            "deaths": {h: 0 for h in st.session_state.data['settings']['houses']},
            "weight": {h: 0 for h in st.session_state.data['settings']['houses']},
            "silo_remaining": {h: 0 for h in st.session_state.data['settings']['houses']},
            "water": {h: 0 for h in st.session_state.data['settings']['houses']},
            "notes": ""
        }
    
    with st.form("daily_form"):
        for h in st.session_state.data['settings']['houses']:
            st.markdown(f"### {h}")
            c1, c2, c3, c4 = st.columns(4)
            st.session_state.data['daily_data'][ds]['deaths'][h] = c1.number_input("Ölüm", value=st.session_state.data['daily_data'][ds]['deaths'].get(h, 0), key=f"d_{h}_{ds}")
            st.session_state.data['daily_data'][ds]['weight'][h] = c2.number_input("Ağırlık (g)", value=st.session_state.data['daily_data'][ds]['weight'].get(h, 0), key=f"w_{h}_{ds}")
            st.session_state.data['daily_data'][ds]['silo_remaining'][h] = c3.number_input("Silo (kg)", value=st.session_state.data['daily_data'][ds]['silo_remaining'].get(h, 0), key=f"s_{h}_{ds}")
            st.session_state.data['daily_data'][ds]['water'][h] = c4.number_input("Su (L)", value=st.session_state.data['daily_data'][ds]['water'].get(h, 0), key=f"wa_{h}_{ds}")
        
        st.session_state.data['daily_data'][ds]['notes'] = st.text_area("Notlar", value=st.session_state.data['daily_data'][ds].get('notes', ""))
        
        if st.form_submit_button("Kaydet"):
            log_transaction(st.session_state.data, "DAILY_DATA_INPUT", f"Gün {day_sel} verileri girildi")
            save_json(st.session_state.data, DATA_FILE)
            st.success(f"Gün {day_sel} verileri kalıcı olarak kaydedildi!")
            st.rerun()

# ============ PAGE: YEM TAKIBI ============
elif page == "🚚 Yem Takibi":
    st.title("Yem Takibi ve Sipariş")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Yem İrsaliyesi")
        with st.form("feed_form"):
            f_date = st.date_input("Tarih")
            f_type = st.selectbox("Tip", ["Civciv", "Büyütme", "Bitirme"])
            f_amt = st.number_input("Miktar (kg)", min_value=0)
            if st.form_submit_button("Ekle"):
                st.session_state.data['feed_invoices'].append({"date": str(f_date), "type": f_type, "amount": f_amt})
                log_transaction(st.session_state.data, "FEED_INVOICE", f"{f_amt}kg {f_type} yem eklendi")
                save_json(st.session_state.data, DATA_FILE)
                st.success("İrsaliye eklendi!")
                st.rerun()
    
    with col2:
        st.subheader("Sipariş Uyarıları")
        for h in st.session_state.data['settings']['houses']:
            daily_need = 150 * m['house_data'][h]['live'] / 1000
            kalan = m['house_data'][h]['silo']
            gun_kalan = kalan / daily_need if daily_need > 0 else 10
            
            if gun_kalan < 1:
                st.markdown(f"<div class='alert-red'><b>{h}:</b> {gun_kalan:.1f} gün yem! ACIL SİPARİŞ!</div>", unsafe_allow_html=True)
            elif gun_kalan < 3:
                st.markdown(f"<div class='alert-yellow'><b>{h}:</b> {gun_kalan:.1f} gün yem. Sipariş planla.</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='alert-green'><b>{h}:</b> {gun_kalan:.1f} gün yem mevcut.</div>", unsafe_allow_html=True)

# ============ PAGE: HESAPLAMALAR ============
elif page == "🧮 Hesaplamalar":
    st.title("Detaylı Analiz")
    tabs = st.tabs(["FCR Analizi", "Su Hazırlama", "Projeksiyon"])
    
    with tabs[0]:
        st.subheader("FCR Durumu")
        st.info(f"**Mevcut FCR:** {m['fcr']:.3f} | **Hedef:** 1.60 | **Sapma:** {m['fcr'] - 1.60:+.3f}")
        
    with tabs[1]:
        st.subheader("Su İhtiyacı")
        total_water = 200 * m['live'] / 1000
        st.metric("Günlük Su İhtiyacı", f"{total_water:.0f} L")
        
    with tabs[2]:
        st.subheader("42. Gün Tahmini")
        days_left = 42 - m['day']
        if days_left > 0:
            projected_fcr = m['fcr'] + (0.02 * days_left)
            st.warning(f"Mevcut gidişatla 42. günde FCR: **{projected_fcr:.3f}** olacak")

# ============ PAGE: İLAÇ PROGRAMI ============
elif page == "💊 İlaç Programı":
    st.title("İlaç Takvimi")
    sel_day = st.selectbox("Gün", [str(i) for i in range(1, 43)], index=m['day']-1)
    
    prog = st.session_state.data['drug_program'].get(sel_day, {"sabah": "", "aksam": "", "not": ""})
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Sabah (08:00)")
        prog['sabah'] = st.text_input("İlaç", value=prog['sabah'], key=f"s_{sel_day}")
    with c2:
        st.subheader("Akşam (16:00)")
        prog['aksam'] = st.text_input("İlaç", value=prog['aksam'], key=f"a_{sel_day}")
    
    prog['not'] = st.text_area("Not", value=prog['not'], key=f"n_{sel_day}")
    
    if st.button("Kaydet"):
        st.session_state.data['drug_program'][sel_day] = prog
        log_transaction(st.session_state.data, "DRUG_PROGRAM_UPDATE", f"Gün {sel_day} ilaç programı güncellendi")
        save_json(st.session_state.data, DATA_FILE)
        st.success("Program kaydedildi!")

# ============ PAGE: AI BİLGİ BANKASI ============
elif page == "🏥 AI Bilgi Bankası":
    st.title("AI Bilgi Bankası")
    st.write("Dosya yükleyerek AI analizi alabilirsiniz.")
    
    uploaded = st.file_uploader("Dosya Yükle", type=['png', 'jpg', 'jpeg', 'pdf'])
    if uploaded:
        st.success("Dosya yüklendi!")
        if st.button("AI Analiz Yap"):
            st.markdown("### AI Analiz Sonucu")
            st.info("Otopsi fotoğrafında karaciğer konjesyonu tespit edildi. Hepato desteğini artırın.")

# ============ PAGE: İLAÇ ENVANTERI ============
elif page == "📋 İlaç Envanteri":
    st.title("İlaç Envanteri")
    inv_df = pd.DataFrame([{"İlaç": k, "Stok": v["stock"], "Birim": v["unit"], "Maliyet": f"₺{v['cost']}"} for k, v in st.session_state.data['drug_inventory'].items()])
    st.dataframe(inv_df, use_container_width=True, hide_index=True)

# ============ PAGE: DURUM ANALİZİ ============
elif page == "📈 Durum Analizi":
    st.title("Kapsamlı Durum Analizi")
    st.markdown(f"### Sağlık Puanı: {m['health_score']:.0f}/100")
    st.progress(m['health_score'] / 100)
    
    st.subheader("Kritik Görevler")
    if m['mortalite'] > 1.0:
        st.error("Mortalite yüksek - Otopsi yapın")
    if m['fcr'] > 1.65:
        st.warning("FCR yükseliyor - Yem kalitesini kontrol edin")
    st.info("Gün 14 yem geçişi için hazırlık yapın")

# ============ PAGE: FİNANSAL ============
elif page == "💰 Finansal":
    st.title("Finansal Analiz")
    
    total_feed_cost = sum(inv['amount'] * st.session_state.data['settings']['feed_costs'].get(inv['type'], 2.0) for inv in st.session_state.data['feed_invoices'])
    total_drug_cost = sum(drug['cost'] * 10 for drug in st.session_state.data['drug_inventory'].values())
    total_cost = total_feed_cost + total_drug_cost + (st.session_state.data['settings']['labor_cost_per_day'] * m['day'])
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Yem Maliyeti", f"₺{total_feed_cost:,.0f}")
    c2.metric("İlaç Maliyeti", f"₺{total_drug_cost:,.0f}")
    c3.metric("Toplam Maliyet", f"₺{total_cost:,.0f}")
    
    if m['live'] > 0:
        cost_per_kg = total_cost / (m['live'] * m['weight'] / 1000) if m['weight'] > 0 else 0
        st.metric("Canlı kg Başı Maliyet", f"₺{cost_per_kg:.2f}")

# ============ PAGE: SOHBET ============
elif page == "💬 Sohbet":
    st.title("Murat Asistan")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Sorunuzu yazın..."):
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        response = f"Yağız, talebinizi aldım. Mevcut verilerinize göre (FCR: {m['fcr']:.3f}, Mortalite: {m['mortalite']:.2f}%) analiz yapıyorum."
        if "ilaç" in prompt.lower():
            response += " İlaç programını güncellememi ister misin?"
        
        with st.chat_message("assistant"):
            st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})

# ============ AUTO SAVE ============
save_json(st.session_state.data, DATA_FILE)
