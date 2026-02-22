import streamlit as st
import json
import os
from datetime import datetime, timedelta
import google.generativeai as genai

# Mock Streamlit functions and session_state for testing
class MockSessionState:
    def __init__(self):
        self.farm_data = {}
        self.banvit_data = {}
        self.drug_program = {}
        self.chat_history = []

class MockStreamlit:
    def __init__(self):
        self.session_state = MockSessionState()
        self.secrets = {"GEMINI_API_KEY": "mock_api_key"}

    def set_page_config(self, **kwargs): pass
    def markdown(self, *args, **kwargs): pass
    def title(self, *args, **kwargs): pass
    def subheader(self, *args, **kwargs): pass
    def write(self, *args, **kwargs): pass
    def info(self, *args, **kwargs): pass
    def warning(self, *args, **kwargs): pass
    def error(self, *args, **kwargs): pass
    def success(self, *args, **kwargs): pass
    def text_input(self, *args, **kwargs): return ""
    def date_input(self, *args, **kwargs): return datetime.now().date()
    def number_input(self, *args, **kwargs): return 0
    def form(self, *args, **kwargs): return self
    def form_submit_button(self, *args, **kwargs): return False
    def expander(self, *args, **kwargs): return self
    def radio(self, *args, **kwargs): return ""
    def columns(self, *args, **kwargs): return [self, self, self]
    def button(self, *args, **kwargs): return False
    def text_area(self, *args, **kwargs): return ""
    def spinner(self, *args, **kwargs): return self
    def rerun(self): pass
    def stop(self): pass
    def dataframe(self, *args, **kwargs): pass
    def sidebar(self): return self

    def __enter__(self): return self
    def __exit__(self, exc_type, exc_val, exc_tb): pass

st = MockStreamlit()
genai.configure(api_key="mock_api_key") # Configure genai with a mock key

# Re-import functions from streamlit_app.py after mocking st
from streamlit_app import (
    DATA_FILE, BANVIT_FILE, DRUG_PROGRAM_FILE,
    initialize_data_file, load_json, save_json, log_transaction,
    get_current_day, calculate_live_birds_per_house, calculate_total_live_birds,
    calculate_average_weight, calculate_fcr, calculate_death_rate,
    calculate_feed_days_remaining, calculate_water_preparation, calculate_health_score,
    page_dashboard, page_settings, page_daily_entry, page_drug_program, page_feed_logistics,
    page_chat, page_calculations, page_ai_knowledge_base, page_drug_inventory,
    page_status_analysis, page_financial_analysis
)

print("--- Starting Page Loading Tests ---")

# Initialize data files for testing if they don't exist
initialize_data_file(DATA_FILE, {"settings": {"farm_name": "Test Farm", "start_date": "2026-02-01", "target_slaughter_date": "2026-03-14", "houses": {"Kümes 1": {"chick_count": 10000, "silo_capacity": 20.0}}}, "daily_data": {}})
initialize_data_file(BANVIT_FILE, {"1": {"ross_ağırlık": 50, "yem_tüketimi": 10, "su_tüketimi": 20, "fcr": 0.5}})
initialize_data_file(DRUG_PROGRAM_FILE, {"drug_program_complete": {"1": {"sabah": "Vitamin", "aksam": "Antibiyotik"}}})

st.session_state.farm_data = load_json(DATA_FILE)
st.session_state.banvit_data = load_json(BANVIT_FILE)
st.session_state.drug_program = load_json(DRUG_PROGRAM_FILE)

# Test each page function
page_functions = {
    "Dashboard": page_dashboard,
    "Ayarlar": page_settings,
    "Günlük Veri Girişi": page_daily_entry,
    "İlaç Programı": page_drug_program,
    "Yem Lojistiği": page_feed_logistics,
    "AI Asistan": page_chat,
    "Hesaplamalar": page_calculations,
    "AI Bilgi Bankası": page_ai_knowledge_base,
    "İlaç Envanteri": page_drug_inventory,
    "Durum Analizi": page_status_analysis,
    "Finansal Analiz": page_financial_analysis,
}

for page_name, page_func in page_functions.items():
    try:
        print(f"Testing page: {page_name}...")
        page_func()
        print(f"✅ Page {page_name} loaded successfully.")
    except Exception as e:
        print(f"❌ Error loading page {page_name}: {e}")

print("--- Page Loading Tests Completed ---")
