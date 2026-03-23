# BankAI — Komut Referansı

Tüm komutlar proje kök dizininde çalıştırılır: `cd C:\Users\iQM\Desktop\bank_agents`

---

## Kurulum & Hazırlık

```bash
# Bağımlılıkları kur
pip install -r requirements.txt

# .env dosyasını hazırla (kopyala ve düzenle)
copy .env.example .env
# .env içine ekle:
#   ANTHROPIC_API_KEY=sk-ant-...
#   GROQ_API_KEY=gsk_...
#   PROVIDER=anthropic   # veya groq

# RAG veritabanını oluştur (dokümanlar yükle)
python training/ingest.py

# Sistem durumunu kontrol et
python main.py --stats
python main.py --list
```

---

## Provider Seçimi

```bash
# Anthropic Claude (varsayılan)
set PROVIDER=anthropic
python main.py --demo

# Groq llama-3.3-70b
set PROVIDER=groq
python main.py --demo
```

---

## Genel Kullanım

```bash
# İnteraktif mod (sohbet arayüzü)
python main.py

# Demo modunda 5 hazır senaryo çalıştır
python main.py --demo

# Tüm ajanları listele
python main.py --list

# Departmana göre ajan listesi
python main.py --list --dept "Credit Risk"
python main.py --list --dept "Fraud Detection"
python main.py --list --dept "AML/KYC"
python main.py --list --dept "Customer Service"
python main.py --list --dept "Treasury & Liquidity"
python main.py --list --dept "Regulatory Compliance"
python main.py --list --dept "Retail Banking"
python main.py --list --dept "Corporate & SME Banking"
python main.py --list --dept "Operations & Process"
python main.py --list --dept "IT & Cybersecurity"
python main.py --list --dept "Data Quality"

# Ajan ağı istatistikleri
python main.py --stats

# Otomatik rotalama (en uygun ajanı sistem seçer)
python main.py --auto --task "Müşteri C12345 için kredi riski değerlendirmesi"
python main.py --auto --task "Şüpheli işlem tespiti gerekiyor"
python main.py --auto --task "KVKK uyum kontrolü"
```

---

## Tek Ajan Komutları (--agent)

### 1. KREDİ RİSKİ

```bash
# credit_risk_analyst_001 — Kredi Riski Analisti (L2)
python main.py --agent credit_risk_analyst_001 --task "Müşteri C12345 için 500,000 TRY, 60 ay ihtiyaç kredisi. Aylık net gelir 15,000 TRY, kredi skoru 720. Risk değerlendir, DTI hesapla, ONAY/RED/ESKALASYON ver."

# loan_application_reviewer_002 — Kredi Başvuru Gözden Geçirici (L1)
python main.py --agent loan_application_reviewer_002 --task "Gelen bireysel kredi başvurusunda gelir belgesi eksik, kimlik fotokopisi bulanık. Eksik belgeler listesi oluştur, hangi aşamaya yönlendir?"

# credit_scoring_agent_003 — Kredi Skorlama Ajanı (L2)
python main.py --agent credit_scoring_agent_003 --task "Müşteri C22222: Aylık gelir 30,000 TRY, toplam borç 120,000 TRY, büro skoru 680. Scorecard çalıştır, skor üret, pozitif/negatif faktörleri açıkla."

# portfolio_risk_monitor_004 — Portföy Risk Monitörü (L2)
python main.py --agent portfolio_risk_monitor_004 --task "Kurumsal kredi portföyümüzde son çeyrekte NPL oranı %3.2'den %4.8'e yükseldi. Hangi sektörler etkileniyor? Erken uyarı sinyalleri neler?"

# collateral_evaluator_005 — Teminat Değerlendirici (L2)
python main.py --agent collateral_evaluator_005 --task "Istanbul Kadıköy'de ticari gayrimenkul teminat olarak sunuldu. Tapu değeri 3.5M TRY. BDDK iskonto oranları uygulandığında net teminat değeri nedir?"

# npl_manager_007 — Takipteki Kredi Yöneticisi (L3)
python main.py --agent npl_manager_007 --task "Müşteri C55000, 2.5M TRY kurumsal kredisinde 95 gündür ödeme yok. Teminat İstanbul ticari gayrimenkul. Tahsilat stratejisi, hukuki süreç başlatılmalı mı?"

# stress_test_agent_008 — Stres Test Ajanı (L2)
python main.py --agent stress_test_agent_008 --task "Faiz oranları 500 baz puan artsa kredi portföyümüze etkisi nedir? NPL oranı ve sermaye yeterlilik oranı nasıl değişir?"

# corporate_credit_analyst_010 — Kurumsal Kredi Analisti (L2)
python main.py --agent corporate_credit_analyst_010 --task "ABC İnşaat A.Ş. 15M TRY proje finansmanı istiyor. Son 3 yıl bilançoları mevcut. EBITDA/Borç oranı, LTV analizi yap, Kredi Komitesi'ne eskalas mı?"
```

