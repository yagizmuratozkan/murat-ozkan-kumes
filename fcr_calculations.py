
def calculate_fcr(day_data, settings):
    """
    FCR = (Toplam Yem - Kalan Yem) / Toplam Canli Kutle
    """
    fcr_results = {}
    
    for kumes_id in ["1", "2", "3", "4"]:
        total_feed = day_data.get("feed_consumption", {}).get(kumes_id, 0)
        remaining_feed = day_data.get("silo_remaining", {}).get(kumes_id, 0)
        
        # Consumed feed
        consumed_feed = total_feed - remaining_feed if total_feed > remaining_feed else 0
        
        # Live weight
        live_weight = day_data.get("weight", {}).get(kumes_id, 0)
        
        # Calculate FCR
        if live_weight > 0:
            fcr = consumed_feed / (live_weight / 1000)  # Convert grams to kg
        else:
            fcr = 0
        
        fcr_results[kumes_id] = {
            "consumed_feed": consumed_feed,
            "live_weight": live_weight,
            "fcr": round(fcr, 2)
        }
    
    return fcr_results

def calculate_mortality_rate(day_data, settings):
    """
    Mortalite Orani = (Olem Hayvan Sayisi / Baslangic Hayvan Sayisi) * 100
    """
    mortality = {}
    
    for kumes_id in ["1", "2", "3", "4"]:
        deaths = day_data.get("deaths", {}).get(kumes_id, 0)
        capacity = settings["kumes"][kumes_id]["capacity"]
        
        mortality_rate = (deaths / capacity * 100) if capacity > 0 else 0
        
        mortality[kumes_id] = {
            "deaths": deaths,
            "capacity": capacity,
            "mortality_rate": round(mortality_rate, 2)
        }
    
    return mortality

def calculate_feed_order_alert(silo_status, daily_consumption, days_remaining):
    """
    Yem Siparis Uyarisi:
    - Silo kalan yem < 3 gunluk tuketim ise UYARI
    - Siparis miktari = 9 cuval = 450 kg (standart)
    """
    alerts = {}
    
    for kumes_id in ["1", "2", "3", "4"]:
        current_silo = silo_status[kumes_id]["current"]
        daily_feed = daily_consumption.get(kumes_id, 0)
        three_day_consumption = daily_feed * 3
        
        if current_silo < three_day_consumption:
            order_quantity = 450  # 9 cuval
            alerts[kumes_id] = {
                "status": "UYARI",
                "current_silo": current_silo,
                "three_day_need": three_day_consumption,
                "order_quantity": order_quantity,
                "message": f"Kumes {kumes_id}: {order_quantity} kg yem siparis etmelisiniz"
            }
        else:
            alerts[kumes_id] = {
                "status": "OK",
                "current_silo": current_silo,
                "three_day_need": three_day_consumption,
                "order_quantity": 0,
                "message": f"Kumes {kumes_id}: Yem stogu yeterli"
            }
    
    return alerts
