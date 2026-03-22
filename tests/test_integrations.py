
import sys
import os
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestIntegrationConfig(unittest.TestCase):

    def test_config_loads_without_credentials(self):
        from integrations.config import IntegrationConfig
        cfg = IntegrationConfig()
        self.assertIsNotNone(cfg.kkb_base_url)
        self.assertIsNotNone(cfg.masak_base_url)
        self.assertIsNotNone(cfg.boa_base_url)

    def test_all_unconfigured_by_default(self):
        with patch.dict(os.environ, {}, clear=False):
            keys = ["KKB_CLIENT_ID", "KKB_CLIENT_SECRET",
                    "MASAK_API_KEY", "MASAK_INSTITUTION_CODE",
                    "BOA_USERNAME", "BOA_PASSWORD",
                    "TCMB_API_KEY", "TCMB_USERNAME", "TCMB_PASSWORD",
                    "SWIFT_CONSUMER_KEY", "SWIFT_CONSUMER_SECRET"]
            clean_env = {k: v for k, v in os.environ.items() if k not in keys}
            with patch.dict(os.environ, clean_env, clear=True):
                from integrations.config import IntegrationConfig
                cfg = IntegrationConfig()
                self.assertFalse(cfg.is_kkb_configured())
                self.assertFalse(cfg.is_masak_configured())
                self.assertFalse(cfg.is_boa_configured())
                self.assertFalse(cfg.is_tcmb_configured())
                self.assertFalse(cfg.is_swift_configured())

    def test_config_detects_kkb_when_set(self):
        with patch.dict(os.environ, {
            "KKB_CLIENT_ID": "test_id",
            "KKB_CLIENT_SECRET": "test_secret",
        }):
            from integrations.config import IntegrationConfig
            cfg = IntegrationConfig()
            self.assertTrue(cfg.is_kkb_configured())

    def test_summary_returns_dict(self):
        from integrations.config import IntegrationConfig
        cfg = IntegrationConfig()
        summary = cfg.summary()
        self.assertIn("kkb", summary)
        self.assertIn("masak", summary)
        self.assertIn("boa", summary)
        self.assertIn("tcmb", summary)
        self.assertIn("swift", summary)


class TestKKBClient(unittest.TestCase):

    def test_mock_credit_bureau_returns_valid_structure(self):
        from integrations.kkb_client import query_credit_bureau
        result = query_credit_bureau("12345678901", "standard")
        self.assertEqual(result["bureau"], "KKB")
        self.assertEqual(result["source"], "MOCK")
        self.assertIn("credit_score", result)
        self.assertIn("active_credits", result)
        self.assertIn("payment_history", result)
        self.assertGreaterEqual(result["credit_score"], 400)
        self.assertLessEqual(result["credit_score"], 900)

    def test_mock_credit_bureau_deterministic(self):
        from integrations.kkb_client import query_credit_bureau
        r1 = query_credit_bureau("98765432109", "standard")
        r2 = query_credit_bureau("98765432109", "standard")
        self.assertEqual(r1["credit_score"], r2["credit_score"])

    def test_credit_bureau_detailed_report(self):
        from integrations.kkb_client import query_credit_bureau
        result = query_credit_bureau("11122233344", "detailed")
        self.assertEqual(result["report_type"], "detailed")

    def test_risk_grade_consistent_with_score(self):
        from integrations.kkb_client import query_credit_bureau
        result = query_credit_bureau("12345678901", "standard")
        score = result["credit_score"]
        grade = result["risk_grade"]
        if score > 750:
            self.assertEqual(grade, "A")
        elif score > 650:
            self.assertEqual(grade, "B")
        elif score > 550:
            self.assertEqual(grade, "C")
        else:
            self.assertEqual(grade, "D")


class TestMASAKClient(unittest.TestCase):

    def test_mock_aml_screening_structure(self):
        from integrations.masak_client import screen_aml
        result = screen_aml("transaction_monitoring", "C12345")
        self.assertIn("alert_score", result)
        self.assertIn("typologies_detected", result)
        self.assertIn("str_candidate", result)
        self.assertEqual(result["source"], "MOCK")
        self.assertIsInstance(result["typologies_detected"], list)

    def test_mock_sanctions_check_structure(self):
        from integrations.masak_client import check_sanctions
        result = check_sanctions("Test Person", "individual")
        self.assertIn("hit", result)
        self.assertIn("matches", result)
        self.assertIn("action_required", result)
        self.assertIn(result["action_required"], ["CLEAR", "BLOCK_AND_REPORT"])

    def test_mock_str_submission(self):
        from integrations.masak_client import submit_str_report
        result = submit_str_report(
            customer_id="C12345",
            transaction_data={"amount": 50000, "currency": "TRY"},
            typologies=["STRUCTURING"],
            alert_score=0.85,
        )
        self.assertTrue(result["success"])
        self.assertIn("submission_id", result)
        self.assertEqual(result["source"], "MOCK")

    def test_low_hit_rate_for_sanctions(self):
        from integrations.masak_client import check_sanctions
        hits = sum(
            check_sanctions(f"Person {i}", "individual")["hit"]
            for i in range(100)
        )
        self.assertLessEqual(hits, 15, "Hit rate too high for sanctions mock")


