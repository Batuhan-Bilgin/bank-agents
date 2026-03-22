# BankAI — Teknik Sistem Raporu

---

## 1. Genel Bakış

BankAI, Türk bankacılık operasyonları için geliştirilmiş 80 ajanından oluşan çok-ajanlı bir yapay zeka sistemidir. Her ajan belirli bir bankacılık departmanında uzmanlaşmış, araç çağırma (tool calling) kapasitesine sahip ve gerçek veya sahte veri kaynaklarına bağlanabilen bağımsız bir LLM instance'ıdır.

**Çalışma adresi:** `https://github.com/Batuhan-Bilgin/bank-agents`

---

## 2. Mimari

```
┌──────────────────────────────────────────────────────────────┐
│                        main.py / API                         │
│              (CLI  ·  FastAPI REST  ·  Demo)                  │
└──────────────────────────┬───────────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────────┐
│                      Orchestrator                            │
│         run() · auto() · pipeline() · broadcast()           │
└────────┬────────────────────────────────────────┬────────────┘
         │                                        │
┌────────▼────────┐                    ┌──────────▼──────────┐
│  AgentFactory   │                    │    ToolRegistry      │
│ get() · best_   │                    │  execute_tool()      │
│ agent_for() ·   │                    │  43 araç kaydı       │
│ broadcast()     │                    └──────────┬──────────┘
└────────┬────────┘                               │
         │                         ┌──────────────┼──────────────┐
┌────────▼────────┐         ┌──────▼───┐  ┌──────▼───┐  ┌──────▼───┐
│  BaseAgent      │         │ banking_ │  │complian- │  │communic- │
│  (Anthropic)    │         │ tools    │  │ ce_tools │  │ation_    │
│  GroqBaseAgent  │         │ 13 araç  │  │ 8 araç   │  │ tools    │
│  (Groq/Llama)   │         └──────────┘  └──────────┘  │ 13 araç  │
└─────────────────┘                                      └──────────┘
                                        │
┌───────────────────────────────────────▼─────────────────────┐
│                     Integrations                            │
│  KKB · MASAK · BOA · TCMB/EVDS3 · SWIFT                    │
│  (Canlı HTTP bağlantısı veya deterministik mock fallback)   │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Ajan Konfigürasyonu

### 3.1 Temel Yapı (`agents_config.json`)

| Alan | Tip | Açıklama |
|------|-----|----------|
| `id` | string | Benzersiz tanımlayıcı (ör. `credit_risk_analyst_001`) |
| `role` | string | Görev adı |
| `department` | string | Departman |
| `specialization` | string | Detaylı uzmanlık tanımı |
| `authority_level` | int 1–5 | Yetki seviyesi |
| `base_instructions` | string | LLM'e gönderilen sistem komutu |
| `tools` | string[] | Kullanabileceği araç adları |
| `data_access` | string[] | Erişebileceği veri kategorileri |
| `escalation_path` | string | Yükseltme zinciri |
| `compliance_flags` | string[] | Uyumluluk çerçeveleri (BDDK, FATF, vb.) |
| `max_auto_approval_amount` | float | Otomatik onay üst limiti (TRY) |
| `audit_required` | bool | Denetim kaydı zorunluluğu |

### 3.2 Yetki Seviyeleri

| Seviye | Ad | Yetkiler |
|--------|----|----------|
| 1 | Salt okunur | Yalnızca analiz ve tavsiye |
| 2 | Tavsiye | Aksiyon önerir; onay gerektirir |
| 3 | Uygulama | Onaylı parametreler dahilinde işlem yapar |
| 4 | Onaylama | `max_auto_approval_amount` limitine kadar onayla |
| 5 | Yönetici | Düzenleyici sınırlar dahilinde tam yetki |

### 3.3 Departman Dağılımı

| Departman | Ajan Sayısı |
|-----------|-------------|
| Credit Risk | 10 |
| Customer Service | 10 |
| AML/KYC | 8 |
| Fraud Detection | 8 |
| Regulatory Compliance | 8 |
| Corporate & SME Banking | 6 |
| Data Quality | 6 |
| IT & Cybersecurity | 6 |
| Operations & Process | 6 |
| Retail Banking | 6 |
| Treasury & Liquidity | 6 |
| **TOPLAM** | **80** |

---

## 4. Çekirdek Modüller

### 4.1 `BaseAgent` (Anthropic/Claude)

**Dosya:** `core/base_agent.py`

| Sabit | Değer |
|-------|-------|
| `MODEL` | `claude-opus-4-6` |
| `MAX_TOKENS` | 8192 |
| `MAX_TOOL_LOOPS` | 15 |

**Akış:**
1. `chat(message)` → konuşma geçmişine ekle
2. `_call_api()` → Claude'a gönder (`thinking: adaptive` ile)
3. Yanıtta araç çağrısı varsa → `execute_tool()` → sonucu history'ye ekle
4. `stop_reason == "end_turn"` veya araç kalmadı → metni döndür
5. Döngü 15 turu aşarsa hata mesajı döndür

**Sistem Komutu İçeriği:**
- Ajan kimliği (ID, rol, departman, yetki seviyesi)
- `base_instructions` (config'den)
- Operasyonel kısıtlar (max onay miktarı, yükseltme yolu)
- Uyumluluk çerçevesi listesi
- Veri erişim listesi
- Araç kullanım kuralları (5 madde)
- Türkçe/İngilizce iki dilli iletişim standartları

### 4.2 `GroqBaseAgent` (Groq/Llama)

**Dosya:** `core/groq_agent.py`

| Sabit | Değer |
|-------|-------|
| `GROQ_MODEL` | `llama-3.3-70b-versatile` |
| `MAX_TOKENS` | 4096 |
| `MAX_TOOL_LOOPS` | 15 |

Anthropic şema formatını OpenAI/Groq formatına dönüştürür (`_to_openai_tools()`). `PROVIDER=groq` env değişkeniyle aktifleştirilir.

### 4.3 `AgentFactory`

**Dosya:** `core/agent_factory.py`

| İç yapı | Açıklama |
|---------|----------|
| `_configs: dict[str, dict]` | agent_id → konfigürasyon |
| `_instances: dict[str, BaseAgent]` | agent_id → ajan (lazy cache) |
| `_by_role: dict[str, list[str]]` | rol anahtar kelimesi → ID listesi |
| `_by_department: dict[str, list[str]]` | departman → ID listesi |

**`best_agent_for(task)` yönlendirme mantığı:** Görev metnindeki anahtar kelimelere göre departman eşleşmesi yapılır. Eşleşme yoksa varsayılan: `customer_inquiry_agent_027`.

| Anahtar Kelimeler | Yönlendirilen Departman |
|-------------------|------------------------|
| fraud, dolandırıcılık, sahte | Fraud Detection |
| AML, kara para, şüpheli | AML/KYC |
| kredi, loan, mortgage | Credit Risk |
| likidite, FX, hazine | Treasury & Liquidity |
| BDDK, sermaye, Basel | Regulatory Compliance |
| ödeme, EFT, SWIFT | Operations & Process |
| veri kalitesi, data quality | Data Quality |
| siber, güvenlik, hacker | IT & Cybersecurity |
| şikâyet, müşteri, hesap | Customer Service |

### 4.4 `Orchestrator`

**Dosya:** `core/orchestrator.py`

| Metot | Açıklama |
|-------|----------|
| `run(agent_id, task)` | Tek ajana görev gönder |
| `auto(task)` | Otomatik yönlendirme ile görev gönder |
| `pipeline(agent_ids, task)` | Zincirleme: her ajanın çıktısı bir sonrakine girdi olur |
| `broadcast(department, task)` | Tüm departman ajanlarına aynı görevi gönder |

**Pipeline Akışı:**
```
task → Ajan A → (task + A çıktısı) → Ajan B → (task + A+B çıktıları) → Ajan C → ...
```

---

## 5. Araç Katmanı (Tool Registry)

**Dosya:** `core/tool_registry.py`

Toplam **43 araç** kayıtlı. Her araç: bir JSON şema (LLM'e açıklama) + bir Python fonksiyon çiftidir.

### 5.1 Bankacılık Araçları (13 araç)

| Araç | Fonksiyon | Açıklama |
|------|-----------|----------|
| `database_query` | `execute_database_query` | BOA core banking SQL benzeri sorgu |
| `customer_360_lookup` | `execute_customer_360` | Müşteri 360 profili |
| `transaction_history` | `execute_transaction_history` | İşlem geçmişi |
| `credit_bureau_api` | `execute_credit_bureau` | KKB kredi bürosu sorgusu |
| `risk_scoring_engine` | `execute_risk_scoring` | ML tabanlı risk skoru |
| `payment_gateway` | `execute_payment_gateway` | EFT/FAST/HAVALE/SWIFT ödeme |
| `swift_api` | `execute_swift_api` | SWIFT mesaj gönder/al |
| `collateral_valuation` | `execute_collateral_valuation` | Teminat değerleme |
| `stress_test_engine` | `execute_stress_test` | Stres testi senaryoları |
| `portfolio_analytics` | `execute_portfolio_analytics` | Portföy analizi |
| `ml_model_inference` | `execute_ml_inference` | Genel ML model çağrısı |
| `market_data_feed` | `execute_market_data` | Piyasa verisi (BIST, FX) |
| `fx_rate_api` | `execute_fx_rate` | Döviz kuru (TCMB canlı) |

### 5.2 Uyumluluk Araçları (8 araç)

| Araç | Fonksiyon | Açıklama |
|------|-----------|----------|
| `fraud_detection_api` | `execute_fraud_detection` | İşlem/giriş dolandırıcılık skoru |
| `aml_screening` | `execute_aml_screening` | MASAK AML taraması |
| `sanctions_check` | `execute_sanctions_check` | Yaptırım listesi sorgusu |
| `kyc_verification` | `execute_kyc_verification` | KYC/kimlik doğrulama |
| `document_ocr` | `execute_document_ocr` | OCR belge çıkarma |
| `data_quality_checker` | `execute_data_quality` | Veri kalitesi kontrolü |
| `data_lineage_api` | `execute_data_lineage` | Veri soy ağacı |
| `regulatory_reporting_api` | `execute_regulatory_reporting` | COREP/FINREP/LCR raporlama |

### 5.3 İletişim Araçları (13 araç)

| Araç | Fonksiyon | Açıklama |
|------|-----------|----------|
| `email_sender` | `execute_email_sender` | E-posta gönder |
| `sms_sender` | `execute_sms_sender` | SMS gönder |
| `alert_manager` | `execute_alert_manager` | Uyarı oluştur/yükselt/çöz |
| `audit_logger` | `execute_audit_logger` | Denetim kaydı (8 yıl saklama) |
| `workflow_trigger` | `execute_workflow_trigger` | İş akışı başlat |
| `approval_request` | `execute_approval_request` | Onay talebi oluştur |
| `report_generator` | `execute_report_generator` | PDF/Excel/JSON rapor üret |
| `dashboard_writer` | `execute_dashboard_writer` | Dashboard metriği güncelle |
| `sentiment_analyzer` | `execute_sentiment_analyzer` | Duygu analizi (TR/EN) |
| `crm_api` | `execute_crm_api` | CRM müşteri aksiyonları |
| `product_catalog` | `execute_product_catalog` | Ürün kataloğu ve uygunluk |
| `hr_system_api` | `execute_hr_system` | İK sistemi |
| `calendar_api` | `execute_calendar_api` | Takvim randevusu |

---

## 6. Entegrasyon Katmanı

Her entegrasyon: canlı HTTP bağlantısı (kimlik bilgisi varsa) veya deterministik mock (yoksa) çalışır. Mock'lar sabit çıktı değil — girdi veriye göre tohum (seed) alarak tutarlı sahte sonuç üretir.

### 6.1 `BaseIntegrationClient`

| Özellik | Değer |
|---------|-------|
| Retry sayısı | 3 (ayarlanabilir) |
| Backoff | `0.5 × 2^(attempt-1)` saniye |
| 401 yönetimi | Otomatik token yenileme |
| Timeout | 15 saniye (ayarlanabilir) |

### 6.2 KKB — Kredi Kayıt Bürosu

**Endpoint:** `https://api.kkb.com.tr/v2`
**Auth:** OAuth2 Client Credentials (`/oauth/token`)
**Ortam değişkenleri:** `KKB_CLIENT_ID`, `KKB_CLIENT_SECRET`, `KKB_MEMBER_CODE`

