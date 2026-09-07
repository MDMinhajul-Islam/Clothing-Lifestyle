import React from 'react';
import { ChevronDown, ChevronUp, FileText, Mic, PhoneCall, PhoneOff, Send, Sparkles, Volume2, VolumeX } from 'lucide-react';
import type { VoiceSession, VoiceState, VoiceTurnMessage } from '../../types/voice';
import { ClarificationPrompt } from './ClarificationPrompt';
import { ConfirmationCard } from './ConfirmationCard';
import { HandoffCard } from './HandoffCard';
import { VoiceDebugDrawer } from './VoiceDebugDrawer';
import { VoiceOrb } from './VoiceOrb';

interface VoiceAssistantPanelProps {
  session: VoiceSession | null; voiceState: VoiceState; onStartSession: () => void; onEndSession: () => void;
  onSendTranscript: (text: string) => void; history: VoiceTurnMessage[]; lastTurn: VoiceTurnMessage | null;
  onConfirmAction: (actionName: string, token?: string) => void; onCancelAction: () => void;
  isExpanded: boolean; onToggleExpand: () => void; authNotice?: string | null;
}

interface SpeechResultEvent { results: { 0: { 0: { transcript: string } } } }
interface SpeechRecognizer { lang: string; interimResults: boolean; maxAlternatives: number; onresult: ((event: SpeechResultEvent) => void) | null; onerror: (() => void) | null; onend: (() => void) | null; start: () => void }
type SpeechRecognizerConstructor = new () => SpeechRecognizer;

const inquiries = [
  ['Black dresses', 'Show me black dresses'], ['Party outfit', 'I need a dress for a party'],
  ['Check availability', 'Check availability for size M'], ['Track order', 'Where is my order?'],
  ['Return help', 'Can I return an online order in store?'], ['Human stylist', 'I want to speak with a stylist'],
] as const;

const stateLabel: Record<VoiceState, string> = {
  IDLE: 'Ready to connect', CONNECTING: 'Connecting', LISTENING: 'Listening',
  THINKING: 'Stylist finding pieces', SPEAKING: 'Stylist speaking',
};

