import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import json
from pathlib import Path
import os
from google import genai
from google.genai import types


# Sayfa Konfigürasyonu
st.set_page_config(
    page_title="Murat Özkan Kümes Takip Sistemi",
    page_icon="🐔",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Banvit Verileri Yükle
@st.cache_data
def load_banvit_data():
    try:
        with open('banvit_data.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}


# Gemini AI Initialization
@st.cache_resource
def init_gemini():
    api_key = os.getenv('GEMINI_API_KEY')
    if api_key:
        client = genai.Client(api_key=api_key)
        return client
    return None

gemini_client = init_gemini()

# Session State Başlat
def init_session_state():
    if 'ayarlar' not in st.session_state:
        st.session_state.ayarlar = {
            'ciftlik_adi': 'Cambel Ciftligi',
            'baslangic_tarihi': datetime(2026, 2, 14),
            'kumes_civciv': [10248, 10836, 10836, 10836],
            'silo_kapasiteleri': [5.0, 5.0, 5.0, 5.0]
        }
    
    if 'gunluk_veriler' not in st.session_state:
        st.session_state.gunluk_veriler = {}
    
    if 'yem_irsaliyesi' not in st.session_state:
        st.session_state.yem_irsaliyesi = []
    
    if 'suru_notlari' not in st.session_state:
        st.session_state.suru_notlari = {}

# Dashboard Sayfası
def page_dashboard():
    st.title("Dashboard")
    
    ayarlar = st.session_state.ayarlar
    gunluk = st.session_state.gunluk_veriler
    
    # Üst Bilgiler
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Ciftlik", ayarlar['ciftlik_adi'])
    with col2:
        gun_farki = (datetime.now().date() - ayarlar['baslangic_tarihi'].date()).days + 1
        st.metric("Program Gunu", min(max(1, gun_farki), 42))
    with col3:
        st.metric("Baslangic Tarihi", ayarlar['baslangic_tarihi'].strftime("%d.%m.%Y"))
    with col4:
        kesim_tarihi = ayarlar['baslangic_tarihi'] + timedelta(days=41)
        st.metric("Tahmini Kesim", kesim_tarihi.strftime("%d.%m.%Y"))
    
    st.markdown("---")
    
    # KPI Kartları
    st.header("KPI Kartlari")
    
    toplam_hayvan = sum(ayarlar['kumes_civciv'][:4])
    toplam_olum = 0
    toplam_agirlik = 0
    
    for gun_data in gunluk.values():
        if isinstance(gun_data, dict) and 'olum' in gun_data:
            for kumes_olum in gun_data['olum'][:4]:
                toplam_olum += kumes_olum
    
    canli_hayvan = toplam_hayvan - toplam_olum
    olum_orani = (toplam_olum / toplam_hayvan * 100) if toplam_hayvan > 0 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Toplam Canli Hayvan", f"{canli_hayvan:,}")
    with col2:
        st.metric("Olum Orani", f"{olum_orani:.2f}%")
    with col3:
        st.metric("Ortalama Agirlik", "180 g")
    with col4:
        st.metric("Saglik Puani", "85/100")
    
    st.markdown("---")
    
    # Kümes Özeti
    st.header("Kumes Ozeti")
    
    kumes_data = []
    for i in range(4):
        kumes_olum = sum(gun_data.get('olum', [0,0,0,0])[i] for gun_data in gunluk.values() if isinstance(gun_data, dict))
        kumes_canli = ayarlar['kumes_civciv'][i] - kumes_olum
        kumes_data.append({
            'Kumes': f'Kumes {i+1}',
            'Baslangic': ayarlar['kumes_civciv'][i],
            'Canli': kumes_canli,
            'Olum': kumes_olum,
            'Olum Orani': f"{(kumes_olum/ayarlar['kumes_civciv'][i]*100):.2f}%" if ayarlar['kumes_civciv'][i] > 0 else "0%"
        })
    
    df_kumes = pd.DataFrame(kumes_data)
    st.dataframe(df_kumes, use_container_width=True)
    
    st.markdown("---")
    
    # Performans Grafikleri
    st.header("Performans Grafikleri")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Ölüm Trendi
        fig_olum = go.Figure()
        fig_olum.add_trace(go.Scatter(
            x=list(range(1, 43)),
            y=[0] * 42,
            mode='lines',
            name='Olum Sayisi'
        ))
        fig_olum.update_layout(title="Gunluk Olum Trendi", xaxis_title="Gun", yaxis_title="Olum Sayisi")
        st.plotly_chart(fig_olum, use_container_width=True)
    
    with col2:
        # Ağırlık Trendi
        fig_agirlik = go.Figure()
        fig_agirlik.add_trace(go.Scatter(
            x=list(range(1, 43)),
            y=[50 + i*50 for i in range(42)],
            mode='lines',
            name='Canli Agirlik'
        ))
        fig_agirlik.update_layout(title="Canli Agirlik Trendi", xaxis_title="Gun", yaxis_title="Agirlik (g)")
        st.plotly_chart(fig_agirlik, use_container_width=True)

# Ayarlar Sayfası
def page_ayarlar():
    st.title("Sistem Ayarlari")
    
    ayarlar = st.session_state.ayarlar
    
    st.header("Ciftlik Bilgileri")
    
    ciftlik_adi = st.text_input("Ciftlik Adi", value=ayarlar['ciftlik_adi'])
    baslangic_tarihi = st.date_input("Baslangic Tarihi", value=ayarlar['baslangic_tarihi'])
    
    st.markdown("---")
    
    st.header("Kumes Kapasiteleri (Civciv Sayisi)")
    
    col1, col2, col3, col4 = st.columns(4)
    
    kumes_civciv = []
    with col1:
        k1 = st.number_input("Kumes 1", value=ayarlar['kumes_civciv'][0], min_value=0, step=100)
        kumes_civciv.append(k1)
    with col2:
        k2 = st.number_input("Kumes 2", value=ayarlar['kumes_civciv'][1], min_value=0, step=100)
        kumes_civciv.append(k2)
    with col3:
        k3 = st.number_input("Kumes 3", value=ayarlar['kumes_civciv'][2], min_value=0, step=100)
        kumes_civciv.append(k3)
    with col4:
        k4 = st.number_input("Kumes 4", value=ayarlar['kumes_civciv'][3], min_value=0, step=100)
        kumes_civciv.append(k4)
    
    st.markdown("---")
    
    st.header("Silo Kapasiteleri (Ton)")
    
    col1, col2, col3, col4 = st.columns(4)
    
    silo_kapasiteleri = []
    with col1:
        s1 = st.number_input("Silo 1", value=ayarlar['silo_kapasiteleri'][0], min_value=0.0, step=0.5)
        silo_kapasiteleri.append(s1)
    with col2:
        s2 = st.number_input("Silo 2", value=ayarlar['silo_kapasiteleri'][1], min_value=0.0, step=0.5)
        silo_kapasiteleri.append(s2)
    with col3:
        s3 = st.number_input("Silo 3", value=ayarlar['silo_kapasiteleri'][2], min_value=0.0, step=0.5)
        silo_kapasiteleri.append(s3)
    with col4:
        s4 = st.number_input("Silo 4", value=ayarlar['silo_kapasiteleri'][3], min_value=0.0, step=0.5)
        silo_kapasiteleri.append(s4)
    
    st.markdown("---")
    
    if st.button("Kaydet", type="primary"):
        st.session_state.ayarlar = {
            'ciftlik_adi': ciftlik_adi,
            'baslangic_tarihi': datetime.combine(baslangic_tarihi, datetime.min.time()),
            'kumes_civciv': kumes_civciv,
            'silo_kapasiteleri': silo_kapasiteleri
        }
        st.success("Ayarlar kaydedildi!")
        st.rerun()

# Günlük Veriler Sayfası
def page_gunluk_veriler():
    st.title("Gunluk Veri Girisi")
    
    gun = st.slider("Gun Sec", 1, 42, 1)
    
    st.header(f"Gun {gun} - Veri Girisi")
    
    # Ölüm Verileri
    st.write("**Olum Sayilari**")
    col1, col2, col3, col4 = st.columns(4)
    
    olum_verileri = []
    with col1:
        o1 = st.number_input("Kumes 1 Olum", value=0, min_value=0, key=f"olum1_{gun}")
        olum_verileri.append(o1)
    with col2:
        o2 = st.number_input("Kumes 2 Olum", value=0, min_value=0, key=f"olum2_{gun}")
        olum_verileri.append(o2)
    with col3:
        o3 = st.number_input("Kumes 3 Olum", value=0, min_value=0, key=f"olum3_{gun}")
        olum_verileri.append(o3)
    with col4:
        o4 = st.number_input("Kumes 4 Olum", value=0, min_value=0, key=f"olum4_{gun}")
        olum_verileri.append(o4)
    
    st.markdown("---")
    
    # Ağırlık Verileri
    st.write("**Canli Agirlik (gram)**")
    col1, col2, col3, col4 = st.columns(4)
    
    agirlik_verileri = []
    with col1:
        a1 = st.number_input("Kumes 1 Agirlik", value=0.0, min_value=0.0, step=1.0, key=f"agirlik1_{gun}")
        agirlik_verileri.append(a1)
    with col2:
        a2 = st.number_input("Kumes 2 Agirlik", value=0.0, min_value=0.0, step=1.0, key=f"agirlik2_{gun}")
        agirlik_verileri.append(a2)
    with col3:
        a3 = st.number_input("Kumes 3 Agirlik", value=0.0, min_value=0.0, step=1.0, key=f"agirlik3_{gun}")
        agirlik_verileri.append(a3)
    with col4:
        a4 = st.number_input("Kumes 4 Agirlik", value=0.0, min_value=0.0, step=1.0, key=f"agirlik4_{gun}")
        agirlik_verileri.append(a4)
    
    st.markdown("---")
    
    if st.button("Kaydet", type="primary"):
        st.session_state.gunluk_veriler[gun] = {
            'olum': olum_verileri,
            'agirlik': agirlik_verileri
        }
        st.success(f"Gun {gun} verileri kaydedildi!")

# Hesaplamalar Sayfası
def page_hesaplamalar():
    st.title("Hesaplamalar")
    
    st.info("Otomatik hesaplamalar burada goruntulenecek")
    
    st.header("FCR Hesaplama")
    st.write("FCR = (Toplam Yem - Kalan Yem) / Toplam Canli Kutle")
    
    st.header("Su Hazirlama")
    st.write("Gunluk su tuketimi hesaplari")

# İlaç Programı Sayfası
def page_ilac_programi():
    st.title("Ilac Programi")
    
    st.info("Nihai Uzman Veteriner Programi - Gun gun ilac takvimi")
    
    gun = st.slider("Gun Sec", 1, 42, 1)
    
    st.header(f"Gun {gun} - Ilac Uygulamasi")
    
    st.write("**Sabah:**")
    st.write("- Ilac bilgisi burada goruntulenecek")
    
    st.write("**Aksam:**")
    st.write("- Ilac bilgisi burada goruntulenecek")

# AI Bilgi Bankası Sayfası
def page_ai_bilgi_bankasi():
    st.title("AI Bilgi Bankasi")
    
    st.header("Fotograf Yukleme")
    
    uploaded_file = st.file_uploader("Otopsi, FAL veya Antibiyogram fotografini yukleyin", type=['jpg', 'jpeg', 'png'])
    
    if uploaded_file:
        st.image(uploaded_file, caption="Yuklenen Fotograf", use_column_width=True)
        
        if st.button("AI Analiz Yap", type="primary"):
            if gemini_client:
                with st.spinner("AI analiz yapiliyor..."):
                    try:
                        # Upload image
                        file_path = f"/tmp/{uploaded_file.name}"
                        with open(file_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        
                        # Upload to Gemini
                        uploaded_gemini = gemini_client.files.upload(path=file_path)
                        
                        # Analyze with Gemini
                        response = gemini_client.models.generate_content(
                            model='gemini-2.0-flash-exp',
                            contents=[
                                types.Content(
                                    role="user",
                                    parts=[
                                        types.Part.from_uri(
                                            file_uri=uploaded_gemini.uri,
                                            mime_type=uploaded_gemini.mime_type
                                        ),
                                        types.Part.from_text(
                                            "Bu bir tavuk ciftligi otopsi, FAL raporu veya antibiyogram fotografidir. "
                                            "Lutfen fotograftaki bilgileri analiz et ve asagidaki bilgileri ver:\n"
                                            "1. Tespit edilen hastalik veya sorun\n"
                                            "2. Etkilenen organlar\n"
                                            "3. Onerilen ilac tedavisi\n"
                                            "4. Dikkat edilmesi gerekenler\n"
                                            "Turkce cevap ver."
                                        )
                                    ]
                                )
                            ]
                        )
                        
                        st.success("AI Analiz Tamamlandi!")
                        st.markdown("### Analiz Sonucu:")
                        st.write(response.text)
                        
                        # Clean up
                        os.remove(file_path)
                        
                    except Exception as e:
                        st.error(f"AI analiz hatasi: {str(e)}")
            else:
                st.warning("Gemini API baglantisi yok. Simulasyon modu:")
                st.info("""
                **AI Analiz Sonucu (Simulasyon):**
                
                1. **Tespit:** Omfalitis/Septisemi belirtileri
                2. **Etkilenen Organlar:** Karaciger, akciger
                3. **Onerilen Tedavi:** Neomisin Sulfat 100mg/L, 4 gun
                4. **Dikkat:** Hepato ile karaciger korumasi onemli
                """)

# İlaç Envanteri Sayfası
def page_ilac_envanteri():
    st.title("Ilac Envanteri")
    
    st.info("Ilac prospektusu bilgileri burada goruntulenecek")

# Durum Analizi Sayfası
def page_durum_analizi():
    st.title("Durum Analizi")
    
    st.header("AI Raporu")
    
    st.metric("Saglik Puani", "85/100")
    st.write("Suru saglik durumu iyi. Devam edin.")
    
    st.header("Kritik Gorevler")
    st.write("1. Gun 10'da Hepato uygula")
    st.write("2. Yem siparisi ver (3 gun kaldi)")
    st.write("3. Veteriner kontrolu yap")

# Sohbet Sayfası
def page_sohbet():
    st.title("Sohbet")
    
    st.info("AI Asistan ile canli sohbet")
    
    # Initialize chat history
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    # Display chat history
    for msg in st.session_state.chat_history:
        if msg['role'] == 'user':
            st.markdown(f"**Siz:** {msg['content']}")
        else:
            st.markdown(f"**AI:** {msg['content']}")
    
    st.markdown("---")
    
    user_input = st.text_input("Mesajiniz:", key="chat_input")
    
    if st.button("Gonder"):
        if user_input:
            # Add user message
            st.session_state.chat_history.append({'role': 'user', 'content': user_input})
            
            if gemini_client:
                try:
                    # Get AI response
                    response = gemini_client.models.generate_content(
                        model='gemini-2.0-flash-exp',
                        contents=f"""Sen bir tavuk ciftligi yonetim asistanisin. 
                        Kullanici sorusu: {user_input}
                        
                        Ciftlik bilgileri:
                        - Ciftlik: {st.session_state.ayarlar['ciftlik_adi']}
                        - Kumes sayisi: 4
                        - Toplam civciv: {sum(st.session_state.ayarlar['kumes_civciv'])}
                        
                        Lutfen Turkce, kisa ve net cevap ver."""
                    )
                    
                    ai_response = response.text
                    
                except Exception as e:
                    ai_response = f"Uzgunum, bir hata olustu: {str(e)}"
            else:
                ai_response = "Merhaba! Size nasil yardimci olabilirim? (Gemini API baglantisi yok, simulasyon modu)"
            
            # Add AI response
            st.session_state.chat_history.append({'role': 'assistant', 'content': ai_response})
            
            st.rerun()

# Ana Uygulama
def main():
    init_session_state()
    
    # Sidebar Menü
    st.sidebar.title("Murat Ozkan Kumes Takip Sistemi")
    
    sayfa = st.sidebar.radio(
        "Sayfalar",
        [
            "Dashboard",
            "Ayarlar",
            "Gunluk Veriler",
            "Hesaplamalar",
            "Ilac Programi",
            "AI Bilgi Bankasi",
            "Ilac Envanteri",
            "Durum Analizi",
            "Sohbet"
        ]
    )
    
    # Sayfa Yönlendirme
    if sayfa == "Dashboard":
        page_dashboard()
    elif sayfa == "Ayarlar":
        page_ayarlar()
    elif sayfa == "Gunluk Veriler":
        page_gunluk_veriler()
    elif sayfa == "Hesaplamalar":
        page_hesaplamalar()
    elif sayfa == "Ilac Programi":
        page_ilac_programi()
    elif sayfa == "AI Bilgi Bankasi":
        page_ai_bilgi_bankasi()
    elif sayfa == "Ilac Envanteri":
        page_ilac_envanteri()
    elif sayfa == "Durum Analizi":
        page_durum_analizi()
    elif sayfa == "Sohbet":
        page_sohbet()

if __name__ == "__main__":
    main()
