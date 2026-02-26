from flask import Flask, render_template, request, redirect, url_for, jsonify
import requests
from datetime import datetime, timedelta
import urllib.parse
import os
import json
import init_db

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

# --- PocketBase Yardımcı Fonksiyonları ---
def get_cases(filter_query=""):
    url = f"{POCKETBASE_URL}/api/collections/cases/records"
    params = {'sort': '-created'}
    if filter_query:
        params['filter'] = filter_query

    try:
        response = requests.get(url, params=params, timeout=5).json()
        return response.get('items', [])
    except Exception as e:
        print(f"PocketBase Hatası: {e}")
        return []

def get_case(case_id):
    url = f"{POCKETBASE_URL}/api/collections/cases/records/{case_id}"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"PocketBase Hatası: {e}")
    return None

def create_case(data):
    url = f"{POCKETBASE_URL}/api/collections/cases/records"
    try:
        response = requests.post(url, json=data, timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f"PocketBase Hatası: {e}")
        return False

def update_case(case_id, data):
    url = f"{POCKETBASE_URL}/api/collections/cases/records/{case_id}"
    try:
        response = requests.patch(url, json=data, timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f"PocketBase Hatası: {e}")
        return False

def delete_case(case_id):
    url = f"{POCKETBASE_URL}/api/collections/cases/records/{case_id}"
    try:
        response = requests.delete(url, timeout=5)
        return response.status_code == 204
    except Exception as e:
        print(f"PocketBase Hatası: {e}")
        return False

# --- Şehir Koordinatları (Basit Harita Verisi) ---
CITY_COORDS = {
    'Adana': {'lat': 37.0000, 'lon': 35.3213},
    'Ankara': {'lat': 39.9334, 'lon': 32.8597},
    'Antalya': {'lat': 36.8969, 'lon': 30.7133},
    'Bursa': {'lat': 40.1828, 'lon': 29.0667},
    'Diyarbakır': {'lat': 37.9144, 'lon': 40.2306},
    'Erzurum': {'lat': 39.9043, 'lon': 41.2679},
    'Eskişehir': {'lat': 39.7767, 'lon': 30.5206},
    'Gaziantep': {'lat': 37.0662, 'lon': 37.3833},
    'İstanbul': {'lat': 41.0082, 'lon': 28.9784},
    'İzmir': {'lat': 38.4192, 'lon': 27.1287},
    'Kayseri': {'lat': 38.7312, 'lon': 35.4787},
    'Kocaeli': {'lat': 40.8533, 'lon': 29.8815},
    'Konya': {'lat': 37.8714, 'lon': 32.4846},
    'Mersin': {'lat': 36.8000, 'lon': 34.6333},
    'Sakarya': {'lat': 40.7569, 'lon': 30.3783},
    'Samsun': {'lat': 41.2928, 'lon': 36.3313},
    'Şanlıurfa': {'lat': 37.1591, 'lon': 38.7969},
    'Trabzon': {'lat': 41.0027, 'lon': 39.7168},
    'Van': {'lat': 38.4891, 'lon': 43.4089},
    # Diğer şehirler eklenebilir veya geocoding servisi kullanılabilir
}

