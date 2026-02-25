# Hafif bir Python sürümü kullanıyoruz
FROM python:3.10-slim

# Çalışma dizinini belirliyoruz
WORKDIR /app

# Gerekli paketleri kopyalayıp kuruyoruz
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulamanın tüm dosyalarını kopyalıyoruz
COPY . .

# Flask'ın çalışacağı portu açıyoruz
EXPOSE 5000

# Uygulamayı başlatıyoruz
CMD ["python", "app.py"]