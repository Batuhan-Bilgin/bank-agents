
import json
import sys
import os
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def make_mock_response(text: str, stop_reason: str = "end_turn"):
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = text

    msg = MagicMock()
    msg.content = [text_block]
    msg.stop_reason = stop_reason
    return msg


def make_mock_tool_response(tool_name: str, tool_input: dict, tool_id: str = "toolu_test001"):
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.name = tool_name
    tool_block.input = tool_input
    tool_block.id = tool_id

    msg = MagicMock()
    msg.content = [tool_block]
    msg.stop_reason = "tool_use"
    return msg


class TestToolRegistry(unittest.TestCase):
    def test_all_tools_registered(self):
        from core.tool_registry import list_all_tools
        tools = list_all_tools()
        self.assertGreaterEqual(len(tools), 35)

    def test_core_tools_present(self):
        from core.tool_registry import list_all_tools
        tools = set(list_all_tools())
        required = {
            "database_query", "customer_360_lookup", "transaction_history",
            "credit_bureau_api", "risk_scoring_engine", "fraud_detection_api",
            "aml_screening", "sanctions_check", "audit_logger", "alert_manager",
        }
        missing = required - tools
        self.assertEqual(missing, set(), f"Missing tools: {missing}")

    def test_tool_execution_database_query(self):
        from core.tool_registry import execute_tool
        result = execute_tool("database_query", {
            "query": "SELECT * FROM customers WHERE id = 'C001'",
            "database": "core_banking"
        })
        self.assertNotIn("error", result)
        self.assertIn("rows", result)

    def test_tool_execution_fraud_detection(self):
        from core.tool_registry import execute_tool
        result = execute_tool("fraud_detection_api", {
            "event_type": "card_transaction",
            "customer_id": "C001",
            "amount": 50000,
            "currency": "TRY",
        })
        self.assertNotIn("error", result)

    def test_tool_execution_credit_bureau(self):
        from core.tool_registry import execute_tool
        result = execute_tool("credit_bureau_api", {
            "national_id": "12345678901",
            "report_type": "standard"
        })
        self.assertNotIn("error", result)

    def test_tool_execution_sanctions_check(self):
        from core.tool_registry import execute_tool
        result = execute_tool("sanctions_check", {
            "name": "Test Entity",
            "entity_type": "company"
        })
        self.assertNotIn("error", result)

    def test_unknown_tool_returns_error(self):
        from core.tool_registry import execute_tool
        result = execute_tool("nonexistent_tool", {})
        self.assertIn("error", result)

    def test_tool_schema_structure(self):
        from core.tool_registry import get_tool_schema
        schema = get_tool_schema("customer_360_lookup")
        self.assertIsNotNone(schema)
        self.assertIn("name", schema)
        self.assertIn("description", schema)
        self.assertIn("input_schema", schema)


class TestAgentFactory(unittest.TestCase):
    def setUp(self):
        from core.agent_factory import AgentFactory, CONFIG_PATH
        self.factory = AgentFactory(CONFIG_PATH)

    def test_100_agents_loaded(self):
        self.assertEqual(self.factory.total, 80)

    def test_15_departments(self):
        depts = self.factory.list_departments()
        self.assertEqual(len(depts), 11)

    def test_get_agent_by_id(self):
        agent = self.factory.get("credit_risk_analyst_001")
        self.assertEqual(agent.id, "credit_risk_analyst_001")
        self.assertEqual(agent.department, "Credit Risk")

    def test_get_fraud_agent(self):
        agent = self.factory.get("transaction_fraud_detector_011")
        self.assertEqual(agent.department, "Fraud Detection")
        self.assertGreater(len(agent.tool_names), 0)

    def test_unknown_agent_raises(self):
        with self.assertRaises(ValueError):
            self.factory.get("nonexistent_agent_999")

    def test_get_by_department(self):
        agents = self.factory.get_by_department("Fraud Detection")
        self.assertGreater(len(agents), 0)
        for agent in agents:
            self.assertEqual(agent.department, "Fraud Detection")

    def test_stats_structure(self):
        stats = self.factory.stats()
        self.assertEqual(stats["total_agents"], 80)
        self.assertGreaterEqual(stats["departments"], 10)
        self.assertIn("by_department", stats)
        self.assertIn("by_authority_level", stats)

    def test_authority_levels(self):
        stats = self.factory.stats()
        levels = stats["by_authority_level"]
        total = sum(levels.values())
        self.assertEqual(total, 80)
        for level in [1, 2, 3]:
            self.assertIn(level, levels)


