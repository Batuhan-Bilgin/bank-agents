import os
os.environ["PROVIDER"] = "groq"

from core.orchestrator import Orchestrator

orch = Orchestrator()

print("=" * 60)
print("MULTI-AGENT PIPELINE TESTI")
print("=" * 60)

gorev = input("\nGorev gir: ")

print("\nHangi pipeline?")
print("1. Kredi Baskuru  (credit_risk + sanctions + regulatory)")
print("2. Dolandiricilik (fraud_detector + aml_monitor + alert)")
print("3. Musteri 360    (customer_inquiry + credit_risk + aml)")
print("4. Manuel         (ajan ID'lerini kendin gir)")

secim = input("\nSecim (1-4): ").strip()

if secim == "1":
    ajanlar = [
        "credit_risk_analyst_001",
        "sanctions_screening_agent_023",
        "regulatory_reporting_agent_049",
    ]
elif secim == "2":
    ajanlar = [
        "transaction_fraud_detector_011",
        "aml_transaction_monitor_019",
        "fraud_alert_manager_017",
    ]
elif secim == "3":
    ajanlar = [
        "customer_inquiry_agent_027",
        "credit_risk_analyst_001",
        "aml_transaction_monitor_019",
    ]
elif secim == "4":
    print("Ajan ID'lerini virgülle yaz:")
    print("Ornek: credit_risk_analyst_001,sanctions_screening_agent_023")
    ajanlar = [a.strip() for a in input("> ").split(",")]
else:
    print("Gecersiz secim.")
    exit()

print(f"\nPipeline: {' -> '.join(ajanlar)}")
print("-" * 60)

import time
t0 = time.time()

sonuclar = orch.pipeline(ajanlar, gorev, verbose=False)

for ajan_id, yanit in sonuclar.items():
    print(f"\n[{ajan_id}]")
    print(yanit)
    print()

print(f"Toplam sure: {time.time() - t0:.1f}s")
