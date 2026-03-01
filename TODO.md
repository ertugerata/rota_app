# TODO — Hata ve Kod Düzeltme Listesi

## 🔴 Kritik Hatalar

### ✅ 1. `init_db.py` — Kullanılmayan / Hatalı Dosya
- `init_db.py`, PocketBase API'sine bağlanmaya çalışıyor. Ancak proje artık PocketBase değil **Flask-SQLAlchemy + PostgreSQL** kullanıyor.
- Bu dosya tamamen devre dışı/gereksiz; karışıklığa neden olur. Ya silinmeli ya da güncellenmeli.

### ✅ 2. `templates/index.html` — Ölü Şablon
- `templates/index.html` dosyası eski PocketBase tabanlı koda ait; artık hiçbir route tarafından kullanılmıyor.
- Gereksiz karmaşıklık yaratır, silinmeli.

### ✅ 3. `app.py` — Rota Hesaplamasında `best_stop` Mutasyon Hatası
- `calculate_route()` içinde `best_stop = dest` atandıktan sonra `best_stop['distance']` ve `best_stop['travel_dur']` anahtarları **orijinal `dest` dict'ine** yazılıyor. Bu, `grouped_destinations` sözlüğünü bozar.
- Düzeltme: `best_stop = dict(dest)` ile kopyasını al.

```python
# YANLIŞ
best_stop = dest
best_stop['distance'] = dist  # orijinal dict'i değiştiriyor

# DOĞRU
best_stop = dict(dest)
best_stop['distance'] = dist
```

### ✅ 4. `app.py` — `selected_ids` Integer'a Çevrilmiyor
- `Case.query.filter(Case.id.in_(selected_case_ids))` satırında `selected_case_ids` string listesidir (formdan gelen değerler).
- PostgreSQL ile tip uyumsuzluğu nedeniyle **hiçbir sonuç dönmeyebilir** veya hata fırlatır.
- Düzeltme: `[int(i) for i in selected_case_ids]`

---

## 🟠 Önemli Hatalar

### ✅ 5. `app.py` — Hafta Formatı Parsing Yanlışlığı
- `datetime.strptime(start_date_str + '-1', "%Y-W%W-%w")` ifadesi `2026-W09-1` gibi girdiler için **Python versiyonuna bağlı olarak hatalı sonuç** üretebilir.
- Standart ISO hafta formatı (`%G-W%V-%u`) kullanılmalıdır:
```python
current_time = datetime.strptime(start_date_str + '-1', "%G-W%V-%u")
```

### ✅ 6. `app.py` — Mesai Dışı Saat Kontrolü Eksik
- Gece yarısını geçen seyahat süreleri için kontrol sadece `>= 17` veya `< 9` bakıyor; gece `00:00–09:00` arası için `arrival_time.hour < 9` koşulu doğru çalışıyor ama **ertesi gün** ekleme unutulmuş. Gece yarısı geçişi durumunda tarihe +1 gün eklenmiyor, sadece saat 09:00 yapılıyor.
- Düzeltme: `arrival_time` güncellenirken doğru gün hesabı yapılmalı.
- Düzeltme kısmen uygulandı; ancak **aşağıdaki 🔴 19. maddeye bakınız**, overtim hesabı hâlâ hatalı.

### ✅ 7. `app.py` — `datetime.utcnow()` Kullanımı Deprecated
- `default=datetime.utcnow` Python 3.12+ sürümünde deprecated.
- Düzeltme: `from datetime import timezone` ekleyip `datetime.now(timezone.utc)` kullanılmalı.

### ✅ 8. `docker-compose.yml` — `web` Servisi `db` Hazır Olmadan Başlayabilir
- `depends_on: db` yalnızca konteynerin başladığını garantiler, **PostgreSQL'in hazır olduğunu değil**.
- `app.py`'daki `init_db()` retry döngüsü bunu kısmen çözüyor, ama daha temiz çözüm `healthcheck` eklemektir:
```yaml
db:
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U postgres"]
    interval: 5s
    timeout: 5s
    retries: 10
web:
  depends_on:
    db:
      condition: service_healthy
```