### 2. DOLANDIRICILIK TESPİTİ

```bash
# transaction_fraud_detector_011 — İşlem Fraud Dedektörü (L3)
python main.py --agent transaction_fraud_detector_011 --task "Müşteri C98765 yeni kayıtlı alıcıya 85,000 TRY transfer başlattı. Normal limiti 5,000 TRY, IP Romanya'dan, yeni cihaz. Risk skoru hesapla, islem bloke et mi?"

# account_takeover_detector_012 — Hesap Devralma Dedektörü (L3)
python main.py --agent account_takeover_detector_012 --task "Son 30 dakikada: şifre değişikliği, e-posta güncelleme, 3 farklı şehirden giriş, büyük transfer. Hesap devralma (ATO) riski var mı?"

# card_fraud_analyst_013 — Kart Fraud Analisti (L3)
python main.py --agent card_fraud_analyst_013 --task "Aynı kart 20 dakika arayla Istanbul ve Dubai'de kullanıldı. Istanbul: 2,500 TRY market, Dubai: 4,200 USD elektronik. Geolocation fraud mu? Kart bloke et mi?"

# online_fraud_monitor_014 — Online Fraud Monitörü (L3)
python main.py --agent online_fraud_monitor_014 --task "Son 1 saatte 500 farklı IP'den login denemesi, %80 başarısız. Credential stuffing saldırısı mı? Önlem al."

# fraud_investigation_agent_016 — Fraud Soruşturma Ajanı (L3)
python main.py --agent fraud_investigation_agent_016 --task "12 farklı müşteriden benzer dolandırıcılık şikayeti, hepsi aynı POS terminali kullanmış. Organize fraud mu? Soruşturma başlat."

# fraud_alert_manager_017 — Fraud Alert Yöneticisi (L2)
python main.py --agent fraud_alert_manager_017 --task "Sistemde 45 aktif fraud alarmı var, 8 tanesi kritik seviyede. Önceliklendirme yap, hangi alarmlar hemen aksiyon gerektiriyor?"
```

### 3. AML/KYC

```bash
# aml_transaction_monitor_019 — AML İşlem Monitörü (L3)
python main.py --agent aml_transaction_monitor_019 --task "Müşteri C77777 6 ay içinde 45 farklı hesaptan küçük miktarlı havale aldı (structuring), toplam 890,000 TRY. AML riski nedir? STR gerekli mi?"

# kyc_verification_agent_020 — KYC Doğrulama Ajanı (L2)
python main.py --agent kyc_verification_agent_020 --task "Yeni müşteri: Ahmed Al-Rashid, BAE vatandaşı, İstanbul'da inşaat şirketi kurucusu. KYC süreci nasıl işlemeli? Enhanced due diligence gerekir mi?"

# suspicious_activity_reporter_021 — Şüpheli İşlem Raporlayıcı (L3)
python main.py --agent suspicious_activity_reporter_021 --task "Müşteri C88888: 3 ayda yabancı hesaplara 2.1M TRY havale, açıklama yok. MASAK'a STR (Şüpheli İşlem Bildirimi) hazırla."

# pep_screening_agent_022 — PEP Tarama Ajanı (L2)
python main.py --agent pep_screening_agent_022 --task "Yeni müşteri Ahmet Yılmaz, eski Maliye Bakanlığı danışmanı. PEP kapsamında mı? Risk değerlendirmesi ve ek kontroller."

# sanctions_screening_agent_023 — Yaptırım Tarama Ajanı (L4)
python main.py --agent sanctions_screening_agent_023 --task "Gelen SWIFT MT103: USD 250,000 'Al Baraka Trading LLC'den BAE muhabir banka üzerinden. OFAC, UN, AB, MASAK listeleriyle tara."

# beneficial_owner_analyzer_024 — Nihai Yararlanan Analisti (L2)
python main.py --agent beneficial_owner_analyzer_024 --task "XYZ Holding Ltd, Cayman adaları kayıtlı. Şirket yapısını analiz et, nihai yararlanan sahipleri tespit et."

# wire_transfer_monitor_026 — Havale Monitörü (L3)
python main.py --agent wire_transfer_monitor_026 --task "Günlük 12 yurt dışı havale, toplam 1.2M USD. Alıcılar Cayman, BVI, Panama. CTR raporu gerekli mi? Offshore risk var mı?"
```