| Metot | Endpoint | Açıklama |
|-------|----------|----------|
| `get_credit_score()` | `POST /score/inquiry` | Yalnızca skor |
| `get_risk_report()` | `POST /risk-report/query` | Tam risk raporu |

**Döndürülen alanlar:** `credit_score`, `risk_grade` (A/B/C/D), `active_credits`, `payment_history`, `inquiries_last_6m`

### 6.3 MASAK — Mali Suçları Araştırma Kurulu

**Endpoint:** `https://api.masak.gov.tr/v1`
**Auth:** `X-API-Key` ve `X-Institution-Code` header'ları
**Ortam değişkenleri:** `MASAK_API_KEY`, `MASAK_INSTITUTION_CODE`

| Metot | Endpoint |
|-------|----------|
| `screen_customer()` | `POST /screening/customer` |
| `check_watchlist()` | `GET /watchlist/check` |
| `submit_str()` | `POST /str/submit` |

**Tespit edilen tipologiler (8):** STRUCTURING, LAYERING, RAPID_FUND_MOVEMENT, HIGH_RISK_JURISDICTION, ROUND_AMOUNT_PATTERN, CASH_INTENSIVE_BUSINESS, SUSPICIOUS_WIRE_TRANSFER, SMURFING

### 6.4 BOA Core Banking

