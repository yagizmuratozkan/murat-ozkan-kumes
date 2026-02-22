# Enhanced Chat Module with Real Gemini AI Integration
import streamlit as st
import google.generativeai as genai
from datetime import datetime
import os

def build_farm_context(farm_data, banvit_data, current_day, calculations):
    """Build comprehensive farm context for AI analysis"""
    
    total_live = calculations['total_live']
    death_rate = calculations['death_rate']
    avg_weight = calculations['avg_weight']
    fcr = calculations['fcr']
    health_score = calculations['health_score']
    feed_days = calculations['feed_days']
    morning_water = calculations['morning_water']
    evening_water = calculations['evening_water']
    
    # Get Ross targets
    banvit_day = str(current_day)
    target_weight = 0
    target_fcr = 0
    if banvit_day in banvit_data:
        target_weight = banvit_data[banvit_day].get('ross_ağırlık', 0)
        target_fcr = banvit_data[banvit_day].get('fcr', 0)
    
    # Get today's drug program
    today_drug = ""
    if banvit_day in farm_data.get('drug_program', {}):
        today_drug_data = farm_data['drug_program'][banvit_day]
        today_drug = f"Sabah: {today_drug_data.get('sabah', 'Yok')} | Akşam: {today_drug_data.get('aksam', 'Yok')}"
    
    # Calculate weight deviation
    weight_deviation = 0
    if target_weight > 0:
        weight_deviation = ((avg_weight - target_weight) / target_weight) * 100
    
    # Get house-wise data
    house_data = []
    for house_name in farm_data['settings']['houses'].keys():
        house_data.append(f"- {house_name}: Canlı={farm_data.get('daily_data', {}).get(f'day_{current_day}', {}).get(house_name, {}).get('live', 'N/A')}")
    
    context = f"""Sen bir Ross 308 broiler çiftliği yönetim danışmanısın. Çiftlik hakkında aşağıdaki gerçek verilere dayanarak analiz ve tavsiyelerde bulun.

=== ÇIFTLIK DURUMU (Gün {current_day}/42) ===
Çiftlik Adı: {farm_data['settings'].get('farm_name', 'N/A')}
Başlangıç: {farm_data['settings'].get('start_date', 'N/A')}
Kesim Tarihi: {farm_data['settings'].get('target_slaughter_date', 'N/A')}

=== HAYVAN VERİLERİ ===
Toplam Canlı Hayvan: {total_live:,}
Ölüm Oranı: %{death_rate:.2f}
Ortalama Ağırlık: {avg_weight:.0f}g (Hedef: {target_weight}g, Sapma: {weight_deviation:.1f}%)
Sağlık Puanı: {health_score:.1f}/100

=== YEM VE SU YÖNETİMİ ===
FCR: {fcr:.2f} (Hedef: {target_fcr:.2f})
Siloda Kalan Yem (Gün): {min(feed_days.values()) if feed_days else 0:.1f} gün
Günlük Su Hazırlama: {morning_water + evening_water:.0f}L (Sabah: {morning_water:.0f}L, Akşam: {evening_water:.0f}L)

=== BUGÜNÜN İLAÇ PROGRAMI ===
{today_drug}

=== UYARILAR ===
"""
    
    # Add warnings
    warnings = []
    min_feed_days = min(feed_days.values()) if feed_days else 999
    if min_feed_days < 2:
        warnings.append(f"🔴 KRİTİK: Siloda {min_feed_days:.1f} günlük yem kaldı!")
    elif min_feed_days < 3:
        warnings.append(f"🟡 UYARI: Siloda {min_feed_days:.1f} günlük yem kaldı.")
    
    if death_rate > 2:
        warnings.append(f"🔴 KRİTİK: Ölüm oranı %{death_rate:.2f}")
    elif death_rate > 1:
        warnings.append(f"🟡 UYARI: Ölüm oranı %{death_rate:.2f}")
    
    if fcr > target_fcr + 0.1:
        warnings.append(f"🔴 KRİTİK: FCR {fcr:.2f} (Hedef: {target_fcr:.2f})")
    elif fcr > target_fcr + 0.05:
        warnings.append(f"🟡 UYARI: FCR sapması var")
    
    if weight_deviation < -10:
        warnings.append(f"🔴 KRİTİK: Ağırlık %{weight_deviation:.1f} gerisinde")
    elif weight_deviation < -5:
        warnings.append(f"🟡 UYARI: Ağırlık biraz gerisinde")
    
    if warnings:
        context += "\n".join(warnings)
    else:
        context += "✅ Tüm parametreler normal"
    
    return context


def get_ai_response(context, user_question):
    """Get response from Gemini AI"""
    try:
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            return "❌ Gemini API anahtarı bulunamadı. Lütfen ortam değişkenini ayarlayın."
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        full_prompt = f"""{context}

=== KULLANICI SORUSU ===
{user_question}

Lütfen:
1. Çiftliğin mevcut durumunu değerlendir
2. Kullanıcının sorusuna doğrudan cevap ver
3. Spesifik, uygulanabilir tavsiyelerde bulun
4. Varsa uyarıları belirt
5. Türkçe cevap ver"""
        
        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        return f"❌ Gemini API hatası: {str(e)}"


def render_chat_page(farm_data, banvit_data, current_day, calculations):
    """Render the enhanced chat page"""
    st.title("💬 AI Asistan - Çiftlik Danışmanı")
    
    st.info("🤖 Çiftlik hakkında sorular sorun. AI asistan, gerçek verilerinize dayanarak analiz yapacak.")
    
    # Chat history
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = farm_data.get('chat_history', [])
    
    # Display chat history (last 10 messages)
    for message in st.session_state.chat_history[-10:]:
        if message['role'] == 'user':
            st.write(f"👤 **Siz**: {message['content']}")
        else:
            st.write(f"🤖 **AI**: {message['content']}")
    
    st.markdown("---")
    
    # Quick questions
    st.subheader("Hızlı Sorular")
    col1, col2, col3 = st.columns(3)
    
    quick_questions = [
        "Bugün ne yapmalıyım?",
        "Çiftliğin durumu nasıl?",
        "FCR'ı nasıl iyileştirebilirim?"
    ]
    
    selected_quick = None
    with col1:
        if st.button(quick_questions[0]):
            selected_quick = quick_questions[0]
    with col2:
        if st.button(quick_questions[1]):
            selected_quick = quick_questions[1]
    with col3:
        if st.button(quick_questions[2]):
            selected_quick = quick_questions[2]
    
    # User input
    user_input = st.text_area(
        "Sorunuzu yazın veya hızlı sorulardan birini seçin:",
        value=selected_quick if selected_quick else "",
        height=100
    )
    
    if st.button("📤 Gönder", use_container_width=True):
        if user_input.strip():
            with st.spinner("🤔 AI analiz yapıyor..."):
                # Build context
                context = build_farm_context(farm_data, banvit_data, current_day, calculations)
                
                # Get AI response
                ai_response = get_ai_response(context, user_input)
                
                # Add to chat history
                st.session_state.chat_history.append({"role": "user", "content": user_input})
                st.session_state.chat_history.append({"role": "assistant", "content": ai_response})
                
                # Save to farm data
                farm_data['chat_history'] = st.session_state.chat_history
                
                st.rerun()
