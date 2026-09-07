export interface AdminSessionRecord {
  sessionId: string;
  startedAt: string;
  durationFormatted: string;
  provider: string;
  customerType: string;
  authLevel: string;
  verified: boolean;
  turnsCount: number;
  intents: string[];
  toolsCalled: string[];
  productsDiscussed: string[];
  orderIdsAccessed: string[];
  actionsCompleted: string[];
  confirmationsRequired: number;
  handoffReason?: string;
  toolFailures: number;
  unresolvedIssues: number;
  transcriptSummary: string;
  businessOutcome: 'CONVERTED_ADD_TO_CART' | 'RESOLVED_POLICY' | 'ORDER_MODIFIED' | 'HANDOFF_ESCALATED' | 'DISCOVERY_BROWSING';
}

export interface AdminMetrics {
  totalVoiceSessions: number;
  activeSessionsNow: number;
  avgDurationSeconds: number;
  intentRecognitionRate: number;
  toolExecutionSuccessRate: number;
  humanHandoffRate: number;
  orderResolutionsToday: number;
  topIntents: Array<{ intent: string; count: number; percentage: number }>;
  topTools: Array<{ tool: string; calls: number; avgLatencyMs: number }>;
}

