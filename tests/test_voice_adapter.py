import unittest
from types import SimpleNamespace

from backend.app.orchestrator.schemas import Route, RouteDecision
from backend.app.tools.dispatcher import GatewayExecution
from backend.app.voice.capabilities.local import LocalVoiceCapabilityBackend


class FakeGateway:
    def __init__(self): self.calls=[]
    def execute(self,name,args,request_id):
        self.calls.append((name,args,request_id))
        if name == "cancel_order" and not args.get("confirmed"):
            return GatewayExecution(False,error={"code":"CONFIRMATION_REQUIRED"},
                confirmation={"confirmation_token":"signed-token","prompt_message":"Confirm cancellation?","summary":{}})
        return GatewayExecution(True,{"products":[{"name":"Grounded shirt","price":39.9,"currency":"USD"}]})


class AdapterTests(unittest.TestCase):
    def test_policy_preserves_reference_boundary(self):
        result_model=SimpleNamespace(status="EVIDENCE_FOUND",
            model_dump=lambda mode=None:{"status":"EVIDENCE_FOUND","evidence":[{"chunk_text":"Thirty days."}]})
        backend=LocalVoiceCapabilityBackend(object(),gateway=FakeGateway(),
            policy_retriever=lambda **kwargs:result_model)
        decision=RouteDecision(route=Route.POLICY_RAG,intent="RETRIEVE_POLICY_KNOWLEDGE",
            confidence=.9,tool_name="retrieve_policy_knowledge",reason_codes=["TEST"],
            tool_arguments={"query":"return window","market":"US","locale":"en"})
        result=backend.execute(decision)
        self.assertEqual(result.data["policy_source_brand"],"Zara")
        self.assertEqual(result.data["policy_usage"],"REFERENCE_DEMO")

    def test_read_uses_gateway(self):
        gateway=FakeGateway(); backend=LocalVoiceCapabilityBackend(object(),gateway=gateway)
        decision=RouteDecision(route=Route.TOOL_GATEWAY,intent="SEARCH_PRODUCTS",confidence=.9,
            tool_name="search_products",reason_codes=["TEST"],tool_arguments={"query":"shirt"})
        self.assertEqual(backend.execute(decision).execution_status,"SUCCESS")
        self.assertEqual(gateway.calls[0][0],"search_products")

    def test_preflight_preserves_generated_idempotency_key(self):
        backend=LocalVoiceCapabilityBackend(object(),gateway=FakeGateway())
        result=backend.prepare_write("cancel_order",{"order_number":"ORD-1"})
        self.assertEqual(result.execution_status,"CONFIRMATION_REQUIRED")
        self.assertTrue(result.data["prepared_arguments"]["idempotency_key"].startswith("voice-"))
        self.assertEqual(result.confirmation_token,"signed-token")


if __name__ == "__main__": unittest.main()
