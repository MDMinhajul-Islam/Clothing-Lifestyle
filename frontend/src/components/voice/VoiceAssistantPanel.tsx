import React from 'react';
import { 
  Mic, PhoneOff, Volume2, VolumeX, 
  Send, ChevronUp, ChevronDown, CheckCircle, Package,
  MessageSquare, AlertCircle
} from 'lucide-react';
import type { VoiceState, VoiceSession, VoiceTurnMessage } from '../../types/voice';
import { VoiceOrb } from './VoiceOrb';
import { ConfirmationCard } from './ConfirmationCard';
import { ClarificationPrompt } from './ClarificationPrompt';
import { HandoffCard } from './HandoffCard';
import { VoiceDebugDrawer } from './VoiceDebugDrawer';

interface VoiceAssistantPanelProps {
  session: VoiceSession | null;
  voiceState: VoiceState;
  onStartSession: () => void;
  onEndSession: () => void;
  onSendTranscript: (text: string) => void;
  history: VoiceTurnMessage[];
  lastTurn: VoiceTurnMessage | null;
  onConfirmAction: (actionName: string, token?: string) => void;
  onCancelAction: () => void;
  isExpanded: boolean;
  onToggleExpand: () => void;
  authNotice?: string | null;
}

const QUICK_PROMPTS = [
  { label: 'Black dresses', prompt: 'Show me black dresses' },
  { label: 'Party outfit', prompt: 'I need a dress for a party' },
  { label: 'Size guide', prompt: 'What size should I choose?' },
  { label: 'Complete look', prompt: 'What matches with this dress?' },
  { label: 'Track order', prompt: 'Where is my order?' },
  { label: 'Return eligibility', prompt: 'Can I return this?' },
  { label: 'Damaged item', prompt: 'I received a damaged item' },
  { label: 'Human stylist', prompt: 'I want a human' },
];