**Endpoint:** `http://<host>:8080/api` (yapılandırılacak)
**Auth:** Belirlenmedi — BOA API detayları netleşince eklenecek
**Ortam değişkenleri:** `BOA_BASE_URL`, `BOA_USERNAME`, `BOA_PASSWORD`, `BOA_API_KEY`

| Metot | Durum |
|-------|-------|
| `get_customer()` | Bağlantı bekleniyor |
| `get_accounts_for_customer()` | Bağlantı bekleniyor |
| `get_transactions()` | Bağlantı bekleniyor |
| `get_loans_for_customer()` | Bağlantı bekleniyor |

### 6.5 TCMB — Türkiye Cumhuriyet Merkez Bankası

İki ayrı veri kaynağı:

#### today.xml (auth gerekmez)
**URL:** `https://www.tcmb.gov.tr/kurlar/today.xml`
Desteklenen dövizler: USD, EUR, GBP, CHF, JPY, SAR, AED, AUD, CAD, CNY, DKK, NOK, SEK, KWD

#### EVDS3 (kullanıcı adı + şifre + API key gerekir)
**Base URL:** `https://evds3.tcmb.gov.tr/igmevdsms-dis`
**Login:** `POST /public/login?lang=TR` → JSESSIONID cookie
**Veri sorgusu:** `POST /fe` (cookie + `key` header birlikte gerekli)