### 4. MÜŞTERİ HİZMETLERİ

```bash
# customer_inquiry_agent_027 — Müşteri Sorgu Ajanı (L1)
python main.py --agent customer_inquiry_agent_027 --task "Müşteri hesap bakiyesini ve son 10 işlemini sormak istiyor. Müşteri ID: C10050."

# complaint_handler_029 — Şikayet Yöneticisi (L2)
python main.py --agent complaint_handler_029 --task "3 hafta önce yapılan EFT karşıya ulaşmadı, müşteri şikayet etti. Şikayet ID SHK-2026-001. Süreci başlat, tazminat değerlendirmesi yap."

# product_recommendation_agent_030 — Ürün Öneri Ajanı (L1)
python main.py --agent product_recommendation_agent_030 --task "28 yaşında, aylık 8,000 TRY gelirli, orta risk profilli müşteri için birikim ve yatırım ürünü öner."

# vip_customer_service_agent_034 — VIP Müşteri Hizmetleri (L3)
python main.py --agent vip_customer_service_agent_034 --task "VIP müşteri Müşteri C10001, son 3 ay faiz ödemelerini, döviz mevduat bakiyelerini ve yatırım portföy performansını sormaktadır."

# churn_prevention_agent_032 — Müşteri Kayıp Önleme (L2)
python main.py --agent churn_prevention_agent_032 --task "Müşteri C33333 son 3 ayda işlem hacmi %70 düştü, rakip bankadan kredi teklifi aldığı biliniyor. Kayıp riski ve koruma stratejisi nedir?"

# multilingual_support_agent_036 — Çok Dilli Destek (L1)
python main.py --agent multilingual_support_agent_036 --task "A customer wrote: 'My account is frozen and I have urgent payments. Please help me immediately.' Respond and guide them."
```

### 5. HAZİNE & LİKİDİTE

```bash
# liquidity_monitor_043 — Likidite Monitörü (L3)
python main.py --agent liquidity_monitor_043 --task "LCR oranı %118, NSFR %105. Yarın büyük tahvil ödemeleri var. Likidite riski değerlendir, acil önlem gerekir mi?"

# fx_risk_manager_044 — Kur Riski Yöneticisi (L3)
python main.py --agent fx_risk_manager_044 --task "EUR/TRY son 24 saatte %4 arttı. Portföyde 50M EUR açık pozisyon var. VaR hesapla, hedge stratejisi öner."

# interest_rate_risk_agent_045 — Faiz Risk Ajanı (L2)
python main.py --agent interest_rate_risk_agent_045 --task "TCMB faiz oranı 250 baz puan artırdı. Değişken faizli mevduat portföyüne ve kredi marjlarına etkisi nedir?"

# cash_flow_forecaster_046 — Nakit Akışı Tahmincisi (L1)
python main.py --agent cash_flow_forecaster_046 --task "Önümüzdeki 30 gün nakit akışı tahmini yap. Büyük ödemeler: 5M TRY (15. gün), 12M TRY (28. gün). Fon açığı oluşur mu?"

# funding_strategy_agent_048 — Fonlama Stratejisi Ajanı (L2)
python main.py --agent funding_strategy_agent_048 --task "Önümüzdeki çeyrekte 500M TRY fonlamaya ihtiyaç var. Mevduat artırımı mı, bono ihracı mı, TCMB reposu mu? Maliyetleri karşılaştır."
```

### 6. MEVZUAT UYUM

```bash
# regulatory_reporting_agent_049 — Düzenleyici Raporlama (L3)
python main.py --agent regulatory_reporting_agent_049 --task "Aylık BDDK COREP raporu için verileri derle. Sermaye yeterlilik oranı, NPL oranı ve LCR verilerini hazırla."

# gdpr_compliance_agent_051 — KVKK Uyum Ajanı (L3)
python main.py --agent gdpr_compliance_agent_051 --task "Eski müşteri C99999 KVKK 'unutulma hakkı' kullanıyor. Hangi sistemlerdeki veriler silinmeli? Yasal saklama süresi kontrolü yap."

# capital_adequacy_agent_054 — Sermaye Yeterliligi Ajanı (L2)
python main.py --agent capital_adequacy_agent_054 --task "CET1 oranı %11.2, BDDK minimum %9.0. Yeni 500M TRY'lik kurumsal kredi portföyünün RWA etkisini hesapla."

# internal_audit_agent_052 — İç Denetim Ajanı (L2)
python main.py --agent internal_audit_agent_052 --task "Kredi onay süreci iç denetim kontrolü: son 6 ayda onaylanan 50 kredi dosyasında otomasyon hataları var mı? Bulgular raporla."

# policy_compliance_checker_053 — Politika Uyum Denetçisi (L2)
python main.py --agent policy_compliance_checker_053 --task "Yeni kredi politikası değişikliği: DTI limiti %50'den %45'e indirildi. Bu değişiklik mevcut portföyün %8'ini etkiliyor. Uyum eylem planı hazırla."

# regulatory_change_monitor_056 — Mevzuat Değişiklik Monitörü (L1)
python main.py --agent regulatory_change_monitor_056 --task "BDDK son 3 ayda yayımladığı sirküler ve yönetmeliklerin önemli değişikliklerini özetle."
```