class TestBOAClient(unittest.TestCase):

    def test_mock_query_customer(self):
        from integrations.boa_client import query_core_banking
        result = query_core_banking("SELECT * FROM customers LIMIT 5", "core_banking")
        self.assertTrue(result["success"])
        self.assertEqual(result["source"], "MOCK")
        self.assertIn("rows", result)
        self.assertGreater(result["row_count"], 0)

    def test_mock_query_loans(self):
        from integrations.boa_client import query_core_banking
        result = query_core_banking("SELECT * FROM loans WHERE status='NPL'", "risk")
        self.assertTrue(result["success"])
        self.assertIn("rows", result)

    def test_mock_customer_360(self):
        from integrations.boa_client import get_customer_360
        result = get_customer_360("C12345")
        self.assertEqual(result["customer_id"], "C12345")
        self.assertEqual(result["source"], "MOCK")
        self.assertIn("products", result)
        self.assertIn("balances", result)
        self.assertIn("kyc", result)

    def test_mock_customer_360_deterministic(self):
        from integrations.boa_client import get_customer_360
        r1 = get_customer_360("C99999")
        r2 = get_customer_360("C99999")
        self.assertEqual(r1["segment"], r2["segment"])

    def test_mock_transaction_history(self):
        from integrations.boa_client import get_transaction_history
        result = get_transaction_history("C12345", limit=10)
        self.assertEqual(result["customer_id"], "C12345")
        self.assertEqual(result["source"], "MOCK")
        self.assertIn("transactions", result)
        self.assertLessEqual(len(result["transactions"]), 10)


class TestTCMBClient(unittest.TestCase):

    def test_usdtry_rate(self):
        from integrations.tcmb_client import get_fx_rate
        result = get_fx_rate("USD", "TRY")
        self.assertEqual(result["base"], "USD")
        self.assertEqual(result["quote"], "TRY")
        self.assertGreater(result["mid_rate"], 30)
        self.assertIn("bid", result)
        self.assertIn("ask", result)
        self.assertGreater(result["ask"], result["bid"])

    def test_eurtry_rate(self):
        from integrations.tcmb_client import get_fx_rate
        result = get_fx_rate("EUR", "TRY")
        self.assertGreater(result["mid_rate"], 35)

    def test_conversion_amount(self):
        from integrations.tcmb_client import get_fx_rate
        result = get_fx_rate("USD", "TRY", amount=1000)
        self.assertIn("converted_amount", result)
        self.assertAlmostEqual(result["converted_amount"],
                               result["mid_rate"] * 1000, delta=1)

    def test_forward_tenor_higher_than_spot(self):
        from integrations.tcmb_client import get_fx_rate
        spot = get_fx_rate("USD", "TRY", tenor="spot")
        fwd_1y = get_fx_rate("USD", "TRY", tenor="1y")
        self.assertGreater(fwd_1y["mid_rate"], spot["mid_rate"])

    def test_market_data_fx_pairs(self):
        from integrations.tcmb_client import get_market_data
        result = get_market_data(["USDTRY", "EURTRY", "BIST100"])
        self.assertIn("quotes", result)
        self.assertIn("USDTRY", result["quotes"])
        self.assertIn("BIST100", result["quotes"])

    def test_unknown_pair_returns_value(self):
        from integrations.tcmb_client import get_fx_rate
        result = get_fx_rate("XYZ", "ABC")
        self.assertIn("mid_rate", result)
        self.assertGreater(result["mid_rate"], 0)


class TestToolsUseIntegrations(unittest.TestCase):

    def test_banking_tools_credit_bureau_uses_integration(self):
        from tools.banking_tools import execute_credit_bureau
        result = execute_credit_bureau("12345678901")
        self.assertIn("credit_score", result)
        self.assertIn("source", result)

    def test_banking_tools_fx_rate_uses_integration(self):
        from tools.banking_tools import execute_fx_rate
        result = execute_fx_rate("USD", "TRY", amount=500)
        self.assertEqual(result["base"], "USD")
        self.assertIn("source", result)

    def test_banking_tools_database_query_uses_integration(self):
        from tools.banking_tools import execute_database_query
        result = execute_database_query(
            "SELECT * FROM customers LIMIT 5", "core_banking"
        )
        self.assertIn("source", result)
        self.assertIn("rows", result)

    def test_compliance_aml_uses_integration(self):
        from tools.compliance_tools import execute_aml_screening
        result = execute_aml_screening("transaction_monitoring", "C12345")
        self.assertIn("alert_score", result)
        self.assertIn("source", result)

    def test_compliance_sanctions_uses_integration(self):
        from tools.compliance_tools import execute_sanctions_check
        result = execute_sanctions_check("Test Person")
        self.assertIn("hit", result)
        self.assertIn("source", result)


if __name__ == "__main__":
    unittest.main()
