"""Reusable audited dispatch over existing Tool Gateway domain services."""
from dataclasses import dataclass
from typing import Any

from backend.app.repositories.audit_repo import AuditRepository
from backend.app.recommendation.service import RecommendationService
from backend.app.services.catalogue_service import CatalogueService
from backend.app.services.capability_service import RetailCapabilityService
from backend.app.services.customer_service import CustomerService
from backend.app.services.exchange_service import ExchangeService
from backend.app.services.inventory_service import InventoryService
from backend.app.services.order_service import OrderService
from backend.app.services.refund_service import RefundService
from backend.app.services.return_service import ReturnService
from backend.app.services.shipment_service import ShipmentService
from backend.app.tools.registry import TOOL_REGISTRY

SENSITIVE={"access_token","confirmation_token","verification_value","email","phone",
           "destination","factual_summary"}
WRITE_TOOLS={"cancel_order","create_return","create_exchange","create_incident","create_support_case","create_order_request"}

@dataclass
class GatewayExecution:
    success:bool
    data:dict[str,Any]|None=None
    error:dict[str,Any]|None=None
    confirmation:dict[str,Any]|None=None
    cached:bool=False

class ToolGatewayDispatcher:
    def __init__(self,conn): self.conn=conn

    def execute(self,tool_name,arguments,request_id):
        if tool_name not in TOOL_REGISTRY: raise ValueError("Unsupported registered capability.")
        definition=TOOL_REGISTRY[tool_name]
        payload=definition.input_model.model_validate(arguments)
        try:
            if definition.is_write:return self._write(tool_name,payload,request_id)
            data=self._read(tool_name,payload); result=GatewayExecution(True,self._dump(data))
            self._audit(tool_name,request_id,arguments,"SUCCESS")
            return result
        except Exception as exc:
            self.conn.rollback()
            self._audit(tool_name,request_id,arguments,"ERROR",type(exc).__name__)
            raise

    def _read(self,name,payload):
        catalogue=CatalogueService(self.conn); inventory=InventoryService(self.conn)
        retail=RetailCapabilityService(self.conn)
        mapping={
            "search_products":(catalogue,"search_products"),"get_product_details":(catalogue,"get_product_details"),
            "compare_products":(catalogue,"compare_products"),"check_inventory":(inventory,"check_inventory"),
            "find_stores":(inventory,"find_stores"),"get_customer":(CustomerService(self.conn),"get_customer"),
            "get_order":(OrderService(self.conn),"get_order"),"track_order":(ShipmentService(self.conn),"track_order"),
            "check_cancellation_eligibility":(OrderService(self.conn),"check_cancellation_eligibility"),
            "check_return_eligibility":(ReturnService(self.conn),"check_return_eligibility"),
            "get_refund_status":(RefundService(self.conn),"get_refund_status"),
            "check_exchange_availability":(ExchangeService(self.conn),"check_exchange_availability"),
            "find_similar_products":(RecommendationService(self.conn),"find_similar_products"),
            "recommend_matching_products":(RecommendationService(self.conn),"recommend_matching_products"),
        }
        for tool in ("get_size_guidance","check_pickup_availability","identify_customer","verify_customer",
                     "get_customer_profile","get_customer_orders","get_loyalty_status","check_promotion",
                     "check_exchange_inventory","prepare_handoff","send_secure_link"):
            mapping[tool]=(retail,tool)
        if name not in mapping: raise ValueError("Capability is not configured for read execution.")
        service,method=mapping[name]; return getattr(service,method)(payload)

    def _write(self,name,payload,request_id):
        if name=="cancel_order": raw=OrderService(self.conn).cancel_order(payload,request_id)
        elif name=="create_return": raw=ReturnService(self.conn).create_return(payload,request_id)
        elif name in {"create_exchange","create_incident","create_support_case","create_order_request"}:
            raw=getattr(RetailCapabilityService(self.conn),name)(payload)
        else: raise ValueError("Capability is not configured for write execution.")
        success,data,error,confirmation,cached=raw
        status="SUCCESS" if success else ("CONFIRMATION_REQUIRED" if confirmation else "ERROR")
        self._audit(name,request_id,payload.model_dump(),status,error.code.value if error else None)
        return GatewayExecution(success,self._dump(data),self._dump(error),self._dump(confirmation),cached)

    def _audit(self,name,request_id,arguments,status,error_code=None):
        summary={k:v for k,v in arguments.items() if k not in SENSITIVE and v is not None}
        AuditRepository(self.conn).log_tool_execution(name,request_id,summary,status,0,
            order_id=arguments.get("order_number"),idempotency_key=arguments.get("idempotency_key"),error_code=error_code)
        self.conn.commit()

    @staticmethod
    def _dump(value):
        if value is None:return None
        if hasattr(value,"model_dump"):return value.model_dump(mode="json")
        return dict(value) if isinstance(value,dict) else {"value":value}
