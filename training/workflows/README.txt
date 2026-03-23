Bu klasöre bankaya özgü iş akışı belgelerini ekleyin.

Her alt klasör bir domain'e karşılık gelir:
  credit_risk/         - Kredi riski prosedürleri, onay limitleri, politikalar
  fraud_detection/     - Dolandırıcılık tespit kuralları, vaka yönetimi
  aml_kyc/             - AML politikası, KYC prosedürleri, şüpheli işlem bildirimi
  customer_service/    - Müşteri hizmetleri kılavuzları, ürün bilgileri
  data_quality/        - Veri kalite standartları, doğrulama kuralları
  treasury_liquidity/  - Hazine işlemleri, likidite yönetimi, ALM
  regulatory_compliance/ - BDDK, TCMB, MASAK düzenlemeleri
  retail_banking/      - Bireysel bankacılık ürünleri, süreçleri
  corporate_sme/       - Kurumsal ve KOBİ bankacılık prosedürleri
  operations_process/  - Operasyon el kitapları, SLA tanımları
  it_cybersecurity/    - BT güvenlik politikaları, olay müdahale

Desteklenen dosya formatları: .txt, .md, .pdf, .docx, .xlsx

Belgeleri ekledikten sonra:
  python training/ingest.py ingest   # Tüm belgeleri işle ve veritabanına yükle
  python training/ingest.py list     # Yüklü domain ve dosyaları listele