### 7. BİREYSEL BANKACILIK

```bash
# mortgage_advisor_agent_057 — Konut Kredisi Danışmanı (L2)
python main.py --agent mortgage_advisor_agent_057 --task "35 yaşında çift, toplam net gelir 45,000 TRY/ay, 1.2M TRY'lik daire için %30 peşin ödeyebiliyorlar. En uygun konut kredisi vadesi ve faiz önerisi."

# personal_loan_agent_058 — Bireysel Kredi Ajanı (L3)
python main.py --agent personal_loan_agent_058 --task "Müşteri 80,000 TRY ihtiyaç kredisi istiyor. Aylık gelir 12,000 TRY, aktif 2 kredi var. Kredi onayı, vade ve aylık taksit hesabı."

# credit_card_agent_060 — Kredi Kartı Ajanı (L3)
python main.py --agent credit_card_agent_060 --task "Müşteri C44444 kredi kartı limitini 30,000'den 75,000 TRY'ye artırmak istiyor. Aylık gelir 18,000 TRY, mevcut borç 12,000 TRY. Onay kriterleri?"

# savings_product_agent_059 — Tasarruf Ürün Ajanı (L2)
python main.py --agent savings_product_agent_059 --task "Müşteri 50,000 TRY birikimini 3-6 ay vadeli değerlendirmek istiyor, risk almak istemiyor. TRY/döviz mevduat seçeneklerini karşılaştır."
```

### 8. KURUMSAL & KOBİ BANKACILIK

```bash
# sme_advisor_agent_064 — KOBİ Danışmanı (L2)
python main.py --agent sme_advisor_agent_064 --task "Tekstil KOBİ'si, ihracat yapıyor, 5M TRY ciro, 50 çalışan. Yeni makine alımı için 2M TRY finansman arıyor. KOBİ kredi seçenekleri ve KOSGEB destekleri."

# trade_finance_agent_065 — Dış Ticaret Finansmanı (L3)
python main.py --agent trade_finance_agent_065 --task "İhracatçı firma Almanya'ya 500,000 EUR'luk mal gönderiyor, Alman alıcı akreditif istiyor. LC türleri, belgeler, risk değerlendirmesi."

# corporate_fx_agent_067 — Kurumsal FX Ajanı (L3)
python main.py --agent corporate_fx_agent_067 --task "İthalat şirketinin 3M EUR borc taksiti 30 gün içinde. EUR/TRY volatil. Forward mu, opsiyon mu kullanmalı? Hedge stratejisi."

# supply_chain_finance_agent_068 — Tedarik Zinciri Finansmanı (L3)
python main.py --agent supply_chain_finance_agent_068 --task "Büyük bir perakende zinciri, tedarikçilerine 90 gün vade verdiği için nakit sıkışıklığı yaşıyor. Tedarik zinciri finansmanı çözümü öner."
```

### 9. OPERASYONLAR & SÜREÇ

```bash
# payment_processing_agent_069 — Ödeme İşleme Ajanı (L3)
python main.py --agent payment_processing_agent_069 --task "Batch EFT: 500 ödeme emri, toplam 8.5M TRY. 3 ödeme hatalı IBAN, 2 ödeme kara listedeki bankaya gidiyor. Nasıl yönetelim?"

# swift_message_agent_070 — SWIFT Mesaj Ajanı (L3)
python main.py --agent swift_message_agent_070 --task "Gelen SWIFT MT202: USD 1.2M muhabir bankadan. Mesajı parse et, muhabir bankayı doğrula, hesap kredilendirme başlat."

# reconciliation_agent_071 — Mutabakat Ajanı (L2)
python main.py --agent reconciliation_agent_071 --task "Günlük NOSTRO mutabakatında 3 kalem fark: +50,000 TRY, -12,000 TRY, +3,200 TRY. Fark nedenlerini analiz et."

# sla_monitor_agent_074 — SLA Monitör Ajanı (L2)
python main.py --agent sla_monitor_agent_074 --task "Bugün 45 işlem SLA ihlali yaşandı: 30 EFT işlemi 4 saat gecikti, 15 kredi onayı 2 günü geçti. Kök neden analizi ve iyileştirme önerileri."
```

