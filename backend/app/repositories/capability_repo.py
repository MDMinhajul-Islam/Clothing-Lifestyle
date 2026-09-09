"""Private data access for Phase 2F.1 retail capabilities."""
import json
from backend.app.repositories.base import BaseRepository

class CapabilityRepository(BaseRepository):
    def identify(self, *, email=None, phone=None, order_number=None):
        if order_number:
            sql="""SELECT c.customer_id,c.email,c.phone,o.order_id,o.order_number,
                EXISTS(SELECT 1 FROM loyalty_accounts l WHERE l.customer_id=c.customer_id) has_loyalty
                FROM orders o JOIN customers c USING(customer_id) WHERE o.order_number=%s LIMIT 1"""; params=(order_number,)
        elif email:
            sql="SELECT c.customer_id,c.email,c.phone,NULL::text order_id,NULL::text order_number,EXISTS(SELECT 1 FROM loyalty_accounts l WHERE l.customer_id=c.customer_id) has_loyalty FROM customers c WHERE lower(c.email)=lower(%s) LIMIT 1"; params=(email,)
        else:
            sql="SELECT c.customer_id,c.email,c.phone,NULL::text order_id,NULL::text order_number,EXISTS(SELECT 1 FROM loyalty_accounts l WHERE l.customer_id=c.customer_id) has_loyalty FROM customers c WHERE c.phone=%s LIMIT 1"; params=(phone,)
        with self.cursor() as cur: cur.execute(sql,params); row=cur.fetchone(); return dict(row) if row else None

    def verify(self, *, email=None, phone=None, order_number=None, proof):
        if order_number:
            sql="""SELECT c.customer_id,o.order_id,o.order_number FROM orders o JOIN customers c USING(customer_id)
                WHERE o.order_number=%s AND lower(c.email)=lower(%s) LIMIT 1"""; params=(order_number,proof)
        else:
            field='email' if email else 'phone'; identifier=email or phone
            sql=f"""SELECT DISTINCT c.customer_id,NULL::text order_id,NULL::text order_number
                FROM customers c JOIN customer_addresses a USING(customer_id)
                WHERE {'lower(c.email)=lower(%s)' if field=='email' else 'c.phone=%s'} AND a.postal_code=%s LIMIT 1"""; params=(identifier,proof)
        with self.cursor() as cur: cur.execute(sql,params); row=cur.fetchone(); return dict(row) if row else None

    def create_auth_session(self, token_hash, customer_id, order_id, auth_level, expires_at):
        with self.cursor() as cur:
            cur.execute("""INSERT INTO customer_auth_sessions(token_hash,customer_id,order_id,auth_level,expires_at)
                VALUES(%s,%s,%s,%s,%s)""",(token_hash,customer_id,order_id,auth_level,expires_at))

    def get_auth_session(self, token_hash):
        with self.cursor() as cur:
            cur.execute("""SELECT s.customer_id::text,s.order_id,s.auth_level,s.expires_at,o.order_number
                FROM customer_auth_sessions s LEFT JOIN orders o ON o.order_id=s.order_id
                WHERE s.token_hash=%s AND s.revoked_at IS NULL AND s.expires_at>now() LIMIT 1""",(token_hash,))
            row=cur.fetchone(); return dict(row) if row else None

    def get_profile(self, customer_id):
        with self.cursor() as cur:
            cur.execute("""SELECT customer_id::text,first_name,last_name,email,phone,city,state,
                preferred_language,preferred_currency,account_status FROM customers WHERE customer_id=%s""",(customer_id,))
            row=cur.fetchone(); return dict(row) if row else None

    def get_orders(self, customer_id, limit, order_id=None):
        clause='AND o.order_id=%s' if order_id else ''; params=[customer_id]
        if order_id: params.append(order_id)
        params.append(limit)
        with self.cursor() as cur:
            cur.execute(f"""SELECT o.order_id,o.order_number,o.order_status,o.placed_at,o.grand_total,o.currency,
                COALESCE(jsonb_agg(jsonb_build_object('order_item_id',oi.order_item_id,'product_id',oi.product_id,
                'variant_id',oi.variant_id,'product_name',oi.product_name_snapshot,'size',oi.size_snapshot,
                'color',oi.color_snapshot,'quantity',oi.quantity)) FILTER(WHERE oi.order_item_id IS NOT NULL),'[]') items
                FROM orders o LEFT JOIN order_items oi USING(order_id) WHERE o.customer_id=%s {clause}
                GROUP BY o.order_id ORDER BY o.placed_at DESC LIMIT %s""",tuple(params))
            return [dict(r) for r in cur.fetchall()]

    def size_guidance(self, product_id):
        with self.cursor() as cur:
            cur.execute("""SELECT p.product_id,p.fit_information,
                COALESCE(array_agg(DISTINCT v.size_name) FILTER(WHERE v.size_name IS NOT NULL),ARRAY[]::text[]) sizes
                FROM products p LEFT JOIN product_variants v USING(product_id)
                WHERE p.product_id=%s GROUP BY p.product_id""",(product_id,))
            row=cur.fetchone(); return dict(row) if row else None

    def get_loyalty(self, customer_id):
        with self.cursor() as cur:
            cur.execute("SELECT tier,points_balance,benefits,points_expire_at FROM loyalty_accounts WHERE customer_id=%s",(customer_id,))
            row=cur.fetchone(); return dict(row) if row else None

    def get_promotion(self, code):
        with self.cursor() as cur:
            cur.execute("SELECT * FROM promotions WHERE upper(promotion_code)=upper(%s)",(code,))
            row=cur.fetchone(); return dict(row) if row else None

    def order_belongs_to(self, customer_id, order_number):
        with self.cursor() as cur:
            cur.execute("SELECT order_id FROM orders WHERE customer_id=%s AND order_number=%s",(customer_id,order_number))
            row=cur.fetchone(); return dict(row) if row else None

    def item_scope(self, order_item_id):
        with self.cursor() as cur:
            cur.execute("""SELECT oi.order_item_id,oi.order_id,o.order_number,o.customer_id::text,oi.variant_id
                FROM order_items oi JOIN orders o USING(order_id) WHERE oi.order_item_id=%s""",(order_item_id,))
            row=cur.fetchone(); return dict(row) if row else None

    def verified_destinations(self, customer_id):
        with self.cursor() as cur:
            cur.execute("SELECT email,phone FROM customers WHERE customer_id=%s",(customer_id,))
            row=cur.fetchone(); return dict(row) if row else None

    def create_exchange_atomic(self, exchange_id, item, replacement_variant_id):
        return_id='RET-'+exchange_id; return_item_id='RETITEM-'+exchange_id
        with self.cursor() as cur:
            cur.execute("""INSERT INTO returns(return_id,order_id,return_status,return_reason,return_method,requested_at,is_synthetic)
                VALUES(%s,%s,'REQUESTED','Exchange requested','STORE',now(),true)""",(return_id,item['order_id']))
            cur.execute("""INSERT INTO return_items(return_item_id,return_id,order_item_id,quantity,reason_code,resolution,refund_amount,is_synthetic)
                VALUES(%s,%s,%s,1,'DOES_NOT_FIT','EXCHANGE',0,true)""",(return_item_id,return_id,item['order_item_id']))
            cur.execute("""INSERT INTO exchanges(exchange_id,return_item_id,original_variant_id,replacement_variant_id,exchange_status,requested_at,is_synthetic)
                VALUES(%s,%s,%s,%s,'APPROVED',now(),true)""",(exchange_id,return_item_id,item['variant_id'],replacement_variant_id))
            cur.execute("UPDATE orders SET order_status='RETURN_REQUESTED',updated_at=now() WHERE order_id=%s",(item['order_id'],))

    def get_exchange(self, exchange_id):
        with self.cursor() as cur:
            cur.execute("SELECT exchange_id,replacement_variant_id,exchange_status FROM exchanges WHERE exchange_id=%s",(exchange_id,))
            row=cur.fetchone(); return dict(row) if row else None

    def create_incident(self, incident_id, customer_id, order_id, order_item_id, issue_type, summary):
        with self.cursor() as cur: cur.execute("""INSERT INTO incidents(incident_id,customer_id,order_id,order_item_id,issue_type,factual_summary)
            VALUES(%s,%s,%s,%s,%s,%s)""",(incident_id,customer_id,order_id,order_item_id,issue_type,summary))

    def create_support_case(self, case_id, customer_id, order_id, product_id, data):
        with self.cursor() as cur: cur.execute("""INSERT INTO support_cases(case_id,customer_id,order_id,product_id,issue_category,
            requested_outcome,factual_summary,verified_facts,attempted_actions,tool_errors)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb)""",
            (case_id,customer_id,order_id,product_id,data.issue_category,data.requested_outcome,data.factual_summary,
             json.dumps(data.verified_facts),json.dumps(data.attempted_actions),json.dumps(data.tool_errors)))

    def order_request_product(self, product_id, variant_id):
        with self.cursor() as cur:
            cur.execute("""SELECT p.product_id,p.exact_product_name product_name,p.current_price::float price,p.currency,
                v.variant_id,v.sku,v.size_name,v.public_availability_state,v.color_name color
                FROM products p JOIN product_variants v USING(product_id)
                WHERE p.product_id=%s AND v.variant_id=%s AND p.lifecycle_status='ACTIVE'""",(product_id,variant_id))
            row=cur.fetchone(); return dict(row) if row else None

    def shipping_address(self, customer_id, address_id=None):
        clause="AND address_id=%s" if address_id else "ORDER BY is_default_shipping DESC,created_at LIMIT 1"
        params=(customer_id,address_id) if address_id else (customer_id,)
        with self.cursor() as cur:
            cur.execute(f"SELECT * FROM customer_addresses WHERE customer_id=%s {clause}",params)
            row=cur.fetchone(); return dict(row) if row else None

    def create_shipping_address(self, customer_id, address_id, data):
        with self.cursor() as cur: cur.execute("""INSERT INTO customer_addresses(address_id,customer_id,recipient_name,address_line_1,address_line_2,city,state,postal_code,country_code,is_default_shipping,is_default_billing,is_synthetic)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,false,false,true)""",(address_id,customer_id,data.recipient_name,data.address_line_1,data.address_line_2,data.city,data.state,data.postal_code,data.country_code))

    def create_order_request(self, order_id, order_number, customer_id, address_id, item_id, product, quantity):
        total=product['price']*quantity
        with self.cursor() as cur:
            cur.execute("""INSERT INTO orders(order_id,order_number,customer_id,order_status,shipping_address_id,currency,subtotal,grand_total,payment_status,placed_at,is_synthetic,data_origin)
                VALUES(%s,%s,%s,'PENDING_PAYMENT',%s,%s,%s,%s,'PENDING',now(),true,'voice_commerce_mvp')""",(order_id,order_number,customer_id,address_id,product['currency'],total,total,total))
            cur.execute("""INSERT INTO order_items(order_item_id,order_id,product_id,variant_id,quantity,unit_price,line_total,product_name_snapshot,size_snapshot,color_snapshot,is_synthetic)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,true)""",(item_id,order_id,product['product_id'],product['variant_id'],quantity,product['price'],total,product['product_name'],product.get('size_name'),product.get('color')))

    def get_order_request(self, order_id, customer_id):
        with self.cursor() as cur:
            cur.execute("""SELECT o.order_id,o.order_number,o.order_status,o.payment_status,o.grand_total::float,
                o.currency,o.created_at,oi.product_id,oi.variant_id,oi.product_name_snapshot product_name,
                oi.color_snapshot color,oi.size_snapshot size,oi.quantity
                FROM orders o JOIN order_items oi USING(order_id)
                WHERE o.order_id=%s AND o.customer_id=%s LIMIT 1""",(order_id,customer_id))
            row=cur.fetchone(); return dict(row) if row else None

    def record_notification(self, order_id, event_type, provider, recipient_hash, status,
                            provider_message_id=None, failure_code=None):
        with self.cursor() as cur:
            cur.execute("""INSERT INTO notification_history(order_id,event_type,provider,recipient_hash,
                delivery_status,provider_message_id,failure_code,sent_at)
                VALUES(%s,%s,%s,%s,%s,%s,%s,CASE WHEN %s='SENT' THEN now() ELSE NULL END)""",
                (order_id,event_type,provider,recipient_hash,status,provider_message_id,failure_code,status))

    def admin_orders(self, limit=100):
        with self.cursor() as cur:
            cur.execute("""SELECT o.order_number,concat(c.first_name,' ',c.last_name) customer,p.product_name_snapshot product,
                p.variant_id,p.size_snapshot size,p.quantity,o.order_status,o.payment_status,o.created_at
                FROM orders o JOIN customers c USING(customer_id) LEFT JOIN order_items p USING(order_id)
                ORDER BY o.created_at DESC LIMIT %s""",(limit,)); return [dict(r) for r in cur.fetchall()]

    def admin_cases(self, limit=100):
        with self.cursor() as cur:
            cur.execute("""SELECT s.case_id,concat(c.first_name,' ',c.last_name) customer,o.order_number,
                s.issue_category category,s.factual_summary summary,s.case_status status,s.created_at
                FROM support_cases s LEFT JOIN customers c USING(customer_id) LEFT JOIN orders o USING(order_id)
                ORDER BY s.created_at DESC LIMIT %s""",(limit,)); return [dict(r) for r in cur.fetchall()]
