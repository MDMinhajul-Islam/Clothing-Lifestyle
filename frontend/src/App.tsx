import React from 'react';
import { AdminDashboard } from './components/admin/AdminDashboard';
import { CustomerAuthModal } from './components/auth/CustomerAuthModal';
import { Footer } from './components/layout/Footer';
import { Hero } from './components/layout/Hero';
import { Navbar } from './components/layout/Navbar';
import { FilterBar } from './components/storefront/FilterBar';
import { ProductDetailModal } from './components/storefront/ProductDetailModal';
import { ProductGrid } from './components/storefront/ProductGrid';
import { VoiceAssistantPanel } from './components/voice/VoiceAssistantPanel';
import { MOCK_PRODUCTS } from './data/mockCatalog';
import { createVoiceSession, endVoiceSession, getHealth, sendVoiceTurn } from './lib/api';
import type { CustomerProfile } from './types/auth';
import type { Product, ProductFilter } from './types/catalog';
import type { VoiceSession, VoiceState, VoiceTurnMessage } from './types/voice';

const DEFAULT_FILTER: ProductFilter = { inStockOnly: false, sort: 'featured' };
const PAGE_SIZE = 24;
const CONNECTED_CATALOGUE_COUNT = 6018;

export const App: React.FC = () => {
  const [currentView, setCurrentView] = React.useState<'storefront' | 'admin'>('storefront');
  const [isAuthModalOpen, setIsAuthModalOpen] = React.useState(false);
  const [customer, setCustomer] = React.useState<CustomerProfile>({ id: 'ae7cdeee-b0a3-5c13-9f18-6a57187fea1e', name: 'Elena Vance', email: 'elena.vance@example.com', type: 'VIP_LOYALTY', authLevel: 'VIP_VERIFIED', verified: true, activeOrderNumber: 'ZUS-2025-00001' });
  const [cartItems, setCartItems] = React.useState<Array<{ product: Product; size: string }>>([]);
  const [filter, setFilter] = React.useState<ProductFilter>(DEFAULT_FILTER);
  const [visibleCount, setVisibleCount] = React.useState(PAGE_SIZE);
  const [isLoadingMore, setIsLoadingMore] = React.useState(false);
  const [selectedProduct, setSelectedProduct] = React.useState<Product | null>(null);
  const [matchingProducts, setMatchingProducts] = React.useState<Product[]>([]);
  const [voiceSession, setVoiceSession] = React.useState<VoiceSession | null>(null);
  const [voiceState, setVoiceState] = React.useState<VoiceState>('IDLE');
  const [turnHistory, setTurnHistory] = React.useState<VoiceTurnMessage[]>([]);
  const [lastTurn, setLastTurn] = React.useState<VoiceTurnMessage | null>(null);
  const [isVoiceExpanded, setIsVoiceExpanded] = React.useState(false);
  const [authNotice, setAuthNotice] = React.useState<string | null>(null);
  const [activeVoiceFilterLabel, setActiveVoiceFilterLabel] = React.useState<string | null>(null);

  React.useEffect(() => { void getHealth().then((health) => { if (health.proxyRequiredNotice) setAuthNotice('Protected voice actions require a secure server-side connection. Product discovery remains available in this browser.'); }); }, []);

  const filteredProducts = React.useMemo(() => MOCK_PRODUCTS.filter((product) => {
    if (filter.department && product.department !== filter.department) return false;
    if (filter.category && product.category !== filter.category) return false;
    if (filter.occasion && !product.occasion?.includes(filter.occasion)) return false;
    if (filter.color && !product.colors.some((color) => color.name.toLowerCase() === filter.color?.toLowerCase())) return false;
    if (filter.size && !product.sizes.includes(filter.size)) return false;
    if (filter.inStockOnly && !product.inStock) return false;
    if (filter.minPrice !== undefined && product.price < filter.minPrice) return false;
    if (filter.maxPrice !== undefined && product.price > filter.maxPrice) return false;
    if (filter.searchQuery) { const query = filter.searchQuery.toLowerCase(); if (![product.name, product.description, product.category, product.department].some((value) => value.toLowerCase().includes(query))) return false; }
    return true;
  }).sort((a, b) => filter.sort === 'price-asc' ? a.price - b.price : filter.sort === 'price-desc' ? b.price - a.price : filter.sort === 'newest' ? Number(b.isNew) - Number(a.isNew) : 0), [filter]);

  const resetFilters = React.useCallback(() => { setFilter(DEFAULT_FILTER); setActiveVoiceFilterLabel(null); setVisibleCount(PAGE_SIZE); }, []);
  const startVoice = React.useCallback(async () => {
    if (voiceSession?.status === 'ACTIVE') { setIsVoiceExpanded(true); return voiceSession; }
    setVoiceState('CONNECTING');
    try {
      const session = await createVoiceSession('mock', customer.id);
      setVoiceSession(session); setVoiceState('LISTENING'); setIsVoiceExpanded(true);
      const welcome: VoiceTurnMessage = { id: `welcome-${Date.now()}`, sender: 'assistant', text: `Welcome to NexGen, ${customer.name.split(' ')[0]}. Tell me what you are shopping for, or ask me to check availability or track an order.`, timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }), route: 'GENERAL_CONVERSATION', intent: 'GREETING', executionStatus: 'SUCCEEDED' };
      setLastTurn(welcome); setTurnHistory((history) => history.length ? history : [welcome]); return session;
    } catch { setVoiceState('IDLE'); return null; }
  }, [customer.id, customer.name, voiceSession]);

  const sendTranscript = React.useCallback(async (transcript: string) => {
    const text = transcript.trim(); if (!text) return;
    const userTurn: VoiceTurnMessage = { id: `user-${Date.now()}`, sender: 'user', text, timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) };
    setTurnHistory((history) => [...history, userTurn]); setVoiceState('THINKING'); setIsVoiceExpanded(true);
    const session = voiceSession?.status === 'ACTIVE' ? voiceSession : await startVoice();
    if (!session) return;
    const result = await sendVoiceTurn(session, text, MOCK_PRODUCTS);
    if (result.updatedFilter) {
      setFilter((current) => ({ ...current, ...result.updatedFilter })); setVisibleCount(PAGE_SIZE);
      setActiveVoiceFilterLabel([result.updatedFilter.color, result.updatedFilter.category, result.updatedFilter.searchQuery].filter(Boolean).join(' ') || text);
    }
    if (result.openProductDetail) { setSelectedProduct(result.openProductDetail); setMatchingProducts(MOCK_PRODUCTS.filter((product) => result.openProductDetail?.matchingProductIds?.includes(product.id))); }
    if (result.matchingProducts?.length) setMatchingProducts(result.matchingProducts);
    setLastTurn(result.message); setTurnHistory((history) => [...history, result.message]); setVoiceState('SPEAKING');
    window.speechSynthesis.cancel(); const speech = new SpeechSynthesisUtterance(result.message.text); speech.rate = 1.05; speech.onend = () => setVoiceState('LISTENING'); speech.onerror = () => setVoiceState('LISTENING'); window.speechSynthesis.speak(speech);
  }, [startVoice, voiceSession]);

  const endVoice = async () => { if (voiceSession) await endVoiceSession(voiceSession.sessionId); if ('speechSynthesis' in window) window.speechSynthesis.cancel(); setVoiceSession(null); setVoiceState('IDLE'); setLastTurn(null); setIsVoiceExpanded(false); };
  const selectProduct = (product: Product) => { setSelectedProduct(product); setMatchingProducts(MOCK_PRODUCTS.filter((candidate) => product.matchingProductIds?.includes(candidate.id))); };
  const selectCategory = (category: string) => { setFilter((current) => ({ ...current, category: category === 'All Items' ? undefined : category })); setVisibleCount(PAGE_SIZE); };

  if (currentView === 'admin') return <AdminDashboard onBackToStorefront={() => setCurrentView('storefront')} />;
  return (
    <div className="flex min-h-screen flex-col bg-[#fcfcfc] text-neutral-900">
      <Navbar currentView={currentView} onNavigate={setCurrentView} customer={customer} onOpenAuth={() => setIsAuthModalOpen(true)} voiceState={voiceState} isVoiceActive={voiceSession?.status === 'ACTIVE'} onToggleVoice={() => { if (voiceSession?.status === 'ACTIVE') void endVoice(); else void startVoice(); }} cartCount={cartItems.length} onSearchClick={() => window.scrollTo({ top: 640, behavior: 'smooth' })} onSelectCategory={selectCategory} />
      <Hero onStartVoice={() => void startVoice()} onExploreCollection={() => window.scrollTo({ top: 720, behavior: 'smooth' })} onSelectPrompt={(prompt) => void sendTranscript(prompt)} />
      <FilterBar filter={filter} onChangeFilter={(next) => { setFilter(next); setVisibleCount(PAGE_SIZE); }} onResetFilter={resetFilters} totalResults={filteredProducts.length} totalCatalogueCount={CONNECTED_CATALOGUE_COUNT} activeVoiceFilterLabel={activeVoiceFilterLabel} onClearVoiceFilter={resetFilters} />
      <main className="flex-1"><ProductGrid products={filteredProducts.slice(0, visibleCount)} onSelectProduct={selectProduct} onAskAboutProduct={(product) => void sendTranscript(`Tell me about ${product.name}`)} onResetFilters={resetFilters} onAskVoice={(prompt) => void sendTranscript(prompt)} voiceActionNotice={activeVoiceFilterLabel ? { actionText: `Selected for ${activeVoiceFilterLabel}`, route: lastTurn?.route, onClear: resetFilters } : null} totalCatalogueCount={CONNECTED_CATALOGUE_COUNT} hasMore={visibleCount < filteredProducts.length} isLoadingMore={isLoadingMore} onLoadMore={() => { setIsLoadingMore(true); window.setTimeout(() => { setVisibleCount((count) => count + PAGE_SIZE); setIsLoadingMore(false); }, 250); }} /></main>
      <ProductDetailModal product={selectedProduct} onClose={() => setSelectedProduct(null)} onAddToCart={(product, size) => setCartItems((items) => [...items, { product, size }])} onAskVoicePrompt={(prompt) => void sendTranscript(prompt)} matchingProducts={matchingProducts} onSelectMatchingProduct={selectProduct} />
      <CustomerAuthModal isOpen={isAuthModalOpen} onClose={() => setIsAuthModalOpen(false)} currentCustomer={customer} onUpdateCustomer={setCustomer} />
      <VoiceAssistantPanel session={voiceSession} voiceState={voiceState} onStartSession={() => void startVoice()} onEndSession={() => void endVoice()} onSendTranscript={(text) => void sendTranscript(text)} history={turnHistory} lastTurn={lastTurn} onConfirmAction={() => void sendTranscript('Yes, confirm the action')} onCancelAction={() => void sendTranscript('Cancel that action')} isExpanded={isVoiceExpanded} onToggleExpand={() => setIsVoiceExpanded((expanded) => !expanded)} authNotice={authNotice} />
      <Footer />
    </div>
  );
};

export default App;
