# Advanced Feed Logistics Module
# Intelligent feed ordering, silo management, and consumption planning

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

class FeedLogistics:
    """Advanced feed logistics management system"""
    
    def __init__(self, farm_data, banvit_data):
        self.farm_data = farm_data
        self.banvit_data = banvit_data
        self.settings = farm_data['settings']
        
    def get_daily_consumption_per_bird(self, day: int) -> float:
        """Get daily feed consumption per bird in grams (from Banvit data)"""
        day_str = str(day)
        if day_str in self.banvit_data:
            return self.banvit_data[day_str].get('yem_tüketimi', 150) / 1000  # Convert to kg
        return 0.15  # Default fallback
    
    def calculate_house_daily_consumption(self, house_name: str, day: int, live_birds: int) -> float:
        """Calculate daily feed consumption for a house in kg"""
        daily_per_bird = self.get_daily_consumption_per_bird(day)
        return live_birds * daily_per_bird
    
    def calculate_days_until_empty(self, house_name: str, silo_remaining_kg: float, 
                                   day: int, live_birds: int) -> float:
        """Calculate how many days until silo is empty"""
        daily_consumption = self.calculate_house_daily_consumption(house_name, day, live_birds)
        if daily_consumption > 0:
            return silo_remaining_kg / daily_consumption
        return 999
    
    def get_optimal_order_quantity(self, min_days_remaining: float) -> int:
        """
        Calculate optimal order quantity (9, 18, 27, or 36 tons)
        Based on minimum days remaining in any silo
        """
        order_options = [9, 18, 27, 36]  # Available order quantities in tons
        
        # If less than 2 days remaining, order maximum (36 tons)
        if min_days_remaining < 2:
            return 36
        # If less than 3 days, order 27 tons
        elif min_days_remaining < 3:
            return 27
        # If less than 5 days, order 18 tons
        elif min_days_remaining < 5:
            return 18
        # Otherwise, order 9 tons
        else:
            return 9
    
    def check_silo_overflow_risk(self, house_name: str, current_silo_kg: float, 
                                 order_quantity_tons: float) -> Tuple[bool, str]:
        """
        Check if adding order quantity will cause silo overflow
        Returns (is_overflow_risk, message)
        """
        silo_capacity_tons = self.settings['houses'][house_name]['silo_capacity']
        silo_capacity_kg = silo_capacity_tons * 1000
        
        total_after_order = current_silo_kg + (order_quantity_tons * 1000)
        
        if total_after_order > silo_capacity_kg:
            overflow_amount = total_after_order - silo_capacity_kg
            return (True, f"⚠️ Taşma riski! {overflow_amount/1000:.1f} ton fazla olacak")
        
        return (False, f"✅ Güvenli. Silo %{(total_after_order/silo_capacity_kg)*100:.0f} dolu olacak")
    
    def get_feed_type_for_day(self, day: int) -> str:
        """Determine feed type (Civciv/Büyütme/Bitirme) based on day"""
        chick_to_grower = self.settings['feed_transition'].get('chick_to_grower', 14)
        grower_to_finisher = self.settings['feed_transition'].get('grower_to_finisher', 28)
        
        if day <= chick_to_grower:
            return "Civciv"
        elif day <= grower_to_finisher:
            return "Büyütme"
        else:
            return "Bitirme"
    
    def calculate_stale_risk(self, silo_days_remaining: float) -> Tuple[str, str]:
        """
        Calculate risk of feed becoming stale (dust increase)
        Returns (risk_level, message)
        """
        stale_threshold = self.settings.get('feed_stale_days', 7)
        
        if silo_days_remaining > stale_threshold:
            return ("🟡 UYARI", f"Yem {silo_days_remaining:.1f} gün siloda kalacak (Bayatlama riski >7 gün)")
        else:
            return ("🟢 NORMAL", f"Yem {silo_days_remaining:.1f} gün içinde tüketilecek")
    
    def generate_order_recommendation(self, current_day: int, farm_data: Dict) -> Dict:
        """Generate comprehensive feed order recommendation"""
        
        recommendation = {
            "day": current_day,
            "timestamp": datetime.now().isoformat(),
            "houses": {},
            "overall_recommendation": "",
            "critical_alerts": [],
            "warnings": []
        }
        
        min_days_remaining = 999
        houses_needing_order = []
        
        # Analyze each house
        for house_name in self.settings['houses'].keys():
            house_info = self.settings['houses'][house_name]
            
            # Get live birds
            live_birds = farm_data.get('daily_data', {}).get(f'day_{current_day}', {}).get(house_name, {}).get('live', house_info['chick_count'])
            
            # Get current silo level
            silo_remaining = farm_data.get('daily_data', {}).get(f'day_{current_day}', {}).get(house_name, {}).get('silo_remaining', 0)
            
            # Calculate days remaining
            days_remaining = self.calculate_days_until_empty(house_name, silo_remaining, current_day, live_birds)
            
            min_days_remaining = min(min_days_remaining, days_remaining)
            
            # Determine feed type
            feed_type = self.get_feed_type_for_day(current_day)
            
            # Check stale risk
            stale_risk, stale_msg = self.calculate_stale_risk(days_remaining)
            
            # Check overflow risk
            order_qty = self.get_optimal_order_quantity(days_remaining)
            overflow_risk, overflow_msg = self.check_silo_overflow_risk(house_name, silo_remaining, order_qty)
            
            house_rec = {
                "house_name": house_name,
                "live_birds": live_birds,
                "silo_remaining_kg": silo_remaining,
                "silo_capacity_tons": house_info['silo_capacity'],
                "days_remaining": days_remaining,
                "feed_type": feed_type,
                "daily_consumption_kg": self.calculate_house_daily_consumption(house_name, current_day, live_birds),
                "stale_risk": stale_risk,
                "stale_message": stale_msg,
                "overflow_risk": overflow_risk,
                "overflow_message": overflow_msg,
                "needs_order": days_remaining < self.settings.get('min_feed_days', 2)
            }
            
            recommendation["houses"][house_name] = house_rec
            
            if house_rec["needs_order"]:
                houses_needing_order.append(house_name)
        
        # Overall recommendation
        order_quantity = self.get_optimal_order_quantity(min_days_remaining)
        
        if min_days_remaining < 1:
            recommendation["critical_alerts"].append(f"🔴 ACİL: Siloda 1 günden az yem kaldı! Hemen sipariş ver!")
            recommendation["overall_recommendation"] = f"ACIL SİPARİŞ: {order_quantity} ton yem gerekli"
        elif min_days_remaining < 2:
            recommendation["critical_alerts"].append(f"🔴 KRİTİK: Siloda {min_days_remaining:.1f} günlük yem kaldı!")
            recommendation["overall_recommendation"] = f"HEMEN SİPARİŞ: {order_quantity} ton yem gerekli"
        elif min_days_remaining < 3:
            recommendation["warnings"].append(f"🟡 UYARI: Siloda {min_days_remaining:.1f} günlük yem kaldı")
            recommendation["overall_recommendation"] = f"SİPARİŞ ÖNERİSİ: {order_quantity} ton yem"
        else:
            recommendation["overall_recommendation"] = f"Siloda yeterli yem var ({min_days_remaining:.1f} gün). Sonraki sipariş: {order_quantity} ton"
        
        # Check if it's a weekday (Monday-Friday)
        today = datetime.now()
        day_of_week = today.weekday()  # 0=Monday, 4=Friday, 5=Saturday, 6=Sunday
        
        if day_of_week >= 5:  # Weekend
            recommendation["warnings"].append("⚠️ Bugün hafta sonu! Sipariş Pazartesi'ye ertelendi.")
        
        return recommendation
    
    def calculate_feed_projection(self, current_day: int, days_ahead: int = 7) -> pd.DataFrame:
        """Project feed consumption for next N days"""
        
        projections = []
        
        for day_offset in range(days_ahead):
            projection_day = current_day + day_offset
            
            if projection_day > 42:
                break
            
            day_str = str(projection_day)
            daily_per_bird = self.get_daily_consumption_per_bird(projection_day)
            feed_type = self.get_feed_type_for_day(projection_day)
            
            projections.append({
                "Gün": projection_day,
                "Tarih": (datetime.now() + timedelta(days=day_offset)).strftime('%Y-%m-%d'),
                "Yem Tipi": feed_type,
                "Günlük Tüketim (g/hayvan)": daily_per_bird * 1000,
                "FCR Hedefi": self.banvit_data.get(day_str, {}).get('fcr', 0),
                "Ross Hedef (g)": self.banvit_data.get(day_str, {}).get('canlı_ağırlık', 0)
            })
        
        return pd.DataFrame(projections)
    
    def get_order_history(self) -> pd.DataFrame:
        """Get feed order history"""
        
        orders = []
        for invoice in self.farm_data.get('feed_invoices', []):
            orders.append({
                "Tarih": invoice.get('date', 'N/A'),
                "Yem Tipi": invoice.get('feed_type', 'N/A'),
                "Miktar (kg)": invoice.get('quantity', 0),
                "Tedarikçi": invoice.get('supplier', 'N/A'),
                "Teslim Tarihi": invoice.get('delivery_date', 'N/A')
            })
        
        return pd.DataFrame(orders) if orders else pd.DataFrame()


