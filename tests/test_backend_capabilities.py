import hashlib
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from backend.app.orchestrator.schemas import RouteRequest
from backend.app.orchestrator.service import OrchestratorService
from backend.app.schemas.capabilities import *
from backend.app.schemas.returns import CheckExchangeAvailabilityOutput
from backend.app.schemas.returns import CreateReturnInput, ReturnItemRequest
from backend.app.rules.cancellation import CancellationRules
from backend.app.rules.returns import ReturnRules
from backend.app.services.capability_service import RetailCapabilityService
from backend.app.services.return_service import ReturnService
from backend.app.tools.registry import TOOL_REGISTRY

TOKEN='verified-access-token-1234567890'
GUEST='guest-access-token-123456789012'

class FakeConn:
    def __init__(self): self.commits=0
    def commit(self): self.commits+=1

class FakeIdempotency:
    def __init__(self): self.rows={}
    def get_idempotency_record(self,key): return self.rows.get(key)
    def record_idempotency(self,key,tool_name,request_hash,response_json,status='SUCCEEDED'):
        self.rows[key]={'tool_name':tool_name,'request_hash':request_hash,'response_json':response_json,'status':status}

class FakeRepo:
    def __init__(self):
        self.identify_row=None; self.verify_row=None; self.auth={}; self.created=[]
        self.auth[hashlib.sha256(TOKEN.encode()).hexdigest()]={'customer_id':'cust-1','order_id':None,'order_number':None,'auth_level':'TRANSACTION_VERIFIED'}
        self.auth[hashlib.sha256(GUEST.encode()).hexdigest()]={'customer_id':'cust-1','order_id':'order-1','order_number':'ORD-1','auth_level':'ORDER_VERIFIED'}
    def identify(self,**kwargs): return self.identify_row
    def verify(self,**kwargs): return self.verify_row
    def create_auth_session(self,token_hash,customer_id,order_id,auth_level,expires_at): self.created.append(('auth',auth_level))
    def get_auth_session(self,token_hash): return self.auth.get(token_hash)
    def get_profile(self,c): return {'customer_id':c,'first_name':'Demo','last_name':'Customer','email':'demo@example.test','phone':None,'city':'New York','state':'NY','preferred_language':'en','preferred_currency':'USD','account_status':'ACTIVE'}
    def get_orders(self,c,limit,order_id=None): return [{'order_number':'ORD-1','order_status':'DELIVERED','placed_at':datetime.now(timezone.utc),'grand_total':49.0,'currency':'USD','items':[{'product_id':'zara-us:00029400','size':'M'}]}]
    def size_guidance(self,p): return {'product_id':p,'fit_information':'Relaxed fit','sizes':['S','M','L']}
    def get_loyalty(self,c): return {'tier':'GOLD','points_balance':1200,'benefits':['Demo priority support'],'points_expire_at':datetime(2099,1,1,tzinfo=timezone.utc)}
    def get_promotion(self,code):
        if code=='BAD': return None
        active=code!='OLD'
        return {'status':'ACTIVE' if active else 'INACTIVE','starts_at':datetime(2020,1,1,tzinfo=timezone.utc),'ends_at':datetime(2099,1,1,tzinfo=timezone.utc) if active else datetime(2021,1,1,tzinfo=timezone.utc),'minimum_spend':50,'discount_type':'PERCENT','discount_value':10,'stacking_allowed':False,'eligible_product_ids':None}
    def order_belongs_to(self,c,n): return {'order_id':'order-1'} if n=='ORD-1' else None
    def item_scope(self,i): return {'order_item_id':i,'order_id':'order-1','order_number':'ORD-1','customer_id':'cust-1','variant_id':'variant-1'} if i=='ITEM-1' else None
    def verified_destinations(self,c): return {'email':'demo@example.test','phone':'+15550001111'}
    def create_exchange_atomic(self,*args): self.created.append(('exchange',args[0]))
    def get_exchange(self,exchange_id): return {'exchange_id':exchange_id,'replacement_variant_id':'variant-2','exchange_status':'APPROVED'}
    def create_incident(self,*args): self.created.append(('incident',args[0]))
    def create_support_case(self,*args): self.created.append(('case',args[0]))

class FakeInventory:
    available=2
    def check_inventory(self,d):
        store=SimpleNamespace(store_id=d.store_id,quantity_available=self.available)
        variant=SimpleNamespace(stores=[store])
        return SimpleNamespace(matching_variants=[variant])