**Kritik payload alanları:**
```json
{
  "ozelFormuller": [],      ← boş array (string değil!)
  "frequency": "1",         ← 1=günlük, 5=aylık
  "formulas": "0"           ← 0=seviye, 1=aylık%, 2=yıllık%
}
```

**Aktif seri kodları:**

| Veri | Seri Kodu | Frekans |
|------|-----------|---------|
| Politika faizi | `TP.PY.P06.1HI` | Günlük |
| Gecelik repo | `TP.AOFOBAP` | Günlük |
| TLREF | `TP.BISTTLREF.ORAN` | Günlük |
| TÜFE endeks | `TP.TUKFIY2025.GENEL` | Aylık |
| ÜFE endeks | `TP.TUFE1YI.T1` | Aylık |
| USD/TRY (alış) | `TP.DK.USD.A.YTL` | Günlük |
| EUR/TRY (alış) | `TP.DK.EUR.A.YTL` | Günlük |

**Ortam değişkenleri:** `TCMB_USERNAME`, `TCMB_PASSWORD`, `TCMB_API_KEY`

---

## 7. REST API

**Çerçeve:** FastAPI
**Çalıştırma:** `uvicorn api.server:app --reload --port 8080`

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| GET | `/health` | Sistem durumu |
| GET | `/stats` | Ajan istatistikleri |
| GET | `/departments` | Departman listesi |
| GET | `/agents` | Tüm ajanlar (`?department=` filtresi) |
| GET | `/agents/{id}` | Ajan detayı |
| POST | `/agents/{id}/chat` | Ajana mesaj gönder |
| POST | `/auto` | Otomatik yönlendirme ile mesaj |
| POST | `/pipeline` | Zincirleme çoklu ajan |

**CORS:** `allow_origins=["*"]` (geliştirme ortamı — üretimde kısıtlanmalı)

---

## 8. Sağlayıcı Yapılandırması

`.env` dosyasındaki `PROVIDER` değişkeni ile seçilir:

| `PROVIDER` değeri | Kullanılan sınıf | Model |
|-------------------|-----------------|-------|
| `anthropic` (varsayılan) | `BaseAgent` | `claude-opus-4-6` |
| `groq` | `GroqBaseAgent` | `llama-3.3-70b-versatile` |

---

## 9. Test Altyapısı

**Çalıştırma:** `python -m pytest tests/ -q`
**Toplam:** 68 test, 2 dosya

