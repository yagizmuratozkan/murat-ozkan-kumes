import json
import os
from datetime import datetime, timedelta

# Mock Streamlit session_state for testing
class MockSessionState:
    def __init__(self):
        self.farm_data = {}
        self.banvit_data = {}
        self.drug_program = {}

st.session_state = MockSessionState()

# Load data files (simplified for testing)
def load_json_test(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

st.session_state.farm_data = load_json_test('farm_data.json')
st.session_state.banvit_data = load_json_test('banvit_data.json')
st.session_state.drug_program = load_json_test('complete_drug_program.json')

# Import functions from streamlit_app.py (assuming they are in the same directory)
from streamlit_app import (
    get_current_day,
    calculate_live_birds_per_house,
    calculate_total_live_birds,
    calculate_average_weight,
    calculate_fcr,
    calculate_death_rate,
    calculate_feed_days_remaining,
    calculate_water_preparation,
    calculate_health_score,
    log_transaction,
    save_json,
    DATA_FILE
)

print("--- Starting App Logic Tests ---")

# Test 1: get_current_day
print("\nTesting get_current_day...")
# Ensure start_date is set for testing
if 'settings' not in st.session_state.farm_data:
    st.session_state.farm_data['settings'] = {}
st.session_state.farm_data['settings']['start_date'] = '2026-02-01'
current_day = get_current_day()
print(f"Current Day: {current_day}")
assert current_day > 0, "get_current_day returned invalid day"
print("✅ get_current_day passed.")

# Test 2: calculate_live_birds_per_house and calculate_total_live_birds
print("\nTesting live bird calculations...")
# Mock some initial data
st.session_state.farm_data['settings']['houses'] = {
    'Kümes 1': {'chick_count': 10000, 'silo_capacity': 20.0},
    'Kümes 2': {'chick_count': 10000, 'silo_capacity': 20.0}
}
st.session_state.farm_data['daily_data'] = {
    'day_1': {'Kümes 1': {'deaths': 10}, 'Kümes 2': {'deaths': 5}},
    'day_2': {'Kümes 1': {'deaths': 5}, 'Kümes 2': {'deaths': 3}}
}
live_kumes1 = calculate_live_birds_per_house('Kümes 1', 2)
live_kumes2 = calculate_live_birds_per_house('Kümes 2', 2)
total_live = calculate_total_live_birds(2)
print(f"Live birds Kümes 1 (Day 2): {live_kumes1}")
print(f"Live birds Kümes 2 (Day 2): {live_kumes2}")
print(f"Total live birds (Day 2): {total_live}")
assert live_kumes1 == 9985, "Live birds for Kümes 1 incorrect"
assert live_kumes2 == 9992, "Live birds for Kümes 2 incorrect"
assert total_live == 19977, "Total live birds incorrect"
print("✅ Live bird calculations passed.")

# Test 3: calculate_average_weight
print("\nTesting average weight calculation...")
st.session_state.farm_data['daily_data']['day_2']['Kümes 1']['weight'] = 500
st.session_state.farm_data['daily_data']['day_2']['Kümes 2']['weight'] = 520
avg_weight = calculate_average_weight(2)
print(f"Average weight (Day 2): {avg_weight:.2f}g")
assert abs(avg_weight - 509.97) < 0.01, "Average weight incorrect"
print("✅ Average weight calculation passed.")

# Test 4: calculate_fcr
print("\nTesting FCR calculation...")
st.session_state.farm_data['feed_invoices'] = [{'quantity': 10000}, {'quantity': 5000}]
st.session_state.farm_data['daily_data']['day_2']['Kümes 1']['silo_remaining'] = 1000
st.session_state.farm_data['daily_data']['day_2']['Kümes 2']['silo_remaining'] = 500
fcr = calculate_fcr(2)
print(f"FCR (Day 2): {fcr:.2f}")
assert abs(fcr - 0.68) < 0.01, "FCR calculation incorrect"
print("✅ FCR calculation passed.")

# Test 5: calculate_death_rate
print("\nTesting death rate calculation...")
death_rate = calculate_death_rate(2)
print(f"Death rate (Day 2): {death_rate:.2f}%")
assert abs(death_rate - 0.09) < 0.01, "Death rate calculation incorrect"
print("✅ Death rate calculation passed.")

# Test 6: calculate_feed_days_remaining
print("\nTesting feed days remaining...")
feed_days = calculate_feed_days_remaining(2)
print(f"Feed days remaining (Day 2): {feed_days}")
assert len(feed_days) == 2, "Feed days remaining count incorrect"
assert abs(feed_days['Kümes 1'] - 33.28) < 0.01, "Feed days remaining for Kümes 1 incorrect"
print("✅ Feed days remaining passed.")

# Test 7: calculate_water_preparation
print("\nTesting water preparation...")
morning_water, evening_water = calculate_water_preparation(2)
print(f"Water preparation (Day 2): Morning={morning_water:.2f}L, Evening={evening_water:.2f}L")
assert abs(morning_water - 400.0) < 0.01, "Morning water incorrect"
assert abs(evening_water - 400.0) < 0.01, "Evening water incorrect"
print("✅ Water preparation passed.")

# Test 8: calculate_health_score
print("\nTesting health score...")
health_score = calculate_health_score(2)
print(f"Health score (Day 2): {health_score:.1f}")
assert abs(health_score - 100.0) < 0.1, "Health score incorrect"
print("✅ Health score passed.")

print("\n--- All App Logic Tests Completed Successfully ---")
