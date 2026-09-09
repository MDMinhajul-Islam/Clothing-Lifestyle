"""Database access for Customer Portal credentials and sessions."""
from backend.app.repositories.base import BaseRepository

class CustomerAuthRepository(BaseRepository):
    def customer_by_email(self,email):
        with self.cursor() as cur:
            cur.execute("SELECT customer_id::text,first_name,last_name,email,phone FROM customers WHERE lower(email)=lower(%s) LIMIT 1",(email,))
            row=cur.fetchone(); return dict(row) if row else None

    def credentials_by_email(self,email):
        with self.cursor() as cur:
            cur.execute("""SELECT c.customer_id::text,c.first_name,c.last_name,c.email,c.phone,c.account_status,
                cc.password_hash,cc.email_verified_at,cc.failed_login_count,cc.locked_until
                FROM customers c JOIN customer_credentials cc USING(customer_id)
                WHERE lower(c.email)=lower(%s) LIMIT 1""",(email,))
            row=cur.fetchone(); return dict(row) if row else None

    def create_customer(self,customer_id,data):
        with self.cursor() as cur:
            cur.execute("""INSERT INTO customers(customer_id,first_name,last_name,email,phone,is_synthetic,data_origin)
                VALUES(%s,%s,%s,%s,%s,false,'customer_portal')""",
                (customer_id,data.first_name,data.last_name,data.email,data.phone))

    def create_credentials(self,customer_id,password_hash):
        with self.cursor() as cur:
            cur.execute("INSERT INTO customer_credentials(customer_id,password_hash) VALUES(%s,%s)",
                        (customer_id,password_hash))

    def replace_token(self,customer_id,purpose,token_hash,expires_at):
        with self.cursor() as cur:
            cur.execute("DELETE FROM customer_portal_tokens WHERE customer_id=%s AND purpose=%s AND consumed_at IS NULL",
                        (customer_id,purpose))
            cur.execute("""INSERT INTO customer_portal_tokens(token_hash,customer_id,purpose,expires_at)
                VALUES(%s,%s,%s,%s)""",(token_hash,customer_id,purpose,expires_at))

    def consume_token(self,token_hash,purpose):
        with self.cursor() as cur:
            cur.execute("""UPDATE customer_portal_tokens SET consumed_at=now()
                WHERE token_hash=%s AND purpose=%s AND consumed_at IS NULL AND expires_at>now()
                RETURNING customer_id::text""",(token_hash,purpose))
            row=cur.fetchone(); return dict(row) if row else None

    def mark_verified(self,customer_id):
        with self.cursor() as cur:
            cur.execute("UPDATE customer_credentials SET email_verified_at=COALESCE(email_verified_at,now()),updated_at=now() WHERE customer_id=%s",(customer_id,))

    def login_failed(self,customer_id,locked):
        with self.cursor() as cur:
            cur.execute("""UPDATE customer_credentials SET failed_login_count=failed_login_count+1,
                locked_until=CASE WHEN %s THEN now()+interval '15 minutes' ELSE locked_until END,updated_at=now()
                WHERE customer_id=%s""",(locked,customer_id))

    def login_succeeded(self,customer_id):
        with self.cursor() as cur:
            cur.execute("UPDATE customer_credentials SET failed_login_count=0,locked_until=NULL,updated_at=now() WHERE customer_id=%s",(customer_id,))

    def create_session(self,token_hash,customer_id,expires_at):
        with self.cursor() as cur:
            cur.execute("INSERT INTO customer_portal_sessions(token_hash,customer_id,expires_at) VALUES(%s,%s,%s)",
                        (token_hash,customer_id,expires_at))

    def session_customer(self,token_hash):
        with self.cursor() as cur:
            cur.execute("""UPDATE customer_portal_sessions s SET last_seen_at=now()
                FROM customers c WHERE s.token_hash=%s AND s.customer_id=c.customer_id
                AND s.revoked_at IS NULL AND s.expires_at>now()
                RETURNING c.customer_id::text,c.first_name,c.last_name,c.email,c.phone,c.city,c.state""",(token_hash,))
            row=cur.fetchone(); return dict(row) if row else None

    def revoke_session(self,token_hash):
        with self.cursor() as cur: cur.execute("UPDATE customer_portal_sessions SET revoked_at=now() WHERE token_hash=%s",(token_hash,))

    def reset_password(self,customer_id,password_hash):
        with self.cursor() as cur:
            cur.execute("""UPDATE customer_credentials SET password_hash=%s,password_changed_at=now(),
                failed_login_count=0,locked_until=NULL,updated_at=now() WHERE customer_id=%s""",(password_hash,customer_id))
            cur.execute("UPDATE customer_portal_sessions SET revoked_at=now() WHERE customer_id=%s AND revoked_at IS NULL",(customer_id,))

    def addresses(self,customer_id):
        with self.cursor() as cur:
            cur.execute("""SELECT address_id::text,recipient_name,address_line_1,address_line_2,city,state,
                postal_code,country_code,is_default_shipping FROM customer_addresses
                WHERE customer_id=%s ORDER BY is_default_shipping DESC,created_at""",(customer_id,))
            return [dict(row) for row in cur.fetchall()]

    def orders(self,customer_id,limit=25):
        with self.cursor() as cur:
            cur.execute("""SELECT order_number,order_status,payment_status,grand_total::float,currency,placed_at
                FROM orders WHERE customer_id=%s ORDER BY placed_at DESC LIMIT %s""",(customer_id,limit))
            return [dict(row) for row in cur.fetchall()]

    def owns_order(self,customer_id,order_number):
        with self.cursor() as cur:
            cur.execute("SELECT 1 FROM orders WHERE customer_id=%s AND order_number=%s",(customer_id,order_number))
            return cur.fetchone() is not None