---

## 🟡 İyileştirme Gereken Alanlar

### ✅ 9. `app.py` — OSRM API Timeout Düşük
- `requests.get(url, timeout=5)` değeri OSRM'nin yavaş yanıt verdiği durumlarda istek başarısız olur ve rota hesabı `float('inf')` değeriyle bozulur.
- Timeout değeri en az `10–15` saniyeye çıkarılmalı; hata durumunda kullanıcıya bilgi verilmeli.

### ✅ 10. `app.py` — Koordinatsız Şehirler İçin Hatalı Fallback
- `CITY_COORDS`'da bulunmayan bir şehir girildiğinde `lat=0, lon=0` atanıyor. Bu koordinatlar **Atlas Okyanusu'nda bir noktaya** karşılık gelir ve OSRM'den anlamsız mesafeler döner.
- Düzeltme: Koordinatı bulunamayan şehirleri kullanıcıya uyarı ile işaretlemeli veya rotadan çıkarmalı.

### ✅ 11. `templates/dashboard.html` — Arama Formu Çalışmıyor
- `#searchInput` için herhangi bir JavaScript veya form submit mantığı **yok**. Kullanıcı yazdığında hiçbir şey olmuyor.
- Düzeltme: Input'a `keyup` event'i eklenip `/` adresine `?search=` parametresiyle yönlendirme yapılmalı veya canlı filtreleme eklenmeli.

### ✅ 12. `templates/dashboard.html` — Şehir Filtresi Pasif
- "Tüm Şehirler" dropdown'ı seçildiğinde herhangi bir filtreleme gerçekleşmiyor; backend'de bu parametre hiç işlenmiyor.
- `app.py`'daki `index()` fonksiyonuna `city` parametresi desteği eklenmeli.

### ✅ 13. `app.py` — `api_delete_case` Hata Durumunda Redirect Yapıyor
- `try/except` bloğunda hata olsa bile `return redirect(url_for('index'))` çalışıyor. Kullanıcı silme işleminin başarısız olduğunu anlayamıyor.
- Hata durumunda flash mesajı veya hata yanıtı döndürülmeli.

### ✅ 14. `requirements.txt` — Versiyon Sabitleme Yok
- Hiçbir paketin versiyonu belirtilmemiş. Gelecekte uyumsuz güncellemeler uygulamayı bozabilir.
- Örnek: `flask==3.0.3`, `flask-sqlalchemy==3.1.1` şeklinde sabitlenmeli.

### ✅ 15. `app.py` — `SECRET_KEY` Tanımlı Değil
- Flask session ve CSRF koruması için `app.secret_key` tanımlanmamış. Flash mesajı eklendiğinde veya session kullanıldığında uygulama hata verir.
- `.env` dosyasına `SECRET_KEY` eklenmeli ve `app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret')` tanımlanmalı.

---

## 🔵 Eksik Özellikler / Teknik Borç

### ✅ 16. Dosya Düzenleme (Edit) Butonu Çalışmıyor
- `dashboard.html`'deki "Düzenle" butonu sadece görsel; herhangi bir modal veya route bağlantısı yok.
- `/api/cases/update/<id>` endpoint'i ve ilgili modal eklenmeli.

### ✅ 17. `route.html` — AJAX `selected_cases[]` vs `selected_cases` Tutarsızlığı
- `app.py`'de hem `selected_cases[]` hem `selected_cases` parametresi deneniyor (ikili kontrol mevcut), ancak jQuery `$.ajax` `data:` nesnesinde dizi gönderiminde `traditional: true` ayarı olmadan parametreler doğru iletilmeyebilir.
- jQuery AJAX çağrısına `traditional: true` eklenmeli:
```javascript
$.ajax({
    url: '/api/planla',
    method: 'POST',
    traditional: true,  // Bunu ekle
    data: { 'selected_cases': selectedCases, ... }
})
```

