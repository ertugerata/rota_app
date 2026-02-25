from flask import Flask, render_template
import requests
from datetime import datetime, timedelta
import urllib.parse
import os

app = Flask(__name__)

# Docker ortamında "http://pocketbase:8090" olarak çalışır, lokalde ise "http://127.0.0.1:8090"
POCKETBASE_URL = os.environ.get("POCKETBASE_URL", "http://127.0.0.1:8090")

# --- OSRM API Karayolu Hesaplama ---
def get_osrm_route(lat1, lon1, lat2, lon2):
    url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"
    try:
        response = requests.get(url, timeout=5).json()
        if response.get("code") == "Ok":
            distance_km = response["routes"][0]["distance"] / 1000.0
            duration_min = response["routes"][0]["duration"] / 60.0
            return distance_km, duration_min
    except Exception as e:
        print(f"OSRM Hatası: {e}")
    return float('inf'), float('inf')

# --- PocketBase Veri Çekme ve Gruplama ---
def get_open_cases_from_pb():
    # Sadece durumu 'Açık' olan dosyaları çek ve ilişkili adliye bilgilerini (courthouse_id) genişlet
    filter_query = urllib.parse.quote("(status='Açık')")
    url = f"{POCKETBASE_URL}/api/collections/cases/records?filter={filter_query}&expand=courthouse_id"
    
    try:
        response = requests.get(url, timeout=5).json()
        records = response.get('items', [])
    except Exception as e:
        print(f"PocketBase Hatası: {e}")
        return []

    # Aynı adliyeye ait dosyaları grupla
    grouped_destinations = {}
    
    for record in records:
        if 'expand' not in record or 'courthouse_id' not in record['expand']:
            continue
            
        ch = record['expand']['courthouse_id']
        ch_id = ch['id']
        
        if ch_id not in grouped_destinations:
            grouped_destinations[ch_id] = {
                'name': ch['name'],
                'city': ch['city'],
                'lat': ch['lat'],
                'lon': ch['lon'],
                'cases': [],
                'case_count': 0
            }
        
        grouped_destinations[ch_id]['cases'].append(record['case_no'])
        grouped_destinations[ch_id]['case_count'] += 1

    # Rota algoritmasının beklediği formata çevir
    destinations = []
    for dest in grouped_destinations.values():
        dest['cases'] = ", ".join(dest['cases'])
        destinations.append(dest)
        
    return destinations

# --- Rota Optimizasyon Algoritması ---
def calculate_route():
    destinations = get_open_cases_from_pb()

    if not destinations:
        return []

    # Başlangıç Noktası: Bursa
    current_location = {'name': 'Bursa Ofis', 'lat': 40.1828, 'lon': 29.0667}
    current_time = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    
    # Hafta sonu kontrolü (Cumartesi veya Pazar ise Pazartesi sabahına atla)
    if current_time.weekday() >= 5: 
        current_time += timedelta(days=(7 - current_time.weekday()))

    unvisited = destinations.copy()
    route_plan = []
    step = 1

    while unvisited:
        best_stop = None
        shortest_dur = float('inf')
        
        # Gidilecek en iyi (zaman olarak en yakın) adliyeyi bul
        for dest in unvisited:
            dist, dur = get_osrm_route(current_location['lat'], current_location['lon'], dest['lat'], dest['lon'])
            if dur < shortest_dur:
                shortest_dur = dur
                best_stop = dest
                best_stop['distance'] = dist
                best_stop['travel_dur'] = dur

        if not best_stop:
            break

        # Varış saati hesaplama
        arrival_time = current_time + timedelta(minutes=best_stop['travel_dur'])
        
        # Mesai dışı sarkma kontrolü (09:00 - 17:00 arası)
        if arrival_time.hour >= 17 or arrival_time.hour < 9:
            arrival_time = arrival_time.replace(hour=9, minute=0) + timedelta(days=1)
            # Eğer ertesi gün hafta sonuna denk geliyorsa Pazartesiye atla
            if arrival_time.weekday() >= 5:
                arrival_time += timedelta(days=(7 - arrival_time.weekday()))

        # Adliyedeki işlem süresi (Dosya başı 45 dakika varsayımı)
        departure_time = arrival_time + timedelta(minutes=(best_stop['case_count'] * 45))
        
        # Eğer işlem süresi mesaiyi (17:00) aşıyorsa, kalan süreyi ertesi gün sabahına devret
        if departure_time.hour >= 17:
            overtime = departure_time - arrival_time.replace(hour=17, minute=0)
            departure_time = departure_time.replace(hour=9, minute=0) + timedelta(days=1) + overtime
            if departure_time.weekday() >= 5:
                departure_time += timedelta(days=(7 - departure_time.weekday()))

        route_plan.append({
            'step': step,
            'city': best_stop['city'],
            'courthouse': best_stop['name'],
            'distance': round(best_stop['distance'], 1),
            'arrival': arrival_time.strftime('%d.%m.%Y %H:%M'),
            'departure': departure_time.strftime('%d.%m.%Y %H:%M'),
            'cases': best_stop['cases']
        })

        current_location = best_stop
        current_time = departure_time
        unvisited.remove(best_stop)
        step += 1

    return route_plan

# --- Web Yönlendirmeleri ---
@app.route('/')
def index():
    return render_template('index.html', route=None)

@app.route('/planla', methods=['POST'])
def planla():
    route_data = calculate_route()
    return render_template('index.html', route=route_data)

if __name__ == '__main__':
    # Docker içerisinde çalışacağı için host '0.0.0.0' olmalı
    app.run(host='0.0.0.0', port=5000)