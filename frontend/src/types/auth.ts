export type AuthLevel = 'ANONYMOUS' | 'GUEST_ORDER_VERIFIED' | 'LOGGED_IN' | 'VIP_VERIFIED';

export type CustomerType = 'GUEST' | 'REGISTERED' | 'VIP_LOYALTY';

export interface CustomerProfile {
  id: string;
  name: string;
  email: string;
  phone?: string;
  type: CustomerType;
  authLevel: AuthLevel;
  verified: boolean;
  activeOrderNumber?: string;
  defaultAddress?: string;
  addresses?: Array<Record<string, unknown>>;
  orders?: Array<Record<string, unknown>>;
}
