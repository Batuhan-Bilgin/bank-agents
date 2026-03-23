"""
BankAI - Kapsamli Ajan Test Suiti
Tum 80 ajanı ve 11 departmanı test eder.
Kullanim: python test_agents.py [--group GROUP] [--agent AGENT_ID] [--dry-run] [--provider PROVIDER]
"""

import argparse
import json
import os
import sys
import time
import traceback
from typing import Callable

from dotenv import load_dotenv
load_dotenv()

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

# ─── Test Scenaryo Katalogu ───────────────────────────────────────────────────

SCENARIOS = {

    # ── 1. KREDİ RİSKİ ──────────────────────────────────────────────────────
    "credit_risk": {
        "label": "Credit Risk",
        "tests": [
            {
                "id": "cr-01",
                "agent": "credit_risk_analyst_001",
                "name": "Bireysel Kredi Degerlendirmesi",
                "task": (
                    "Musteri C12345 icin 500,000 TRY tutarinda 60 ay vadeli "
                    "ihtiyac kredisi basvurusu. Aylik net gelir: 15,000 TRY, "
                    "kredi skoru 720, aktif 1 kredi karti borcu var. "
                    "Risk degerlendir, DTI hesapla ve ONAY/RED/ESKALASYON ver."
                ),
            },
            {
                "id": "cr-02",
                "agent": "loan_application_reviewer_002",
                "name": "Eksik Belge Tespiti",
                "task": (
                    "Gelen bireysel kredi basvurusunda gelir belgesi eksik, "
                    "kimlik fotokopisi bulanik. Hangi belgeler eksik, "
                    "basvuru hangi asama icin hazir? Eksik belge listesi olustur."
                ),
            },
            {
                "id": "cr-03",
                "agent": "credit_scoring_agent_003",
                "name": "Kredi Skoru Hesaplama",
                "task": (
                    "Musteri C22222: Aylik gelir 30,000 TRY, toplam borc 120,000 TRY, "
                    "kredi burosu skoru 680, 3 yillik hesap gecmisi temiz. "
                    "Scorecard calistir, skor uret, pozitif/negatif faktorleri acikla."
                ),
            },
            {
                "id": "cr-04",
                "agent": "npl_manager_007",
                "name": "Takipteki Kredi Yonetimi",
                "task": (
                    "Musteri C55000, 2.5M TRY kurumsal kredisinde 95 gundur "
                    "odeme yapmamakta. Teminat Istanbul'da ticari gayrimenkul. "
                    "Tahsilat stratejisi olustur, hukuki surec baslat mi?"
                ),
            },
            {
                "id": "cr-05",
                "agent": "corporate_credit_analyst_010",
                "name": "Kurumsal Kredi Analizi",
                "task": (
                    "ABC Insaat A.S. 15M TRY'lik proje finansmani istiyor. "
                    "Son 3 yil bilancolarini degerlendirmemi istiyorlar. "
                    "EBITDA/Borc orani, LTV ve kredi komitesi eskalasyon karari ver."
                ),
            },
        ],
    },

    # ── 2. DOLANDIRICILIK TESPİTİ ────────────────────────────────────────────
    "fraud_detection": {
        "label": "Fraud Detection",
        "tests": [
            {
                "id": "fd-01",
                "agent": "transaction_fraud_detector_011",
                "name": "Suphe Uyandiran Transfer",
                "task": (
                    "Musteri C98765 yeni kayit edilen bir aliciya mobil bankadan "
                    "85,000 TRY transfer baslatti. Musteri normalde 5,000 TRY limit. "
                    "IP Romanya'dan, yeni cihaz. Risk skoru hesapla, islem bloke et mi?"
                ),
            },
            {
                "id": "fd-02",
                "agent": "account_takeover_detector_012",
                "name": "Hesap Devralma Girişimi",
                "task": (
                    "Son 30 dakikada musteri hesabinda: sifre degisikligi, "
                    "e-posta guncelleme, 3 farkli sehirden giris denemesi, "
                    "buyuk para transferi. Hesap devralma (ATO) risk analizi yap."
                ),
            },
            {
                "id": "fd-03",
                "agent": "card_fraud_analyst_013",
                "name": "Kart Dolandiriciligi",
                "task": (
                    "Musteri kartinda 20 dakika arayla Istanbul ve Dubai'de "
                    "islem gerceklesti. Istanbul: 2,500 TRY market, "
                    "Dubai: USD 4,200 elektronik. Geolocation fraud midir? Kart bloke et mi?"
                ),
            },
            {
                "id": "fd-04",
                "agent": "fraud_investigation_agent_016",
                "name": "Fraud Sorusturmasi",
                "task": (
                    "Cikarildi: Son 2 ayda 12 farkli musteriden gelen "
                    "benzer dolandiricilik sikayeti, hepsi ayni POS terminali kullanmis. "
                    "Orgu mu var? Sistematik fraud investigasyonu baslat."
                ),
            },
            {
                "id": "fd-05",
                "agent": "online_fraud_monitor_014",
                "name": "Online Kanal İzleme",
                "task": (
                    "Internet banking kanalinda son 1 saatte anomali: "
                    "500 farkli IP'den login denemesi, yuzde 80 basarisiz. "
                    "Credential stuffing saldirisı mi? Ne yapilmali?"
                ),
            },
        ],
    },

    # ── 3. AML/KYC ──────────────────────────────────────────────────────────
    "aml_kyc": {
        "label": "AML/KYC",
        "tests": [
            {
                "id": "ak-01",
                "agent": "sanctions_screening_agent_023",
                "name": "SWIFT Yaptirım Taraması",
                "task": (
                    "Gelen SWIFT MT103: USD 250,000 'Al Baraka Trading LLC'den "
                    "BAE muhabir banka uzerinden. Gonderen ve tum tarafları "
                    "OFAC, UN, AB, MASAK listeleriyle tara. Sonuc raporla."
                ),
            },
            {
                "id": "ak-02",
                "agent": "aml_transaction_monitor_019",
                "name": "Kara Para Aklama Tarama",
                "task": (
                    "Musteri C77777, 6 ay icinde 45 farkli hesaptan "
                    "kucuk miktarli havale aldi (structuring pattern). "
                    "Toplam 890,000 TRY. AML riski degerlendir, STR gerekli mi?"
                ),
            },
            {
                "id": "ak-03",
                "agent": "kyc_verification_agent_020",
                "name": "Yeni Musteri KYC",
                "task": (
                    "Yeni musteri onboarding: Ahmed Al-Rashid, BAE vatandasi, "
                    "Istanbul'da insaat sirketi kurucu. Pasaport sundu. "
                    "KYC dogrulama süreci, enhanced due diligence gerekir mi?"
                ),
            },
            {
                "id": "ak-04",
                "agent": "pep_screening_agent_022",
                "name": "PEP Taraması",
                "task": (
                    "Yeni musteri Ahmet Yilmaz, eski Maliye Bakanligi danismani. "
                    "Siyasi acidan ifsat edilmis kisi (PEP) mi? "
                    "Risk degerlendirmesi ve ek kontroller belirle."
                ),
            },
            {
                "id": "ak-05",
                "agent": "wire_transfer_monitor_026",
                "name": "Uluslararasi Havale İzleme",
                "task": (
                    "Gunluk 12 farkli yurt disi havale, toplam 1.2M USD, "
                    "alicilar Cayman Adaları, BVI, Panama. "
                    "Offshor yapi sezgisi var mi? CTR raporu gerekli mi?"
                ),
            },
        ],
    },

    # ── 4. MÜŞTERİ HİZMETLERİ ────────────────────────────────────────────────
    "customer_service": {
        "label": "Customer Service",
        "tests": [
            {
                "id": "cs-01",
                "agent": "vip_customer_service_agent_034",
                "name": "VIP Musteri Sorgusu",
                "task": (
                    "VIP musteri Musteri C10001, son 3 ay faiz odemelerini "
                    "ve doviz mevduat bakiyelerini soruyor. "
                    "Ayrica yatirim portfoyu performans raporu istiyor."
                ),
            },
            {
                "id": "cs-02",
                "agent": "complaint_handler_029",
                "name": "Sikayet Yonetimi",
                "task": (
                    "Musteri, 3 hafta once yaptigi EFT'nin karsiya ulasmadigini "
                    "soyleyerek sikayet etti. Sikayet ID: SHK-2026-001. "
                    "Durumu incele, cozum sureci baslat, tazminat degerlendirmesi yap."
                ),
            },
            {
                "id": "cs-03",
                "agent": "product_recommendation_agent_030",
                "name": "Urun Onerisi",
                "task": (
                    "28 yasinda, aylik 8,000 TRY gelirli, duzenli tasarruf yapan "
                    "bir musteri icin en uygun birikim ve yatirim urunu onerisi yap. "
                    "Risk profili orta duzey."
                ),
            },
            {
                "id": "cs-04",
                "agent": "churn_prevention_agent_032",
                "name": "Musteri Kayip Onleme",
                "task": (
                    "Musteri C33333, son 3 ayda islem hacmi yuzde 70 dusmus, "
                    "rakip bankadan kredi teklifi aldigi belli oluyor. "
                    "Kayip riski ne kadar? Koruma stratejisi olustur."
                ),
            },
            {
                "id": "cs-05",
                "agent": "multilingual_support_agent_036",
                "name": "Cok Dilli Destek",
                "task": (
                    "A customer is asking: 'I need to know why my account was "
                    "frozen and how I can unfreeze it. I have urgent payments.' "
                    "Assess and respond appropriately."
                ),
            },
        ],
    },

    # ── 5. HAZİNE & LİKİDİTE ─────────────────────────────────────────────────
    "treasury_liquidity": {
        "label": "Treasury & Liquidity",
        "tests": [
            {
                "id": "tl-01",
                "agent": "liquidity_monitor_043",
                "name": "LCR İzleme",
                "task": (
                    "Bugunun LCR orani yuzde 118, NSFR yuzde 105. "
                    "Yarinki beklenen buyuk tahvil odemeleri var. "
                    "Likidite riski degerlendir, acil onlem gerekir mi?"
                ),
            },
            {
                "id": "tl-02",
                "agent": "fx_risk_manager_044",
                "name": "Kur Riski Yonetimi",
                "task": (
                    "EUR/TRY paritesi son 24 saatte yuzde 4 artti. "
                    "Portfoyde 50M EUR acik pozisyon var. "
                    "VaR hesapla, hedge stratejisi oner, limitleri kontrol et."
                ),
            },
            {
                "id": "tl-03",
                "agent": "cash_flow_forecaster_046",
                "name": "Nakit Akisi Tahmini",
                "task": (
                    "Onumuzdeki 30 gun icin nakit akisi tahmini yap. "
                    "Buyuk kredi odemeleri: 5M TRY (15. gun), 12M TRY (28. gun). "
                    "Fon acigi olusur mu? Likidite tamponu yeterli mi?"
                ),
            },
        ],
    },

    # ── 6. MEVZUAT UYUM ───────────────────────────────────────────────────────
    "regulatory_compliance": {
        "label": "Regulatory Compliance",
        "tests": [
            {
                "id": "rc-01",
                "agent": "regulatory_reporting_agent_049",
                "name": "BDDK Raporlamasi",
                "task": (
                    "Aylik BDDK COREP raporu icin verileri derlememiz lazim. "
                    "Sermaye yeterlilik orani, NPL orani ve LCR verilerini "
                    "raporlama formatinda hazirla, eksik verileri flag et."
                ),
            },
            {
                "id": "rc-02",
                "agent": "gdpr_compliance_agent_051",
                "name": "KVKK Veri Silme Talebi",
                "task": (
                    "Eski musteri C99999, KVKK kapsaminda 'unutulma hakki' kullaniyor. "
                    "Hangi sistemlerdeki verileri silmemiz gerekiyor? "
                    "Yasal saklama suresi bitmis kayitlar var mi?"
                ),
            },
            {
                "id": "rc-03",
                "agent": "capital_adequacy_agent_054",
                "name": "Sermaye Yeterliligi",
                "task": (
                    "CET1 orani yuzde 11.2, BDDK minimum yuzde 9.0. "
                    "Yeni 500M TRY'lik kurumsal kredi portfoyunun RWA etkisini "
                    "hesapla. Sermaye tamponumuz yeterli mi?"
                ),
            },
            {
                "id": "rc-04",
                "agent": "internal_audit_agent_052",
                "name": "İc Denetim",
                "task": (
                    "Kredi onay sureci ic denetim kontrolu: son 6 ayda "
                    "onaylanan 50 kredi dosyasinda otomasyon hatalari var mi? "
                    "Denetim bulgulari raporla, kontrol zafiyetlerini tespit et."
                ),
            },
        ],
    },

    # ── 7. BİREYSEL BANKACILIK ───────────────────────────────────────────────
    "retail_banking": {
        "label": "Retail Banking",
        "tests": [
            {
                "id": "rb-01",
                "agent": "mortgage_advisor_agent_057",
                "name": "Konut Kredisi Danismanligi",
                "task": (
                    "35 yasinda cift, toplam net gelir 45,000 TRY/ay. "
                    "1.2M TRY'lik daire almak istiyorlar, yuzde 30 pesin odeyebilirler. "
                    "En uygun konut kredisi vadesi ve faiz orani onerisi yap."
                ),
            },
            {
                "id": "rb-02",
                "agent": "credit_card_agent_060",
                "name": "Kredi Karti Yonetimi",
                "task": (
                    "Musteri C44444 kredi karti limitini 30,000 TRY'den "
                    "75,000 TRY'ye cikarmak istiyor. Aylik gelir 18,000 TRY, "
                    "mevcut kart borcu 12,000 TRY. Onay kriterleri saglanmakta mi?"
                ),
            },
            {
                "id": "rb-03",
                "agent": "savings_product_agent_059",
                "name": "Tasarruf Urun Tavsiyesi",
                "task": (
                    "Musteri 50,000 TRY birikimiyle en yuksek getiriyi istiyor. "
                    "Vade tercihi 3-6 ay, risk almak istemiyor. "
                    "Mevcut TRY/doviz mevduat faizlerini karsilastir, en iyi secenegi sun."
                ),
            },
        ],
    },

    # ── 8. KURUMSAl & KOBİ BANKACILIK ───────────────────────────────────────
    "corporate_sme": {
        "label": "Corporate & SME Banking",
        "tests": [
            {
                "id": "cb-01",
                "agent": "sme_advisor_agent_064",
                "name": "KOBİ Danismanlik",
                "task": (
                    "Tekstil KOBIsi, ihracat yapıyor, 5M TRY ciro, 50 calisan. "
                    "Yeni makine alimi icin 2M TRY finansman ariyor. "
                    "KOBI kredi secenekleri, KOSGEB destekleri, uygun vade onerisi."
                ),
            },
            {
                "id": "cb-02",
                "agent": "trade_finance_agent_065",
                "name": "Dis Ticaret Finansmani",
                "task": (
                    "Ihracatci firma Almanya'ya 500,000 EUR'luk mal gonderiyor. "
                    "Alici Alman sirket, akreditif istiyor. "
                    "LC turleri karsilastir, belgeler listesi ver, risk degerlendir."
                ),
            },
            {
                "id": "cb-03",
                "agent": "corporate_fx_agent_067",
                "name": "Kurumsal FX Danismanlik",
                "task": (
                    "Ithalat sirketinin 3M EUR'luk ithalat borc taksiti var, 30 gun vadeli. "
                    "EUR/TRY volatil. Forward sozlesme mi, opsiyon mu kullanmali? "
                    "Mevcut piyasa kosullarinda hedge stratejisi olustur."
                ),
            },
        ],
    },

    # ── 9. OPERASYONLAR ───────────────────────────────────────────────────────
    "operations": {
        "label": "Operations & Process",
        "tests": [
            {
                "id": "op-01",
                "agent": "payment_processing_agent_069",
                "name": "Odeme İsleme",
                "task": (
                    "Batch EFT islemi: 500 adet odeme emri, toplam 8.5M TRY. "
                    "3 odeme hatali IBAN ile geldi, 2 odeme yabanci kara listedeki "
                    "bankaya gidiyor. Islemi nasil yonetelim?"
                ),
            },
            {
                "id": "op-02",
                "agent": "swift_message_agent_070",
                "name": "SWIFT Mesaj İsleme",
                "task": (
                    "Gelen SWIFT MT202: USD 1.2M muhabir bankadan fon transferi. "
                    "MT202 mesaj icerigini parse et, muhabir bankayi dogrula, "
                    "hesap kredilendirme akisini baslat."
                ),
            },
            {
                "id": "op-03",
                "agent": "reconciliation_agent_071",
                "name": "Mutabakat",
                "task": (
                    "Gunluk NOSTRO mutabakatinda 3 kalem fark var: "
                    "+50,000 TRY, -12,000 TRY, +3,200 TRY. "
                    "Fark nedenlerini analiz et, mutabakat kayitlari guncelle."
                ),
            },
        ],
    },

    # ── 10. IT & SİBER GÜVENLİK ──────────────────────────────────────────────
    "it_cybersecurity": {
        "label": "IT & Cybersecurity",
        "tests": [
            {
                "id": "cy-01",
                "agent": "cybersecurity_monitor_075",
                "name": "Siber Guvenlik İzleme",
                "task": (
                    "SIEM sisteminden alarm: Banka ic aginda yetkisiz lateral movement. "
                    "3 sunucu etkilendi, Active Directory'e erisim girisi var. "
                    "Olay on tespiti yap, critical mi?"
                ),
            },
            {
                "id": "cy-02",
                "agent": "incident_response_agent_077",
                "name": "Siber Olay Mudahale",
                "task": (
                    "Ransomware saldirisı tespiti: 5 isci istasyonu sifrelendi, "
                    "kritik olmayan sistemler etkilendi, izole edildi. "
                    "Incident response plani baslat, BCM protokolunu aktifles."
                ),
            },
            {
                "id": "cy-03",
                "agent": "access_control_agent_076",
                "name": "Erisim Kontrol",
                "task": (
                    "Eski calisan (istten ayrılma 30 gun once) hesabi hala aktif. "
                    "Core banking sistemine 2 defa giris yapmis. "
                    "Hesabi kapat, erisim loglarini incele, disiplin sureci baslat mi?"
                ),
            },
        ],
    },

    # ── 11. VERİ KALİTESİ ────────────────────────────────────────────────────
    "data_quality": {
        "label": "Data Quality",
        "tests": [
            {
                "id": "dq-01",
                "agent": "data_quality_monitor_037",
                "name": "Veri Kalitesi İzleme",
                "task": (
                    "Musteri segmentasyon verisinde yuzde 8 bosluk orani var, "
                    "252 musteride dogum tarihi eksik, 1,200 musteride adres yanlis. "
                    "Veri kalite skoru hesapla, duzeltme onceliklendirmesi yap."
                ),
            },
            {
                "id": "dq-02",
                "agent": "data_reconciliation_agent_038",
                "name": "Mutabakat Analizi",
                "task": (
                    "Core banking ile raporlama sistemi arasinda bakiye farki: "
                    "Core banking toplam: 15.2B TRY, Raporlama: 15.18B TRY. "
                    "Fark: 20M TRY. Kaynak analiz et, hangi segment etkilenmis?"
                ),
            },
        ],
    },
}

