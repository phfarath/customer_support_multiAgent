"""
Test Escalation Scenarios (Fallback Logic - Deterministic)
"""
from . import BaseTestCase
from src.agents.escalator_agent import EscalatorAgent
from datetime import datetime, timedelta

class TestEscalation(BaseTestCase):
    async def _run_logic(self):
        escalator = EscalatorAgent()
        
        # Case 1: Negative Sentiment -> Should Escalate
        context_negative = self._build_context(
            sentiment=-0.8,
            confidence=0.9,
            interactions_count=1
        )
        # Using fallback directly for deterministic tests
        res_neg = escalator._make_escalation_decision_fallback(
            context_negative["ticket"],
            context_negative["triage_result"],
            context_negative["routing_result"],
            context_negative["resolver_result"],
            context_negative["interactions"]
        )
        
        if res_neg.get("escalate_to_human") == True:
            print("   ✅ Negative Sentiment Escalation: PASS")
        else:
            print(f"   ❌ Negative Sentiment Escalation: FAIL (escalate={res_neg.get('escalate_to_human')})")
        
        # Case 2: Low Confidence -> Should Escalate
        context_low_conf = self._build_context(
            sentiment=0.0,
            confidence=0.4,
            interactions_count=1
        )
        res_low = escalator._make_escalation_decision_fallback(
            context_low_conf["ticket"],
            context_low_conf["triage_result"],
            context_low_conf["routing_result"],
            context_low_conf["resolver_result"],
            context_low_conf["interactions"]
        )
        
        if res_low.get("escalate_to_human") == True:
            print("   ✅ Low Confidence Escalation: PASS")
        else:
            print(f"   ❌ Low Confidence Escalation: FAIL (escalate={res_low.get('escalate_to_human')})")
        
        # Case 3: Normal conditions -> Should NOT Escalate
        context_normal = self._build_context(
            sentiment=0.2,
            confidence=0.9,
            interactions_count=1
        )
        res_normal = escalator._make_escalation_decision_fallback(
            context_normal["ticket"],
            context_normal["triage_result"],
            context_normal["routing_result"],
            context_normal["resolver_result"],
            context_normal["interactions"]
        )
        
        if res_normal.get("escalate_to_human") == False:
            print("   ✅ Normal (No Escalation): PASS")
        else:
            print(f"   ❌ Normal (No Escalation): FAIL (escalate={res_normal.get('escalate_to_human')})")

    def _build_context(self, sentiment: float, confidence: float, interactions_count: int):
        return {
            "ticket": {
                "ticket_id": "t_esc_test",
                "subject": "Test Escalation",
                "description": "Testing escalation logic",
                "priority": "P3",
                "created_at": datetime.utcnow()
            },
            "triage_result": {
                "sentiment": sentiment,
                "category": "general",
                "confidence": 0.9
            },
            "routing_result": {
                "target_team": "general"
            },
            "resolver_result": {
                "confidence": confidence,
                "needs_escalation": False,
                "escalation_reasons": [],
                "response": "Test response"
            },
            "interactions": [{"content": "msg"}] * interactions_count
        }

