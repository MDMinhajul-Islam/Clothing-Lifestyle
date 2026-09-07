"""Real local adapter: voice plans to existing RAG, recommendation, and gateway services."""
from uuid import uuid4
from backend.app.orchestrator.schemas import Route,RouteDecision
from backend.app.config import settings
from backend.app.rag.service import retrieve_policy_knowledge
from backend.app.tools.dispatcher import ToolGatewayDispatcher
from backend.app.voice.schemas import CapabilityResult

class LocalVoiceCapabilityBackend:
    def __init__(self,conn,gateway=None,policy_retriever=retrieve_policy_knowledge):
        self.conn=conn; self.gateway=gateway or ToolGatewayDispatcher(conn)
        self.policy_retriever=policy_retriever

    def execute(self,decision:RouteDecision):
        if decision.route==Route.POLICY_RAG:
            result=self.policy_retriever(conn=self.conn,**decision.tool_arguments)
            data=result.model_dump(mode="json")
            data.update({"policy_source_brand":settings.policy_reference_brand,
                         "policy_market":settings.policy_reference_market,
                         "policy_locale":settings.policy_reference_locale,
                         "policy_usage":settings.policy_usage})
            return CapabilityResult(execution_status=result.status,data=data)
        try:
            result=self.gateway.execute(decision.tool_name,decision.tool_arguments,self._request_id())
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
            result=self.gateway.execute(tool_name,prepared,self._request_id())
            if result.confirmation:
                return CapabilityResult(execution_status="CONFIRMATION_REQUIRED",data={"prepared_arguments":prepared,
                    "confirmation_summary":result.confirmation.get("summary",{})},
                    confirmation_token=result.confirmation["confirmation_token"],
                    confirmation_prompt=result.confirmation["prompt_message"])
            return CapabilityResult(execution_status="SUCCESS" if result.success else self._error_status(result),
                                    data={"prepared_arguments":prepared,**(result.data or {})})
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
            result=self.gateway.execute(tool_name,confirmed,self._request_id())
            if result.success:return CapabilityResult(execution_status="SUCCESS",data=result.data or {})
            return CapabilityResult(execution_status=self._error_status(result),data={"error":result.error or {}})
        except Exception:
            return CapabilityResult(execution_status="CAPABILITY_UNAVAILABLE",
                                    spoken_text="I couldn't safely complete that action.")

    @staticmethod
    def _request_id():return f"voice-{uuid4().hex[:12]}"
    @staticmethod
    def _error_status(result):
        return (result.error or {}).get("code","CAPABILITY_REJECTED")
