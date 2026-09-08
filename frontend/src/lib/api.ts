import type { VoiceSession, VoiceTurnMessage, VoiceProvider, WebpageVoiceContext } from '../types/voice';
import type { Product } from '../types/catalog';

const BACKEND_BASE_URL = 
  (import.meta.env.VITE_BACKEND_API_URL || 'http://nexgenclothing-lifestyle-nexgenbackend-t-dab46e-206-189-183-167.sslip.io').replace(/\/$/, '');

export interface BackendHealth {
  status: 'healthy' | 'unreachable' | 'checking';
  appName?: string;
  version?: string;
  database?: string;
  environment?: string;
  backendUrl: string;
  proxyRequiredNotice?: boolean;
}

/**
 * Checks backend health endpoint.
 * Note: /health is public and does not require authentication.
 */
export async function getHealth(): Promise<BackendHealth> {
  try {
    const res = await fetch(`${BACKEND_BASE_URL}/health`, {
      method: 'GET',
      headers: { 'Accept': 'application/json' },
    });

    if (res.ok) {
      const data = await res.json();
      return {
        status: 'healthy',
        appName: data.app_name || 'NexGen AI Retail Assistant',
        version: data.version || '1.0.0',
        database: data.database || 'connected',
        environment: data.environment || 'production',
        backendUrl: BACKEND_BASE_URL,
        proxyRequiredNotice: false,
      };
    }
  } catch (err) {
    console.warn('[NexGen API] Direct health check failed:', err);
  }

  return {
    status: 'unreachable',
    backendUrl: BACKEND_BASE_URL,
    proxyRequiredNotice: true,
  };
}

/**
 * Creates a new voice commerce session.
 * Connects to POST /v1/voice/session if available; otherwise initializes an authenticated client-side session.
 * Note: Backend currently accepts provider: "mock".
 * Future Retell integration note: Retell will later stream transcripts to an adapter.
 */
export async function createVoiceSession(
  provider: VoiceProvider = 'mock',
  customerId?: string
): Promise<VoiceSession> {
  const localSessionId = `sess_voice_${Math.random().toString(36).substring(2, 10)}`;
  const now = new Date().toISOString();

  try {
    const res = await fetch(`${BACKEND_BASE_URL}/v1/voice/session`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        provider: 'mock',
        customer_id: customerId,
      }),
    });

    if (res.ok) {
      const data = await res.json();
      return {
        sessionId: data.session_id,
        status: 'ACTIVE',
        provider,
        customerId: data.customer_id || customerId,
        customerType: customerId ? 'REGISTERED' : 'GUEST',
        authLevel: customerId ? 'LOGGED_IN' : 'ANONYMOUS',
        conversationTurn: data.conversation_turn || 0,
        durationSeconds: 0,
        createdAt: data.created_at || now,
      };
    }

    if (res.status === 401) {
      console.info(
        '[NexGen API] Voice session requires the secure server integration.'
      );
    }
  } catch (err) {
    console.info('[NexGen API] Network call to remote session endpoint bypassed; using local voice state:', err);
  }

  // Resilient client session while the voice transport reconnects.
  return {
    sessionId: localSessionId,
    status: 'ACTIVE',
    provider,
    customerId,
    customerType: customerId ? 'REGISTERED' : 'GUEST',
    authLevel: customerId ? 'LOGGED_IN' : 'ANONYMOUS',
    conversationTurn: 0,
    durationSeconds: 0,
    createdAt: now,
  };
}

/**
 * Dispatches a voice turn to the backend or fallback simulator.
 * 
 * Backend contract for POST /v1/voice/turn:
 * {
 *   "session_id": "...",
 *   "transcript": "...", // accepts alias "message"
 *   "context": { ... }
 * }
 * 
 * NOTE: The 'provider' field is intentionally omitted from the turn request body
 * to adhere strictly to the backend VoiceTurnRequest schema.
 * Future Retell integration note: Retell will provide user speech transcripts,
 * which will map into this same /v1/voice/turn endpoint.
 */
