# ⚖️ Hukuk Bürosu Rota Planlayıcı

Bu proje, hukuk büroları için avukatların duruşma veya dosya takibi amacıyla ziyaret etmesi gereken adliyeler arasında en optimize edilmiş rotayı oluşturur.

**Özellikler:**
- **Otomatik Rota Planlama:** Gidilecek adliyeleri birbirine en yakın olacak şekilde sıralar.
- **Zaman Yönetimi:** Mesai saatleri (09:00 - 17:00) ve hafta sonu tatillerini dikkate alarak varış/çıkış saatlerini hesaplar.
- **Veritabanı:** Verileri bulut tabanlı Supabase (PostgreSQL) veritabanında saklar.
- **Harita Servisi:** Rota hesaplamaları için açık kaynaklı OSRM (Open Source Routing Machine) API kullanılır.

## 🚀 Kurulum ve Başlatma

Bu projeyi çalıştırmak için bilgisayarınızda **Docker** ve **Docker Compose** kurulu olmalıdır.

1. **Projeyi İndirin:**
   ```bash
   git clone <repo-url>
   cd <proje-klasoru>
   ```

2. **Çevresel Değişkenleri Ayarlayın:**
   `.env` dosyasını oluşturun veya mevcut olanı düzenleyin (`env-sample.txt` dosyasını kopyalayabilirsiniz).
   - Yerel kullanım için: `DATABASE_URL=postgresql://postgres:postgres@db:5432/postgres` (Docker Compose ile oluşturulan yerel veritabanına erişimi sağlar)
   - Bulut (Cloud) Supabase kullanımı için ilgili satırı yorumdan çıkarıp, Supabase bulut adresinizi yapıştırın.

3. **Uygulamayı ve Yerel Veritabanını Başlatın:**
   Terminalde şu komutu çalıştırın:
   ```bash
   docker compose up -d --build
   ```
   Bu komut, uygulamanızı ve yerel PostgreSQL (Supabase uyumlu) veritabanınızı Docker içerisinde başlatacaktır. `DATABASE_URL` hedefinde bulunan veritabanınıza bağlanılacak ve ilk açılışta veritabanı tabloları otomatik olarak oluşturulacaktır. Yerel veritabanı dışarıya `54322` portundan açık durumdadır.

4. **Erişim:**
   - **Web Arayüzü:** [http://localhost:5000](http://localhost:5000)

## 🗄️ Veri Girişi ve Yönetimi

Uygulama, Supabase (PostgreSQL) veritabanı ile çalışmaktadır. Web arayüzü üzerinden dosya ekleme, silme, listeleme ve Excel işlemleri yapılabilir.

### Dosya Ekleme
Web arayüzündeki "Yeni Dosya" butonunu kullanarak yeni dava dosyaları ekleyebilirsiniz. Şehir seçimi yapıldığında koordinatlar otomatik olarak atanır. Ayrıca "Excel Yükle" seçeneği ile toplu dosya ekleyebilirsiniz.

### Dışa Aktarma
"Excel İndir" butonuna tıklayarak mevcut veritabanındaki tüm kayıtlarınızı Excel (xlsx) formatında bilgisayarınıza indirebilir, tıpkı şablonla aktardığınız gibi dışarı alabilirsiniz.

### Rota Planlama
1. **Web Arayüzüne Gidin:** [http://localhost:5000/rota](http://localhost:5000/rota) adresini açın.
2. **Dosyaları Seçin:** Listeden gitmek istediğiniz dosyaları seçin.
3. **Başlangıç Bilgilerini Girin:** Başlangıç şehri ve haftasını seçin.
4. **Rota Oluşturun:** "Rota Hesapla" butonuna tıklayın.
5. **Sonuçları İnceleyin:**
   - Sistem, seçilen başlangıç noktasından en uygun rotayı çizer.
   - Her adliye için tahmini varış ve işlem bitiş sürelerini gösterir.

## ⚙️ Yapılandırma ve Notlar

- **Başlangıç Noktası:** Varsayılan olarak "Bursa Ofis" ayarlanmıştır.
- **İşlem Süresi:** Her dosya için varsayılan işlem süresi 45 dakika olarak ayarlanmıştır (`app.py` içinde değiştirilebilir).
- **API:** Rota hesaplaması için `router.project-osrm.org` kullanılmaktadır.

## 🐳 Docker Yönetimi

- Uygulamayı durdurmak için:
  ```bash
  docker compose down
  ```
- Logları izlemek için:
  ```bash
  docker compose logs -f
  ```