### 10. IT & SİBER GÜVENLİK

```bash
# cybersecurity_monitor_075 — Siber Güvenlik Monitörü (L3)
python main.py --agent cybersecurity_monitor_075 --task "SIEM'den alarm: iç ağda yetkisiz lateral movement, 3 sunucu etkilendi, Active Directory erişim girişimi var. Ön değerlendirme yap."

# incident_response_agent_077 — Olay Müdahale Ajanı (L4)
python main.py --agent incident_response_agent_077 --task "Ransomware tespiti: 5 işçi istasyonu şifrelendi, kritik sistemler etkilenmedi, izole edildi. Incident response planı başlat, BCM protokolunu aktifleştir."

# access_control_agent_076 — Erişim Kontrol Ajanı (L3)
python main.py --agent access_control_agent_076 --task "İşten ayrılan eski çalışan hesabı 30 gün sonra hala aktif ve core banking'e giriş yapmış. Hesabı kapat, erişim loglarını incele."

# vulnerability_scanner_agent_078 — Zafiyet Tarama Ajanı (L2)
python main.py --agent vulnerability_scanner_agent_078 --task "İnternet bankacılığı uygulamasında kritik güvenlik açığı raporu geldi: SQL Injection zafiyeti. Risk değerlendirmesi ve acil yama planı."

# api_security_agent_079 — API Güvenlik Ajanı (L3)
python main.py --agent api_security_agent_079 --task "Open Banking API'de anormal trafik: saniyede 10,000 istek, normal 200. DDoS mi yoksa scraping mi? Önlem al."
```

### 11. VERİ KALİTESİ

```bash
# data_quality_monitor_037 — Veri Kalite Monitörü (L2)
python main.py --agent data_quality_monitor_037 --task "Müşteri segmentasyon verisinde %8 boşluk oranı, 252 müşteride doğum tarihi eksik, 1,200 müşteride adres yanlış. Veri kalite skoru ve önceliklendirme."

# data_reconciliation_agent_038 — Veri Mutabakat Ajanı (L2)
python main.py --agent data_reconciliation_agent_038 --task "Core banking ile raporlama sistemi arasında 20M TRY fark var. Core: 15.2B TRY, Raporlama: 15.18B TRY. Kaynak analiz et."

# data_anomaly_detector_041 — Veri Anomali Dedektörü (L2)
python main.py --agent data_anomaly_detector_041 --task "Kredi portföy raporunda anormallik tespiti: geçen aya göre kurumsal kredi toplamı %35 artmış ama yeni onay sayısı azalmış. Açıkla."
```

---

## Pipeline Senaryoları (Sıralı Çok Ajan)

Pipeline'da her ajan bir öncekinin çıktısını alır.

```bash
# Senaryo 1: NPL Tahsilat Pipeline
python -c "
from dotenv import load_dotenv; load_dotenv()
from core.orchestrator import Orchestrator
o = Orchestrator()
result = o.pipeline(
    ['npl_manager_007', 'collateral_evaluator_005', 'suspicious_activity_reporter_021'],
    'Müşteri C55000, 2.5M TRY kurumsal kredisinde 95 gündür gecikme. Teminat: İstanbul ticari gayrimenkul. Hesabı incele, teminat kapsimını değerlendir, AML endişesi raporla.'
)
print('Pipeline tamamlandi:', list(result.keys()))
"

# Senaryo 2: KYC + Kredi + Raporlama Pipeline
python -c "
from dotenv import load_dotenv; load_dotenv()
from core.orchestrator import Orchestrator
o = Orchestrator()
o.pipeline(
    ['kyc_verification_agent_020', 'credit_risk_analyst_001', 'regulatory_reporting_agent_049'],
    'XYZ Holding 10M TRY kredi istiyor. Önce KYC tamamla, sonra kredi analizi yap, son olarak BDDK raporlama gereksinimlerini kontrol et.'
)
"

# Senaryo 3: Fraud + AML + STR Pipeline
python -c "
from dotenv import load_dotenv; load_dotenv()
from core.orchestrator import Orchestrator
o = Orchestrator()
o.pipeline(
    ['transaction_fraud_detector_011', 'aml_transaction_monitor_019', 'suspicious_activity_reporter_021'],
    'Müşteri C98765, 45 dakikada 5 farklı hesaba toplam 400,000 TRY dağıttı. Önce fraud kontrol, sonra AML analizi, sonra STR karar ver.'
)
"

# Senaryo 4: Siber Olay Müdahale Pipeline
python -c "
from dotenv import load_dotenv; load_dotenv()
from core.orchestrator import Orchestrator
o = Orchestrator()
o.pipeline(
    ['cybersecurity_monitor_075', 'incident_response_agent_077', 'access_control_agent_076'],
    'Banka ağında ransomware tespiti: 5 iş istasyonu şifrelendi. Sistematik müdahale başlat.'
)
"
```