class TestAutoRouting(unittest.TestCase):
    def setUp(self):
        from core.agent_factory import AgentFactory, CONFIG_PATH
        self.factory = AgentFactory(CONFIG_PATH)

    def _route(self, task):
        return self.factory.best_agent_for(task).department.lower()

    def test_fraud_routing(self):
        self.assertEqual(self._route("suspicious transaction on card"), "fraud detection")

    def test_aml_routing(self):
        self.assertEqual(self._route("AML screening required for wire"), "aml/kyc")

    def test_sanctions_routing(self):
        self.assertEqual(self._route("sanctions check for OFAC compliance"), "aml/kyc")

    def test_credit_routing(self):
        self.assertEqual(self._route("loan application credit risk assessment"), "credit risk")

    def test_fx_routing(self):
        self.assertEqual(self._route("FX forward rate hedge for USD/TRY"), "treasury & liquidity")

    def test_cyber_routing(self):
        self.assertEqual(self._route("cyber incident ransomware attack response"), "it & cybersecurity")

    def test_compliance_routing(self):
        self.assertEqual(self._route("GDPR data subject access request"), "regulatory compliance")

    def test_retail_routing(self):
        self.assertEqual(self._route("mortgage housing loan application"), "retail banking")

    def test_sme_routing(self):
        self.assertEqual(self._route("SME small business trade finance"), "corporate & sme banking")


class TestBaseAgent(unittest.TestCase):

    def _get_fraud_agent(self):
        with patch.dict(os.environ, {"PROVIDER": "anthropic"}):
            from core.agent_factory import AgentFactory, CONFIG_PATH
            factory = AgentFactory(CONFIG_PATH)
            return factory.get("transaction_fraud_detector_011")

    def _get_credit_agent(self):
        with patch.dict(os.environ, {"PROVIDER": "anthropic"}):
            from core.agent_factory import AgentFactory, CONFIG_PATH
            factory = AgentFactory(CONFIG_PATH)
            return factory.get("credit_risk_analyst_001")

    @patch("core.base_agent.anthropic.Anthropic")
    def test_simple_chat_no_tools(self, MockAnthropic):
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client
        mock_client.messages.create.return_value = make_mock_response(
            "Risk assessment complete. The credit score is 750, indicating low risk."
        )

        agent = self._get_credit_agent()
        agent._client = mock_client

        result = agent.chat("Assess credit risk for customer C001", verbose=False)
        self.assertIn("750", result)
        mock_client.messages.create.assert_called_once()

    @patch("core.base_agent.anthropic.Anthropic")
    def test_chat_with_tool_call(self, MockAnthropic):
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client

        mock_client.messages.create.side_effect = [
            make_mock_tool_response(
                "fraud_detection_api",
                {"transaction_id": "TXN_999", "amount": 85000, "currency": "TRY",
                 "customer_id": "C001", "merchant_category": "transfer",
                 "transaction_type": "wire_transfer"}
            ),
            make_mock_response("HIGH RISK: Transaction flagged for manual review."),
        ]

        agent = self._get_fraud_agent()
        agent._client = mock_client
        agent.reset()

        result = agent.chat("Check transaction TXN_999 for fraud", verbose=False)
        self.assertIn("HIGH RISK", result)
        self.assertEqual(mock_client.messages.create.call_count, 2)

    def test_agent_reset(self):
        agent = self._get_credit_agent()
        agent._conversation = [{"role": "user", "content": "test"}]
        agent.reset()
        self.assertEqual(agent._conversation, [])

    def test_agent_repr(self):
        agent = self._get_credit_agent()
        r = repr(agent)
        self.assertIn("credit_risk_analyst_001", r)

    def test_system_prompt_includes_role(self):
        agent = self._get_credit_agent()
        prompt = agent._build_system_prompt()
        self.assertIn("Credit Risk Analyst", prompt)
        self.assertIn("BankAI", prompt)
        self.assertIn("BDDK", prompt)