| Dosya | Sınıf | Test Sayısı | Kapsam |
|-------|-------|-------------|--------|
| `test_integration.py` | TestToolRegistry, TestBaseAgent, TestOrchestrator, TestAPIServer | ~40 | Core agent, tool execution, API |
| `test_integrations.py` | TestIntegrationConfig, TestKKBClient, TestMASAKClient, TestBOAClient, TestTCMBClient, TestToolsUseIntegrations | ~28 | Entegrasyon katmanı, mock fallback'ler |

Testler gerçek HTTP çağrısı yapmaz; entegrasyonlar mock mod üzerinden test edilir.

---

## 10. Ortam Değişkenleri

| Değişken | Zorunlu | Açıklama |
|----------|---------|----------|
| `ANTHROPIC_API_KEY` | Evet* | Claude API anahtarı |
| `GROQ_API_KEY` | Evet* | Groq API anahtarı (*provider'a göre) |
| `PROVIDER` | Hayır | `anthropic` veya `groq` (varsayılan: `anthropic`) |
| `TCMB_USERNAME` | Hayır | EVDS3 kullanıcı adı |
| `TCMB_PASSWORD` | Hayır | EVDS3 şifresi |
| `TCMB_API_KEY` | Hayır | EVDS3 API anahtarı |
| `KKB_CLIENT_ID` | Hayır | KKB OAuth2 istemci ID |
| `KKB_CLIENT_SECRET` | Hayır | KKB OAuth2 istemci gizli anahtar |
| `KKB_MEMBER_CODE` | Hayır | KKB üye kodu |
| `MASAK_API_KEY` | Hayır | MASAK API anahtarı |
| `MASAK_INSTITUTION_CODE` | Hayır | MASAK kurum kodu |
| `BOA_BASE_URL` | Hayır | BOA REST API adresi |
| `BOA_USERNAME` | Hayır | BOA kullanıcı adı |
| `BOA_PASSWORD` | Hayır | BOA şifresi |
| `USE_MOCK_INTEGRATIONS` | Hayır | `true`/`false` (varsayılan: `true`) |
| `INTEGRATION_HTTP_TIMEOUT` | Hayır | HTTP zaman aşımı saniye (varsayılan: 15) |
| `INTEGRATION_HTTP_RETRIES` | Hayır | Yeniden deneme sayısı (varsayılan: 3) |

---

## 11. Bağımlılıklar

| Paket | Versiyon | Kullanım |
|-------|----------|----------|
| `anthropic` | >=0.40.0 | Claude API istemcisi |
| `python-dotenv` | >=1.0.0 | .env yükleyici |
| `pydantic` | >=2.0.0 | Veri doğrulama (API modelleri) |
| `rich` | >=13.0.0 | CLI görsel çıktı |
| `httpx` | >=0.27.0 | Async HTTP istemcisi (entegrasyonlar) |
| `fastapi` | >=0.110.0 | REST API çerçevesi |
| `uvicorn[standard]` | >=0.29.0 | ASGI sunucu |

---

## 12. Proje Yapısı

```
bank_agents/
├── agents_config.json          # 80 ajan konfigürasyonu
├── main.py                     # CLI giriş noktası
├── requirements.txt
├── .env                        # Kimlik bilgileri (git'te yok)
├── .env.example                # Şablon
├── api/
│   └── server.py               # FastAPI REST API
├── core/
│   ├── agent_factory.py        # Ajan fabrikası + yönlendirme
│   ├── base_agent.py           # Anthropic/Claude ajan
│   ├── groq_agent.py           # Groq/Llama ajan
│   ├── orchestrator.py         # Çok-ajan orkestrasyon
│   └── tool_registry.py        # Araç kayıt ve çalıştırma
├── integrations/
│   ├── config.py               # Kimlik bilgisi yönetimi
│   ├── base_client.py          # HTTP istemci temeli
│   ├── kkb_client.py           # Kredi Kayıt Bürosu
│   ├── masak_client.py         # AML/MASAK
│   ├── boa_client.py           # Core Banking (BOA)
│   └── tcmb_client.py          # TCMB döviz + EVDS3
├── tools/
│   ├── banking_tools.py        # 13 bankacılık aracı
│   ├── compliance_tools.py     # 8 uyumluluk aracı
│   └── communication_tools.py  # 13 iletişim aracı
└── tests/
    ├── test_integration.py     # Core/API testleri
    └── test_integrations.py    # Entegrasyon testleri
```