---

## Paralel Senaryo Komutları

Birden fazla ajan aynı anda çalışır.

```bash
# Senaryo 1: Çok Boyutlu Risk Analizi (paralel)
python -c "
from dotenv import load_dotenv; load_dotenv()
from core.orchestrator import Orchestrator
o = Orchestrator()
results = o.parallel(
    ['credit_risk_analyst_001', 'transaction_fraud_detector_011', 'aml_transaction_monitor_019'],
    'Müşteri C77777 için kapsamlı risk analizi: kredi, fraud ve AML riskini aynı anda değerlendir.'
)
for k, v in results.items(): print(f'{k}: {v[:80]}...')
"

# Senaryo 2: Uyum Paralel Kontrol
python -c "
from dotenv import load_dotenv; load_dotenv()
from core.orchestrator import Orchestrator
o = Orchestrator()
results = o.parallel(
    ['gdpr_compliance_agent_051', 'capital_adequacy_agent_054', 'regulatory_reporting_agent_049'],
    'Yıl sonu uyum kontrolü: KVKK durumu, sermaye yeterliliği ve düzenleyici raporlama aynı anda değerlendir.'
)
"

# Senaryo 3: Paralel + Sentez (parallel_then_merge)
python -c "
from dotenv import load_dotenv; load_dotenv()
from core.orchestrator import Orchestrator
o = Orchestrator()
final = o.parallel_then_merge(
    parallel_ids=['corporate_credit_analyst_010', 'aml_transaction_monitor_019', 'collateral_evaluator_005'],
    merge_id='credit_risk_analyst_001',
    task='DEF Holding 20M TRY kredi başvurusu: kredi analizi, AML taraması ve teminat değerlendirmesini paralel yap, sonra sentezle.'
)
print('Sentez sonucu:', final[:200])
"
```

---

## Supervisor (Otomatik Rotalama)

LLM hangi ajanların çalıştırılacağına otomatik karar verir.

```bash
# Supervisor — tek komutla çalıştır
python -c "
from dotenv import load_dotenv; load_dotenv()
from core.supervisor import Supervisor
sup = Supervisor()
result = sup.run('Müşteri C99 için kapsamlı fraud ve AML değerlendirmesi yap.')
print('Mod:', result['mode'])
print('Routing:', result['routing'])
"

python -c "
from dotenv import load_dotenv; load_dotenv()
from core.supervisor import Supervisor
sup = Supervisor()
result = sup.run('XYZ A.Ş. 8M TRY kredi istiyor, KYC ve kredi analizi tamamlansın.')
print('Mod:', result['mode'])
"

python -c "
from dotenv import load_dotenv; load_dotenv()
from core.supervisor import Supervisor
sup = Supervisor()
result = sup.run('Banka ağında şüpheli aktivite var, siber güvenlik ve fraud ekibi aynı anda değerlendirsin.')
print('Mod:', result['mode'], '| Ajanlar:', result.get('routing'))
"
```

---

## Müşteri Hafızası (Memory) Senaryoları

Aynı müşteri ID'si ile sürekli konuşma geçmişi birikir.

```bash
# Cok turlu müşteri diyalogu
python -c "
from dotenv import load_dotenv; load_dotenv()
from core.agent_factory import get_factory
f = get_factory()
agent = f.get('customer_inquiry_agent_027')
cid = 'TEST_C_001'
# Tur 1
agent.chat('Merhaba, hesap bakiyemi öğrenebilir miyim?', customer_id=cid)
# Tur 2
agent.chat('Geçen ay kaç EFT yaptım?', customer_id=cid)
# Tur 3 — önceki konuşmaları hatırlamalı
agent.chat('Bir önceki sorumdaki hesap durumu hakkında ek bilgi verir misin?', customer_id=cid)
"

# Müşteri hafızasını görüntüle
python -c "
from core.memory import get_history, build_context_block
history = get_history('TEST_C_001')
for h in history:
    print(f'[{h[\"role\"]}] {h[\"content\"][:80]}')
"

# Müşteri verisini sil (KVKK unutulma hakkı)
python -c "
from core.memory import delete_customer
delete_customer('TEST_C_001')
print('Müşteri verisi silindi.')
"
```

---

## RAG (Bilgi Tabanı) Komutları

