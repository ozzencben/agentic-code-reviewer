# Test Senaryoları (Fixtures) ve Hata Analizi Rehberi

Bu klasör (`src/test/fixtures`), **Agentic Code Reviewer** projesinin güvenlik, mimari, zaman dilimi ve kod kalitesi analiz yeteneklerini test etmek amacıyla özel olarak hazırlanmış Python test dosyalarını içermektedir.

---

## 📁 Dosya Bazlı Hata ve Güvenlik Analizi

### 1. `sample_redis_leak.py`

* **Dosya Amacı**: Multi-tenant (Çok Kiracılı) mimaride çalışan bir FastAPI profil getirme servisi.
* **Mevcut Hata**: Multi-Tenant Veri İzolasyon Eksikliği (Redis Key Leak).
* **Hata Tanımı**:
  `cache_key = f"user:{user_id}:profile"` ifadesinde Redis key'ine `tenant_id` namespace'i eklenmemiştir.
* **Nedeni ve Riski**:
  Multi-tenant sistemlerde farklı organizasyonlardaki kullanıcılar aynı `user_id` değerine veya sıralı id'lere sahip olabilir. `tenant_id` key içerisinde bulunmadığında:
  - Tenant A'daki `user_id = 10` verisi önbelleğe alınır.
  - Tenant B'deki `user_id = 10` profili istediğinde Redis'ten Tenant A'nın önbellekteki verisini okur.
  - Bu durum ciddi bir **Cross-Tenant Data Leakage** (Kiracılar arası veri sızıntısı) güvenlik zafiyetidir.
* **Çözüm**:
  Redis anahtarı kiracı bazında izole edilmelidir:
  ```python
  cache_key = f"tenant:{tenant_id}:user:{user_id}:profile"
  ```

---

### 2. `sample_security_risk.py`

* **Dosya Amacı**: Kullanıcı kimlik doğrulama ve Stripe ödeme alma fonksiyonları.
* **Mevcut Hata 1**: Kaynak Koda Hardcoded Secret Ekleme (CWE-798 / Hardcoded Credentials).
  - `STRIPE_SECRET_KEY = "sk_test_placeholder_key_for_testing_12345"`
  - `JWT_SECRET_KEY = "super_secret_jwt_key_that_should_not_be_here"`
* **Nedeni ve Riski 1**:
  Canlı API anahtarları veya JWT imzalama anahtarlarının koda sabit yazılması, kod repository'ye (Git, GitHub, GitLab vb.) push edildiğinde tüm yetkisiz kişilerin veya saldırganların eline geçmesine sebep olur.
* **Çözüm 1**:
  Hassas veriler ortam değişkenlerinden (`os.getenv`) veya kasa servislerinden (AWS Secrets Manager, Vault) okunmalıdır:
  ```python
  import os
  STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
  ```

* **Mevcut Hata 2**: SQL Injection Riski (CWE-89 / SQL Injection).
  - `query = "SELECT id, email, role FROM users WHERE email = '" + email + "' AND password = '" + password_hash + "'"`
* **Nedeni ve Riski 2**:
  Kullanıcıdan alınan `email` ve `password` parametreleri doğrudan ham SQL string birleştirmesi (string concatenation) ile sorguya eklenmiştir. Bir saldırgan `email` alanına `' OR '1'='1` girdiğinde tüm veritabanı sorgusunun akışını değiştirebilir ve yetkisiz giriş/veri sızdırma gerçekleştirebilir.
* **Çözüm 2**:
  Parametrik SQL sorguları (Parameterized Queries / Prepared Statements) kullanılmalıdır:
  ```python
  cursor.execute(
      "SELECT id, email, role FROM users WHERE email = ? AND password = ?",
      (email, password_hash)
  )
  ```

---

### 3. `sample_timezone_bug.py`

* **Dosya Amacı**: Sipariş oluşturma ve son ödeme tarihi (expiration) kontrolü.
* **Mevcut Hata**: Zaman Dilimsiz Datetime Kullanımı (Naive Datetime Usage).
  - `created_at = datetime.now()`
* **Nedeni ve Riski**:
  `datetime.now()` parametresiz çağrıldığında sunucunun yerel zaman dilimini (local timezone) baz alan **naive datetime** üretir. Dağıtık mimarilerde, farklı zaman dilimlerindeki sunucularda veya Docker konteynırlarında çalışan servisler veritabanına farklı zaman dilimlerinde zaman damgası yazar. Bu durum:
  - Yanlış sipariş süresi dolma (expiration) hesaplamalarına,
  - Veri analizlerinde tutarsızlıklara,
  - Log takibinde zaman uyuşmazlıklarına yol açar.
* **Çözüm**:
  Zaman bilgisi her zaman açıkça UTC zaman dilimi ile (timezone-aware) oluşturulmalıdır:
  ```python
  from datetime import datetime, timezone
  created_at = datetime.now(timezone.utc)
  ```

---

### 4. `sample_clean_code.py`

* **Dosya Amacı**: Tüm güvenlik, mimari ve clean code prensiplerine uyan örnek referans kod.
* **Uygulanan Best Practice'ler**:
  1. **Kiracı İzolasyonu**: Redis key'leri `tenant:{tenant_id}:user:{user_id}:profile` yapısıyla tamamen izole edilmiştir.
  2. **Güvenli Secret Yönetimi**: Gizli anahtarlar koda yazılmamış, `os.getenv` ile ortam değişkenlerinden çekilmiştir.
  3. **SQL Injection Koruması**: Tüm SQL işlemleri parametrik sorgular (`?` placeholders) ile gerçekleştirilmiştir.
  4. **UTC Datetime Kullanımı**: Zaman işlemleri `datetime.now(timezone.utc)` ile zaman dilimine duyarlı yapılmıştır.
  5. **Veri Doğrulama (Pydantic)**: Request ve response body'leri Pydantic modelleri (`BaseModel`, `EmailStr`, `Field`) ile tip ve değer kontrolünden geçirilmektedir.