def render_feed_logistics_page(farm_data, banvit_data, current_day, live_birds_per_house):
    """Render the feed logistics management page"""
    
    st.title("🚛 Yem Lojistiği ve Sipariş Yönetimi")
    
    logistics = FeedLogistics(farm_data, banvit_data)
    
    # Generate recommendation
    recommendation = logistics.generate_order_recommendation(current_day, farm_data)
    
    # Display critical alerts
    if recommendation["critical_alerts"]:
        for alert in recommendation["critical_alerts"]:
            st.error(alert)
    
    if recommendation["warnings"]:
        for warning in recommendation["warnings"]:
            st.warning(warning)
    
    st.markdown("---")
    
    # Overall recommendation
    st.subheader("📋 Genel Sipariş Önerisi")
    st.info(recommendation["overall_recommendation"])
    
    st.markdown("---")
    
    # House-by-house analysis
    st.subheader("🏠 Kümes Bazında Analiz")
    
    for house_name, house_rec in recommendation["houses"].items():
        with st.expander(f"{house_name} - {house_rec['days_remaining']:.1f} gün yem kaldı"):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Canlı Hayvan", f"{house_rec['live_birds']:,}")
            with col2:
                st.metric("Siloda Kalan (kg)", f"{house_rec['silo_remaining_kg']:,.0f}")
            with col3:
                st.metric("Günlük Tüketim (kg)", f"{house_rec['daily_consumption_kg']:.0f}")
            with col4:
                st.metric("Silo Kapasitesi (ton)", f"{house_rec['silo_capacity_tons']}")
            
            st.write(f"**Yem Tipi**: {house_rec['feed_type']}")
            st.write(f"**Stale Risk**: {house_rec['stale_message']}")
            st.write(f"**Taşma Riski**: {house_rec['overflow_message']}")
            
            if house_rec["needs_order"]:
                st.error(f"⚠️ Bu kümese sipariş gerekli!")
    
    st.markdown("---")
    
    # Feed consumption projection
    st.subheader("📊 Yem Tüketim Projeksiyonu (Sonraki 7 Gün)")
    
    projection_df = logistics.calculate_feed_projection(current_day, 7)
    st.dataframe(projection_df, use_container_width=True)
    
    st.markdown("---")
    
    # Order history
    st.subheader("📜 Sipariş Geçmişi")
    
    order_history = logistics.get_order_history()
    if not order_history.empty:
        st.dataframe(order_history, use_container_width=True)
    else:
        st.info("Henüz sipariş geçmişi yok.")
    
    st.markdown("---")
    
    # Manual order entry
    st.subheader("➕ Yeni Sipariş Ekle")
    
    with st.form("new_order_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            order_date = st.date_input("Sipariş Tarihi")
            feed_type = st.selectbox("Yem Tipi", ["Civciv", "Büyütme", "Bitirme"])
        
        with col2:
            quantity = st.number_input("Miktar (kg)", min_value=0, step=1000)
            supplier = st.text_input("Tedarikçi", "Banvit")
        
        delivery_date = st.date_input("Teslim Tarihi")
        
        if st.form_submit_button("➕ Sipariş Ekle", use_container_width=True):
            new_order = {
                "date": order_date.isoformat(),
                "feed_type": feed_type,
                "quantity": quantity,
                "supplier": supplier,
                "delivery_date": delivery_date.isoformat()
            }
            
            if 'feed_invoices' not in farm_data:
                farm_data['feed_invoices'] = []
            
            farm_data['feed_invoices'].append(new_order)
            st.success(f"✅ {quantity}kg {feed_type} yemi sipariş eklendi!")
