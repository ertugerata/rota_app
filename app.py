from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
import requests
from datetime import datetime, timedelta
import os
import json
import time
from sqlalchemy import or_

app = Flask(__name__)

# PostgreSQL Konfigürasyonu
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL", "postgresql://admin:AvukatRota2026!@localhost:5432/hukukburosu")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- Veritabanı Modelleri ---
class Case(db.Model):
    __tablename__ = 'cases'
    id = db.Column(db.Integer, primary_key=True)
    case_no = db.Column(db.String(50), nullable=False)
    client = db.Column(db.String(100))
    opponent = db.Column(db.String(100))
    city = db.Column(db.String(50), nullable=False)
    district = db.Column(db.String(50))
    court_office = db.Column(db.String(100))
    case_type = db.Column(db.String(50))
    status = db.Column(db.String(50))
    priority = db.Column(db.String(50))
    follower_lawyer = db.Column(db.String(100))
    authorized_lawyer = db.Column(db.String(100))
    due_date = db.Column(db.Date, nullable=True)
    description = db.Column(db.Text)
    lat = db.Column(db.Float, nullable=True)
    lon = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'case_no': self.case_no,
            'client': self.client,
            'opponent': self.opponent,
            'city': self.city,
            'district': self.district,
            'court_office': self.court_office,
            'case_type': self.case_type,
            'status': self.status,
            'priority': self.priority,
            'follower_lawyer': self.follower_lawyer,
            'authorized_lawyer': self.authorized_lawyer,
            'due_date': self.due_date.strftime('%Y-%m-%d') if self.due_date else None,
            'lat': self.lat,
            'lon': self.lon
        }

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
}

# --- Rota Optimizasyon Algoritması ---
def calculate_route(selected_case_ids, start_city="Bursa", start_date_str=None):
    # 1. Seçilen dosyaları çek
    # selected_case_ids are string IDs from checkbox values
    cases = Case.query.filter(Case.id.in_(selected_case_ids)).all()

    if not cases:
        return []

    # 2. Şehirlere göre grupla
    grouped_destinations = {}
    
    for case in cases:
        city = case.city
        # Şehir koordinatlarını bul
        coords = CITY_COORDS.get(city, {'lat': 0, 'lon': 0})
        if case.lat and case.lon:
             coords = {'lat': case.lat, 'lon': case.lon}

        city_key = city
        
        if city_key not in grouped_destinations:
            grouped_destinations[city_key] = {
                'name': city,
                'city': city,
                'lat': coords['lat'],
                'lon': coords['lon'],
                'cases': [],
                'case_count': 0
            }
        
        grouped_destinations[city_key]['cases'].append(f"{case.case_no} ({case.client})")
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
            if 'W' in start_date_str:
                 current_time = datetime.strptime(start_date_str + '-1', "%Y-W%W-%w")
            else:
                 current_time = datetime.strptime(start_date_str, "%Y-%m-%d")
        except:
            current_time = datetime.now()
    else:
        current_time = datetime.now()

    current_time = current_time.replace(hour=9, minute=0, second=0, microsecond=0)
    
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
            if dest['lat'] == 0 and dest['lon'] == 0:
                 dist, dur = 100, 60
            else:
                dist, dur = get_osrm_route(current_location['lat'], current_location['lon'], dest['lat'], dest['lon'])

            if dur < shortest_dur:
                shortest_dur = dur
                best_stop = dest
                best_stop['distance'] = dist
                best_stop['travel_dur'] = dur

        if not best_stop:
            break

        arrival_time = current_time + timedelta(minutes=best_stop['travel_dur'])
        
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
    filter_q = request.args.get('search', '')

    if filter_q:
        cases = Case.query.filter(
            or_(
                Case.case_no.ilike(f'%{filter_q}%'),
                Case.client.ilike(f'%{filter_q}%'),
                Case.city.ilike(f'%{filter_q}%')
            )
        ).order_by(Case.created_at.desc()).all()
    else:
        cases = Case.query.order_by(Case.created_at.desc()).all()

    # Stats
    total_files = Case.query.count()
    cities_count = db.session.query(Case.city).distinct().count()
    urgent_files = Case.query.filter_by(priority='Acil').count()
    hearings = Case.query.filter_by(status='Duruşma Bekliyor').count()

    return render_template('dashboard.html',
                           cases=cases,
                           stats={
                               'total': total_files,
                               'cities': cities_count,
                               'urgent': urgent_files,
                               'hearings': hearings
                           })

@app.route('/rota')
def rota_page():
    # Sadece Aktif veya Duruşma Bekleyen dosyalar
    cases = Case.query.filter(
        or_(Case.status == 'Aktif', Case.status == 'Duruşma Bekliyor')
    ).order_by(Case.created_at.desc()).all()

    return render_template('route.html', cases=cases)

@app.route('/api/cases', methods=['POST'])
def api_create_case():
    try:
        data = request.form.to_dict()
        new_case = Case(
            case_no=data.get('case_no'),
            client=data.get('client'),
            opponent=data.get('opponent'),
            city=data.get('city'),
            district=data.get('district'),
            court_office=data.get('court_office'),
            case_type=data.get('case_type'),
            status=data.get('status'),
            priority=data.get('priority'),
            follower_lawyer=data.get('follower_lawyer'),
            authorized_lawyer=data.get('authorized_lawyer'),
            description=data.get('description'),
            due_date=datetime.strptime(data.get('due_date'), '%Y-%m-%d') if data.get('due_date') else None
        )

        # Koordinatları şehirden otomatik al (basit çözüm)
        coords = CITY_COORDS.get(data.get('city'))
        if coords:
            new_case.lat = coords['lat']
            new_case.lon = coords['lon']

        db.session.add(new_case)
        db.session.commit()
        return redirect(url_for('index'))
    except Exception as e:
        print(f"Hata: {e}")
        return "Kaydedilirken hata oluştu", 500

@app.route('/api/cases/delete/<int:case_id>', methods=['POST'])
def api_delete_case(case_id):
    try:
        case = Case.query.get_or_404(case_id)
        db.session.delete(case)
        db.session.commit()
    except Exception as e:
        print(f"Silme Hatası: {e}")
    return redirect(url_for('index'))

@app.route('/api/planla', methods=['POST'])
def api_planla():
    selected_ids = request.form.getlist('selected_cases[]') # AJAX array params often come with []
    if not selected_ids:
        selected_ids = request.form.getlist('selected_cases')

    start_date = request.form.get('start_date')
    start_city = request.form.get('start_city', 'Bursa')

    route_data = calculate_route(selected_ids, start_city, start_date)
    return jsonify(route_data)

def init_db():
    with app.app_context():
        # Wait for DB
        retries = 30
        while retries > 0:
            try:
                db.create_all()
                print("Veritabanı tabloları oluşturuldu.")
                break
            except Exception as e:
                print(f"DB Bağlantısı bekleniyor... ({e})")
                time.sleep(2)
                retries -= 1

if __name__ == '__main__':
    # Initialize DB on startup
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