```bash
# Dokümanları RAG veritabanına yükle
python training/ingest.py

# RAG sistemini test et
python -c "
from training.retriever import retrieve, is_ready, retrieve_with_scores
print('Hazir mi:', is_ready())
# Semantik arama
result = retrieve('kredi skoru eşikleri', domains=['credit_risk'], top_k=3)
print(result)
# Skorlarla arama
scored = retrieve_with_scores('fraud tespiti kuralları', domains=['fraud_detection'])
for r in scored:
    print(f'Skor: {r[\"relevance\"]:.3f} | {r[\"text\"][:80]}')
"

# Hybrid RAG (BM25 + Semantik) test
python -c "
from training.retriever import retrieve
# use_hybrid=True (varsayılan)
result = retrieve('şüpheli işlem bildirimi STR', domains=['aml_kyc'], top_k=5, use_hybrid=True)
print(result[:500])
"
```

---

## Test Suite Komutları

```bash
# Tüm testleri çalıştır (uzun sürer — API çağrıları yapar)
python test_agents.py --group all

# Sadece altyapı testleri (API çağrısı yok, hızlı)
python test_agents.py --group pii
python test_agents.py --group hitl
python test_agents.py --group rag

# Departman bazlı testler
python test_agents.py --group credit_risk
python test_agents.py --group fraud_detection
python test_agents.py --group aml_kyc
python test_agents.py --group customer_service
python test_agents.py --group treasury_liquidity
python test_agents.py --group regulatory_compliance
python test_agents.py --group retail_banking
python test_agents.py --group corporate_sme
python test_agents.py --group operations
python test_agents.py --group it_cybersecurity
python test_agents.py --group data_quality

# Çok-ajan testleri
python test_agents.py --group pipeline
python test_agents.py --group parallel
python test_agents.py --group memory
python test_agents.py --group supervisor

# Belirli bir ajanı test et
python test_agents.py --agent credit_risk_analyst_001 --task "500,000 TRY kredi başvurusu değerlendir."
python test_agents.py --agent transaction_fraud_detector_011 --task "Yüksek riskli transfer tespit edildi."

# Groq ile test
python test_agents.py --group credit_risk --provider groq

# Dry-run (API çağrısı simüle eder, tool guard test eder)
python test_agents.py --group fraud_detection --dry-run
```

---

## Monitoring & Metrik Komutları

```bash
# Son 24 saatlik metrik özeti
python -c "
from core.metrics import summary
data = summary(hours=24)
for agent in data['agents']:
    print(f'{agent[\"agent_id\"]}: {agent[\"calls\"]} çağrı, {agent[\"avg_latency\"]:.0f}ms ort.')
"

# Belirli bir ajanın geçmişi
python -c "
from core.metrics import agent_history
rows = agent_history('credit_risk_analyst_001', limit=10)
for r in rows:
    print(r)
"

# Metrikleri JSONL olarak dışa aktar
python -c "
from core.metrics import export_jsonl
export_jsonl('data/metrics_export.jsonl', hours=168)
print('Dışa aktarıldı: data/metrics_export.jsonl')
"

# Orchestrator üzerinden metrik tablosu
python -c "
from dotenv import load_dotenv; load_dotenv()
from core.orchestrator import Orchestrator
Orchestrator().metrics(hours=24)
"
```

---

## HITL (İnsan Denetimi) Komutları

```bash
# Bekleyen inceleme kuyruğunu görüntüle
python -c "
from core.hitl import get_pending, stats
print('HITL İstatistikleri:', stats())
pending = get_pending(limit=5)
for p in pending:
    print(f'ID: {p[\"id\"]} | Güven: {p[\"confidence\"]:.2f} | {p[\"agent_id\"]}')
    print(f'  Yanıt: {p[\"agent_response\"][:100]}...')
"

# Etkileşimli HITL inceleme CLI'ını başlat
python -c "
from core.hitl import review_cli
review_cli()
"

# HITL istatistikleri
python -c "
from core.hitl import stats
s = stats()
print(f'Toplam: {s[\"total\"]} | Bekleyen: {s[\"pending\"]} | Çözümlendi: {s[\"resolved\"]}')
"
```

---

## Fine-tuning Veri Pipeline Komutları

```bash
# Karar loglarını görüntüle
python training/decision_logger.py stats

# SFT (Supervised Fine-Tuning) formatında dışa aktar
python training/decision_logger.py export --output data/finetune_sft.jsonl

# DPO (Direct Preference Optimization) formatında dışa aktar
python training/decision_logger.py export-dpo --output data/finetune_dpo.jsonl

# Sadece etiketlenmiş ve kaliteli kararları dışa aktar (min_quality=4)
python -c "
from training.decision_logger import export_finetune_jsonl
export_finetune_jsonl('data/finetune_quality.jsonl', labeled_only=True, min_quality=4)
print('Dışa aktarıldı.')
"
```

