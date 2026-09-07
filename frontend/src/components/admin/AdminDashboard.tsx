import React from 'react';
import { 
  Users, PhoneCall, CheckCircle2, ArrowUpRight, 
  Search, ShieldCheck, Activity, ArrowLeft 
} from 'lucide-react';
import { MOCK_ADMIN_METRICS, MOCK_ADMIN_SESSIONS } from '../../data/mockAdmin';
import type { AdminSessionRecord } from '../../types/admin';

interface AdminDashboardProps {
  onBackToStorefront: () => void;
}

export const AdminDashboard: React.FC<AdminDashboardProps> = ({ onBackToStorefront }) => {
  const [selectedSession, setSelectedSession] = React.useState<AdminSessionRecord | null>(MOCK_ADMIN_SESSIONS[0]);
  const [searchQuery, setSearchQuery] = React.useState('');

  const filteredSessions = MOCK_ADMIN_SESSIONS.filter((s) =>
    s.sessionId.toLowerCase().includes(searchQuery.toLowerCase()) ||
    s.intents.some(i => i.toLowerCase().includes(searchQuery.toLowerCase())) ||
    s.transcriptSummary.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="min-h-screen bg-neutral-100 text-neutral-900 pb-16">
      {/* Top Bar */}
      <header className="border-b border-neutral-200 bg-white sticky top-0 z-30">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <button
              onClick={onBackToStorefront}
              className="flex items-center space-x-1.5 px-3 py-1.5 text-xs text-neutral-600 hover:text-black hover:bg-neutral-100 transition-colors uppercase tracking-wider font-medium"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Back to Store</span>
            </button>
            <span className="text-neutral-300">|</span>
            <div className="flex items-center space-x-2">
              <span className="font-display tracking-widest text-lg font-bold uppercase">NEXGEN</span>
              <span className="text-xs font-mono uppercase bg-neutral-900 text-white px-2 py-0.5 tracking-wider">
                Ops Console
              </span>
            </div>
          </div>

          <div className="flex items-center space-x-3 text-xs font-mono text-neutral-500">
            <span className="flex items-center space-x-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <span>Voice Cluster: US-East (Healthy)</span>
            </span>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 pt-8 space-y-8">
        {/* KPI Metrics Grid */}
        <section className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-5 bg-white border border-neutral-200 shadow-sm space-y-1">
            <span className="text-[11px] font-mono uppercase tracking-wider text-neutral-500 flex items-center justify-between">
              <span>Total Voice Sessions</span>
              <PhoneCall className="w-3.5 h-3.5 text-neutral-400" />
            </span>
            <div className="text-2xl font-bold font-mono text-neutral-900">
              {MOCK_ADMIN_METRICS.totalVoiceSessions.toLocaleString()}
            </div>
            <span className="text-[10px] text-emerald-600 font-mono flex items-center">
              <ArrowUpRight className="w-3 h-3 mr-0.5" />
              +14% vs last week
            </span>
          </div>

          <div className="p-5 bg-white border border-neutral-200 shadow-sm space-y-1">
            <span className="text-[11px] font-mono uppercase tracking-wider text-neutral-500 flex items-center justify-between">
              <span>Intent Accuracy</span>
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
            </span>
            <div className="text-2xl font-bold font-mono text-neutral-900">
              {MOCK_ADMIN_METRICS.intentRecognitionRate}%
            </div>
            <span className="text-[10px] text-neutral-500 font-mono">
              Deterministic Tool Gateway
            </span>
          </div>

          <div className="p-5 bg-white border border-neutral-200 shadow-sm space-y-1">
            <span className="text-[11px] font-mono uppercase tracking-wider text-neutral-500 flex items-center justify-between">
              <span>Tool Execution Success</span>
              <Activity className="w-3.5 h-3.5 text-blue-500" />
            </span>
            <div className="text-2xl font-bold font-mono text-neutral-900">
              {MOCK_ADMIN_METRICS.toolExecutionSuccessRate}%
            </div>
            <span className="text-[10px] text-neutral-500 font-mono">
              Avg latency: 228ms
            </span>
          </div>

          <div className="p-5 bg-white border border-neutral-200 shadow-sm space-y-1">
            <span className="text-[11px] font-mono uppercase tracking-wider text-neutral-500 flex items-center justify-between">
              <span>Human Handoff Rate</span>
              <Users className="w-3.5 h-3.5 text-amber-500" />
            </span>
            <div className="text-2xl font-bold font-mono text-neutral-900">
              {MOCK_ADMIN_METRICS.humanHandoffRate}%
            </div>
            <span className="text-[10px] text-neutral-500 font-mono">
              32 concierge escalations
            </span>
          </div>
        </section>

        {/* Top Intents & Tool Performance Breakdown */}
        <section className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Top Intents Bar Graph */}
          <div className="lg:col-span-6 p-6 bg-white border border-neutral-200 shadow-sm space-y-4">
            <h3 className="text-sm font-semibold uppercase tracking-wider font-mono text-neutral-900">
              Intent Volume Distribution
            </h3>
            <div className="space-y-3">
              {MOCK_ADMIN_METRICS.topIntents.map((item) => (
                <div key={item.intent} className="space-y-1">
                  <div className="flex items-center justify-between text-xs font-mono">
                    <span className="text-neutral-700">{item.intent}</span>
                    <span className="text-neutral-500">{item.count} ({item.percentage}%)</span>
                  </div>
                  <div className="w-full h-2 bg-neutral-100 overflow-hidden">
                    <div
                      className="h-full bg-neutral-900 transition-all duration-500"
                      style={{ width: `${item.percentage}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Tool Gateway Latencies */}
          <div className="lg:col-span-6 p-6 bg-white border border-neutral-200 shadow-sm space-y-4">
            <h3 className="text-sm font-semibold uppercase tracking-wider font-mono text-neutral-900">
              Tool Latency & Invocation Health
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full text-xs font-mono text-left">
                <thead className="border-b border-neutral-200 text-neutral-400 uppercase text-[10px]">
                  <tr>
                    <th className="py-2">Tool Endpoint</th>
                    <th className="py-2">Calls (24h)</th>
                    <th className="py-2">Avg Latency</th>
                    <th className="py-2">SLA Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-100">
                  {MOCK_ADMIN_METRICS.topTools.map((t) => (
                    <tr key={t.tool}>
                      <td className="py-2.5 font-medium text-neutral-900">{t.tool}</td>
                      <td className="py-2.5 text-neutral-600">{t.calls}</td>
                      <td className="py-2.5 text-neutral-600">{t.avgLatencyMs}ms</td>
                      <td className="py-2.5">
                        <span className="inline-block px-1.5 py-0.5 bg-emerald-50 text-emerald-700 text-[10px]">
                          PASS (&lt;400ms)
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>

        {/* Live Voice Sessions Explorer */}
        <section className="bg-white border border-neutral-200 shadow-sm overflow-hidden">
          <div className="p-5 border-b border-neutral-200 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold uppercase tracking-wider font-mono text-neutral-900">
                Voice Session Audit Inspector
              </h3>
              <p className="text-xs text-neutral-500 font-sans mt-0.5">
                Inspect live conversations, authenticated customer levels, tool payloads, and outcomes.
              </p>
            </div>

            <div className="relative">
              <input
                type="text"
                placeholder="Search sessions or intents..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-64 pl-8 pr-3 py-1.5 text-xs font-mono bg-neutral-50 border border-neutral-200 focus:bg-white focus:border-black focus:outline-none"
              />
              <Search className="w-3.5 h-3.5 text-neutral-400 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 divide-y lg:divide-y-0 lg:divide-x divide-neutral-200 min-h-[420px]">
            {/* Session List */}
            <div className="lg:col-span-5 divide-y divide-neutral-100 overflow-y-auto max-h-[500px]">
              {filteredSessions.map((sess) => {
                const isSelected = selectedSession?.sessionId === sess.sessionId;
                return (
                  <div
                    key={sess.sessionId}
                    onClick={() => setSelectedSession(sess)}
                    className={`p-4 cursor-pointer transition-colors text-xs ${
                      isSelected ? 'bg-neutral-50 border-l-2 border-black' : 'hover:bg-neutral-50/60'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-mono font-semibold text-neutral-900">{sess.sessionId}</span>
                      <span className="font-mono text-[10px] text-neutral-400">{sess.durationFormatted}</span>
                    </div>

                    <div className="flex items-center space-x-2 text-[10px] font-mono text-neutral-500 mb-2">
                      <span className="bg-neutral-200 text-neutral-800 px-1.5 py-0.5 rounded">
                        {sess.authLevel}
                      </span>
                      <span>•</span>
                      <span>{sess.turnsCount} turns</span>
                      <span>•</span>
                      <span className="text-emerald-700 font-medium">{sess.businessOutcome}</span>
                    </div>

                    <p className="text-neutral-600 line-clamp-2 text-[11px] leading-relaxed">
                      {sess.transcriptSummary}
                    </p>
                  </div>
                );
              })}
            </div>

            {/* Selected Session Deep Dive */}
            <div className="lg:col-span-7 p-6 space-y-6 overflow-y-auto max-h-[500px] text-xs">
              {selectedSession ? (
                <>
                  <div className="flex items-start justify-between border-b border-neutral-200 pb-4">
                    <div>
                      <div className="flex items-center space-x-2">
                        <h4 className="text-base font-bold font-mono text-neutral-900">
                          {selectedSession.sessionId}
                        </h4>
                        {selectedSession.verified ? (
                          <span className="flex items-center text-[10px] font-mono text-emerald-700 bg-emerald-50 px-2 py-0.5">
                            <ShieldCheck className="w-3 h-3 mr-1" />
                            Verified Session
                          </span>
                        ) : (
                          <span className="text-[10px] font-mono text-neutral-400 bg-neutral-100 px-2 py-0.5">
                            Unverified Guest
                          </span>
                        )}
                      </div>
                      <span className="text-[11px] text-neutral-500 font-mono block mt-1">
                        Started: {selectedSession.startedAt} • Duration: {selectedSession.durationFormatted} • Provider: {selectedSession.provider}
                      </span>
                    </div>

                    <span className="px-2.5 py-1 bg-black text-white text-[10px] font-mono uppercase tracking-wider">
                      {selectedSession.businessOutcome}
                    </span>
                  </div>

                  {/* Transcript Summary */}
                  <div className="space-y-1.5">
                    <span className="font-mono text-[10px] uppercase tracking-wider text-neutral-400 block">
                      Executive Dialogue Summary
                    </span>
                    <p className="p-3 bg-neutral-50 border border-neutral-200 text-neutral-800 text-[11px] leading-relaxed">
                      {selectedSession.transcriptSummary}
                    </p>
                  </div>

                  {/* Intent & Tool Invocation Badges */}
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <span className="font-mono text-[10px] uppercase tracking-wider text-neutral-400 block">
                        Recognized Intents
                      </span>
                      <div className="flex flex-wrap gap-1.5">
                        {selectedSession.intents.map((intent, i) => (
                          <span key={i} className="px-2 py-0.5 bg-neutral-100 border border-neutral-200 text-neutral-800 font-mono text-[10px]">
                            {intent}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div className="space-y-2">
                      <span className="font-mono text-[10px] uppercase tracking-wider text-neutral-400 block">
                        Deterministic Tools Executed
                      </span>
                      <div className="flex flex-wrap gap-1.5">
                        {selectedSession.toolsCalled.length > 0 ? (
                          selectedSession.toolsCalled.map((tool, i) => (
                            <span key={i} className="px-2 py-0.5 bg-amber-50 border border-amber-200 text-amber-900 font-mono text-[10px]">
                              {tool}
                            </span>
                          ))
                        ) : (
                          <span className="text-neutral-400 font-mono text-[10px]">None (Direct Conversational Response)</span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Discussed Products & Orders */}
                  <div className="grid grid-cols-2 gap-4 pt-2 border-t border-neutral-100">
                    <div>
                      <span className="font-mono text-[10px] uppercase tracking-wider text-neutral-400 block mb-1">
                        Catalog Entities Discussed
                      </span>
                      {selectedSession.productsDiscussed.length > 0 ? (
                        selectedSession.productsDiscussed.map((p, idx) => (
                          <span key={idx} className="block text-[11px] font-mono text-neutral-800 truncate">
                            • {p}
                          </span>
                        ))
                      ) : (
                        <span className="text-neutral-400 font-mono text-[10px]">None</span>
                      )}
                    </div>

                    <div>
                      <span className="font-mono text-[10px] uppercase tracking-wider text-neutral-400 block mb-1">
                        Orders Touched
                      </span>
                      {selectedSession.orderIdsAccessed.length > 0 ? (
                        selectedSession.orderIdsAccessed.map((o, idx) => (
                          <span key={idx} className="block text-[11px] font-mono text-neutral-800 font-semibold">
                            • {o}
                          </span>
                        ))
                      ) : (
                        <span className="text-neutral-400 font-mono text-[10px]">No orders accessed</span>
                      )}
                    </div>
                  </div>

                  {/* Escalation / Handoff Detail */}
                  {selectedSession.handoffReason && (
                    <div className="p-3 bg-rose-50 border border-rose-200 text-[11px] text-rose-800 space-y-1">
                      <div className="flex items-center space-x-1.5 font-semibold uppercase text-[10px]">
                        <span className="text-rose-600 font-mono text-xs">⚠️</span>
                        <span>Handoff Escalation Triggered</span>
                      </div>
                      <p>{selectedSession.handoffReason}</p>
                    </div>
                  )}
                </>
              ) : (
                <div className="flex items-center justify-center h-full text-neutral-400 font-mono text-xs">
                  Select a voice session to inspect execution payload
                </div>
              )}
            </div>
          </div>
        </section>
      </main>
    </div>
  );
};