# ─── Paralel / Supervisor Senaryolari ────────────────────────────────────────

PIPELINE_SCENARIOS = [
    {
        "id": "pipe-01",
        "name": "NPL Tahsilat Pipeline",
        "type": "pipeline",
        "agents": ["npl_manager_007", "collateral_evaluator_005", "suspicious_activity_reporter_021"],
        "task": (
            "Musteri C55000, 2.5M TRY kurumsal kredisinde 95 gunduR gecikme. "
            "Teminat: Istanbul'da ticari gayrimenkul. Hesabi gozden gecir, "
            "teminat kapsimini degerlendir, AML endisesi var mi raporla."
        ),
    },
    {
        "id": "pipe-02",
        "name": "KYC + Kredi Onay Pipeline",
        "type": "pipeline",
        "agents": ["kyc_verification_agent_020", "credit_risk_analyst_001", "regulatory_reporting_agent_049"],
        "task": (
            "Yeni kurumsal musteri: XYZ Holding, 10M TRY kredi istiyor. "
            "Once KYC tamamla, sonra kredi analizi yap, son olarak BDDK raporlama gereksinimlerini kontrol et."
        ),
    },
    {
        "id": "pipe-03",
        "name": "Fraud + AML Pipeline",
        "type": "pipeline",
        "agents": ["transaction_fraud_detector_011", "aml_transaction_monitor_019", "suspicious_activity_reporter_021"],
        "task": (
            "Suphe uyandiran islem: Musteri C98765, "
            "45 dakikada 5 farkli hesaba toplam 400,000 TRY dagitti. "
            "Once fraud kontrol, sonra AML analizi, sonra STR karar ver."
        ),
    },
]

