"""Real local adapter: voice plans to existing RAG, recommendation, and gateway services."""
import time
from uuid import uuid4
from backend.app.orchestrator.schemas import Route,RouteDecision
from backend.app.config import settings
from backend.app.rag.service import retrieve_policy_knowledge
from backend.app.services.capability_service import RetailCapabilityService
from backend.app.tools.dispatcher import ToolGatewayDispatcher
from backend.app.voice.schemas import CapabilityResult
from backend.app.retell.timing import timed

class LocalVoiceCapabilityBackend:
    PRIVATE_LEGACY_TOOLS={"get_order","track_order","check_cancellation_eligibility",
        "cancel_order","check_return_eligibility","create_return","get_refund_status",
        "check_exchange_availability"}
    def __init__(self,conn,gateway=None,policy_retriever=retrieve_policy_knowledge,authorizer=None):
        self.conn=conn; self.gateway=gateway or ToolGatewayDispatcher(conn)
        self.policy_retriever=policy_retriever
        self.authorizer=authorizer

    def execute(self,decision:RouteDecision):
        if decision.route==Route.POLICY_RAG:
            started=time.perf_counter()
            try:result=self.policy_retriever(conn=self.conn,**decision.tool_arguments)
            finally:timed("policy_retrieval",started,tool=decision.tool_name)
            data=result.model_dump(mode="json")
            data.update({"policy_source_brand":settings.policy_reference_brand,
                         "policy_market":settings.policy_reference_market,
                         "policy_locale":settings.policy_reference_locale,
                         "policy_usage":settings.policy_usage})
            return CapabilityResult(execution_status=result.status,data=data)
        try:
            self._authorize_private(decision.tool_name,decision.tool_arguments)
            started=time.perf_counter()
            try:result=self.gateway.execute(decision.tool_name,decision.tool_arguments,self._request_id())
            finally:timed("tool_gateway",started,tool=decision.tool_name)
            return CapabilityResult(execution_status="SUCCESS" if result.success else self._error_status(result),
                                    data=result.data or {"error":result.error or {}})
        except PermissionError:
            return CapabilityResult(execution_status="AUTHORIZATION_REQUIRED",
                                    spoken_text="Please verify your identity before I access that information.")
        except ValueError as exc:
            return CapabilityResult(execution_status="CAPABILITY_REJECTED",spoken_text=str(exc))
        except Exception:
            return CapabilityResult(execution_status="CAPABILITY_UNAVAILABLE",
                                    spoken_text="That service is temporarily unavailable.")

    def prepare_write(self,tool_name,arguments):
        prepared=dict(arguments); prepared.setdefault("idempotency_key",f"voice-{uuid4().hex}")
        try:
            self._authorize_private(tool_name,prepared)
            started=time.perf_counter()
            try:result=self.gateway.execute(tool_name,prepared,self._request_id())
            finally:timed("tool_gateway_prepare",started,tool=tool_name)
            if result.confirmation:
                return CapabilityResult(execution_status="CONFIRMATION_REQUIRED",data={"prepared_arguments":prepared,
                    "confirmation_summary":result.confirmation.get("summary",{})},
                    confirmation_token=result.confirmation["confirmation_token"],
                    confirmation_prompt=result.confirmation["prompt_message"])
            data={"prepared_arguments":prepared,**(result.data or {})}
            if result.error:data["error"]=result.error
            return CapabilityResult(execution_status="SUCCESS" if result.success else self._error_status(result),
                                    data=data)
        except PermissionError:
            return CapabilityResult(execution_status="AUTHORIZATION_REQUIRED",
                                    spoken_text="Please verify your identity before I prepare that action.")
        except ValueError as exc:
            return CapabilityResult(execution_status="CAPABILITY_REJECTED",spoken_text=str(exc))
        except Exception:
            return CapabilityResult(execution_status="CAPABILITY_UNAVAILABLE",
                                    spoken_text="I couldn't safely prepare that action.")

    def confirm_write(self,tool_name,arguments,confirmation_token):
        confirmed={**arguments,"confirmed":True,"confirmation_token":confirmation_token}
        try:
            self._authorize_private(tool_name,confirmed)
            started=time.perf_counter()
            try:result=self.gateway.execute(tool_name,confirmed,self._request_id())
            finally:timed("tool_gateway_confirm",started,tool=tool_name)
            if result.success:return CapabilityResult(execution_status="SUCCESS",data=result.data or {})
            return CapabilityResult(execution_status=self._error_status(result),data={"error":result.error or {}})
        except PermissionError:
            return CapabilityResult(execution_status="AUTHORIZATION_REQUIRED",
                                    spoken_text="Please verify your identity again before I complete that action.")
        except Exception:
            return CapabilityResult(execution_status="CAPABILITY_UNAVAILABLE",
                                    spoken_text="I couldn't safely complete that action.")

    @staticmethod
    def _request_id():return f"voice-{uuid4().hex[:12]}"

    def _authorize_private(self,tool_name,arguments):
        if tool_name not in self.PRIVATE_LEGACY_TOOLS:return
        authorize=self.authorizer or RetailCapabilityService(self.conn).authorize_private_access
        authorize(
            arguments.get("access_token"),order_number=arguments.get("order_number"),
            order_item_id=arguments.get("order_item_id"))
    @staticmethod
    def _error_status(result):
        return (result.error or {}).get("code","CAPABILITY_REJECTED")