### ✅ 18. Test Dosyası — `test_route_calculation_api` Gerçek OSRM İsteği Yapıyor
- Unit test, dış ağa (`router.project-osrm.org`) istek atıyor. Bu testleri CI/CD ortamında güvenilmez kılar.
- OSRM çağrısı mock'lanmalı: `unittest.mock.patch('app.get_osrm_route', return_value=(100, 60))`.
---

## 🔴 YENİ — Kritik Hatalar (Kod İncelemesinde Tespit Edildi)

### ❌ 19. `app.py` — `departure_time` Overtime Hesabı Hatalı (Çok Fazla Dosya Durumu)
**Dosya:** `app.py`, `calculate_route()` fonksiyonu, ~satır 148–156

**Problem:** `departure_time = arrival_time + timedelta(minutes=(best_stop['case_count'] * 45))` hesabında, bir şehirde çok sayıda dosya varsa (örn. 20 dosya → 900 dk = 15 saat), `departure_time` **ertesi güne veya daha ileriye taşabilir**. Bu durumda `overtime` hesabı şöyle yapılıyor:

```python
overtime = departure_time - departure_time.replace(hour=17, minute=0, second=0, microsecond=0)
```

`departure_time.replace(hour=17)` çağrısı **aynı günün** 17:00'ini alır. Eğer `departure_time` ertesi gün 09:30 ise, `replace(hour=17)` da ertesi günün 17:00'ini verir → `overtime = -7.5 saat` (negatif!) → sonuç tamamen yanlış.

**Düzeltme:**
```python
# ÖNCE kaç tam iş günü ve artık dakika olduğunu hesapla
WORK_MINUTES = 8 * 60  # 09:00–17:00 = 480 dk
total_minutes = best_stop['case_count'] * 45
day_of_departure = arrival_time

remaining = total_minutes
while remaining > 0:
    end_of_day = day_of_departure.replace(hour=17, minute=0, second=0, microsecond=0)
    available = (end_of_day - day_of_departure).total_seconds() / 60
    if remaining <= available:
        day_of_departure = day_of_departure + timedelta(minutes=remaining)
        remaining = 0
    else:
        remaining -= available
        day_of_departure = day_of_departure.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)
        if day_of_departure.weekday() >= 5:
            day_of_departure += timedelta(days=(7 - day_of_departure.weekday()))

departure_time = day_of_departure
```

---

### ❌ 20. `app.py` — `render_template` Çağrılarında `active_page` Parametresi Eksik
**Dosya:** `app.py`, `index()` ve `rota_page()` fonksiyonları

**Problem:** `base.html` şablonu sidebar menüsünde aktif sayfayı belirtmek için `active_page` değişkenini kullanıyor:
```html
<a href="/" class="{{ 'active' if active_page == 'dashboard' else '' }}">
<a href="/rota" class="{{ 'active' if active_page == 'rota' else '' }}">
```
Ancak ne `index()` ne de `rota_page()` fonksiyonu bu değişkeni `render_template`'e geçiriyor. Sonuç olarak sidebar'da hiçbir menü öğesi aktif görünmüyor (sarı kenarlık ve highlight eksik).

**Düzeltme:**
```python
# index() içinde:
return render_template('dashboard.html', ..., active_page='dashboard')

# rota_page() içinde:
return render_template('route.html', cases=cases, active_page='rota')
```

---

## 🟠 YENİ — Önemli Hatalar

### ❌ 21. `templates/dashboard.html` — Şehir Filtresi Dropdown'u Eksik Şehirler İçeriyor
**Dosya:** `templates/dashboard.html`, şehir `<select>` dropdown'ı

**Problem:** Dropdown'da `Denizli` seçeneği var, ancak `CITY_COORDS` sözlüğünde ve `app.py`'nin `index()` filtresinde Denizli koordinatı **tanımlı değil**. Kullanıcı Denizli'yi şehir olarak seçip kaydedebilir, ancak bu dosya rota hesabına dahil edilemez (koordinat bulunamaz, atlanır). Aynı durum `addCaseModal`'daki şehir listesi için de geçerli.