PARALLEL_SCENARIOS = [
    {
        "id": "par-01",
        "name": "Risk Paralel Analiz",
        "type": "parallel",
        "agents": ["credit_risk_analyst_001", "transaction_fraud_detector_011", "aml_transaction_monitor_019"],
        "task": (
            "Musteri C77777 icin kapsamli risk analizi: "
            "Kredi riski, fraud riski ve AML riski ayni anda degerlendir."
        ),
    },
    {
        "id": "par-02",
        "name": "Uyum Paralel Kontrol",
        "type": "parallel",
        "agents": ["gdpr_compliance_agent_051", "capital_adequacy_agent_054", "regulatory_reporting_agent_049"],
        "task": (
            "Yil sonu uyum kontrol: KVKK durum, sermaye yeterliligi ve "
            "duzenleyici raporlama durumu ayni anda degerlendir."
        ),
    },
    {
        "id": "par-03",
        "name": "Kurumsal Kredi Paralel + Sentez",
        "type": "parallel_then_merge",
        "agents": ["corporate_credit_analyst_010", "aml_transaction_monitor_019", "collateral_evaluator_005"],
        "merge_agent": "credit_risk_analyst_001",
        "task": (
            "DEF Holding 20M TRY kredi basvurusu: "
            "Kredi analizi, AML taramasi ve teminat degerlendirmesini paralel yap, "
            "sonra sentezle."
        ),
    },
]

