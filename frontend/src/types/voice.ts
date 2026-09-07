import type { Product } from './catalog';

export type VoiceState = 'IDLE' | 'CONNECTING' | 'LISTENING' | 'THINKING' | 'SPEAKING';

/**
 * Voice session provider. Backend session accepts 'mock'. Retell integration will be supported in future phases.
 */
export type VoiceProvider = 'mock' | 'retell' | 'web_speech';

export interface VoiceSession {
  sessionId: string;
  status: 'ACTIVE' | 'PAUSED' | 'ENDED';
  provider: VoiceProvider;
  customerId?: string;
  customerType: 'GUEST' | 'REGISTERED' | 'VIP_LOYALTY';
  authLevel: 'ANONYMOUS' | 'GUEST_ORDER_VERIFIED' | 'LOGGED_IN' | 'VIP_VERIFIED';
  conversationTurn: number;
  durationSeconds: number;
  createdAt: string;
  activeOrderNumber?: string;
  currentProductId?: string;
}

export type RouteType = 
  | 'DYNAMIC_TOOL_CALL' 
  | 'RAG_GROUNDED_RETRIEVAL' 
  | 'GENERAL_CONVERSATION' 
  | 'CLARIFICATION' 
  | 'CONFIRMATION' 
  | 'HANDOFF';

export interface ConfirmationPayload {
  actionName: string;
  targetId: string;
  headline: string;
  summary: string;
  token?: string;
  expiresInSeconds?: number;
  parameters?: Record<string, unknown>;
}

export interface ClarificationPrompt {
  field: string;
  prompt: string;
  options: string[];
}

export interface HandoffDetails {
  reason: string;
  urgency: 'LOW' | 'MEDIUM' | 'HIGH';
  department: string;
  assignedQueue: string;
  estimatedWaitMinutes: number;
}

export interface VoiceTurnMessage {
  id: string;
  sender: 'user' | 'assistant' | 'system';
  text: string;
  timestamp: string;
  route?: RouteType;
  intent?: string;
  toolName?: string;
  executionStatus?: string;
  latencyMs?: number;
  products?: Product[];
  selectedProduct?: Product;
  matchingProducts?: Product[];
  confirmationPayload?: ConfirmationPayload;
  clarificationPrompt?: ClarificationPrompt;
  handoffDetails?: HandoffDetails;
  trackingData?: {
    orderNumber: string;
    carrier: string;
    trackingNumber: string;
    estimatedDelivery: string;
    currentStatus: string;
    milestones: Array<{ date: string; title: string; location: string; completed: boolean }>;
  };
  rawMetadata?: Record<string, unknown>;
}

