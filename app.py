from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
import requests
from datetime import datetime, timedelta, timezone
import os
import json
import time
from sqlalchemy import or_
import pandas as pd
from io import BytesIO

app = Flask(__name__)

# Veritabanı Konfigürasyonu (Supabase PostgreSQL uyumlu)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL", "sqlite:///local_fallback.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret')

db = SQLAlchemy(app)

# Sürüm okuma
def get_version():
    try:
        with open('VERSION', 'r') as f:
            return f.read().strip()
    except Exception:
        return "Bilinmiyor"

@app.context_processor
def inject_version():
    return dict(version=get_version())

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
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

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
        response = requests.get(url, timeout=15).json()
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
    # DÜZELTİLDİ: selected_case_ids listesi string'lerden integer'lara çevrilmeli
    selected_case_ids = [int(i) for i in selected_case_ids]
    cases = Case.query.filter(Case.id.in_(selected_case_ids)).all()

    if not cases:
        return []

    # 2. Şehirlere göre grupla
    grouped_destinations = {}

    for case in cases:
        city = case.city
        coords = None
        if case.lat and case.lon:
            coords = {'lat': case.lat, 'lon': case.lon}
        elif city in CITY_COORDS:
            coords = CITY_COORDS[city]

        if not coords:
            # Koordinatları bulunamayan ve sisteme eklenmemiş (lat/lon yok) şehirleri atla
            continue

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
                # DÜZELTİLDİ: ISO hafta formatı için %G-W%V-%u kullanılmalı
                current_time = datetime.strptime(start_date_str + '-1', "%G-W%V-%u")
            else:
                current_time = datetime.strptime(start_date_str, "%Y-%m-%d")
        except Exception:
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
                dist, dur = get_osrm_route(
                    current_location['lat'], current_location['lon'],
                    dest['lat'], dest['lon']
                )

            if dur < shortest_dur:
                shortest_dur = dur
                # DÜZELTİLDİ: dict(dest) ile sığ kopya alınıyor, orijinal dict bozulmuyor
                best_stop = dict(dest)
                best_stop['distance'] = dist
                best_stop['travel_dur'] = dur

        if not best_stop:
            break

        arrival_time = current_time + timedelta(minutes=best_stop['travel_dur'])

        # DÜZELTİLDİ: Gece yarısını geçen seyahatlerde veya mesai dışı durumlarda gün atlaması
        if arrival_time.hour >= 17:
            # 17:00'den sonraysa ertesi gün sabah 09:00'a atla
            arrival_time = arrival_time.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)
            if arrival_time.weekday() >= 5: # Cumartesi/Pazar ise Pazartesiye atla
                arrival_time += timedelta(days=(7 - arrival_time.weekday()))
        elif arrival_time.hour < 9:
            # Gece yarısını geçtiyse (veya sabah 09:00'dan önceyse), zaten yeni güne geçilmiştir, sadece saati 09:00 yap
            # Eğer gün değişmişse +1 gün eklemeye gerek yok, current_time + travel_dur zaten günü ilerletmiş olabilir
            # Veya current_time'a göre aynı gün içinde <9 ise
            if current_time.date() == arrival_time.date():
                 # Aynı gün içindeyse (nasıl olduysa, mesela 08:00'de başlandıysa) saati 09:00 yap
                 arrival_time = arrival_time.replace(hour=9, minute=0, second=0, microsecond=0)
            else:
                 # Geceyi geçtiyse saati 09:00 yap (gün zaten ilerledi)
                 arrival_time = arrival_time.replace(hour=9, minute=0, second=0, microsecond=0)

            if arrival_time.weekday() >= 5:
                arrival_time += timedelta(days=(7 - arrival_time.weekday()))

        departure_time = arrival_time + timedelta(minutes=(best_stop['case_count'] * 45))

        if departure_time.hour >= 17:
            # İşlemler mesai sonrasına taşıyorsa
            overtime = departure_time - departure_time.replace(hour=17, minute=0, second=0, microsecond=0)
            departure_time = departure_time.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1) + overtime
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
        # DÜZELTİLDİ: unvisited listesinden orijinal dest nesnesi kaldırılıyor (best_stop kopya olduğundan)
        unvisited = [d for d in unvisited if d['city'] != best_stop['city']]
        step += 1

    return route_plan

