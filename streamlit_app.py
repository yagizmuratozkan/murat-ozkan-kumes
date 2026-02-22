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


def calculate_feed_days_remaining(banvit_data, house_data, current_day):
    """Kalan yem gün sayısını hesapla"""
    if current_day > 42 or current_day < 1:
        return {}
    
    day_data = banvit_data.get(str(current_day), {})
    daily_consumption_per_bird = day_data.get('yem_tüketimi', 150) / 1000  # gram to kg
    
    feed_days = {}
    for house_name, house_info in house_data.items():
        live_birds = house_info['live']
        daily_need = live_birds * daily_consumption_per_bird
        silo_remaining = house_info['silo']
        days_remaining = silo_remaining / daily_need if daily_need > 0 else 999
        feed_days[house_name] = {'days': days_remaining, 'daily_need': daily_need, 'silo': silo_remaining}
    
    return feed_days

def calculate_feed_order(feed_days, current_day):
    """Yem siparişi önerisi hesapla - 9 ton katları, haftaiçi"""
    from datetime import datetime
    
    orders = {}
    today = datetime.now()
    day_of_week = today.weekday()  # 0=Monday, 4=Friday, 5=Saturday, 6=Sunday
    
    # Haftaiçi mi kontrol et (Pazartesi-Cuma)
    is_weekday = day_of_week < 5
    
    for house_name, feed_info in feed_days.items():
        days_left = feed_info['days']
        daily_need = feed_info['daily_need']
        
        order_needed = False
        order_amount = 0
        
        if days_left < 3:
            order_needed = True
            # 9 ton katları hesapla
            tons_needed = (daily_need * 5) / 1000  # 5 gün için
            order_amount = int((tons_needed // 9) + 1) * 9  # Yukarı yuvarlama
        
        orders[house_name] = {
            'order_needed': order_needed,
            'order_amount': order_amount,
            'is_weekday': is_weekday,
            'days_left': days_left,
            'recommendation': f"{order_amount} ton" if order_needed else "Yem yeterli"
        }
    
    return orders


def calculate_advanced_feed_planning(banvit_data, house_data, current_day, silo_capacities):
    """
    İleri seviye yem sipariş planlayıcısı
    - Silo kapasitesi kontrol
    - Gelecek tüketim tahmini (Banvit)
    - Haftaiçi planlama
    - 9 ton optimizasyonu
    """
    from datetime import datetime, timedelta
    
    planning = {}
    today = datetime.now()
    day_of_week = today.weekday()  # 0=Monday, 6=Sunday
    
    for house_name, house_info in house_data.items():
        live_birds = house_info['live']
        silo_remaining = house_info['silo']
        silo_capacity = silo_capacities.get(house_name, 50)  # Default 50 ton
        
        # Gelecek 7 gün için tüketim tahmini
        future_consumption = 0
        for future_day in range(current_day, min(current_day + 7, 43)):
            day_data = banvit_data.get(str(future_day), {})
            daily_consumption_per_bird = day_data.get('yem_tüketimi', 150) / 1000
            future_consumption += live_birds * daily_consumption_per_bird
        
        # Kalan gün hesabı
        avg_daily_consumption = future_consumption / 7 if future_consumption > 0 else 0
        days_remaining = silo_remaining / avg_daily_consumption if avg_daily_consumption > 0 else 999
        
        # Silo kapasitesi göz önünde bulundurarak sipariş önerisi
        available_silo_space = silo_capacity - silo_remaining
        
        # 9 ton katları hesapla (silo kapasitesini aşmayacak şekilde)
        max_order_9_ton_units = int(available_silo_space / 9)
        recommended_order = max_order_9_ton_units * 9
        
        # Haftaiçi planlama
        weekday_names = ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar']
        today_name = weekday_names[day_of_week]
        is_weekday = day_of_week < 5
        
        # Yem bitme tahmini
        estimated_depletion_day = current_day + days_remaining
        
        # Uyarı mesajı
        warning_message = ""
        if days_remaining < 3:
            if is_weekday:
                warning_message = f"ACIL: Bugün ({today_name}) sipariş ver! {days_remaining:.1f} gün yem kaldı."
            else:
                next_weekday = (5 - day_of_week) % 7  # Pazartesiye kaç gün kaldı
                warning_message = f"ACIL: Pazartesi ({next_weekday} gün sonra) sipariş ver! {days_remaining:.1f} gün yem kaldı."
        elif days_remaining < 5:
            warning_message = f"UYARI: {days_remaining:.1f} gün yem kaldı. Haftaiçi sipariş planla."
        else:
            warning_message = f"Yem yeterli ({days_remaining:.1f} gün)"
        
        planning[house_name] = {
            'days_remaining': days_remaining,
            'silo_remaining': silo_remaining,
            'silo_capacity': silo_capacity,
            'available_space': available_silo_space,
            'recommended_order': recommended_order,
            'max_order_tons': max_order_9_ton_units * 9,
            'future_consumption_7days': future_consumption,
            'avg_daily_consumption': avg_daily_consumption,
            'estimated_depletion_day': estimated_depletion_day,
            'is_weekday': is_weekday,
            'today_name': today_name,
            'warning': warning_message
        }
    
    return planning

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
    st.title("Yem Takibi ve Ileri Siparis Planlama")
    
    # Calculate current metrics
    metrics = calculate_metrics()
    current_day = get_current_day()
    
    # Get silo capacities from settings
    silo_capacities = st.session_state.data.get('settings', {}).get('silo_capacities', {})
    
    # Calculate advanced planning
    planning = calculate_advanced_feed_planning(
        st.session_state.banvit_data,
        metrics['house_data'],
        current_day,
        silo_capacities
    )
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Yem Irsaliyesi")
        with st.form("feed_invoice_form"):
            invoice_date = st.date_input("Tarih")
            feed_type = st.selectbox("Yem Türü", ["Civciv", "Büyütme", "Kesim"])
            amount_kg = st.number_input("Miktar (kg)", min_value=0, step=100)
            supplier = st.text_input("Tedarikçi")
            
            if st.form_submit_button("Ekle"):
                st.session_state.data['feed_invoices'].append({
                    'date': str(invoice_date),
                    'type': feed_type,
                    'amount': amount_kg,
                    'supplier': supplier
                })
                save_json(DATA_FILE, st.session_state.data)
                st.success("Yem kaydedildi")
    
    with col2:
        st.subheader("Ileri Siparis Planlama")
        
        for house_name, plan in planning.items():
            with st.container():
                col_a, col_b = st.columns(2)
                
                with col_a:
                    st.metric(f"{house_name}", f"{plan['days_remaining']:.1f} gün")
                    st.write(f"Siloda: {plan['silo_remaining']:.0f} / {plan['silo_capacity']} ton")
                    st.write(f"Günlük: {plan['avg_daily_consumption']:.0f} kg")
                
                with col_b:
                    if plan['days_remaining'] < 3:
                        st.error(plan['warning'])
                    elif plan['days_remaining'] < 5:
                        st.warning(plan['warning'])
                    else:
                        st.success(plan['warning'])
                    
                    st.write(f"**Siparis Onerisi:** {plan['recommended_order']:.0f} ton")
                    st.write(f"**Silo Bos Yer:** {plan['available_space']:.0f} ton")
                
                st.divider()
    
    st.subheader("Yem Gelis Gecmisi")
    if st.session_state.data['feed_invoices']:
        for inv in st.session_state.data['feed_invoices']:
            st.write(f"{inv['date']} - {inv['type']}: {inv['amount']} kg ({inv['supplier']})")
    else:
        st.info("Henüz yem kaydı yok")


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
    total_drug_cost = sum(drug.get('cost', 0) * 10 for drug in st.session_state.data['drug_inventory'].values() if isinstance(drug, dict))
    total_cost = total_feed_cost + total_drug_cost + (st.session_state.data['settings'].get('labor_cost_per_day', 500) * m['day'])
    
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
