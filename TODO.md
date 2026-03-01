# TODO — Hata ve Kod Düzeltme Listesi

## 🔴 Kritik Hatalar

### 1. `init_db.py` — Kullanılmayan / Hatalı Dosya
- `init_db.py`, PocketBase API'sine bağlanmaya çalışıyor. Ancak proje artık PocketBase değil **Flask-SQLAlchemy + PostgreSQL** kullanıyor.
- Bu dosya tamamen devre dışı/gereksiz; karışıklığa neden olur. Ya silinmeli ya da güncellenmeli.

### 2. `templates/index.html` — Ölü Şablon
- `templates/index.html` dosyası eski PocketBase tabanlı koda ait; artık hiçbir route tarafından kullanılmıyor.
- Gereksiz karmaşıklık yaratır, silinmeli.

### 3. `app.py` — Rota Hesaplamasında `best_stop` Mutasyon Hatası
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

### 4. `app.py` — `selected_ids` Integer'a Çevrilmiyor
- `Case.query.filter(Case.id.in_(selected_case_ids))` satırında `selected_case_ids` string listesidir (formdan gelen değerler).
- PostgreSQL ile tip uyumsuzluğu nedeniyle **hiçbir sonuç dönmeyebilir** veya hata fırlatır.
- Düzeltme: `[int(i) for i in selected_case_ids]`

---

## 🟠 Önemli Hatalar

### 5. `app.py` — Hafta Formatı Parsing Yanlışlığı
- `datetime.strptime(start_date_str + '-1', "%Y-W%W-%w")` ifadesi `2026-W09-1` gibi girdiler için **Python versiyonuna bağlı olarak hatalı sonuç** üretebilir.
- Standart ISO hafta formatı (`%G-W%V-%u`) kullanılmalıdır:
```python
current_time = datetime.strptime(start_date_str + '-1', "%G-W%V-%u")
```

### 6. `app.py` — Mesai Dışı Saat Kontrolü Eksik
- Gece yarısını geçen seyahat süreleri için kontrol sadece `>= 17` veya `< 9` bakıyor; gece `00:00–09:00` arası için `arrival_time.hour < 9` koşulu doğru çalışıyor ama **ertesi gün** ekleme unutulmuş. Gece yarısı geçişi durumunda tarihe +1 gün eklenmiyor, sadece saat 09:00 yapılıyor.
- Düzeltme: `arrival_time` güncellenirken doğru gün hesabı yapılmalı.

### 7. `app.py` — `datetime.utcnow()` Kullanımı Deprecated
- `default=datetime.utcnow` Python 3.12+ sürümünde deprecated.
- Düzeltme: `from datetime import timezone` ekleyip `datetime.now(timezone.utc)` kullanılmalı.

### 8. `docker-compose.yml` — `web` Servisi `db` Hazır Olmadan Başlayabilir
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

### 9. `app.py` — OSRM API Timeout Düşük
- `requests.get(url, timeout=5)` değeri OSRM'nin yavaş yanıt verdiği durumlarda istek başarısız olur ve rota hesabı `float('inf')` değeriyle bozulur.
- Timeout değeri en az `10–15` saniyeye çıkarılmalı; hata durumunda kullanıcıya bilgi verilmeli.

### 10. `app.py` — Koordinatsız Şehirler İçin Hatalı Fallback
- `CITY_COORDS`'da bulunmayan bir şehir girildiğinde `lat=0, lon=0` atanıyor. Bu koordinatlar **Atlas Okyanusu'nda bir noktaya** karşılık gelir ve OSRM'den anlamsız mesafeler döner.
- Düzeltme: Koordinatı bulunamayan şehirleri kullanıcıya uyarı ile işaretlemeli veya rotadan çıkarmalı.

### 11. `templates/dashboard.html` — Arama Formu Çalışmıyor
- `#searchInput` için herhangi bir JavaScript veya form submit mantığı **yok**. Kullanıcı yazdığında hiçbir şey olmuyor.
- Düzeltme: Input'a `keyup` event'i eklenip `/` adresine `?search=` parametresiyle yönlendirme yapılmalı veya canlı filtreleme eklenmeli.

### 12. `templates/dashboard.html` — Şehir Filtresi Pasif
- "Tüm Şehirler" dropdown'ı seçildiğinde herhangi bir filtreleme gerçekleşmiyor; backend'de bu parametre hiç işlenmiyor.
- `app.py`'daki `index()` fonksiyonuna `city` parametresi desteği eklenmeli.

### 13. `app.py` — `api_delete_case` Hata Durumunda Redirect Yapıyor
- `try/except` bloğunda hata olsa bile `return redirect(url_for('index'))` çalışıyor. Kullanıcı silme işleminin başarısız olduğunu anlayamıyor.
- Hata durumunda flash mesajı veya hata yanıtı döndürülmeli.

### 14. `requirements.txt` — Versiyon Sabitleme Yok
- Hiçbir paketin versiyonu belirtilmemiş. Gelecekte uyumsuz güncellemeler uygulamayı bozabilir.
- Örnek: `flask==3.0.3`, `flask-sqlalchemy==3.1.1` şeklinde sabitlenmeli.

### 15. `app.py` — `SECRET_KEY` Tanımlı Değil
- Flask session ve CSRF koruması için `app.secret_key` tanımlanmamış. Flash mesajı eklendiğinde veya session kullanıldığında uygulama hata verir.
- `.env` dosyasına `SECRET_KEY` eklenmeli ve `app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret')` tanımlanmalı.

---

## 🔵 Eksik Özellikler / Teknik Borç

### 16. Dosya Düzenleme (Edit) Butonu Çalışmıyor
- `dashboard.html`'deki "Düzenle" butonu sadece görsel; herhangi bir modal veya route bağlantısı yok.
- `/api/cases/update/<id>` endpoint'i ve ilgili modal eklenmeli.

### 17. `route.html` — AJAX `selected_cases[]` vs `selected_cases` Tutarsızlığı
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

### 18. Test Dosyası — `test_route_calculation_api` Gerçek OSRM İsteği Yapıyor
- Unit test, dış ağa (`router.project-osrm.org`) istek atıyor. Bu testleri CI/CD ortamında güvenilmez kılar.
- OSRM çağrısı mock'lanmalı: `unittest.mock.patch('app.get_osrm_route', return_value=(100, 60))`.