# --- Web Yönlendirmeleri ---

@app.route('/')
def index():
    filter_q = request.args.get('search', '')
    city_filter = request.args.get('city', '')

    query = Case.query

    if filter_q:
        query = query.filter(
            or_(
                Case.case_no.ilike(f'%{filter_q}%'),
                Case.client.ilike(f'%{filter_q}%'),
                Case.city.ilike(f'%{filter_q}%')
            )
        )

    if city_filter:
        query = query.filter(Case.city == city_filter)

    cases = query.order_by(Case.created_at.desc()).all()

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

@app.route('/api/cases/update/<int:case_id>', methods=['POST'])
def api_update_case(case_id):
    try:
        case = Case.query.get_or_404(case_id)
        data = request.form.to_dict()

        case.case_no = data.get('case_no', case.case_no)
        case.client = data.get('client', case.client)
        case.opponent = data.get('opponent', case.opponent)
        case.city = data.get('city', case.city)
        case.district = data.get('district', case.district)
        case.court_office = data.get('court_office', case.court_office)
        case.case_type = data.get('case_type', case.case_type)
        case.status = data.get('status', case.status)
        case.priority = data.get('priority', case.priority)
        case.follower_lawyer = data.get('follower_lawyer', case.follower_lawyer)
        case.authorized_lawyer = data.get('authorized_lawyer', case.authorized_lawyer)
        case.description = data.get('description', case.description)

        if data.get('due_date'):
            case.due_date = datetime.strptime(data.get('due_date'), '%Y-%m-%d')

        coords = CITY_COORDS.get(data.get('city'))
        if coords:
            case.lat = coords['lat']
            case.lon = coords['lon']

        db.session.commit()
        return redirect(url_for('index'))
    except Exception as e:
        print(f"Güncelleme Hatası: {e}")
        return jsonify({"error": "Güncelleme sırasında bir hata oluştu."}), 500

@app.route('/api/cases/delete/<int:case_id>', methods=['POST'])
def api_delete_case(case_id):
    try:
        case = Case.query.get_or_404(case_id)
        db.session.delete(case)
        db.session.commit()
    except Exception as e:
        print(f"Silme Hatası: {e}")
        return jsonify({"error": "Silme işlemi sırasında bir hata oluştu."}), 500
    return redirect(url_for('index'))

@app.route('/api/planla', methods=['POST'])
def api_planla():
    # DÜZELTİLDİ: Hem 'selected_cases[]' hem 'selected_cases' parametresi deneniyor
    selected_ids = request.form.getlist('selected_cases[]')
    if not selected_ids:
        selected_ids = request.form.getlist('selected_cases')

    # DÜZELTİLDİ: String ID'leri integer'a çevir, geçersiz değerleri atla
    try:
        selected_ids = [int(i) for i in selected_ids if str(i).strip().isdigit()]
    except (ValueError, TypeError):
        return jsonify({'error': 'Geçersiz dosya ID formatı'}), 400

    if not selected_ids:
        return jsonify({'error': 'Geçerli dosya seçilmedi'}), 400

    start_date = request.form.get('start_date')
    start_city = request.form.get('start_city', 'Bursa')

    route_data = calculate_route(selected_ids, start_city, start_date)
    return jsonify(route_data)


@app.route('/api/download_template')
def download_template():
    data = {
        'case_no': ['2024/1234', '2024/5678'],
        'client': ['Ahmet Yılmaz', 'Mehmet Demir'],
        'opponent': ['ABC Şirketi', 'XYZ Ltd.'],
        'city': ['İstanbul', 'Ankara'],
        'district': ['Kadıköy', 'Çankaya'],
        'court_office': ['1. Asliye Hukuk', '2. İş Mahkemesi'],
        'case_type': ['Hukuk Davası', 'İş Davası'],
        'status': ['Aktif', 'Aktif'],
        'priority': ['Normal', 'Acil'],
        'follower_lawyer': ['Av. Ali Veli', 'Av. Ayşe Fatma'],
        'authorized_lawyer': ['Av. M.F. ERATA', 'Av. M.F. ERATA'],
        'due_date': ['2024-12-31', '2025-01-15'],
        'description': ['Örnek açıklama 1', 'Örnek açıklama 2']
    }
    df = pd.DataFrame(data)

    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Dosyalar')

    output.seek(0)

    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='dosya_yukleme_sablonu.xlsx'
    )