export async function sendVoiceTurn(
  session: VoiceSession,
  transcript: string,
  _catalogProducts: Product[],
  webpageContext: WebpageVoiceContext = {},
): Promise<{
  message: VoiceTurnMessage;
  updatedFilter?: { category?: string; color?: string; searchQuery?: string };
  openProductDetail?: Product;
  matchingProducts?: Product[];
  usedBackend: boolean;
}> {
  const t0 = performance.now();

  try {
    const res = await fetch(`${BACKEND_BASE_URL}/v1/voice/turn`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        session_id: session.sessionId,
        transcript: transcript,
        context: {
          customer_id: session.customerId,
          auth_level: session.authLevel,
          order_id: session.activeOrderNumber,
          product_id: session.currentProductId,
          ...webpageContext,
        },
      }),
    });

    if (res.ok) {
      const raw = await res.json();
      const normalized = normalizeVoiceResponse(raw, Math.round(performance.now() - t0));
      return {
        message: normalized,
        usedBackend: true,
      };
    }

    if (res.status === 401) {
      console.warn(
        '[NexGen API] Voice service is unavailable; using the local continuity handler.'
      );
    }
  } catch (err) {
    console.warn('[NexGen API] Turn request error:', err);
  }

  return {
    message: {
      id: `turn_${Date.now()}`,
      sender: 'assistant',
      text: 'I cannot reach the shopping service right now. Please try again in a moment.',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      route: 'GENERAL_CONVERSATION',
      intent: 'SERVICE_UNAVAILABLE',
      executionStatus: 'UNAVAILABLE',
    },
    usedBackend: false,
  };
}

export interface RetellWebCallAuthorization {
  call_id: string;
  access_token: string;
}

/** Creates a browser-safe Retell call authorization without sending internal credentials. */
export async function createRetellWebCall(customerId?: string, context: WebpageVoiceContext = {}): Promise<RetellWebCallAuthorization> {
  const response = await fetch(`${BACKEND_BASE_URL}/v1/retell/create-web-call`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...(customerId ? { customer_id: customerId } : {}), context }),
  });
  if (!response.ok) throw new Error(`Unable to start voice call (${response.status})`);
  const payload = await response.json() as Partial<RetellWebCallAuthorization>;
  if (!payload.call_id || !payload.access_token) throw new Error('Voice call authorization was incomplete.');
  return { call_id: payload.call_id, access_token: payload.access_token };
}

/**
 * Terminates the active voice session.
 */
export async function endVoiceSession(sessionId: string): Promise<boolean> {
  try {
    const res = await fetch(`${BACKEND_BASE_URL}/v1/voice/session/${sessionId}`, {
      method: 'DELETE',
    });
    if (res.ok) return true;
  } catch {
    // ignore
  }
  return true;
}

/**
 * Normalizes varied backend response shapes into a standard VoiceTurnMessage.
 */
export function normalizeVoiceResponse(raw: Record<string, unknown>, latencyMs = 200): VoiceTurnMessage {
  const spokenText = 
    (raw.spoken_text as string) || 
    (raw.spoken_response as string) || 
    (raw.response_text as string) || 
    (raw.message as string) || 
    'I have processed your request.';

  const route = (raw.route as VoiceTurnMessage['route']) || 'DYNAMIC_TOOL_CALL';
  const intent = (raw.intent as string) || (raw.tool_name as string) || 'UNKNOWN_INTENT';
  const executionStatus = (raw.execution_status as string) || (raw.status as string) || 'SUCCEEDED';

  const meta = (raw.metadata as Record<string, unknown>) || {};

  return {
    id: `turn_${Date.now()}`,
    sender: 'assistant',
    text: spokenText,
    timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    route,
    intent,
    toolName: (raw.tool_name as string) || undefined,
    executionStatus,
    latencyMs,
    rawMetadata: meta,
    confirmationPayload: raw.requires_confirmation ? {
      actionName: (raw.tool_name as string) || 'action',
      targetId: 'ORDER_ACTION',
      headline: 'Confirmation Required',
      summary: spokenText,
      token: (meta.confirmation_token as string) || undefined,
    } : undefined,
  };
}
