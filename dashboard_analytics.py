# Dashboard and Analytics Module
# Comprehensive KPI tracking, performance visualization, and trend analysis

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import numpy as np
from typing import Dict

class DashboardAnalytics:
    """Advanced dashboard and analytics system"""
    
    def __init__(self, farm_data, banvit_data, current_day):
        self.farm_data = farm_data
        self.banvit_data = banvit_data
        self.current_day = current_day
        self.settings = farm_data['settings']
    
    def get_historical_data(self) -> pd.DataFrame:
        """Extract historical daily data"""
        data = []
        for day in range(1, self.current_day + 1):
            day_key = f'day_{day}'
            day_data = self.farm_data.get('daily_data', {}).get(day_key, {})
            
            total_live = 0
            total_deaths = 0
            total_weight = 0
            house_count = 0
            
            for house_name in self.settings['houses'].keys():
                house_data = day_data.get(house_name, {})
                total_live += house_data.get('live', 0)
                total_deaths += house_data.get('deaths', 0)
                total_weight += house_data.get('avg_weight', 0)
                house_count += 1
            
            if house_count > 0:
                avg_weight = total_weight / house_count
            else:
                avg_weight = 0
            
            # Get Ross targets
            day_str = str(day)
            ross_weight = self.banvit_data.get(day_str, {}).get('canlı_ağırlık', 0)
            ross_fcr = self.banvit_data.get(day_str, {}).get('fcr', 0)
            
            # Calculate FCR
            total_feed_consumed = sum([
                day_data.get(h, {}).get('feed_consumed', 0) 
                for h in self.settings['houses'].keys()
            ])
            
            if total_live > 0 and total_feed_consumed > 0:
                fcr = total_feed_consumed / (total_live * avg_weight / 1000) if avg_weight > 0 else 0
            else:
                fcr = 0
            
            # Calculate death rate
            initial_birds = sum([h['chick_count'] for h in self.settings['houses'].values()])
            death_rate = (total_deaths / initial_birds * 100) if initial_birds > 0 else 0
            
            data.append({
                'day': day,
                'date': (datetime.now() - timedelta(days=self.current_day - day)).date(),
                'live_birds': total_live,
                'deaths': total_deaths,
                'death_rate': death_rate,
                'avg_weight': avg_weight,
                'ross_weight': ross_weight,
                'weight_deviation': ((avg_weight - ross_weight) / ross_weight * 100) if ross_weight > 0 else 0,
                'fcr': fcr,
                'ross_fcr': ross_fcr,
                'fcr_deviation': fcr - ross_fcr if ross_fcr > 0 else 0
            })
        
        return pd.DataFrame(data)
    
    def calculate_kpis(self) -> Dict:
        """Calculate key performance indicators"""
        
        df = self.get_historical_data()
        
        if df.empty:
            return {}
        
        latest = df.iloc[-1]
        
        # Calculate trends
        if len(df) > 1:
            prev = df.iloc[-2]
            weight_trend = latest['avg_weight'] - prev['avg_weight']
            fcr_trend = latest['fcr'] - prev['fcr']
        else:
            weight_trend = 0
            fcr_trend = 0
        
        # Calculate cumulative metrics
        total_deaths = df['deaths'].sum()
        initial_birds = sum([h['chick_count'] for h in self.settings['houses'].values()])
        cumulative_death_rate = (total_deaths / initial_birds * 100) if initial_birds > 0 else 0
        
        # Calculate health score
        health_score = self._calculate_health_score(df)
        
        # Performance vs targets
        avg_weight_vs_target = latest['weight_deviation'] if not df.empty else 0
        fcr_vs_target = latest['fcr_deviation'] if not df.empty else 0
        
        return {
            'current_day': self.current_day,
            'live_birds': int(latest['live_birds']) if not df.empty else 0,
            'cumulative_deaths': int(total_deaths),
            'cumulative_death_rate': cumulative_death_rate,
            'avg_weight': latest['avg_weight'] if not df.empty else 0,
            'ross_weight': latest['ross_weight'] if not df.empty else 0,
            'weight_vs_target': avg_weight_vs_target,
            'weight_trend': weight_trend,
            'fcr': latest['fcr'] if not df.empty else 0,
            'ross_fcr': latest['ross_fcr'] if not df.empty else 0,
            'fcr_vs_target': fcr_vs_target,
            'fcr_trend': fcr_trend,
            'health_score': health_score,
            'performance_grade': self._get_performance_grade(health_score)
        }
    
    def _calculate_health_score(self, df: pd.DataFrame) -> float:
        """Calculate overall health score (0-100)"""
        if df.empty:
            return 50
        
        latest = df.iloc[-1]
        score = 100
        
        # Death rate impact (max -30 points)
        if latest['death_rate'] > 2:
            score -= 30
        elif latest['death_rate'] > 1:
            score -= 20
        elif latest['death_rate'] > 0.5:
            score -= 10
        
        # Weight deviation impact (max -25 points)
        weight_dev = abs(latest['weight_deviation'])
        if weight_dev > 15:
            score -= 25
        elif weight_dev > 10:
            score -= 15
        elif weight_dev > 5:
            score -= 10
        
        # FCR deviation impact (max -20 points)
        fcr_dev = latest['fcr_deviation']
        if fcr_dev > 0.15:
            score -= 20
        elif fcr_dev > 0.1:
            score -= 15
        elif fcr_dev > 0.05:
            score -= 10
        
        # Trend impact (max -15 points)
        if latest['fcr'] > latest['ross_fcr'] and len(df) > 1:
            fcr_trend = latest['fcr'] - df.iloc[-2]['fcr']
            if fcr_trend > 0.05:
                score -= 10
        
        return max(0, min(100, score))
    
    def _get_performance_grade(self, score: float) -> str:
        """Get performance grade based on health score"""
        if score >= 90:
            return "🌟 Mükemmel"
        elif score >= 80:
            return "⭐ Çok İyi"
        elif score >= 70:
            return "✅ İyi"
        elif score >= 60:
            return "⚠️ Orta"
        elif score >= 50:
            return "🟡 Zayıf"
        else:
            return "🔴 Kritik"
    
    def create_weight_chart(self) -> go.Figure:
        """Create weight progress chart"""
        df = self.get_historical_data()
        
        if df.empty:
            return go.Figure()
        
        fig = go.Figure()
        
        # Actual weight
        fig.add_trace(go.Scatter(
            x=df['day'],
            y=df['avg_weight'],
            mode='lines+markers',
            name='Gerçek Ağırlık',
            line=dict(color='#1f77b4', width=3),
            marker=dict(size=6)
        ))
        
        # Ross target
        fig.add_trace(go.Scatter(
            x=df['day'],
            y=df['ross_weight'],
            mode='lines',
            name='Ross Hedefi',
            line=dict(color='#ff7f0e', width=2, dash='dash'),
            marker=dict(size=4)
        ))
        
        # Upper and lower bounds (±10%)
        upper_bound = df['ross_weight'] * 1.1
        lower_bound = df['ross_weight'] * 0.9
        
        fig.add_trace(go.Scatter(
            x=df['day'],
            y=upper_bound,
            fill=None,
            mode='lines',
            line_color='rgba(0,0,0,0)',
            showlegend=False
        ))
        
        fig.add_trace(go.Scatter(
            x=df['day'],
            y=lower_bound,
            fill='tonexty',
            mode='lines',
            line_color='rgba(0,0,0,0)',
            name='Kabul Aralığı (±10%)',
            fillcolor='rgba(255,0,0,0.1)'
        ))
        
        fig.update_layout(
            title='📊 Canlı Ağırlık Gelişimi',
            xaxis_title='Gün',
            yaxis_title='Ağırlık (g)',
            hovermode='x unified',
            template='plotly_white'
        )
        
        return fig
    
    def create_fcr_chart(self) -> go.Figure:
        """Create FCR progress chart"""
        df = self.get_historical_data()
        
        if df.empty:
            return go.Figure()
        
        fig = go.Figure()
        
        # Actual FCR
        fig.add_trace(go.Scatter(
            x=df['day'],
            y=df['fcr'],
            mode='lines+markers',
            name='Gerçek FCR',
            line=dict(color='#2ca02c', width=3),
            marker=dict(size=6)
        ))
        
        # Ross target
        fig.add_trace(go.Scatter(
            x=df['day'],
            y=df['ross_fcr'],
            mode='lines',
            name='Ross Hedefi',
            line=dict(color='#d62728', width=2, dash='dash'),
            marker=dict(size=4)
        ))
        
        fig.update_layout(
            title='📈 Yem Dönüşüm Oranı (FCR)',
            xaxis_title='Gün',
            yaxis_title='FCR',
            hovermode='x unified',
            template='plotly_white'
        )
        
        return fig
    
    def create_mortality_chart(self) -> go.Figure:
        """Create mortality rate chart"""
        df = self.get_historical_data()
        
        if df.empty:
            return go.Figure()
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=df['day'],
            y=df['death_rate'],
            name='Günlük Ölüm Oranı (%)',
            marker=dict(color=df['death_rate'], colorscale='RdYlGn_r', showscale=True)
        ))
        
        # Add threshold line
        fig.add_hline(y=1, line_dash="dash", line_color="orange", 
                      annotation_text="Uyarı Eşiği (1%)", annotation_position="right")
        fig.add_hline(y=2, line_dash="dash", line_color="red", 
                      annotation_text="Kritik Eşiği (2%)", annotation_position="right")
        
        fig.update_layout(
            title='💀 Günlük Ölüm Oranı',
            xaxis_title='Gün',
            yaxis_title='Ölüm Oranı (%)',
            template='plotly_white',
            showlegend=False
        )
        
        return fig
    
    def create_performance_summary(self) -> pd.DataFrame:
        """Create performance summary table"""
        df = self.get_historical_data()
        
        if df.empty:
            return pd.DataFrame()
        
        summary = pd.DataFrame({
            'Metrik': [
                'Canlı Hayvan Sayısı',
                'Toplam Ölüm',
                'Kümülatif Ölüm Oranı',
                'Ortalama Ağırlık',
                'Ross Hedefi',
                'Ağırlık Sapması',
                'FCR',
                'Ross FCR Hedefi',
                'FCR Sapması',
                'Sağlık Puanı'
            ],
            'Değer': [
                f"{df.iloc[-1]['live_birds']:,.0f}",
                f"{df['deaths'].sum():,.0f}",
                f"%{df.iloc[-1]['death_rate']:.2f}",
                f"{df.iloc[-1]['avg_weight']:.0f}g",
                f"{df.iloc[-1]['ross_weight']:.0f}g",
                f"{df.iloc[-1]['weight_deviation']:.1f}%",
                f"{df.iloc[-1]['fcr']:.2f}",
                f"{df.iloc[-1]['ross_fcr']:.2f}",
                f"{df.iloc[-1]['fcr_deviation']:.2f}",
                f"{self._calculate_health_score(df):.1f}/100"
            ]
        })
        
        return summary