@app.route('/api/export_excel')
def export_excel():
    cases = Case.query.order_by(Case.created_at.desc()).all()

    data = []
    for case in cases:
        data.append({
            'case_no': case.case_no,
            'client': case.client,
            'opponent': case.opponent,
            'city': case.city,
            'district': case.district,
            'court_office': case.court_office,
            'case_type': case.case_type,
            'status': case.status,
            'priority': case.priority,
            'follower_lawyer': case.follower_lawyer,
            'authorized_lawyer': case.authorized_lawyer,
            'due_date': case.due_date.strftime('%Y-%m-%d') if case.due_date else None,
            'description': case.description
        })

    df = pd.DataFrame(data)

    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Dosyalar')

    output.seek(0)

    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='dosyalar_disa_aktarim.xlsx'
    )

@app.route('/api/upload_excel', methods=['POST'])
def upload_excel():
    if 'file' not in request.files:
        return "Dosya yüklenmedi", 400

    file = request.files['file']
    if file.filename == '':
        return "Dosya seçilmedi", 400

    if file and (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
        try:
            df = pd.read_excel(file)

            required_columns = ['case_no', 'city']
            for col in required_columns:
                if col not in df.columns:
                    return f"Hata: '{col}' sütunu bulunamadı.", 400

            count = 0
            for _, row in df.iterrows():
                if pd.isna(row.get('case_no')) or str(row.get('case_no')).strip() == '':
                    continue

                case_no_val = str(row.get('case_no')).strip()

                existing_case = Case.query.filter_by(case_no=case_no_val).first()
                if existing_case:
                    continue

                due_date_val = None
                if pd.notna(row.get('due_date')):
                    try:
                        due_date_val = pd.to_datetime(row.get('due_date')).date()
                    except Exception:
                        due_date_val = None

                new_case = Case(
                    case_no=case_no_val,
                    client=str(row.get('client', '')) if pd.notna(row.get('client')) else None,
                    opponent=str(row.get('opponent', '')) if pd.notna(row.get('opponent')) else None,
                    city=str(row.get('city', '')) if pd.notna(row.get('city')) else None,
                    district=str(row.get('district', '')) if pd.notna(row.get('district')) else None,
                    court_office=str(row.get('court_office', '')) if pd.notna(row.get('court_office')) else None,
                    case_type=str(row.get('case_type', '')) if pd.notna(row.get('case_type')) else None,
                    status=str(row.get('status', 'Aktif')) if pd.notna(row.get('status')) else 'Aktif',
                    priority=str(row.get('priority', 'Normal')) if pd.notna(row.get('priority')) else 'Normal',
                    follower_lawyer=str(row.get('follower_lawyer', '')) if pd.notna(row.get('follower_lawyer')) else None,
                    authorized_lawyer=str(row.get('authorized_lawyer', '')) if pd.notna(row.get('authorized_lawyer')) else None,
                    description=str(row.get('description', '')) if pd.notna(row.get('description')) else None,
                    due_date=due_date_val
                )

                city_name = str(row.get('city', ''))
                coords = CITY_COORDS.get(city_name)
                if coords:
                    new_case.lat = coords['lat']
                    new_case.lon = coords['lon']

                db.session.add(new_case)
                count += 1

            db.session.commit()
            return redirect(url_for('index'))

        except Exception as e:
            print(f"Excel yükleme hatası: {e}")
            return f"Hata oluştu: {str(e)}", 500

    return "Geçersiz dosya formatı", 400

def init_db():
    with app.app_context():
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
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
