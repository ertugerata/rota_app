# ⚖️ Hukuk Bürosu Rota Planlayıcı

Bu proje, hukuk büroları için avukatların duruşma veya dosya takibi amacıyla ziyaret etmesi gereken adliyeler arasında en optimize edilmiş rotayı oluşturur.

**Özellikler:**
- **Otomatik Rota Planlama:** Gidilecek adliyeleri birbirine en yakın olacak şekilde sıralar.
- **Zaman Yönetimi:** Mesai saatleri (09:00 - 17:00) ve hafta sonu tatillerini dikkate alarak varış/çıkış saatlerini hesaplar.
- **Veritabanı:** Verileri PostgreSQL veritabanında saklar.
- **Harita Servisi:** Rota hesaplamaları için açık kaynaklı OSRM (Open Source Routing Machine) API kullanılır.

## 🚀 Kurulum ve Başlatma

Bu projeyi çalıştırmak için bilgisayarınızda **Docker** ve **Docker Compose** kurulu olmalıdır.

1. **Projeyi İndirin:**
   ```bash
   git clone <repo-url>
   cd <proje-klasoru>
   ```

2. **Çevresel Değişkenleri Ayarlayın:**
   `.env` dosyasını oluşturun veya mevcut olanı düzenleyin. Örnek `.env` içeriği:
   ```env
   POSTGRES_USER=admin
   POSTGRES_PASSWORD=AvukatRota2026!
   POSTGRES_DB=hukukburosu
   DATABASE_URL=postgresql://admin:AvukatRota2026!@db:5432/hukukburosu
   ```

3. **Uygulamayı Başlatın:**
   Terminalde şu komutu çalıştırın:
   ```bash
   docker-compose up -d --build
   ```
   Bu komut hem Flask web uygulamasını hem de PostgreSQL veritabanını başlatacaktır.

4. **Erişim:**
   - **Web Arayüzü:** [http://localhost:5000](http://localhost:5000)

## 🗄️ Veri Girişi ve Yönetimi

Uygulama, PostgreSQL veritabanı ile çalışmaktadır. Web arayüzü üzerinden dosya ekleme, silme ve listeleme işlemleri yapılabilir.

### Dosya Ekleme
Web arayüzündeki "Yeni Dosya" butonunu kullanarak yeni dava dosyaları ekleyebilirsiniz. Şehir seçimi yapıldığında koordinatlar otomatik olarak atanır.

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
  docker-compose down
  ```
- Logları izlemek için:
  ```bash
  docker-compose logs -f
  ```