MEMORY_SCENARIOS = [
    {
        "id": "mem-01",
        "name": "Cok Turlu Musteri Diyalogu",
        "agent": "customer_inquiry_agent_027",
        "customer_id": "TEST_C_001",
        "turns": [
            "Merhaba, hesap bakiyemi ogrenebilir miyim?",
            "Gecen ay kac EFT yaptim?",
            "Daha once bahsettigim hesap durumu hakkinda ek bilgi verebilir misin?",
        ],
    },
    {
        "id": "mem-02",
        "name": "VIP Musteri Surekli Hafiza",
        "agent": "vip_customer_service_agent_034",
        "customer_id": "VIP_C_999",
        "turns": [
            "Portfoyumdeki hisse senetlerinin performansini gormek istiyorum.",
            "Dolar mevduatimi artirmali miyim?",
            "Bir onceki konusmamizda bahsettigimiz hedging stratejisini uygulamali miyim?",
        ],
    },
]

SUPERVISOR_SCENARIOS = [
    {
        "id": "sup-01",
        "name": "Supervisor - Otomatik Rotalama",
        "task": "Musteri C99 icin kapsamli fraud ve AML degerlendirmesi yap.",
    },
    {
        "id": "sup-02",
        "name": "Supervisor - Kredi Karari",
        "task": "XYZ A.S. 8M TRY kredi istiyor, KYC ve kredi analizi tamamlansin.",
    },
]

