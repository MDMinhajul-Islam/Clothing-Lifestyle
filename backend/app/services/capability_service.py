"""Authorized Phase 2F.1 retail capabilities over existing repositories/services."""
import hashlib, secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from backend.app.repositories.capability_repo import CapabilityRepository
from backend.app.repositories.idempotency_repo import IdempotencyRepository
from backend.app.services.exchange_service import ExchangeService
from backend.app.services.inventory_service import InventoryService
from backend.app.schemas.inventory import CheckInventoryInput
from backend.app.schemas.returns import CheckExchangeAvailabilityInput
from backend.app.schemas.common import ConfirmationPayload, ErrorCode, ToolError
from backend.app.schemas.capabilities import *
from backend.app.utils.security import generate_confirmation_token, verify_confirmation_token, hash_request_payload

class RetailCapabilityService:
    def __init__(self,conn,*,repo=None,inventory=None,exchange=None,idempotency=None):
        self.conn=conn; self.repo=repo or CapabilityRepository(conn)
        self.inventory=inventory or InventoryService(conn); self.exchange=exchange or ExchangeService(conn)
        self.idempotency=idempotency or IdempotencyRepository(conn)

    @staticmethod
    def _hash(token): return hashlib.sha256(token.encode()).hexdigest()
    @staticmethod
    def _mask(value):
        if not value:return None
        if '@' in value:
            left,domain=value.split('@',1); return (left[:1]+'***@'+domain)
        return '***'+value[-4:]

    def identify_customer(self,d):
        row=self.repo.identify(email=d.email,phone=d.phone,order_number=d.order_number)
        if not row:return IdentifyCustomerOutput(found=False,customer_type='ANONYMOUS')
        destination=row.get('email') or row.get('phone')
        customer_type='GUEST' if d.order_number else ('LOYALTY' if row.get('has_loyalty') else 'REGISTERED')
        return IdentifyCustomerOutput(found=True,customer_type=customer_type,
            masked_destination=self._mask(destination),verification_method='ORDER_EMAIL' if d.order_number else 'POSTAL_CODE')

    def verify_customer(self,d):
        row=self.repo.verify(email=d.email,phone=d.phone,order_number=d.order_number,proof=d.verification_value)
        if not row:return VerifyCustomerOutput(verified=False,auth_level=AuthLevel.PUBLIC,customer_type='UNKNOWN')
        level=AuthLevel.ORDER_VERIFIED if d.order_number else AuthLevel.TRANSACTION_VERIFIED
        token=secrets.token_urlsafe(32); expires=datetime.now(timezone.utc)+timedelta(minutes=30)
        self.repo.create_auth_session(self._hash(token),row.get('customer_id'),row.get('order_id'),level.value,expires)
        self.conn.commit()
        return VerifyCustomerOutput(verified=True,auth_level=level,access_token=token,expires_at=expires.isoformat(),
                                    customer_type='GUEST' if d.order_number else 'REGISTERED')

    def _auth(self,token,*,transaction=False,order_number=None,order_item_id=None):
        auth=self.repo.get_auth_session(self._hash(token))
        if not auth or (transaction and auth['auth_level']!='TRANSACTION_VERIFIED'): raise PermissionError('Verified access is required.')
        if order_item_id:
            item=self.repo.item_scope(order_item_id)
            if not item: raise ValueError('Order item was not found.')
            if auth['auth_level']=='ORDER_VERIFIED' and item['order_id']!=auth['order_id']: raise PermissionError('Access is restricted to the verified order.')
            if auth['auth_level']=='TRANSACTION_VERIFIED' and item['customer_id']!=auth['customer_id']: raise PermissionError('Access is restricted to the verified customer.')
        if order_number:
            if auth['auth_level']=='ORDER_VERIFIED' and auth.get('order_number')!=order_number: raise PermissionError('Access is restricted to the verified order.')
            if auth['auth_level']=='TRANSACTION_VERIFIED' and not self.repo.order_belongs_to(auth['customer_id'],order_number): raise PermissionError('Access is restricted to the verified customer.')
        return auth

    def authorize_private_access(self,access_token,*,order_number=None,order_item_id=None):
        """Validate registered ownership or guest order scope for legacy private tools."""
        return self._auth(access_token,order_number=order_number,order_item_id=order_item_id)

    def get_customer_profile(self,d):
        auth=self._auth(d.access_token,transaction=True); row=self.repo.get_profile(auth['customer_id'])
        return AuthorizedProfileOutput(**row,auth_level=auth['auth_level'])
    def get_customer_orders(self,d):
        auth=self._auth(d.access_token); rows=self.repo.get_orders(auth['customer_id'],d.limit,auth.get('order_id') if auth['auth_level']=='ORDER_VERIFIED' else None)
        items=[OrderHistoryItem(order_number=r['order_number'],order_status=r['order_status'],placed_at=r['placed_at'].isoformat() if hasattr(r['placed_at'],'isoformat') else str(r['placed_at']),grand_total=float(r['grand_total']),currency=r['currency'],items=r['items']) for r in rows]
        return GetCustomerOrdersOutput(auth_level=auth['auth_level'],total_orders=len(items),orders=items)

    def get_size_guidance(self,d):
        row=self.repo.size_guidance(d.product_id)
        if not row or (not row.get('fit_information') and not row.get('sizes')):
            return SizeGuidanceOutput(product_id=d.product_id,status='INSUFFICIENT_SIZE_EVIDENCE',advisory='Fit cannot be verified from the available product data.')
        return SizeGuidanceOutput(product_id=d.product_id,status='DOCUMENTED_EVIDENCE',documented_fit=row.get('fit_information'),
            documented_sizes=row.get('sizes') or [],advisory='Use the documented fit and available size labels as guidance; fit is not guaranteed.')

    def check_pickup_availability(self,d):
        out=self.inventory.check_inventory(CheckInventoryInput(product_id=d.product_id,variant_id=d.variant_id,
            store_id=d.store_id,size=d.size,color=d.color))
        variants=len(out.matching_variants); qty=sum(s.quantity_available for v in out.matching_variants for s in v.stores if s.store_id==d.store_id)
        status='UNKNOWN' if variants==0 else ('AVAILABLE' if qty>0 else 'UNAVAILABLE')
        return CheckPickupAvailabilityOutput(status=status,quantity_available=qty,matching_variants=variants,store_id=d.store_id,product_id=d.product_id)

    def get_loyalty_status(self,d):
        auth=self._auth(d.access_token,transaction=True); row=self.repo.get_loyalty(auth['customer_id'])
        if not row: raise ValueError('No synthetic loyalty account is available.')
        return LoyaltyStatusOutput(tier=row['tier'],points_balance=row['points_balance'],benefits=row['benefits'],
            points_expire_at=row['points_expire_at'].isoformat() if row.get('points_expire_at') else None)

    def check_promotion(self,d):
        row=self.repo.get_promotion(d.promotion_code); reasons=[]
        if not row:return CheckPromotionOutput(eligible=False,status='INVALID',reason_codes=['INVALID_CODE'])
        now=datetime.now(timezone.utc); starts=row['starts_at']; ends=row['ends_at']
        if starts.tzinfo is None: starts=starts.replace(tzinfo=timezone.utc)
        if ends.tzinfo is None: ends=ends.replace(tzinfo=timezone.utc)
        if row['status']!='ACTIVE' or now>=ends: reasons.append('EXPIRED_OR_INACTIVE')
        elif now<starts: reasons.append('NOT_STARTED')
        if d.cart_subtotal<float(row['minimum_spend']): reasons.append('MINIMUM_SPEND_NOT_MET')
        eligible_ids=row.get('eligible_product_ids')
        if eligible_ids and d.product_id not in eligible_ids: reasons.append('PRODUCT_NOT_ELIGIBLE')
        if not reasons: reasons=['ELIGIBLE']
        return CheckPromotionOutput(eligible=reasons==['ELIGIBLE'],status='ELIGIBLE' if reasons==['ELIGIBLE'] else 'INELIGIBLE',
            reason_codes=reasons,discount_type=row['discount_type'],discount_value=float(row['discount_value']),stacking_allowed=row['stacking_allowed'])

    def check_exchange_inventory(self,d):
        self._auth(d.access_token,order_item_id=d.order_item_id)
        request=CheckExchangeAvailabilityInput(order_item_id=d.order_item_id,
            replacement_size=d.replacement_size,replacement_color=d.replacement_color,store_id=d.store_id)
        return self.exchange.check_exchange_availability(request)

    def _cached(self,key,request_hash,model):
        if not key:return None
        row=self.idempotency.get_idempotency_record(key)
        if not row:return None
        if row['request_hash']!=request_hash: raise ValueError('Idempotency key conflicts with a different request.')
        return model(**row['response_json'])

    def _confirm(self,action,entity,d,prompt,summary):
        if d.confirmed and d.confirmation_token and verify_confirmation_token(d.confirmation_token,action,entity): return None
        payload=ConfirmationPayload(action=action,entity_id=entity,confirmation_token=generate_confirmation_token(action,entity),prompt_message=prompt,summary=summary)
        return (False,None,ToolError(code=ErrorCode.CONFIRMATION_REQUIRED,message='Explicit confirmation is required.'),payload,False)

    def create_exchange(self,d):
        self._auth(d.access_token,order_item_id=d.order_item_id); req_hash=hash_request_payload(d.model_dump())
        cached=self._cached(d.idempotency_key,req_hash,CreateExchangeOutput)
        if cached:return True,cached,None,None,True
        check=self.exchange.check_exchange_availability(CheckExchangeAvailabilityInput(order_item_id=d.order_item_id,replacement_size=d.replacement_size,replacement_color=d.replacement_color,store_id=d.store_id))
        if not check.eligible:return False,None,ToolError(code=ErrorCode.RETURN_NOT_ELIGIBLE,message=check.reason),None,False
        gate=self._confirm('create_exchange',d.order_item_id,d,
            f"Please confirm exchange for item {d.order_item_id}. The reference policy requires the replaced merchandise to be returned within 14 days; this demo does not automatically enforce or charge for that deadline.",
            {'order_item_id':d.order_item_id,'replacement_variant':check.replacement_variant,'reference_return_days':14,'automatic_charge_enforced':False})
        if gate:return gate
        item=self.repo.item_scope(d.order_item_id); exchange_id='EXC-'+uuid4().hex[:16].upper()
        self.repo.create_exchange_atomic(exchange_id,item,check.replacement_variant['variant_id'])
        verified=self.repo.get_exchange(exchange_id)
        if not verified: raise RuntimeError('Exchange write verification failed.')
        out=CreateExchangeOutput(exchange_id=exchange_id,order_item_id=d.order_item_id,
            replacement_variant_id=verified['replacement_variant_id'],exchange_status=verified['exchange_status'])
        if d.idempotency_key:self.idempotency.record_idempotency(d.idempotency_key,'create_exchange',req_hash,out.model_dump())
        self.conn.commit(); return True,out,None,None,False

    def create_incident(self,d):
        auth=self._auth(d.access_token,order_number=d.order_number,order_item_id=d.order_item_id); req_hash=hash_request_payload(d.model_dump())
        cached=self._cached(d.idempotency_key,req_hash,CreateIncidentOutput)
        if cached:return True,cached,None,None,True
        gate=self._confirm('create_incident',d.order_item_id,d,
            'Please confirm that I should record this issue for human review. This does not approve a refund or replacement.',
            {'issue_type':d.issue_type,'order_number':d.order_number})
        if gate:return gate
        item=self.repo.item_scope(d.order_item_id); incident_id='INC-'+uuid4().hex[:16].upper()
        self.repo.create_incident(incident_id,item['customer_id'],item['order_id'],d.order_item_id,d.issue_type,d.factual_summary)
        out=CreateIncidentOutput(incident_id=incident_id,incident_status='OPEN')
        if d.idempotency_key:self.idempotency.record_idempotency(d.idempotency_key,'create_incident',req_hash,out.model_dump())
        self.conn.commit(); return True,out,None,None,False

    def create_support_case(self,d):
        auth=self._auth(d.access_token,order_number=d.order_number); req_hash=hash_request_payload(d.model_dump())
        cached=self._cached(d.idempotency_key,req_hash,CreateSupportCaseOutput)
        if cached:return True,cached,None,None,True
        entity=d.order_number or auth['customer_id']; gate=self._confirm('create_support_case',entity,d,'Please confirm creation of a support case.',{'issue_category':d.issue_category})
        if gate:return gate
        order=self.repo.order_belongs_to(auth['customer_id'],d.order_number) if d.order_number else None
        case_id='CASE-'+uuid4().hex[:16].upper(); self.repo.create_support_case(case_id,auth['customer_id'],order['order_id'] if order else None,d.product_id,d)
        out=CreateSupportCaseOutput(case_id=case_id,case_status='OPEN')
        if d.idempotency_key:self.idempotency.record_idempotency(d.idempotency_key,'create_support_case',req_hash,out.model_dump())
        self.conn.commit(); return True,out,None,None,False

    def prepare_handoff(self,d):
        auth=None
        if d.access_token: auth=self._auth(d.access_token,order_number=d.order_number)
        elif d.order_number: raise PermissionError('Verified access is required for referenced private context.')
        return {'customer_id':auth.get('customer_id') if auth else None,'auth_level':auth['auth_level'] if auth else 'PUBLIC','intent':d.intent,
            'order_id':d.order_number,'product_id':d.product_id,'verified_facts':d.verified_facts,'actions_attempted':d.actions_attempted,
            'tool_errors':d.tool_errors,'case_reference_id':d.case_reference_id,'customer_requested_outcome':d.customer_requested_outcome,
            'factual_summary':d.factual_summary,'recommended_route':'HUMAN_SUPPORT'}

    def send_secure_link(self,d):
        if not d.consent_confirmed: raise PermissionError('Explicit destination consent is required.')
        auth=self._auth(d.access_token); destinations=self.repo.verified_destinations(auth['customer_id'])
        if not destinations or d.destination not in (destinations.get('email'),destinations.get('phone')): raise PermissionError('Destination is not verified for this customer.')
        return {'status':'DELIVERY_NOT_CONFIGURED','purpose':d.purpose,'handoff_url':f"https://example.invalid/secure-handoff/{d.purpose.lower()}",
                'delivery_claimed':False,'data_origin':'synthetic_operational_layer'}