**Düzeltme:** `CITY_COORDS`'a eksik şehirleri ekle:
```python
'Denizli': {'lat': 37.7765, 'lon': 29.0864},
'Malatya': {'lat': 38.3552, 'lon': 38.3095},
# ... diğer şehirler için de kontrol et
```
Ya da her iki şehir listesini tek bir yerden (CITY_COORDS anahtarlarından) türet.

---

### ❌ 22. `templates/route.html` — `weekPicker` Değeri Hardcoded
**Dosya:** `templates/route.html`, satır: `<input type="week" id="weekPicker" class="form-control" value="2026-W09">`

**Problem:** Başlangıç haftası sabit `2026-W09` olarak kodlanmış. Kullanıcı her seferinde bunu manuel değiştirmek zorunda; uygulama ilk açıldığında geçmiş bir tarihi gösterecek.

**Düzeltme:** Jinja2 ile bu haftanın ISO değerini dinamik olarak ver:
```python
# app.py rota_page() içinde:
from datetime import date
current_week = date.today().strftime('%G-W%V')
return render_template('route.html', cases=cases, active_page='rota', current_week=current_week)
```
```html
<!-- route.html -->
<input type="week" id="weekPicker" class="form-control" value="{{ current_week }}">
```

---

### ❌ 23. `templates/route.html` — `bg-gold` CSS Sınıfı Tanımlı Değil
**Dosya:** `templates/route.html`, satır: `<span class="badge bg-gold text-dark me-2">`

**Problem:** `bg-gold` Bootstrap'te veya `base.html`'deki custom CSS'te tanımlanmamış bir sınıf. Badge arka planı renksiz (şeffaf) görünür.

**Düzeltme:** `base.html`'deki `<style>` bloğuna ekle:
```css
.bg-gold {
    background-color: #fbbf24 !important;
}
```

---

## 🟡 YENİ — İyileştirme Gereken Alanlar

### ❌ 24. `test_app.py` — `city='Istanbul'` (ASCII) Yazım Hatası
**Dosya:** `test_app.py`, satır: `city='Istanbul'`

**Problem:** Test verisinde şehir adı `'Istanbul'` olarak girilmiş; ancak uygulamada tüm şehir adları Türkçe karakter içeriyor (`'İstanbul'`). Bu, CITY_COORDS aramasının başarısız olmasına ve test case'inin koordinatsız kalmasına neden olur; ancak test `lat/lon` elle verildiği için rota hesabında sorun çıkmaz. Yine de tutarsızlık gerçek senaryolarda bulunamayan şehirlere yol açabilir.

**Düzeltme:**
```python
c2 = Case(case_no='C2', client='Client 2', city='İstanbul', lat=41.0, lon=28.9)
```

---

### ❌ 25. `docker-compose.yml` — `web` Servisi İçin `SECRET_KEY` Ortam Değişkeni `.env`'de Yok
**Dosya:** `.env` ve `env-sample.txt`

**Problem:** `app.py`'de `SECRET_KEY` okunuyor (`os.environ.get('SECRET_KEY', 'dev-secret')`), ancak `.env` ve `env-sample.txt` dosyalarında bu değişken **tanımlı değil**. Production'da varsayılan `'dev-secret'` değeri kullanılacak; bu ciddi bir güvenlik açığı.

**Düzeltme:** `.env` ve `env-sample.txt`'ye ekle:
```env
SECRET_KEY=buraya-gizli-ve-uzun-rastgele-bir-deger-girin
```

---

### ❌ 26. `app.py` — `Case.query.get_or_404()` SQLAlchemy 2.x'te Deprecated
**Dosya:** `app.py`, `api_update_case()` ve `api_delete_case()` fonksiyonları

**Problem:** `Case.query.get_or_404(case_id)` Flask-SQLAlchemy 3.x / SQLAlchemy 2.x'te deprecated; `db.get_or_404(Case, case_id)` olarak güncellenmeli.

**Düzeltme:**
```python
# YANLIŞ (deprecated)
case = Case.query.get_or_404(case_id)

# DOĞRU
case = db.get_or_404(Case, case_id)
```
