# TODO — Açık Hatalar ve Düzeltme Listesi

## 🟠 Önemli Hatalar

### ❌ 35. `run_tests.py` — pandas/openpyxl Mock'u `test_upload_excel`'i Kırıyor
**Dosya:** `run_tests.py`

**Problem:** `pandas` ve `openpyxl` `MagicMock` ile eziliyor, ancak
`test_app.py`'deki `test_upload_excel` gerçek `pd.DataFrame` ve
`pd.ExcelWriter` kullanıyor. `run_tests.py` üzerinden çalıştırıldığında
`AttributeError` ile başarısız olur. `pytest test_app.py` ile doğrudan
çalıştırıldığında sorun yok.

**Düzeltme:**
```python
# run_tests.py — tüm sys.modules mock'larını kaldır
import unittest
import test_app

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromModule(test_app)
    unittest.TextTestRunner(verbosity=2).run(suite)
```

---

## 🟡 İyileştirme Gereken Alanlar

### ❌ 36. `.env` — Çalıştırma Senaryoları Yetersiz Belgelenmiş
**Dosya:** `.env`, `env-sample.txt`

**Problem:** Sadece Docker Compose senaryosu aktif. Docker dışında
`python app.py` ile çalıştırıldığında (yerel DB veya Supabase cloud)
hangi satırın uncomment edilmesi gerektiği belirsiz.

**Düzeltme:** Üç senaryoyu açıkça belgele:
```env
# 1) DOCKER COMPOSE içinde (aktif):
DATABASE_URL=postgresql://postgres:postgres@db:5432/postgres

# 2) Docker dışında, yerel Docker DB'ye bağlanmak için:
# DATABASE_URL=postgresql://postgres:postgres@localhost:54322/postgres

# 3) Supabase cloud için:
# DATABASE_URL=postgresql://postgres.xxx:YOUR_PASSWORD@aws-0-eu-central-1.pooler.supabase.com:6543/postgres

SECRET_KEY=7a48f2eb1586a6488d8d6f0f74fc7c4c5d5d19bd00ec83722a90207c1d9252f7
```