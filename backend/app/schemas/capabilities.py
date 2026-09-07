from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

class StrictModel(BaseModel):
    model_config=ConfigDict(extra='forbid')

class AuthLevel(str,Enum):
    PUBLIC='PUBLIC'; ORDER_VERIFIED='ORDER_VERIFIED'; TRANSACTION_VERIFIED='TRANSACTION_VERIFIED'

class IdentifyCustomerInput(StrictModel):
    email: str|None=None; phone: str|None=None; order_number: str|None=None
    @model_validator(mode='after')
    def one_identifier(self):
        if sum(bool(x) for x in (self.email,self.phone,self.order_number))!=1: raise ValueError('Provide exactly one identifier.')
        return self
class IdentifyCustomerOutput(StrictModel):
    found: bool; customer_type: str; masked_destination: str|None=None; verification_method: str|None=None; data_origin: str='synthetic_operational_layer'

class VerifyCustomerInput(StrictModel):
    email: str|None=None; phone: str|None=None; order_number: str|None=None
    verification_value: str=Field(min_length=1,max_length=160)
    @model_validator(mode='after')
    def one_identifier(self):
        if sum(bool(x) for x in (self.email,self.phone,self.order_number))!=1: raise ValueError('Provide exactly one identifier.')
        return self
class VerifyCustomerOutput(StrictModel):
    verified: bool; auth_level: AuthLevel; access_token: str|None=None; expires_at: str|None=None; customer_type: str; data_origin: str='synthetic_operational_layer'

class AuthorizedInput(StrictModel): access_token: str=Field(min_length=20,max_length=500)
class GetCustomerProfileInput(AuthorizedInput): pass
class AuthorizedProfileOutput(StrictModel):
    customer_id: str; first_name: str; last_name: str; email: str; phone: str|None=None
    city: str|None=None; state: str|None=None; preferred_language: str; preferred_currency: str
    account_status: str; auth_level: AuthLevel; data_origin: str='synthetic_operational_layer'
class GetCustomerOrdersInput(AuthorizedInput): limit:int=Field(10,ge=1,le=25)
class OrderHistoryItem(StrictModel):
    order_number:str; order_status:str; placed_at:str; grand_total:float; currency:str; items:list[dict[str,Any]]
class GetCustomerOrdersOutput(StrictModel):
    auth_level:AuthLevel; total_orders:int; orders:list[OrderHistoryItem]; data_origin:str='synthetic_operational_layer'

class GetSizeGuidanceInput(StrictModel): product_id:str
class SizeGuidanceOutput(StrictModel):
    product_id:str; status:str; documented_fit:str|None=None; documented_sizes:list[str]=Field(default_factory=list)
    measurements_available:bool=False; advisory:str; evidence_origin:Literal['public_catalogue']='public_catalogue'

class CheckPickupAvailabilityInput(StrictModel):
    product_id:str; store_id:str; variant_id:str|None=None; size:str|None=None; color:str|None=None
class CheckPickupAvailabilityOutput(StrictModel):
    status:Literal['AVAILABLE','UNAVAILABLE','UNKNOWN']; quantity_available:int; matching_variants:int
    store_id:str; product_id:str; data_origin:Literal['synthetic_operational_layer']='synthetic_operational_layer'

class GetLoyaltyStatusInput(AuthorizedInput): pass
class LoyaltyStatusOutput(StrictModel):
    tier:str; points_balance:int; benefits:list[str]; points_expire_at:str|None=None
    data_origin:Literal['synthetic_operational_layer']='synthetic_operational_layer'; is_demo:Literal[True]=True

class CheckPromotionInput(StrictModel):
    promotion_code:str=Field(min_length=1,max_length=80); cart_subtotal:float=Field(ge=0)
    product_id:str|None=None
class CheckPromotionOutput(StrictModel):
    eligible:bool; status:str; reason_codes:list[str]; discount_type:str|None=None; discount_value:float|None=None
    stacking_allowed:bool=False; data_origin:Literal['synthetic_operational_layer']='synthetic_operational_layer'; is_demo:Literal[True]=True

class CheckExchangeInventoryInput(AuthorizedInput):
    order_item_id:str; replacement_size:str|None=None; replacement_color:str|None=None; store_id:str|None=None

class CreateExchangeInput(AuthorizedInput):
    order_item_id:str; replacement_size:str|None=None; replacement_color:str|None=None; store_id:str|None=None
    confirmation_token:str|None=None; confirmed:bool=False; idempotency_key:str|None=None
class CreateExchangeOutput(StrictModel):
    exchange_id:str; order_item_id:str; replacement_variant_id:str; exchange_status:str
    data_origin:Literal['synthetic_operational_layer']='synthetic_operational_layer'

IssueType=Literal['MISSING_ITEM','WRONG_ITEM','DAMAGED_ITEM','DEFECTIVE_ITEM','DELIVERED_NOT_RECEIVED']
class CreateIncidentInput(AuthorizedInput):
    order_number:str; order_item_id:str; issue_type:IssueType; factual_summary:str=Field(min_length=5,max_length=1000)
    confirmation_token:str|None=None; confirmed:bool=False; idempotency_key:str|None=None
class CreateIncidentOutput(StrictModel):
    incident_id:str; incident_status:str; data_origin:Literal['synthetic_operational_layer']='synthetic_operational_layer'

class CreateSupportCaseInput(AuthorizedInput):
    issue_category:str=Field(min_length=2,max_length=100); factual_summary:str=Field(min_length=5,max_length=1000)
    requested_outcome:str|None=Field(None,max_length=500); order_number:str|None=None; product_id:str|None=None
    verified_facts:list[str]=Field(default_factory=list); attempted_actions:list[str]=Field(default_factory=list)
    tool_errors:list[str]=Field(default_factory=list); confirmation_token:str|None=None; confirmed:bool=False; idempotency_key:str|None=None
class CreateSupportCaseOutput(StrictModel):
    case_id:str; case_status:str; data_origin:Literal['synthetic_operational_layer']='synthetic_operational_layer'

class PrepareHandoffInput(StrictModel):
    access_token:str|None=None; intent:str; order_number:str|None=None; product_id:str|None=None
    verified_facts:list[str]=Field(default_factory=list); actions_attempted:list[str]=Field(default_factory=list)
    tool_errors:list[str]=Field(default_factory=list); case_reference_id:str|None=None
    customer_requested_outcome:str|None=None; factual_summary:str=Field(min_length=2,max_length=1000)
class HandoffPacketOutput(StrictModel):
    customer_id:str|None=None; auth_level:AuthLevel; intent:str; order_id:str|None=None; product_id:str|None=None
    verified_facts:list[str]; actions_attempted:list[str]; tool_errors:list[str]; case_reference_id:str|None=None
    customer_requested_outcome:str|None=None; factual_summary:str; recommended_route:str

Purpose=Literal['PRODUCT','CART','CHECKOUT','RETURN','SUPPORT']
class SendSecureLinkInput(AuthorizedInput):
    purpose:Purpose; destination:str; consent_confirmed:bool
class SendSecureLinkOutput(StrictModel):
    status:Literal['DELIVERY_NOT_CONFIGURED']; purpose:Purpose; handoff_url:str
    delivery_claimed:Literal[False]=False; data_origin:Literal['synthetic_operational_layer']='synthetic_operational_layer'
