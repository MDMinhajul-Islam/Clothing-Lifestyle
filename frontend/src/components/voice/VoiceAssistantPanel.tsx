import React from 'react';
import { ChevronDown, ChevronUp, MessageSquare, Mic, PhoneCall, PhoneOff, Send, Sparkles, Volume2, VolumeX } from 'lucide-react';
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
  IDLE: 'Ready to connect', CONNECTING: 'Connecting your call', LISTENING: 'Caller speaking',
  THINKING: 'Assistant thinking', SPEAKING: 'Assistant speaking',
};

export const VoiceAssistantPanel: React.FC<VoiceAssistantPanelProps> = ({ session, voiceState, onStartSession, onEndSession, onSendTranscript, history, lastTurn, onConfirmAction, onCancelAction, isExpanded, onToggleExpand, authNotice }) => {
  const [textInput, setTextInput] = React.useState('');
  const [isMuted, setIsMuted] = React.useState(false);
  const [isDebugOpen, setIsDebugOpen] = React.useState(false);
  const [showTranscript, setShowTranscript] = React.useState(true);
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
    if (!Recognition) { setMicNotice('Browser microphone fallback is unavailable here. You can type or select a request below.'); return; }
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
    <aside className={`fixed bottom-4 right-4 z-40 overflow-hidden border border-neutral-800 bg-white shadow-2xl transition-all sm:bottom-6 sm:right-6 ${isExpanded ? 'h-[min(760px,calc(100vh-3rem))] w-[min(720px,calc(100vw-2rem))]' : 'h-[min(680px,calc(100vh-3rem))] w-[min(430px,calc(100vw-2rem))]'}`} aria-label="Live AI Shopping Assistant">
      <header className="bg-neutral-950 px-5 py-4 text-white">
        <div className="flex items-center justify-between"><div><p className="flex items-center gap-2 text-[10px] uppercase tracking-[0.18em] text-emerald-400"><span className="h-2 w-2 animate-pulse rounded-full bg-emerald-400" />Live AI Shopping Assistant</p><h2 className="mt-1 font-serif-luxury text-lg">NexGen personal stylist</h2></div><div className="flex items-center gap-3"><span className="font-mono text-xs text-neutral-300">{duration}</span><button onClick={onToggleExpand} className="p-1.5 text-neutral-300 hover:text-white" aria-label={isExpanded ? 'Collapse call' : 'Expand call'}>{isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronUp className="h-4 w-4" />}</button></div></div>
        <div className="mt-4 flex items-center gap-4"><div className="scale-75"><VoiceOrb state={voiceState} isMuted={isMuted} /></div><div className="min-w-0 flex-1"><p className="text-sm font-medium">{stateLabel[voiceState]}</p><AudioWave state={voiceState} muted={isMuted} /></div></div>
        <div className="mt-4 flex items-center justify-center gap-3"><button onClick={toggleMute} className={`rounded-full border p-3 ${isMuted ? 'border-red-400 bg-red-500/20 text-red-300' : 'border-neutral-700 text-white hover:border-neutral-500'}`} aria-label={isMuted ? 'Unmute assistant' : 'Mute assistant'}>{isMuted ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}</button><button onClick={startBrowserMic} className="rounded-full border border-neutral-700 p-3 text-white hover:border-emerald-400" aria-label="Use browser microphone fallback"><Mic className="h-4 w-4" /></button><button onClick={endCall} className="rounded-full bg-red-600 p-3 text-white hover:bg-red-700" aria-label="End voice call"><PhoneOff className="h-4 w-4" /></button></div>
      </header>

      <div className="flex h-[calc(100%-230px)] flex-col">
        {(authNotice || micNotice) && <div className="border-b border-amber-200 bg-amber-50 px-4 py-2 text-[10px] leading-relaxed text-amber-900">{micNotice || authNotice}</div>}
        <button onClick={() => setShowTranscript((shown) => !shown)} className="flex items-center justify-between border-b border-neutral-200 px-4 py-3 text-[10px] font-semibold uppercase tracking-[0.16em]"><span className="flex items-center gap-2"><MessageSquare className="h-3.5 w-3.5" />Transcript preview</span>{showTranscript ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}</button>
        {showTranscript && <div className="min-h-0 flex-1 space-y-3 overflow-y-auto bg-neutral-50 p-4">{history.length === 0 ? <p className="py-10 text-center text-xs text-neutral-400">Your live conversation will appear here.</p> : history.map((message) => <div key={message.id} className={`max-w-[88%] p-3 text-xs leading-relaxed ${message.sender === 'user' ? 'ml-auto bg-neutral-900 text-white' : 'border border-neutral-200 bg-white text-neutral-800'}`}><span className={`mb-1 block text-[9px] uppercase tracking-wider ${message.sender === 'user' ? 'text-neutral-400' : 'text-emerald-700'}`}>{message.sender === 'user' ? 'Caller' : 'NexGen Assistant'} / {message.timestamp}</span>{message.text}</div>)}</div>}
        {lastTurn?.confirmationPayload && <div className="px-4"><ConfirmationCard payload={lastTurn.confirmationPayload} onConfirm={() => onConfirmAction(lastTurn.confirmationPayload!.actionName, lastTurn.confirmationPayload!.token)} onCancel={onCancelAction} /></div>}
        {lastTurn?.clarificationPrompt && <div className="px-4"><ClarificationPrompt prompt={lastTurn.clarificationPrompt} onSelectOption={onSendTranscript} /></div>}
        {lastTurn?.handoffDetails && <div className="px-4"><HandoffCard details={lastTurn.handoffDetails} /></div>}
        <div className="border-t border-neutral-200 bg-white p-3"><div className="mb-2 flex items-center gap-2 text-[9px] uppercase tracking-[0.16em] text-neutral-500"><Sparkles className="h-3 w-3 text-emerald-600" />Suggested requests</div><div className="flex gap-2 overflow-x-auto pb-1">{inquiries.map(([label, prompt]) => <button key={label} onClick={() => onSendTranscript(prompt)} className="shrink-0 border border-neutral-200 px-2.5 py-1.5 text-[10px] hover:border-black">{label}</button>)}</div></div>
        <form onSubmit={submitText} className="flex gap-2 border-t border-neutral-200 bg-white p-3"><input value={textInput} onChange={(event) => setTextInput(event.target.value)} placeholder="Browser text fallback" className="min-w-0 flex-1 border border-neutral-200 bg-neutral-50 px-3 py-2 text-xs outline-none focus:border-black" /><button type="submit" disabled={!textInput.trim()} className="bg-black px-3 text-white disabled:opacity-30" aria-label="Send text fallback"><Send className="h-4 w-4" /></button></form>
        <VoiceDebugDrawer lastTurn={lastTurn} isOpen={isDebugOpen} onToggle={() => setIsDebugOpen((open) => !open)} />
      </div>
    </aside>
  );
};

const AudioWave = ({ state, muted }: { state: VoiceState; muted: boolean }) => <div className="mt-2 flex h-5 items-center gap-1" aria-hidden="true">{[5, 10, 15, 8, 18, 12, 6, 14, 9, 17, 7, 11].map((height, index) => <span key={index} className={`w-1 rounded-full ${muted ? 'bg-neutral-700' : state === 'LISTENING' ? 'bg-emerald-400' : state === 'SPEAKING' ? 'bg-white' : 'bg-neutral-600'} ${!muted && (state === 'LISTENING' || state === 'SPEAKING') ? 'animate-pulse' : ''}`} style={{ height: muted ? 3 : height }} />)}</div>;