export const VoiceAssistantPanel: React.FC<VoiceAssistantPanelProps> = ({
  session,
  voiceState,
  onStartSession,
  onEndSession,
  onSendTranscript,
  history,
  lastTurn,
  onConfirmAction,
  onCancelAction,
  isExpanded,
  onToggleExpand,
  authNotice,
}) => {
  const [textInput, setTextInput] = React.useState('');
  const [isMuted, setIsMuted] = React.useState(false);
  const [isDebugOpen, setIsDebugOpen] = React.useState(false);
  const [showTranscript, setShowTranscript] = React.useState(false);
  const [elapsedSeconds, setElapsedSeconds] = React.useState<number>(0);
  const [isListeningSpeech, setIsListeningSpeech] = React.useState(false);

  // Active call timer
  React.useEffect(() => {
    if (!session || session.status !== 'ACTIVE') {
      return;
    }
    const interval = setInterval(() => {
      setElapsedSeconds(prev => prev + 1);
    }, 1000);
    return () => {
      clearInterval(interval);
      setElapsedSeconds(0);
    };
  }, [session]);

  const sessionTimer = session && session.status === 'ACTIVE' ? elapsedSeconds : 0;

  // Speech Recognition (Optional real voice input using browser Web Speech API)
  const startListeningRealVoice = () => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert('Web Speech API is not supported in this browser. Please use the developer text fallback or demo prompts below.');
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.lang = 'en-US';
      recognition.interimResults = false;
      recognition.maxAlternatives = 1;

      setIsListeningSpeech(true);
      recognition.start();

      recognition.onresult = (event: any) => {
        const spoken = event.results[0][0].transcript;
        setIsListeningSpeech(false);
        onSendTranscript(spoken);
      };

      recognition.onerror = () => {
        setIsListeningSpeech(false);
      };

      recognition.onend = () => {
        setIsListeningSpeech(false);
      };
    } catch {
      setIsListeningSpeech(false);
    }
  };

  const formatTimer = (seconds: number) => {
    const m = Math.floor(seconds / 60).toString().padStart(2, '0');
    const s = (seconds % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

  const handleTextSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!textInput.trim()) return;
    onSendTranscript(textInput);
    setTextInput('');
  };

  // If call is inactive, show floating call trigger dock
  if (!session || session.status !== 'ACTIVE') {
    return (
      <div className="fixed bottom-6 right-6 z-40">
        <button
          onClick={onStartSession}
          className="group flex items-center space-x-3 px-5 py-3.5 bg-black text-white rounded-full shadow-2xl hover:bg-neutral-900 border border-neutral-800 transition-all hover:scale-105"
        >
          <span className="relative flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
          </span>
          <div className="flex flex-col text-left">
            <span className="text-xs uppercase tracking-widest font-semibold font-mono">
              Start Voice Call
            </span>
            <span className="text-[10px] text-neutral-400 font-sans">
              Talk with NexGen AI Stylist
            </span>
          </div>
          <div className="p-1.5 bg-neutral-800 rounded-full group-hover:bg-neutral-700">
            <Mic className="w-4 h-4 text-emerald-400" />
          </div>
        </button>
      </div>
    );
  }

  // Active Voice Commerce Call HUD
  return (
    <div
      className={`fixed z-40 transition-all duration-500 ease-in-out ${
        isExpanded
          ? 'inset-x-4 bottom-4 md:inset-x-auto md:right-8 md:w-[460px] max-h-[90vh]'
          : 'bottom-6 right-6 w-96'
      }`}
    >
      <div className="flex flex-col bg-white border border-neutral-300 shadow-2xl rounded-none overflow-hidden transition-all">
        {/* Call Status Header */}
        <div className="px-4 py-3 bg-neutral-900 text-white flex items-center justify-between border-b border-neutral-800">
          <div className="flex items-center space-x-2.5">
            <span className="relative flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
            </span>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-xs font-semibold uppercase tracking-wider font-mono">
                  NexGen Voice Call
                </span>
                <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/60 px-1.5 py-0.2 border border-emerald-800/40">
                  {formatTimer(sessionTimer)}
                </span>
              </div>
              <span className="text-[10px] text-neutral-400 font-mono block">
                Provider: {session.provider} (Retell-ready) • Auth: {session.authLevel}
              </span>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => setShowTranscript(!showTranscript)}
              className={`p-1.5 rounded text-xs transition-colors ${
                showTranscript ? 'bg-neutral-800 text-white' : 'text-neutral-400 hover:text-white'
              }`}
              title="Toggle transcript drawer"
            >
              <MessageSquare className="w-3.5 h-3.5" />
            </button>

            <button
              onClick={onToggleExpand}
              className="p-1.5 text-neutral-400 hover:text-white rounded transition-colors"
              title={isExpanded ? 'Minimize call HUD' : 'Expand call canvas'}
            >
              {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
            </button>
          </div>
        </div>

        {/* Security / Proxy Notice if applicable */}
        {authNotice && (
          <div className="px-4 py-2 bg-amber-50 border-b border-amber-200 text-[11px] text-amber-800 flex items-center justify-between">
            <div className="flex items-center space-x-1.5">
              <AlertCircle className="w-3.5 h-3.5 shrink-0 text-amber-600" />
              <span>{authNotice}</span>
            </div>
          </div>
        )}

        {/* Main Voice Canvas */}
        <div className="p-4 bg-gradient-to-b from-[#fbfbfb] to-white flex flex-col items-center text-center space-y-3">
          {/* Animated Voice Orb */}
          <VoiceOrb state={voiceState} isMuted={isMuted} />

          {/* Voice State Indicator */}
          <div className="space-y-1">
            <span className="text-[10px] uppercase font-mono tracking-widest text-neutral-400">
              {voiceState === 'LISTENING' ? 'Customer Speaking' : voiceState === 'THINKING' ? 'Consulting Demo Catalogue & Policies' : voiceState === 'SPEAKING' ? 'NexGen Speaking' : 'Call Active'}
            </span>
            <p className="font-serif-luxury text-base text-neutral-900 italic max-w-xs px-2 line-clamp-2">
              {lastTurn ? `“${lastTurn.text}”` : '“Hello, I’m your NexGen AI stylist. What can I find for you today?”'}
            </p>
          </div>

          {/* Real Mic Speak Button */}
          <div className="pt-1 flex items-center space-x-3">
            <button
              onClick={startListeningRealVoice}
              disabled={isListeningSpeech}
              className={`px-4 py-2 rounded-full text-xs font-medium uppercase tracking-wider transition-all flex items-center space-x-2 border ${
                isListeningSpeech
                  ? 'bg-emerald-600 text-white border-emerald-600 animate-pulse'
                  : 'bg-black text-white border-black hover:bg-neutral-800'
              }`}
            >
              <Mic className="w-3.5 h-3.5 text-emerald-300" />
              <span>{isListeningSpeech ? 'Listening to Mic...' : 'Push to Speak'}</span>
            </button>

            <button
              onClick={() => setIsMuted(!isMuted)}
              className={`p-2 rounded-full border text-xs transition-colors ${
                isMuted ? 'bg-rose-100 border-rose-300 text-rose-700' : 'bg-neutral-100 border-neutral-200 text-neutral-600 hover:text-black'
              }`}
              title={isMuted ? 'Unmute microphone' : 'Mute microphone'}
            >
              {isMuted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
            </button>

            <button
              onClick={onEndSession}
              className="p-2 rounded-full bg-rose-600 hover:bg-rose-700 text-white border border-rose-600 transition-colors shadow-sm"
              title="End Voice Call"
            >
              <PhoneOff className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Action Widgets (Confirmation, Clarification, Handoff, Tracking) */}
        {lastTurn?.confirmationPayload && (
          <div className="px-4 pb-2">
            <ConfirmationCard
              payload={lastTurn.confirmationPayload}
              onConfirm={() => onConfirmAction(lastTurn.confirmationPayload!.actionName, lastTurn.confirmationPayload!.token)}
              onCancel={onCancelAction}
            />
          </div>
        )}

        {lastTurn?.clarificationPrompt && (
          <div className="px-4 pb-2">
            <ClarificationPrompt
              prompt={lastTurn.clarificationPrompt}
              onSelectOption={(opt) => onSendTranscript(opt)}
            />
          </div>
        )}

        {lastTurn?.handoffDetails && (
          <div className="px-4 pb-2">
            <HandoffCard details={lastTurn.handoffDetails} />
          </div>
        )}

        {/* Order Tracking Milestone Preview if present */}
        {lastTurn?.trackingData && (
          <div className="px-4 py-2 border-t border-neutral-100 bg-neutral-50 text-xs">
            <div className="flex items-center justify-between mb-2">
              <span className="font-mono text-[10px] uppercase text-neutral-500 font-semibold flex items-center gap-1">
                <Package className="w-3.5 h-3.5 text-neutral-700" />
                <span>Order Tracking: #{lastTurn.trackingData.orderNumber}</span>
              </span>
              <span className="text-[10px] font-mono text-emerald-700 bg-emerald-100 px-1.5 py-0.5">
                {lastTurn.trackingData.currentStatus}
              </span>
            </div>
            <div className="space-y-1.5 text-[11px] font-mono">
              {lastTurn.trackingData.milestones.map((m, idx) => (
                <div key={idx} className="flex items-center space-x-2 text-neutral-700">
                  <CheckCircle className="w-3 h-3 text-emerald-600 shrink-0" />
                  <span className="text-neutral-900 font-medium">{m.title}</span>
                  <span className="text-neutral-400 text-[10px]">({m.location})</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Collapsible Full Transcript Drawer */}
        {showTranscript && (
          <div className="border-t border-neutral-200 p-3 max-h-48 overflow-y-auto bg-neutral-50 space-y-2 text-xs">
            <span className="text-[10px] font-mono uppercase tracking-widest text-neutral-400 block mb-1">
              Live Speech Transcript Log
            </span>
            {history.length === 0 ? (
              <p className="text-neutral-400 italic text-[11px]">No spoken turns yet.</p>
            ) : (
              history.map((msg) => (
                <div
                  key={msg.id}
                  className={`p-2 rounded-sm text-[11px] ${
                    msg.sender === 'user'
                      ? 'bg-neutral-200/80 text-neutral-900 ml-6'
                      : 'bg-white border border-neutral-200 text-neutral-800 mr-6'
                  }`}
                >
                  <span className="font-mono text-[9px] uppercase tracking-wider block text-neutral-400 mb-0.5">
                    {msg.sender === 'user' ? 'Customer' : 'NexGen Voice AI'} • {msg.timestamp}
                  </span>
                  <p>{msg.text}</p>
                </div>
              ))
            )}
          </div>
        )}

        {/* One-Click Voice Demo Prompts */}
        <div className="p-3 bg-neutral-50 border-t border-neutral-200">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[10px] font-mono uppercase tracking-wider text-neutral-400 font-semibold">
              Instant Demo Scenarios
            </span>
            <span className="text-[9px] font-mono text-neutral-400">Click to Simulate Speech</span>
          </div>
          <div className="flex flex-wrap gap-1.5 max-h-24 overflow-y-auto">
            {QUICK_PROMPTS.map((qp, i) => (
              <button
                key={i}
                onClick={() => onSendTranscript(qp.prompt)}
                className="px-2 py-1 bg-white border border-neutral-200 hover:border-black text-[10px] text-neutral-700 text-left transition-colors whitespace-nowrap rounded-none"
              >
                {qp.label}
              </button>
            ))}
          </div>
        </div>

        {/* Secondary Developer Text Fallback Input */}
        <div className="p-3 bg-white border-t border-neutral-200">
          <form onSubmit={handleTextSubmit} className="flex items-center space-x-2">
            <input
              type="text"
              placeholder="Developer text fallback (type spoken turn)..."
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              className="flex-1 px-3 py-1.5 text-xs bg-neutral-50 border border-neutral-200 focus:outline-none focus:border-black text-neutral-900 placeholder:text-neutral-400 font-sans"
            />
            <button
              type="submit"
              disabled={!textInput.trim()}
              className="px-3 py-1.5 bg-black text-white text-xs hover:bg-neutral-800 disabled:opacity-30 transition-colors uppercase tracking-wider font-medium flex items-center gap-1"
            >
              <span>Send</span>
              <Send className="w-3 h-3" />
            </button>
          </form>
          <span className="text-[9px] font-mono text-neutral-400 mt-1 block">
            Note: Retell audio integration will handle microphone input automatically.
          </span>
        </div>

        {/* Debug Drawer */}
        <VoiceDebugDrawer
          lastTurn={lastTurn}
          isOpen={isDebugOpen}
          onToggle={() => setIsDebugOpen(!isDebugOpen)}
        />
      </div>
    </div>
  );
};