---

## PII Maskeleme Komutları

```bash
# PII tarama ve maskeleme testi
python -c "
from core.pii_guard import mask, scan, has_pii
# Tarama
text = 'Müşteri TC: 12345678901, IBAN: TR330006100519786457841326'
found = scan(text)
print('Bulunan PII:', found)
# Maskeleme
masked, counts = mask(text)
print('Maskelendi:', masked)
print('Sayım:', counts)
"

# Tool sonuçlarında PII maskeleme
python -c "
from core.pii_guard import guard_tool_result
result = {'customer_tc': '12345678901', 'iban': 'TR330006100519786457841326', 'balance': 50000}
masked = guard_tool_result('database_query', result)
print('Maskelenen sonuç:', masked)
"
```

---

## API Sunucusu (FastAPI)

```bash
# API sunucusunu başlat
uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload

# Health check
curl http://localhost:8000/health

# Ajan çalıştır (REST API üzerinden)
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d "{\"agent_id\": \"credit_risk_analyst_001\", \"task\": \"Kredi başvurusu değerlendir.\"}"
```

---

## Hızlı Senaryo Koleksiyonu (Kopyala-Çalıştır)

### Senaryo A — Yüksek Riskli Müşteri Profili (Tam Pipeline)
```bash
python -c "
from dotenv import load_dotenv; load_dotenv()
from core.orchestrator import Orchestrator
o = Orchestrator()
task = 'Müşteri C99999: Son 6 ayda offshore hesaplara 3.5M TRY transfer, kredi başvurusu da var.'
o.pipeline(
    ['kyc_verification_agent_020', 'aml_transaction_monitor_019',
     'credit_risk_analyst_001', 'suspicious_activity_reporter_021'],
    task
)
"
```

### Senaryo B — Siber Olay + Fraud Paralel Yanıt
```bash
python -c "
from dotenv import load_dotenv; load_dotenv()
from core.orchestrator import Orchestrator
o = Orchestrator()
task = 'Banka sistemlerine sızılmış olabilir, aynı anda fraud artışı gözlemleniyor. Acil durum değerlendirmesi.'
results = o.parallel(
    ['cybersecurity_monitor_075', 'transaction_fraud_detector_011', 'incident_response_agent_077'],
    task, max_workers=3
)
"
```

### Senaryo C — Kurumsal Müşteri 360° Görünüm
```bash
python -c "
from dotenv import load_dotenv; load_dotenv()
from core.orchestrator import Orchestrator
o = Orchestrator()
task = 'DEF Holding için 360 derece değerlendirme: kredi riski, AML durumu, teminat ve FX riskleri.'
final = o.parallel_then_merge(
    parallel_ids=['corporate_credit_analyst_010', 'aml_transaction_monitor_019',
                  'collateral_evaluator_005', 'corporate_fx_agent_067'],
    merge_id='credit_risk_analyst_001',
    task=task
)
"
```

### Senaryo D — Gün Sonu Kontrol Listesi
```bash
python -c "
from dotenv import load_dotenv; load_dotenv()
from core.orchestrator import Orchestrator
o = Orchestrator()
task = 'Gün sonu kapanış kontrolleri: LCR durumu, açık fraud alarmları, bekleyen HITL kuyruğu.'
results = o.parallel(
    ['liquidity_monitor_043', 'fraud_alert_manager_017', 'sla_monitor_agent_074'],
    task
)
"
```

---

## Ortam Değişkenleri Referansı

| Değişken | Değer | Açıklama |
|---|---|---|
| `PROVIDER` | `anthropic` / `groq` | LLM sağlayıcısı |
| `ANTHROPIC_API_KEY` | `sk-ant-...` | Anthropic API anahtarı |
| `GROQ_API_KEY` | `gsk_...` | Groq API anahtarı |
| `DRY_RUN` | `true` / `false` | Gerçek tool çağrısı yapma |
| `HF_TOKEN` | `hf_...` | HuggingFace token (opsiyonel) |

---

## Departman → Agent ID Hızlı Referans

| Departman | Agent ID'leri |
|---|---|
| Credit Risk | 001–010 |
| Fraud Detection | 011–018 |
| AML/KYC | 019–026 |
| Customer Service | 027–036 |
| Data Quality | 037–042 |
| Treasury & Liquidity | 043–048 |
| Regulatory Compliance | 049–056 |
| Retail Banking | 057–062 |
| Corporate & SME Banking | 063–068 |
| Operations & Process | 069–074 |
| IT & Cybersecurity | 075–080 |