def render_dashboard(farm_data, banvit_data, current_day):
    """Render the main dashboard"""
    
    st.set_page_config(page_title="Çiftlik Dashboard", layout="wide")
    
    analytics = DashboardAnalytics(farm_data, banvit_data, current_day)
    
    # Get KPIs
    kpis = analytics.calculate_kpis()
    
    if not kpis:
        st.warning("Henüz veri yok. Lütfen günlük verileri girin.")
        return
    
    # Header
    st.title("📊 Çiftlik Dashboard")
    st.subheader(f"Gün {kpis['current_day']}/42 - {kpis['performance_grade']}")
    
    st.markdown("---")
    
    # KPI Cards
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            "Canlı Hayvan",
            f"{kpis['live_birds']:,}",
            f"{-kpis['cumulative_deaths']:,} ölüm"
        )
    
    with col2:
        st.metric(
            "Ölüm Oranı",
            f"%{kpis['cumulative_death_rate']:.2f}",
            delta=f"Hedef: <1%"
        )
    
    with col3:
        weight_delta = f"{kpis['weight_trend']:+.0f}g" if kpis['weight_trend'] != 0 else "Sabit"
        st.metric(
            "Ağırlık",
            f"{kpis['avg_weight']:.0f}g",
            delta=weight_delta,
            delta_color="off"
        )
    
    with col4:
        fcr_delta = f"{kpis['fcr_trend']:+.2f}" if kpis['fcr_trend'] != 0 else "Sabit"
        st.metric(
            "FCR",
            f"{kpis['fcr']:.2f}",
            delta=fcr_delta,
            delta_color="inverse"
        )
    
    with col5:
        st.metric(
            "Sağlık Puanı",
            f"{kpis['health_score']:.1f}/100",
            delta=f"Hedef: >90"
        )
    
    st.markdown("---")
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.plotly_chart(analytics.create_weight_chart(), use_container_width=True)
    
    with col2:
        st.plotly_chart(analytics.create_fcr_chart(), use_container_width=True)
    
    st.plotly_chart(analytics.create_mortality_chart(), use_container_width=True)
    
    st.markdown("---")
    
    # Performance Summary
    st.subheader("📋 Performans Özeti")
    summary_df = analytics.create_performance_summary()
    st.dataframe(summary_df, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    
    # Alerts and Recommendations
    st.subheader("⚠️ Uyarılar ve Öneriler")
    
    alerts = []
    
    if kpis['cumulative_death_rate'] > 2:
        alerts.append(("🔴", "KRİTİK", f"Ölüm oranı %{kpis['cumulative_death_rate']:.2f} - Acil veteriner müdahalesi gerekli!"))
    elif kpis['cumulative_death_rate'] > 1:
        alerts.append(("🟡", "UYARI", f"Ölüm oranı %{kpis['cumulative_death_rate']:.2f} - Tedavi başla"))
    
    if abs(kpis['weight_vs_target']) > 15:
        alerts.append(("🔴", "KRİTİK", f"Ağırlık hedeften %{kpis['weight_vs_target']:.1f} sapma"))
    elif abs(kpis['weight_vs_target']) > 10:
        alerts.append(("🟡", "UYARI", f"Ağırlık hedeften %{kpis['weight_vs_target']:.1f} sapma"))
    
    if kpis['fcr_vs_target'] > 0.15:
        alerts.append(("🔴", "KRİTİK", f"FCR hedeften +{kpis['fcr_vs_target']:.2f} sapma"))
    elif kpis['fcr_vs_target'] > 0.05:
        alerts.append(("🟡", "UYARI", f"FCR hedeften +{kpis['fcr_vs_target']:.2f} sapma"))
    
    if not alerts:
        st.success("✅ Tüm parametreler normal!")
    else:
        for icon, level, message in alerts:
            if level == "KRİTİK":
                st.error(f"{icon} {level}: {message}")
            else:
                st.warning(f"{icon} {level}: {message}")
