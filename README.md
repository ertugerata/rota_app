# ⚖️ Hukuk Bürosu Rota Planlayıcı

Bu proje, hukuk büroları için avukatların duruşma veya dosya takibi amacıyla ziyaret etmesi gereken adliyeler arasında en optimize edilmiş rotayı oluşturur.

**Özellikler:**
- **Otomatik Rota Planlama:** Gidilecek adliyeleri birbirine en yakın olacak şekilde sıralar.
- **Zaman Yönetimi:** Mesai saatleri (09:00 - 17:00) ve hafta sonu tatillerini dikkate alarak varış/çıkış saatlerini hesaplar.
- **Entegrasyon:** Verileri doğrudan PocketBase veritabanından çeker.
- **Harita Servisi:** Rota hesaplamaları için açık kaynaklı OSRM (Open Source Routing Machine) API kullanılır.

## 🚀 Kurulum ve Başlatma

Bu projeyi çalıştırmak için bilgisayarınızda **Docker** ve **Docker Compose** kurulu olmalıdır.

1. **Projeyi İndirin:**
   ```bash
   git clone <repo-url>
   cd <proje-klasoru>
   ```

2. **Uygulamayı Başlatın:**
   Terminalde şu komutu çalıştırın:
   ```bash
   docker-compose up -d --build
   ```
   Bu komut hem Flask web uygulamasını hem de PocketBase veritabanını başlatacaktır.

3. **Erişim:**
   - **Web Arayüzü:** [http://localhost:5000](http://localhost:5000)
   - **PocketBase Paneli:** [http://localhost:8090/_/](http://localhost:8090/_/)

## 🗄️ PocketBase Kurulumu ve Veri Girişi

Uygulamanın çalışabilmesi için PocketBase üzerinde belirli koleksiyonların (tabloların) oluşturulması gerekmektedir.

### 1. Yönetici Girişi
PocketBase paneline ([http://localhost:8090/_/](http://localhost:8090/_/)) aşağıdaki bilgilerle giriş yapabilirsiniz (Bu bilgiler `docker-compose.yml` içinden değiştirilebilir):

- **E-posta:** `admin@hukukburosu.com`
- **Şifre:** `AvukatRota2026!`

### 2. Gerekli Koleksiyonlar (Collections)

Aşağıdaki iki koleksiyonu oluşturun.

#### A. `courthouses` (Adliyeler)
Adliyelerin konum bilgilerini tutar.
- **Name:** `courthouses`
- **Type:** Base
- **Fields (Alanlar):**
  - `name` (Type: **Text**) -> Örn: "Çağlayan Adliyesi"
  - `city` (Type: **Text**) -> Örn: "İstanbul"
  - `lat` (Type: **Number**) -> Enlem (Örn: 41.068)
  - `lon` (Type: **Number**) -> Boylam (Örn: 28.979)

#### B. `cases` (Dosyalar)
Takip edilecek dava dosyalarını tutar.
- **Name:** `cases`
- **Type:** Base
- **Fields (Alanlar):**
  - `case_no` (Type: **Text**) -> Örn: "2023/154 Esas"
  - `status` (Type: **Select**) -> Seçenekler: `Açık`, `Kapalı`. (Uygulama sadece "Açık" olanları çeker).
  - `courthouse_id` (Type: **Relation**) ->
    - **Collection:** `courthouses`
    - **Max Select:** 1
    - **Cascade Delete:** İşaretlemeyin (tercihen).

### 3. Örnek Veri Girişi
Önce `courthouses` koleksiyonuna birkaç adliye ekleyin, ardından `cases` koleksiyonuna bu adliyelerle ilişkili ve durumu "Açık" olan dosyalar ekleyin.

## 🛠️ Kullanım

1. **Web Arayüzüne Gidin:** [http://localhost:5000](http://localhost:5000) adresini açın.
2. **Rota Oluşturun:** "Haftalık Rotayı Oluştur" butonuna tıklayın.
3. **Sonuçları İnceleyin:**
   - Sistem, Bursa (varsayılan merkez) çıkışlı en uygun rotayı çizer.
   - Her adliye için tahmini varış ve işlem bitiş sürelerini gösterir.
   - Mesai saatleri dışına taşan işlemler otomatik olarak ertesi güne veya Pazartesiye kaydırılır.

## ⚙️ Yapılandırma ve Notlar

- **Başlangıç Noktası:** Varsayılan olarak "Bursa Ofis" (40.1828, 29.0667) ayarlanmıştır. Bunu değiştirmek için `app.py` dosyasındaki `current_location` değişkenini düzenleyebilirsiniz.
- **İşlem Süresi:** Her dosya için varsayılan işlem süresi 45 dakika olarak ayarlanmıştır (`app.py` içinde değiştirilebilir).
- **API:** Rota hesaplaması için `router.project-osrm.org` kullanılmaktadır. Yoğun isteklerde kendi OSRM sunucunuzu kurmanız önerilir.

## 🐳 Docker Yönetimi

- Uygulamayı durdurmak için:
  ```bash
  docker-compose down
  ```
- Logları izlemek için:
  ```bash
  docker-compose logs -f
  ```