# ─── Test Runner ─────────────────────────────────────────────────────────────

class TestRunner:

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.results: list[dict] = []
        os.environ["DRY_RUN"] = "true" if dry_run else "false"

    def _run_single(self, agent_id: str, task: str,
                    customer_id: str = "") -> tuple[bool, str, float]:
        from core.orchestrator import Orchestrator
        orch = Orchestrator()
        start = time.time()
        try:
            result = orch.run(agent_id, task, verbose=False)
            elapsed = time.time() - start
            if customer_id:
                # Re-run with customer_id through factory directly
                agent = orch._factory.get(agent_id)
                agent.chat(task, verbose=False, customer_id=customer_id)
            return True, result, elapsed
        except Exception as e:
            elapsed = time.time() - start
            return False, f"HATA: {traceback.format_exc()}", elapsed

    def run_group(self, group_key: str) -> None:
        group = SCENARIOS.get(group_key)
        if not group:
            console.print(f"[red]Bilinmeyen grup: {group_key}[/red]")
            return
        console.rule(f"[cyan]{group['label']} Testleri[/cyan]")
        for test in group["tests"]:
            self._run_test(test)

    def _run_test(self, test: dict) -> None:
        tid = test["id"]
        name = test["name"]
        agent = test["agent"]
        task = test["task"]

        console.print(f"  [dim]{tid}[/dim] [bold]{name}[/bold] "
                      f"[dim]→ {agent}[/dim]")
        ok, result, elapsed = self._run_single(agent, task)
        status = "[green]GECTI[/green]" if ok else "[red]HATALI[/red]"
        console.print(f"       {status} ({elapsed:.1f}s) — "
                      f"{result[:80].replace(chr(10), ' ')}...")
        self.results.append({
            "id": tid, "name": name, "agent": agent,
            "passed": ok, "elapsed": elapsed,
            "error": "" if ok else result[:200],
        })

    def run_pipeline(self, scenario: dict) -> None:
        from core.orchestrator import Orchestrator
        orch = Orchestrator()
        console.print(f"\n[bold yellow]PIPELINE:[/bold yellow] {scenario['name']}")
        console.print(f"  Ajanlar: {' -> '.join(scenario['agents'])}")
        start = time.time()
        try:
            results = orch.pipeline(scenario["agents"], scenario["task"], verbose=False)
            elapsed = time.time() - start
            console.print(f"  [green]GECTI[/green] ({elapsed:.1f}s) — {len(results)} ajan yanit verdi")
            self.results.append({
                "id": scenario["id"], "name": scenario["name"],
                "passed": True, "elapsed": elapsed, "error": "",
            })
        except Exception as e:
            elapsed = time.time() - start
            console.print(f"  [red]HATALI[/red] — {str(e)[:100]}")
            self.results.append({
                "id": scenario["id"], "name": scenario["name"],
                "passed": False, "elapsed": elapsed, "error": str(e)[:200],
            })

    def run_parallel(self, scenario: dict) -> None:
        from core.orchestrator import Orchestrator
        orch = Orchestrator()
        console.print(f"\n[bold magenta]PARALEL:[/bold magenta] {scenario['name']}")
        console.print(f"  Ajanlar: {', '.join(scenario['agents'])}")
        start = time.time()
        try:
            if scenario["type"] == "parallel_then_merge":
                result = orch.parallel_then_merge(
                    scenario["agents"], scenario["merge_agent"],
                    scenario["task"], verbose=False
                )
                console.print(f"  [green]GECTI (merge)[/green] ({time.time()-start:.1f}s)")
            else:
                results = orch.parallel(scenario["agents"], scenario["task"], verbose=False)
                console.print(f"  [green]GECTI[/green] ({time.time()-start:.1f}s) — "
                              f"{len(results)} ajan yanit verdi")
            self.results.append({
                "id": scenario["id"], "name": scenario["name"],
                "passed": True, "elapsed": time.time()-start, "error": "",
            })
        except Exception as e:
            console.print(f"  [red]HATALI[/red] — {str(e)[:100]}")
            self.results.append({
                "id": scenario["id"], "name": scenario["name"],
                "passed": False, "elapsed": time.time()-start, "error": str(e)[:200],
            })

    def run_memory_scenario(self, scenario: dict) -> None:
        from core.orchestrator import Orchestrator
        orch = Orchestrator()
        console.print(f"\n[bold blue]HAFIZA:[/bold blue] {scenario['name']}")
        agent_id = scenario["agent"]
        customer_id = scenario["customer_id"]
        agent = orch._factory.get(agent_id)
        ok = True
        for i, turn in enumerate(scenario["turns"], 1):
            try:
                resp = agent.chat(turn, verbose=False, customer_id=customer_id)
                console.print(f"  Tur {i}: [green]OK[/green] — {resp[:60]}...")
            except Exception as e:
                ok = False
                console.print(f"  Tur {i}: [red]HATALI[/red] — {str(e)[:80]}")
        agent.reset()
        self.results.append({
            "id": scenario["id"], "name": scenario["name"],
            "passed": ok, "elapsed": 0, "error": "",
        })

    def run_supervisor(self, scenario: dict) -> None:
        console.print(f"\n[bold green]SUPERVISOR:[/bold green] {scenario['name']}")
        try:
            from core.supervisor import Supervisor
            sup = Supervisor()
            start = time.time()
            result = sup.run(scenario["task"])
            elapsed = time.time() - start
            console.print(f"  Mod: [cyan]{result.get('mode', '?')}[/cyan] "
                          f"({elapsed:.1f}s) — [green]GECTI[/green]")
            self.results.append({
                "id": scenario["id"], "name": scenario["name"],
                "passed": True, "elapsed": elapsed, "error": "",
            })
        except Exception as e:
            console.print(f"  [red]HATALI[/red] — {str(e)[:100]}")
            self.results.append({
                "id": scenario["id"], "name": scenario["name"],
                "passed": False, "elapsed": 0, "error": str(e)[:200],
            })

    def run_pii_test(self) -> None:
        console.rule("[cyan]PII Maskeleme Testi[/cyan]")
        from core.pii_guard import mask, scan, has_pii
        samples = [
            ("TC Kimlik", "Musteri TC: 12345678901 basvuru yapti."),
            ("IBAN", "Havale IBAN: TR330006100519786457841326"),
            ("Kart No", "Kart: 4111 1111 1111 1111"),
            ("Email", "E-posta: musteri@example.com"),
            ("Telefon", "Telefon: 0532 123 45 67"),
        ]
        all_ok = True
        for name, text in samples:
            masked, counts = mask(text)
            ok = bool(counts)
            status = "[green]GECTI[/green]" if ok else "[red]HATALI[/red]"
            console.print(f"  {status} {name}: {masked}")
            if not ok:
                all_ok = False
        self.results.append({
            "id": "pii-01", "name": "PII Maskeleme",
            "passed": all_ok, "elapsed": 0, "error": "",
        })

    def run_hitl_test(self) -> None:
        console.rule("[cyan]HITL Guven Skoru Testi[/cyan]")
        from core.hitl import score_confidence, needs_review
        samples = [
            ("Kesin Yanit", "Musteri kredi limiti 50,000 TRY olarak belirlendi ve onaylandi.", False),
            ("Belirsiz Yanit", "Bu konuda belirsiz bir durum var, daha fazla bilgi gerekiyor ve net değil.", True),
            ("Yuksek Risk", "Bu işlem kritik seviyede fraud riski taşıyor, eskalasyon gerekli.", True),
        ]
        all_ok = True
        for name, text, expect_review in samples:
            conf, reason = score_confidence(text)
            review, _, _ = needs_review(text)
            ok = (review == expect_review)
            status = "[green]GECTI[/green]" if ok else "[red]HATALI[/red]"
            console.print(f"  {status} {name}: guven={conf:.2f}, inceleme={review} (beklenen={expect_review})")
            if not ok:
                all_ok = False
        self.results.append({
            "id": "hitl-01", "name": "HITL Guven Skoru",
            "passed": all_ok, "elapsed": 0, "error": "",
        })

    def run_rag_test(self) -> None:
        console.rule("[cyan]RAG Arama Testi[/cyan]")
        from training.retriever import retrieve, is_ready
        if not is_ready():
            console.print("  [yellow]ATLANDI[/yellow] — RAG veritabani hazir degil. "
                          "Once: python training/ingest.py")
            self.results.append({
                "id": "rag-01", "name": "RAG Arama",
                "passed": None, "elapsed": 0, "error": "RAG not ready",
            })
            return
        queries = [
            ("Kredi skoru esikleri", "credit_risk"),
            ("Fraud tespiti kuralları", "fraud_detection"),
        ]
        all_ok = True
        for query, domain in queries:
            result = retrieve(query, domains=[domain], top_k=2)
            ok = len(result.strip()) > 10
            status = "[green]GECTI[/green]" if ok else "[red]HATALI[/red]"
            console.print(f"  {status} '{query}': {len(result)} karakter dondu")
            if not ok:
                all_ok = False
        self.results.append({
            "id": "rag-01", "name": "RAG Arama",
            "passed": all_ok, "elapsed": 0, "error": "",
        })

    def print_summary(self) -> None:
        total = len(self.results)
        passed = sum(1 for r in self.results if r["passed"] is True)
        failed = sum(1 for r in self.results if r["passed"] is False)
        skipped = sum(1 for r in self.results if r["passed"] is None)

        console.print()
        table = Table(title="Test Sonuclari")
        table.add_column("ID", style="dim")
        table.add_column("Test", style="white")
        table.add_column("Durum", justify="center")
        table.add_column("Sure (s)", justify="right")

        for r in self.results:
            if r["passed"] is True:
                status = "[green]GECTI[/green]"
            elif r["passed"] is False:
                status = "[red]HATALI[/red]"
            else:
                status = "[yellow]ATLANDI[/yellow]"
            table.add_row(
                r["id"], r["name"], status,
                f"{r['elapsed']:.1f}" if r["elapsed"] else "-"
            )
        console.print(table)

        color = "green" if failed == 0 else "red"
        console.print(Panel(
            f"Toplam: {total}  |  "
            f"[green]Gecti: {passed}[/green]  |  "
            f"[red]Hatali: {failed}[/red]  |  "
            f"[yellow]Atlandi: {skipped}[/yellow]",
            title=f"[{color}]Test Ozeti[/{color}]",
            border_style=color,
        ))


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="BankAI Test Suiti")
    parser.add_argument(
        "--group", type=str, default=None,
        help="Test grubu: credit_risk, fraud_detection, aml_kyc, customer_service, "
             "treasury_liquidity, regulatory_compliance, retail_banking, corporate_sme, "
             "operations, it_cybersecurity, data_quality, pipeline, parallel, memory, "
             "supervisor, pii, hitl, rag, all"
    )
    parser.add_argument("--agent", type=str, default=None,
                        help="Belirli bir ajanı test et (ajan ID + --task gerekli)")
    parser.add_argument("--task", type=str, default=None,
                        help="--agent ile kullanilacak gorev")
    parser.add_argument("--dry-run", action="store_true",
                        help="Gercek API cagrisi yapmadan test et")
    parser.add_argument("--provider", type=str, default=None,
                        choices=["anthropic", "groq"],
                        help="LLM saglayicisi (varsayilan: .env'deki PROVIDER)")
    args = parser.parse_args()

    if args.provider:
        os.environ["PROVIDER"] = args.provider

    runner = TestRunner(dry_run=args.dry_run)

    # Tek ajan testi
    if args.agent and args.task:
        console.rule(f"[cyan]Ajan Testi: {args.agent}[/cyan]")
        ok, result, elapsed = runner._run_single(args.agent, args.task)
        status = "[green]GECTI[/green]" if ok else "[red]HATALI[/red]"
        console.print(f"{status} ({elapsed:.1f}s)")
        console.print(result)
        return

    group = args.group or "all"

    # Modul bazli testler
    infra_tests = ["pii", "hitl", "rag"]
    dept_tests = list(SCENARIOS.keys())

    if group == "all" or group in infra_tests:
        if group == "all" or group == "pii":
            runner.run_pii_test()
        if group == "all" or group == "hitl":
            runner.run_hitl_test()
        if group == "all" or group == "rag":
            runner.run_rag_test()

    if group == "all" or group in dept_tests:
        groups_to_run = dept_tests if group == "all" else [group]
        for g in groups_to_run:
            if g in SCENARIOS:
                runner.run_group(g)

    if group == "all" or group == "pipeline":
        console.rule("[cyan]Pipeline Testleri[/cyan]")
        for scenario in PIPELINE_SCENARIOS:
            runner.run_pipeline(scenario)

    if group == "all" or group == "parallel":
        console.rule("[cyan]Paralel Testler[/cyan]")
        for scenario in PARALLEL_SCENARIOS:
            runner.run_parallel(scenario)

    if group == "all" or group == "memory":
        console.rule("[cyan]Hafiza Testleri[/cyan]")
        for scenario in MEMORY_SCENARIOS:
            runner.run_memory_scenario(scenario)

    if group == "all" or group == "supervisor":
        console.rule("[cyan]Supervisor Testleri[/cyan]")
        for scenario in SUPERVISOR_SCENARIOS:
            runner.run_supervisor(scenario)

    runner.print_summary()


if __name__ == "__main__":
    main()