class FakeExchange:
    eligible=True
    def check_exchange_availability(self,d):
        return CheckExchangeAvailabilityOutput(eligible=self.eligible,reason='Available' if self.eligible else 'Unavailable',
            original_item={'order_item_id':d.order_item_id},replacement_variant={'variant_id':'variant-2'} if self.eligible else None,
            quantity_available=2 if self.eligible else 0,stock_status='IN_STOCK' if self.eligible else 'OUT_OF_STOCK')

class FakeReturnRepo:
    def get_return_context_for_order(self,order_number):
        return {'order_id':'order-1','order_number':order_number,'order_status':'DELIVERED',
            'shipped_at':datetime.now(timezone.utc)-timedelta(days=2),
            'delivered_at':datetime.now(timezone.utc)-timedelta(days=1),
            'items':[{'order_item_id':'ITEM-1','product_name_snapshot':'Demo item',
                'size_snapshot':'M','color_snapshot':'black','quantity':1,
                'already_returned_quantity':0,'unit_price':50,'line_total':50}]}

class CapabilityTests(unittest.TestCase):
    def setUp(self):
        self.conn=FakeConn(); self.repo=FakeRepo(); self.idem=FakeIdempotency(); self.inventory=FakeInventory(); self.exchange=FakeExchange()
        self.service=RetailCapabilityService(self.conn,repo=self.repo,inventory=self.inventory,exchange=self.exchange,idempotency=self.idem)
        self.router=OrchestratorService()

    def test_01_anonymous_public_flow(self): self.assertFalse(self.service.identify_customer(IdentifyCustomerInput(email='none@test')).found)
    def test_02_identify_masks_existing_customer(self):
        self.repo.identify_row={'customer_id':'c','email':'demo@example.test','phone':None,'order_id':None}
        out=self.service.identify_customer(IdentifyCustomerInput(email='demo@example.test')); self.assertEqual(out.masked_destination,'d***@example.test')
    def test_03_verification_success(self):
        self.repo.verify_row={'customer_id':'c','order_id':None}; out=self.service.verify_customer(VerifyCustomerInput(email='demo@example.test',verification_value='10001')); self.assertTrue(out.verified); self.assertTrue(out.access_token)
    def test_04_verification_failure(self): self.assertFalse(self.service.verify_customer(VerifyCustomerInput(email='x@y.test',verification_value='bad')).verified)
    def test_05_unauthorized_profile_blocked(self):
        with self.assertRaises(PermissionError): self.service.get_customer_profile(GetCustomerProfileInput(access_token='invalid-token-1234567890'))
    def test_06_verified_profile(self): self.assertEqual(self.service.get_customer_profile(GetCustomerProfileInput(access_token=TOKEN)).customer_id,'cust-1')
    def test_07_guest_order_scope_restricted(self):
        with self.assertRaises(PermissionError): self.service._auth(GUEST,order_number='ORD-2')
    def test_08_authorized_order_history(self): self.assertEqual(self.service.get_customer_orders(GetCustomerOrdersInput(access_token=TOKEN)).total_orders,1)
    def test_09_size_guidance_grounded(self): self.assertEqual(self.service.get_size_guidance(GetSizeGuidanceInput(product_id='zara-us:00029400')).documented_fit,'Relaxed fit')
    def test_10_size_guidance_insufficient(self):
        self.repo.size_guidance=lambda p:None; self.assertEqual(self.service.get_size_guidance(GetSizeGuidanceInput(product_id='zara-us:00029400')).status,'INSUFFICIENT_SIZE_EVIDENCE')
    def test_11_pickup_available(self): self.assertEqual(self.service.check_pickup_availability(CheckPickupAvailabilityInput(product_id='p',store_id='s')).status,'AVAILABLE')
    def test_12_pickup_unknown(self):
        self.inventory.check_inventory=lambda d:SimpleNamespace(matching_variants=[]); self.assertEqual(self.service.check_pickup_availability(CheckPickupAvailabilityInput(product_id='p',store_id='s')).status,'UNKNOWN')
    def test_13_pickup_provenance(self): self.assertEqual(self.service.check_pickup_availability(CheckPickupAvailabilityInput(product_id='p',store_id='s')).data_origin,'synthetic_operational_layer')
    def test_14_unauthorized_loyalty(self):
        with self.assertRaises(PermissionError): self.service.get_loyalty_status(GetLoyaltyStatusInput(access_token='invalid-token-1234567890'))
    def test_15_authenticated_loyalty(self): self.assertEqual(self.service.get_loyalty_status(GetLoyaltyStatusInput(access_token=TOKEN)).tier,'GOLD')
    def test_16_loyalty_provenance(self): self.assertTrue(self.service.get_loyalty_status(GetLoyaltyStatusInput(access_token=TOKEN)).is_demo)
    def test_17_valid_promotion(self): self.assertTrue(self.service.check_promotion(CheckPromotionInput(promotion_code='DEMO10',cart_subtotal=60)).eligible)
    def test_18_invalid_and_expired_promotions(self):
        self.assertEqual(self.service.check_promotion(CheckPromotionInput(promotion_code='BAD',cart_subtotal=60)).reason_codes,['INVALID_CODE'])
        self.assertFalse(self.service.check_promotion(CheckPromotionInput(promotion_code='OLD',cart_subtotal=60)).eligible)
    def test_19_promotion_reason_codes(self): self.assertEqual(self.service.check_promotion(CheckPromotionInput(promotion_code='DEMO10',cart_subtotal=10)).reason_codes,['MINIMUM_SPEND_NOT_MET'])
    def test_20_exchange_inventory(self): self.assertTrue(self.service.check_exchange_inventory(CheckExchangeInventoryInput(access_token=TOKEN,order_item_id='ITEM-1',replacement_size='L')).eligible)
    def test_21_exchange_requires_confirmation(self):
        result=self.service.create_exchange(CreateExchangeInput(access_token=TOKEN,order_item_id='ITEM-1')); self.assertIsNotNone(result[3]); self.assertFalse(result[0])
    def test_22_exchange_confirmation_token(self):
        first=self.service.create_exchange(CreateExchangeInput(access_token=TOKEN,order_item_id='ITEM-1'))
        self.assertIn('14 days',first[3].prompt_message)
        second=self.service.create_exchange(CreateExchangeInput(access_token=TOKEN,order_item_id='ITEM-1',confirmed=True,confirmation_token=first[3].confirmation_token)); self.assertTrue(second[0])
    def test_23_exchange_idempotency(self):
        base=CreateExchangeInput(access_token=TOKEN,order_item_id='ITEM-1',idempotency_key='idem-ex')
        token=self.service.create_exchange(base)[3].confirmation_token
        first=self.service.create_exchange(CreateExchangeInput(**{**base.model_dump(),'confirmed':True,'confirmation_token':token})); second=self.service.create_exchange(base); self.assertTrue(second[4]); self.assertEqual(first[1].exchange_id,second[1].exchange_id)
    def test_24_damaged_incident_creation(self):
        base=CreateIncidentInput(access_token=TOKEN,order_number='ORD-1',order_item_id='ITEM-1',issue_type='DAMAGED_ITEM',factual_summary='Item arrived damaged')
        preflight=self.service.create_incident(base); self.assertIn('human review',preflight[3].prompt_message)
        token=preflight[3].confirmation_token; out=self.service.create_incident(CreateIncidentInput(**{**base.model_dump(),'confirmed':True,'confirmation_token':token})); self.assertTrue(out[0])
    def test_25_unauthorized_incident(self):
        with self.assertRaises(PermissionError): self.service.create_incident(CreateIncidentInput(access_token='invalid-token-1234567890',order_number='ORD-1',order_item_id='ITEM-1',issue_type='DAMAGED_ITEM',factual_summary='Item arrived damaged'))
    def test_26_incident_idempotency(self):
        base=CreateIncidentInput(access_token=TOKEN,order_number='ORD-1',order_item_id='ITEM-1',issue_type='DAMAGED_ITEM',factual_summary='Item arrived damaged',idempotency_key='idem-inc')
        token=self.service.create_incident(base)[3].confirmation_token; first=self.service.create_incident(CreateIncidentInput(**{**base.model_dump(),'confirmed':True,'confirmation_token':token})); second=self.service.create_incident(base); self.assertTrue(second[4]); self.assertEqual(first[1].incident_id,second[1].incident_id)
    def test_27_support_case_creation(self):
        base=CreateSupportCaseInput(access_token=TOKEN,issue_category='COMPLAINT',factual_summary='Repeated delivery problem')
        token=self.service.create_support_case(base)[3].confirmation_token; out=self.service.create_support_case(CreateSupportCaseInput(**{**base.model_dump(),'confirmed':True,'confirmation_token':token})); self.assertTrue(out[0])
    def test_28_handoff_least_privilege(self):
        out=self.service.prepare_handoff(PrepareHandoffInput(intent='HUMAN_SUPPORT',factual_summary='Customer requested a person')); self.assertIsNone(out['customer_id']); self.assertEqual(out['auth_level'],'PUBLIC')
    def test_29_human_request_route(self): self.assertEqual(self.router.route(RouteRequest(message='I want to speak to a person')).tool_name,'prepare_handoff')
    def test_30_unverified_destination_blocked(self):
        with self.assertRaises(PermissionError): self.service.send_secure_link(SendSecureLinkInput(access_token=TOKEN,purpose='SUPPORT',destination='other@test',consent_confirmed=True))
    def test_31_secure_link_never_claims_delivery(self):
        out=self.service.send_secure_link(SendSecureLinkInput(access_token=TOKEN,purpose='SUPPORT',destination='demo@example.test',consent_confirmed=True)); self.assertFalse(out['delivery_claimed']); self.assertEqual(out['status'],'DELIVERY_NOT_CONFIGURED')
    def test_32_loyalty_route(self): self.assertEqual(self.router.route(RouteRequest(message='How many points do I have?')).tool_name,'get_loyalty_status')
    def test_33_promotion_route(self): self.assertEqual(self.router.route(RouteRequest(message="Why isn't my coupon working?")).tool_name,'check_promotion')
    def test_34_pickup_route(self): self.assertEqual(self.router.route(RouteRequest(message='Can I pick this up today?')).tool_name,'check_pickup_availability')
    def test_35_exchange_route(self): self.assertEqual(self.router.route(RouteRequest(message='These jeans are too small. Can I exchange for the next size?')).tool_name,'check_exchange_inventory')
    def test_36_incident_route(self): self.assertEqual(self.router.route(RouteRequest(message='My item arrived damaged.')).tool_name,'create_incident')
    def test_37_handoff_route(self): self.assertEqual(self.router.route(RouteRequest(message='I need a human agent')).tool_name,'prepare_handoff')
    def test_38_existing_tools_preserved(self):
        old={'search_products','get_product_details','compare_products','check_inventory','find_stores','get_customer','get_order','track_order','check_cancellation_eligibility','cancel_order','check_return_eligibility','create_return','get_refund_status','check_exchange_availability','find_similar_products','recommend_matching_products'}; self.assertTrue(old<=set(TOOL_REGISTRY))
    def test_39_recommendation_tools_preserved(self): self.assertTrue({'find_similar_products','recommend_matching_products'}<=set(TOOL_REGISTRY))
    def test_40_existing_write_confirmation_unchanged(self): self.assertTrue(TOOL_REGISTRY['cancel_order'].requires_confirmation and TOOL_REGISTRY['create_return'].requires_confirmation)
    def test_41_registered_token_cannot_access_another_order(self):
        with self.assertRaises(PermissionError): self.service._auth(TOKEN,order_number='ORD-2')
    def test_42_cancellation_next_steps_are_structured(self):
        eligible,reason,action=CancellationRules.evaluate_cancellation_eligibility({'order_status':'SHIPPED'})
        self.assertFalse(eligible); self.assertEqual(action,'TRACK_ORDER_OR_RETURN_AFTER_DELIVERY')
    def test_43_return_window_uses_shipment_date(self):
        now=datetime.now(timezone.utc)
        item={'order_item_id':'ITEM-1','product_name_snapshot':'Demo','quantity':1,
              'already_returned_quantity':0,'unit_price':10,'line_total':10}
        result=ReturnRules.evaluate_order_return_eligibility(
            {'order_status':'DELIVERED','shipped_at':now-timedelta(days=31),'delivered_at':now-timedelta(days=1)},[item],now)
        self.assertFalse(result['eligible']); self.assertIn('shipment',result['reason'])
    def test_44_missing_shipment_date_does_not_approve_return(self):
        result=ReturnRules.evaluate_order_return_eligibility(
            {'order_status':'DELIVERED','delivered_at':datetime.now(timezone.utc)},[],datetime.now(timezone.utc))
        self.assertFalse(result['eligible']); self.assertIn('cannot be verified',result['reason'])
    def test_45_store_and_drop_off_return_fees(self):
        service=ReturnService(self.conn); service.return_repo=FakeReturnRepo(); service.idem_repo=self.idem
        base={'order_number':'ORD-1','items':[ReturnItemRequest(order_item_id='ITEM-1')]}
        store=service.create_return(CreateReturnInput(**base,return_method='STORE'),'request-store')
        drop=service.create_return(CreateReturnInput(**base,return_method='DROP_OFF'),'request-drop')
        self.assertEqual(store[3].summary['return_fee'],0.0)
        self.assertEqual(drop[3].summary['return_fee'],4.95)
        self.assertEqual(drop[3].summary['estimated_refund'],45.05)

if __name__=='__main__': unittest.main()