# --- Rota Optimizasyon Algoritması ---
def calculate_route(selected_case_ids, start_city="Bursa", start_date_str=None):
    # 1. Seçilen dosyaları çek
    cases = []
    for case_id in selected_case_ids:
        case = get_case(case_id)
        if case:
            cases.append(case)

    if not cases:
        return []

    # 2. Şehirlere göre grupla
    grouped_destinations = {}
    
    for case in cases:
        city = case.get('city', '')
        # Şehir koordinatlarını bul, yoksa varsayılan (0,0) - gerçek uygulamada geocoding lazım
        coords = CITY_COORDS.get(city, {'lat': 0, 'lon': 0})
        # Eğer kayıtta lat/lon varsa onu kullan
        if case.get('lat') and case.get('lon'):
             coords = {'lat': case.get('lat'), 'lon': case.get('lon')}
        
        city_key = city # Basitlik için şehir bazlı gruplama

        if city_key not in grouped_destinations:
            grouped_destinations[city_key] = {
                'name': city, # Adliye yerine şehir ismi kullanıyoruz şimdilik
                'city': city,
                'lat': coords['lat'],
                'lon': coords['lon'],
                'cases': [],
                'case_count': 0
            }
        
        grouped_destinations[city_key]['cases'].append(f"{case.get('case_no')} ({case.get('client')})")
        grouped_destinations[city_key]['case_count'] += 1

    # Liste haline getir
    destinations = []
    for dest in grouped_destinations.values():
        dest['cases_str'] = ", ".join(dest['cases'])
        destinations.append(dest)

    # 3. Başlangıç Ayarları
    start_coords = CITY_COORDS.get(start_city, CITY_COORDS.get('Bursa'))
    current_location = {'name': f'{start_city} Ofis', 'lat': start_coords['lat'], 'lon': start_coords['lon']}
    
    if start_date_str:
        try:
            # "2026-W09" formatından (Screenshot'taki hafta seçimi gibi) veya normal tarih
            if 'W' in start_date_str:
                 current_time = datetime.strptime(start_date_str + '-1', "%Y-W%W-%w")
            else:
                 current_time = datetime.strptime(start_date_str, "%Y-%m-%d")
        except:
            current_time = datetime.now()
    else:
        current_time = datetime.now()

    current_time = current_time.replace(hour=9, minute=0, second=0, microsecond=0)

    # Hafta sonu kontrolü
    if current_time.weekday() >= 5: 
        current_time += timedelta(days=(7 - current_time.weekday()))

    unvisited = destinations.copy()
    route_plan = []
    step = 1

    # 4. Greedy Rota Hesabı
    while unvisited:
        best_stop = None
        shortest_dur = float('inf')
        
        for dest in unvisited:
            # Eğer koordinat yoksa (0,0), rastgele bir mesafe ver veya hata yönet
            if dest['lat'] == 0 and dest['lon'] == 0:
                 dist, dur = 100, 60 # Dummy values
            else:
                dist, dur = get_osrm_route(current_location['lat'], current_location['lon'], dest['lat'], dest['lon'])

            if dur < shortest_dur:
                shortest_dur = dur
                best_stop = dest
                best_stop['distance'] = dist
                best_stop['travel_dur'] = dur

        if not best_stop:
            break

        # Varış, İşlem, Çıkış hesapları
        arrival_time = current_time + timedelta(minutes=best_stop['travel_dur'])
        
        # Mesai kontrolü (09-17)
        if arrival_time.hour >= 17 or arrival_time.hour < 9:
            arrival_time = arrival_time.replace(hour=9, minute=0) + timedelta(days=1)
            if arrival_time.weekday() >= 5:
                arrival_time += timedelta(days=(7 - arrival_time.weekday()))

        departure_time = arrival_time + timedelta(minutes=(best_stop['case_count'] * 45))
        
        if departure_time.hour >= 17:
            overtime = departure_time - arrival_time.replace(hour=17, minute=0)
            departure_time = departure_time.replace(hour=9, minute=0) + timedelta(days=1) + overtime
            if departure_time.weekday() >= 5:
                departure_time += timedelta(days=(7 - departure_time.weekday()))

        route_plan.append({
            'step': step,
            'city': best_stop['city'],
            'location_name': best_stop['name'],
            'distance': round(best_stop['distance'], 1),
            'arrival': arrival_time.strftime('%d.%m.%Y %H:%M'),
            'departure': departure_time.strftime('%d.%m.%Y %H:%M'),
            'cases': best_stop['cases_str']
        })

        current_location = best_stop
        current_time = departure_time
        unvisited.remove(best_stop)
        step += 1

    return route_plan

# --- Web Yönlendirmeleri ---

@app.route('/')
def index():
    # Dashboard sayfası
    filter_q = request.args.get('search', '')

    # İstatistikler için tüm verileri çek (filtresiz)
    all_cases = get_cases()

    total_files = len(all_cases)
    cities = set(c.get('city') for c in all_cases if c.get('city'))
    active_files = sum(1 for c in all_cases if c.get('status') == 'Aktif')
    urgent_files = sum(1 for c in all_cases if c.get('priority') == 'Acil')
    hearings = sum(1 for c in all_cases if c.get('status') == 'Duruşma Bekliyor') # Basit varsayım

    # Tablo verisi (varsa arama filtresi ile)
    pb_filter = ""
    if filter_q:
        # PocketBase filter syntax: (field ~ 'value')
        pb_filter = f"(case_no~'{filter_q}' || client~'{filter_q}' || city~'{filter_q}')"

    table_cases = get_cases(pb_filter) if filter_q else all_cases

    return render_template('dashboard.html',
                           cases=table_cases,
                           stats={
                               'total': total_files,
                               'cities': len(cities),
                               'urgent': urgent_files,
                               'hearings': hearings
                           })

@app.route('/rota')
def rota_page():
    # Rota Planlama sayfası
    cases = get_cases("(status='Aktif' || status='Duruşma Bekliyor')")
    return render_template('route.html', cases=cases)

@app.route('/api/cases', methods=['POST'])
def api_create_case():
    data = request.form.to_dict()
    # Checkbox handling if needed, or select inputs
    success = create_case(data)
    if success:
        return redirect(url_for('index'))
    return "Hata oluştu", 500

@app.route('/api/cases/delete/<case_id>', methods=['POST'])
def api_delete_case(case_id):
    delete_case(case_id)
    return redirect(url_for('index'))

@app.route('/api/planla', methods=['POST'])
def api_planla():
    selected_ids = request.form.getlist('selected_cases')
    start_date = request.form.get('start_date')
    start_city = request.form.get('start_city', 'Bursa')

    route_data = calculate_route(selected_ids, start_city, start_date)

    # AJAX ile dönüyorsa JSON, form submit ise render
    # Screenshot'ta sayfa yenilenmeden sağ tarafta çıkıyor gibi,
    # ama basitlik için template render yapabiliriz veya json dönebiliriz.
    # Şimdilik JSON dönelim, frontend JS ile basarız.
    return jsonify(route_data)

@app.route('/init-db')
def trigger_init_db():
    init_db.init_pocketbase()
    return "DB Init Triggered", 200

if __name__ == '__main__':
    # İlk açılışta DB init deneyelim (background thread veya blocking)
    try:
        init_db.init_pocketbase()
    except Exception as e:
        print(f"Init DB Warning: {e}")

    app.run(host='0.0.0.0', port=5000, debug=True)