class TestOrchestrator(unittest.TestCase):
    @patch("core.base_agent.anthropic.Anthropic")
    def test_pipeline_runs_sequentially(self, MockAnthropic):
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client
        mock_client.messages.create.return_value = make_mock_response(
            "Analysis complete."
        )

        with patch.dict(os.environ, {"PROVIDER": "anthropic"}):
            from core.orchestrator import Orchestrator
            orch = Orchestrator()

            for aid in ["npl_manager_007", "collateral_evaluator_005"]:
                orch._factory.get(aid)._client = mock_client

            results = orch.pipeline(
                ["npl_manager_007", "collateral_evaluator_005"],
                "Review NPL case for customer C55000",
                verbose=False
            )
        self.assertEqual(len(results), 2)
        self.assertIn("npl_manager_007", results)
        self.assertIn("collateral_evaluator_005", results)


class TestAPIServer(unittest.TestCase):

    def setUp(self):
        from fastapi.testclient import TestClient
        from api.server import app
        self.client = TestClient(app)

    def test_health_endpoint(self):
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["agents_loaded"], 80)

    def test_list_agents(self):
        resp = self.client.get("/agents")
        self.assertEqual(resp.status_code, 200)
        agents = resp.json()
        self.assertEqual(len(agents), 80)

    def test_list_agents_by_department(self):
        resp = self.client.get("/agents?department=Fraud Detection")
        self.assertEqual(resp.status_code, 200)
        agents = resp.json()
        self.assertGreater(len(agents), 0)
        for agent in agents:
            self.assertEqual(agent["department"], "Fraud Detection")

    def test_get_agent_by_id(self):
        resp = self.client.get("/agents/credit_risk_analyst_001")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["id"], "credit_risk_analyst_001")

    def test_get_unknown_agent_404(self):
        resp = self.client.get("/agents/nonexistent_999")
        self.assertEqual(resp.status_code, 404)

    def test_departments_endpoint(self):
        resp = self.client.get("/departments")
        self.assertEqual(resp.status_code, 200)
        depts = resp.json()["departments"]
        self.assertEqual(len(depts), 11)

    def test_stats_endpoint(self):
        resp = self.client.get("/stats")
        self.assertEqual(resp.status_code, 200)
        stats = resp.json()
        self.assertEqual(stats["total_agents"], 80)

    def test_chat_without_api_key_503(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "your_api_key_here"}):
            resp = self.client.post(
                "/agents/credit_risk_analyst_001/chat",
                json={"message": "test"}
            )
            self.assertEqual(resp.status_code, 503)

    def test_auto_without_api_key_503(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "your_api_key_here"}):
            resp = self.client.post("/auto", json={"task": "assess fraud risk"})
            self.assertEqual(resp.status_code, 503)


def run_tests():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    test_classes = [
        TestToolRegistry,
        TestAgentFactory,
        TestAutoRouting,
        TestBaseAgent,
        TestOrchestrator,
        TestAPIServer,
    ]

    for cls in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)

    print(f"\n{'='*60}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures:  {len(result.failures)}")
    print(f"Errors:    {len(result.errors)}")
    print(f"{'ALL TESTS PASSED' if result.wasSuccessful() else 'SOME TESTS FAILED'}")
    print(f"{'='*60}")
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