export const VoiceAssistantPanel: React.FC<VoiceAssistantPanelProps> = ({ session, voiceState, onStartSession, onEndSession, onSendTranscript, history, lastTurn, onConfirmAction, onCancelAction, isExpanded, onToggleExpand, authNotice }) => {
  const [textInput, setTextInput] = React.useState('');
  const [isMuted, setIsMuted] = React.useState(false);
  const [isDebugOpen, setIsDebugOpen] = React.useState(false);
  const [showCallDetails, setShowCallDetails] = React.useState(false);
  const [showDeveloperFallback, setShowDeveloperFallback] = React.useState(false);
  const [elapsedSeconds, setElapsedSeconds] = React.useState(0);
  const [micNotice, setMicNotice] = React.useState<string | null>(null);
  const isActive = session?.status === 'ACTIVE';

  React.useEffect(() => {
    if (!isActive) return;
    const timer = window.setInterval(() => setElapsedSeconds((seconds) => seconds + 1), 1000);
    return () => window.clearInterval(timer);
  }, [isActive, session?.sessionId]);

  const endCall = () => { setElapsedSeconds(0); onEndSession(); };
  const toggleMute = () => { setIsMuted((muted) => { if (!muted && 'speechSynthesis' in window) window.speechSynthesis.cancel(); return !muted; }); };
  const startBrowserMic = () => {
    const speechWindow = window as Window & { SpeechRecognition?: SpeechRecognizerConstructor; webkitSpeechRecognition?: SpeechRecognizerConstructor };
    const Recognition = speechWindow.SpeechRecognition ?? speechWindow.webkitSpeechRecognition;
    if (!Recognition) { setMicNotice('Browser microphone is unavailable. Open Developer fallback to type a request.'); return; }
    const recognition = new Recognition();
    recognition.lang = 'en-US'; recognition.interimResults = false; recognition.maxAlternatives = 1;
    recognition.onresult = (event) => { const spoken = event.results[0][0].transcript.trim(); if (spoken) onSendTranscript(spoken); };
    recognition.onerror = () => setMicNotice('The browser microphone could not capture speech. Try the text fallback.');
    recognition.onend = () => undefined;
    setMicNotice('Listening through the browser microphone...'); recognition.start();
  };
  const submitText = (event: React.FormEvent) => { event.preventDefault(); const text = textInput.trim(); if (!text) return; onSendTranscript(text); setTextInput(''); };
  const duration = `${Math.floor(elapsedSeconds / 60).toString().padStart(2, '0')}:${(elapsedSeconds % 60).toString().padStart(2, '0')}`;

  if (!isActive) return <div className="fixed bottom-6 right-6 z-40"><button onClick={onStartSession} className="group flex items-center gap-3 rounded-full bg-black px-6 py-4 text-white shadow-2xl transition-transform hover:-translate-y-1"><span className="relative flex h-3 w-3"><span className="absolute h-full w-full animate-ping rounded-full bg-emerald-400 opacity-60" /><span className="relative h-3 w-3 rounded-full bg-emerald-500" /></span><PhoneCall className="h-4 w-4" /><span className="text-[11px] font-semibold uppercase tracking-[0.17em]">Start live voice shopping</span></button></div>;

  return (
    <aside className={`fixed bottom-4 right-4 z-40 max-h-[calc(100vh-2rem)] overflow-y-auto border border-neutral-800 bg-white shadow-2xl transition-all sm:bottom-6 sm:right-6 ${isExpanded ? 'w-[min(520px,calc(100vw-2rem))]' : 'w-[min(390px,calc(100vw-2rem))]'}`} aria-label="Live AI Shopping Assistant">
      <header className="bg-neutral-950 px-5 py-4 text-white">
        <div className="flex items-center justify-between"><div><p className="flex items-center gap-2 text-[10px] uppercase tracking-[0.18em] text-emerald-400"><span className="h-2 w-2 animate-pulse rounded-full bg-emerald-400" />Live AI Shopping Assistant</p><h2 className="mt-1 font-serif-luxury text-lg">NexGen personal stylist</h2></div><div className="flex items-center gap-3"><span className="font-mono text-xs text-neutral-300">{duration}</span><button onClick={onToggleExpand} className="p-1.5 text-neutral-300 hover:text-white" aria-label={isExpanded ? 'Collapse call' : 'Expand call'}>{isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronUp className="h-4 w-4" />}</button></div></div>
        <div className="mt-2 flex items-center gap-2"><div className="-my-3 scale-[0.58]"><VoiceOrb state={voiceState} isMuted={isMuted} /></div><div className="min-w-0 flex-1"><p className="text-sm font-medium">{stateLabel[voiceState]}</p><AudioWave state={voiceState} muted={isMuted} /></div></div>
        <div className="mt-2 flex items-center justify-center gap-3"><button onClick={toggleMute} className={`rounded-full border p-3 ${isMuted ? 'border-red-400 bg-red-500/20 text-red-300' : 'border-neutral-700 text-white hover:border-neutral-500'}`} aria-label={isMuted ? 'Unmute assistant' : 'Mute assistant'}>{isMuted ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}</button><button onClick={startBrowserMic} className="rounded-full border border-neutral-700 p-3 text-white hover:border-emerald-400" aria-label="Use browser microphone fallback"><Mic className="h-4 w-4" /></button><button onClick={endCall} className="rounded-full bg-red-600 p-3 text-white hover:bg-red-700" aria-label="End voice call"><PhoneOff className="h-4 w-4" /></button></div>
      </header>

      <div className="flex flex-col">
        <div className="border-b border-neutral-200 bg-[#faf9f6] px-4 py-3">
          <span className="text-[9px] font-semibold uppercase tracking-[0.16em] text-neutral-400">Latest response</span>
          <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-neutral-700">{lastTurn?.text || 'Tell me what you are looking for and I will curate the collection.'}</p>
        </div>
        {lastTurn?.confirmationPayload && <div className="px-4"><ConfirmationCard payload={lastTurn.confirmationPayload} onConfirm={() => onConfirmAction(lastTurn.confirmationPayload!.actionName, lastTurn.confirmationPayload!.token)} onCancel={onCancelAction} /></div>}
        {lastTurn?.clarificationPrompt && <div className="px-4"><ClarificationPrompt prompt={lastTurn.clarificationPrompt} onSelectOption={onSendTranscript} /></div>}
        {lastTurn?.handoffDetails && <div className="px-4"><HandoffCard details={lastTurn.handoffDetails} /></div>}
        <div className="bg-white p-3"><div className="mb-2 flex items-center gap-2 text-[9px] uppercase tracking-[0.16em] text-neutral-500"><Sparkles className="h-3 w-3 text-emerald-600" />Voice shortcuts</div><div className="flex gap-2 overflow-x-auto pb-1">{inquiries.map(([label, prompt]) => <button key={label} onClick={() => onSendTranscript(prompt)} className="flex shrink-0 items-center gap-1.5 rounded-full border border-neutral-200 px-3 py-1.5 text-[10px] hover:border-black"><Mic className="h-3 w-3 text-emerald-600" />{label}</button>)}</div></div>
        <button onClick={() => setShowCallDetails((shown) => !shown)} className="flex items-center justify-between border-t border-neutral-200 px-4 py-2.5 text-[9px] font-semibold uppercase tracking-[0.16em] text-neutral-500"><span className="flex items-center gap-2"><FileText className="h-3 w-3" />Call details</span>{showCallDetails ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}</button>
        {showCallDetails && <div className="max-h-56 overflow-y-auto border-t border-neutral-200 bg-neutral-50 p-3">
          <div className="space-y-2">{history.map((message) => <div key={message.id} className="text-[10px] leading-relaxed text-neutral-600"><span className="mr-2 font-semibold uppercase tracking-wider text-neutral-400">{message.sender === 'user' ? 'Caller' : 'NexGen'}</span>{message.text}</div>)}</div>
          {(authNotice || micNotice) && <p className="mt-3 border-t border-neutral-200 pt-2 text-[9px] leading-relaxed text-neutral-400">{micNotice || authNotice}</p>}
          <button onClick={() => setShowDeveloperFallback((shown) => !shown)} className="mt-3 text-[9px] uppercase tracking-wider text-neutral-500 underline">Developer fallback</button>
          {showDeveloperFallback && <form onSubmit={submitText} className="mt-2 flex gap-2"><input value={textInput} onChange={(event) => setTextInput(event.target.value)} placeholder="Type a test turn" className="min-w-0 flex-1 border border-neutral-200 bg-white px-3 py-2 text-xs outline-none focus:border-black" /><button type="submit" disabled={!textInput.trim()} className="bg-black px-3 text-white disabled:opacity-30" aria-label="Send developer fallback"><Send className="h-4 w-4" /></button></form>}
          <VoiceDebugDrawer lastTurn={lastTurn} isOpen={isDebugOpen} onToggle={() => setIsDebugOpen((open) => !open)} />
        </div>}
      </div>
    </aside>
  );
};

const AudioWave = ({ state, muted }: { state: VoiceState; muted: boolean }) => <div className="mt-2 flex h-5 items-center gap-1" aria-hidden="true">{[5, 10, 15, 8, 18, 12, 6, 14, 9, 17, 7, 11].map((height, index) => <span key={index} className={`w-1 rounded-full ${muted ? 'bg-neutral-700' : state === 'LISTENING' ? 'bg-emerald-400' : state === 'SPEAKING' ? 'bg-white' : 'bg-neutral-600'} ${!muted && (state === 'LISTENING' || state === 'SPEAKING') ? 'animate-pulse' : ''}`} style={{ height: muted ? 3 : height }} />)}</div>;
