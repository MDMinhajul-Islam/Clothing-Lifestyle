import React from 'react';
import { RetellWebClient } from 'retell-client-js-sdk';
import { AdminAccess } from './components/admin/AdminAccess';
import { CustomerAuthModal } from './components/auth/CustomerAuthModal';
import { Footer } from './components/layout/Footer';
import { Hero } from './components/layout/Hero';
import { Navbar } from './components/layout/Navbar';
import { FilterBar } from './components/storefront/FilterBar';
import { CartDrawer, type CartItem } from './components/storefront/CartDrawer';
import { ProductDetailModal } from './components/storefront/ProductDetailModal';
import { ProductGrid } from './components/storefront/ProductGrid';
import { StyledEdit } from './components/storefront/StyledEdit';
import { VoiceAssistantPanel } from './components/voice/VoiceAssistantPanel';
import { createRetellWebCall, createVoiceSession, endVoiceSession, getHealth, sendVoiceTurn } from './lib/api';
import { fetchCatalogueFacets, fetchCatalogueProducts, fetchProductDetails, fetchStyledEdit, preserveMatchedVariant, type CatalogueFacets } from './lib/catalogueApi';
import { compatibleProducts, matchesColor, matchesProductSearch } from './lib/catalogue';
import { customerAuthTokensFromFragment, customerMe, verifyCustomerEmail } from './lib/customerAuthApi';
import type { CustomerProfile } from './types/auth';
import type { Product, ProductFilter } from './types/catalog';
import type { VoiceSession, VoiceState, VoiceTurnMessage, WebpageVoiceContext } from './types/voice';

const DEFAULT_FILTER: ProductFilter = { inStockOnly: false, sort: 'featured' };
const PAGE_SIZE = 24;
const FALLBACK_PRODUCTS: Product[] = [];
const fallbackColors = Array.from(new Map(FALLBACK_PRODUCTS.flatMap((product) => product.colors).map((color) => [color.name, color])).values());
type AppView = 'storefront' | 'account' | 'admin';

const viewFromPath = (): AppView => {
  const path = window.location.pathname.replace(/\/+$/, '') || '/';
  if (path === '/admin') return 'admin';
  if (path === '/account') return 'account';
  return 'storefront';
};

const consumePortalLinkTokens = () => {
  const tokens = customerAuthTokensFromFragment(window.location.hash);
  if (tokens.verify || tokens.reset) {
    window.history.replaceState({}, '', `${window.location.pathname}${window.location.search}`);
  }
  return tokens;
};

const localResults = (filter: ProductFilter) => FALLBACK_PRODUCTS.filter((product) => {
  if (filter.department && product.department !== filter.department) return false;
  if (filter.category && product.category !== filter.category) return false;
  if (filter.color && !matchesColor(product, filter.color)) return false;
  if (filter.inStockOnly && !product.inStock) return false;
  if (filter.minPrice !== undefined && product.price < filter.minPrice) return false;
  if (filter.maxPrice !== undefined && product.price > filter.maxPrice) return false;
  return !filter.searchQuery || matchesProductSearch(product, filter.searchQuery);
}).sort((a, b) => filter.sort === 'price-asc' ? a.price - b.price : filter.sort === 'price-desc' ? b.price - a.price : filter.sort === 'newest' ? Number(b.isNew) - Number(a.isNew) : 0);

const voiceFilter = (text: string): Partial<ProductFilter> => {
  const value = text.toLowerCase(); const patch: Partial<ProductFilter> = {};
  if (/(dress|blazer|jacket|shirt|top|pant|trouser|jean|beauty|perfume|home|blouse)/.test(value)) patch.searchQuery = text;
  const color = ['black', 'white', 'blue', 'brown', 'red', 'green', 'pink', 'yellow', 'gray'].find((candidate) => value.includes(candidate)); if (color) patch.color = color;
  const price = value.match(/(?:under|below)\s*\$?\s*(\d+(?:\.\d+)?)/); if (price) patch.maxPrice = Number(price[1]);
  return patch;
};

export const App: React.FC = () => {
  const [portalTokens] = React.useState(consumePortalLinkTokens);
  const [currentView, setCurrentView] = React.useState<AppView>(viewFromPath);
  const [isAuthModalOpen, setIsAuthModalOpen] = React.useState(() => Boolean(portalTokens.verify || portalTokens.reset || viewFromPath() === 'account'));
  const [customer, setCustomer] = React.useState<CustomerProfile>({ id: '', name: 'Guest', email: '', type: 'GUEST', authLevel: 'ANONYMOUS', verified: false });
  const [isCustomerSessionReady, setIsCustomerSessionReady] = React.useState(false);
  const [cartItems, setCartItems] = React.useState<CartItem[]>([]);
  const [isCartOpen, setIsCartOpen] = React.useState(false);
  const [filter, setFilter] = React.useState<ProductFilter>(DEFAULT_FILTER);
  const [products, setProducts] = React.useState<Product[]>([]);
  const [styledProducts, setStyledProducts] = React.useState<Product[]>(FALLBACK_PRODUCTS.slice(0, 8));
  const [facets, setFacets] = React.useState<CatalogueFacets | null>(null);
  const [totalProducts, setTotalProducts] = React.useState(0);
  const [hasMore, setHasMore] = React.useState(false);
  const [isLoading, setIsLoading] = React.useState(true);
  const [isLoadingMore, setIsLoadingMore] = React.useState(false);
  const [usingFallback, setUsingFallback] = React.useState(false);
  const [selectedProduct, setSelectedProduct] = React.useState<Product | null>(null);
  const [isProductDetailLoading, setIsProductDetailLoading] = React.useState(false);
  const [productDetailError, setProductDetailError] = React.useState<string | null>(null);
  const [matchingProducts, setMatchingProducts] = React.useState<Product[]>([]);
  const [voiceSession, setVoiceSession] = React.useState<VoiceSession | null>(null);
  const [voiceState, setVoiceState] = React.useState<VoiceState>('IDLE');
  const [isVoiceMuted, setIsVoiceMuted] = React.useState(false);
  const [turnHistory, setTurnHistory] = React.useState<VoiceTurnMessage[]>([]);
  const [lastTurn, setLastTurn] = React.useState<VoiceTurnMessage | null>(null);
  const [isVoiceExpanded, setIsVoiceExpanded] = React.useState(false);
  const [authNotice, setAuthNotice] = React.useState<string | null>(null);
  const [portalNotice, setPortalNotice] = React.useState<string | null>(null);
  const resetToken = portalTokens.reset;
  const [activeVoiceFilterLabel, setActiveVoiceFilterLabel] = React.useState<string | null>(null);

  const detailRequest = React.useRef(0);
  const retellClient = React.useRef<RetellWebClient | null>(null);
  const endingRetellCall = React.useRef(false);
  const retellTranscriptKey = React.useRef('');
  const fallbackVoice = React.useRef<(() => Promise<VoiceSession>) | null>(null);

  const appendRetellTranscript = React.useCallback((update: unknown) => {
    const transcript = (update as { transcript?: Array<{ role?: string; content?: string }> })?.transcript;
    if (!Array.isArray(transcript)) return;
    const messages = transcript.flatMap((entry, index) => {
      const text = typeof entry.content === 'string' ? entry.content.trim() : '';
      if (!text) return [];
      return [{
        id: `retell-${index}-${text}`,
        sender: entry.role === 'agent' ? 'assistant' as const : 'user' as const,
        text,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      }];
    });
    const key = messages.map((message) => `${message.sender}:${message.text}`).join('|');
    if (!messages.length || key === retellTranscriptKey.current) return;
    retellTranscriptKey.current = key;
    setTurnHistory(messages);
    setLastTurn([...messages].reverse().find((message) => message.sender === 'assistant') || messages.at(-1) || null);
  }, []);

  const getRetellClient = React.useCallback(() => {
    if (retellClient.current) return retellClient.current;
    const client = new RetellWebClient();
    client.on('call_started', () => setVoiceState('CONNECTED'));
    client.on('call_ready', () => setVoiceState('LISTENING'));
    client.on('agent_start_talking', () => setVoiceState('SPEAKING'));
    client.on('agent_stop_talking', () => setVoiceState('LISTENING'));
    client.on('update', appendRetellTranscript);
    client.on('call_ended', () => {
      setIsVoiceMuted(false);
      if (endingRetellCall.current) return;
      setVoiceState('DISCONNECTED');
    });
    client.on('error', () => {
      setVoiceState('ERROR');
      void fallbackVoice.current?.().catch(() => setVoiceState('ERROR'));
    });
    retellClient.current = client;
    return client;
  }, [appendRetellTranscript]);

  React.useEffect(() => () => retellClient.current?.stopCall(), []);
  const navigate = React.useCallback((view: AppView, replace = false) => {
    const path = view === 'admin' ? '/admin' : view === 'account' ? '/account' : '/';
    if (window.location.pathname !== path) window.history[replace ? 'replaceState' : 'pushState']({}, '', path);
    setCurrentView(view);
  }, []);
  React.useEffect(() => {
    const restoreView = () => setCurrentView(viewFromPath());
    window.addEventListener('popstate', restoreView);
    return () => window.removeEventListener('popstate', restoreView);
  }, []);
  React.useEffect(() => {
    void customerMe().then((profile) => {
      setCustomer(profile);
      if (viewFromPath() === 'account') setIsAuthModalOpen(true);
    }).catch(() => {
      if (viewFromPath() === 'account') setIsAuthModalOpen(true);
    }).finally(() => setIsCustomerSessionReady(true));
    const token=portalTokens.verify;
    if(token){void verifyCustomerEmail(token).then(()=>{
      setPortalNotice('Your email is verified. You can now sign in.');
    }).catch((reason:unknown)=>setPortalNotice(reason instanceof Error?reason.message:'The verification link could not be used.'));}
  },[portalTokens.verify]);
  React.useEffect(() => { const controller = new AbortController(); void Promise.all([fetchCatalogueFacets(controller.signal), fetchStyledEdit(controller.signal)]).then(([nextFacets, edit]) => { setFacets(nextFacets); if (edit.length) { const unique = Array.from(new Map(edit.map((item) => [item.id, item])).values()); const prior = Number(window.sessionStorage.getItem('nexgen-styled-edit-offset') || '-1'); const offset = (prior + 1) % unique.length; window.sessionStorage.setItem('nexgen-styled-edit-offset', String(offset)); setStyledProducts([...unique.slice(offset), ...unique.slice(0, offset)]); } }).catch(() => undefined); void getHealth().then((health) => { if (health.proxyRequiredNotice) setAuthNotice('Voice service details are available in Call details.'); }); return () => controller.abort(); }, []);
  React.useEffect(() => { const controller = new AbortController(); const timer = window.setTimeout(() => { setIsLoading(true); void fetchCatalogueProducts(filter, PAGE_SIZE, 0, controller.signal).then((result) => { setProducts(result.items); setTotalProducts(result.total); setHasMore(result.has_more); setUsingFallback(false); }).catch((error: unknown) => { if (error instanceof DOMException && error.name === 'AbortError') return; const fallback = localResults(filter); setProducts(fallback); setTotalProducts(fallback.length); setHasMore(false); setUsingFallback(true); }).finally(() => setIsLoading(false)); }, 250); return () => { window.clearTimeout(timer); controller.abort(); }; }, [filter]);

  const resetFilters = React.useCallback(() => { setFilter(DEFAULT_FILTER); setActiveVoiceFilterLabel(null); }, []);
  const startFallbackVoice = React.useCallback(async () => {
    const session = await createVoiceSession('mock', customer.id);
    setVoiceSession(session);
    setVoiceState('LISTENING');
    setIsVoiceExpanded(true);
    setAuthNotice('Live calling is unavailable. Browser voice and text fallback are ready.');
    return session;
  }, [customer.id]);
  React.useEffect(() => {
    fallbackVoice.current = startFallbackVoice;
  }, [startFallbackVoice]);

  const webpageVoiceContext = React.useCallback((activeProduct: Product | null = selectedProduct): WebpageVoiceContext => {
    const matched = activeProduct?.matchedVariant;
    return {
      product_id: activeProduct?.id,
      reference_product_id: activeProduct?.id,
      active_variant_id: matched?.id,
      product_reference: activeProduct?.commercialReference,
      sku: matched?.sku,
      color: matched?.color,
      size: matched?.size,
      query: filter.searchQuery,
      page_url: window.location.href,
      visible_products: products.slice(0, 10).map((product) => ({
        product_id: product.id, name: product.name,
        variant_id: product.matchedVariant?.id, sku: product.matchedVariant?.sku,
        color: product.matchedVariant?.color, size: product.matchedVariant?.size,
      })),
    };
  }, [filter.searchQuery, products, selectedProduct]);

  const startVoice = React.useCallback(async (activeProduct: Product | null = selectedProduct) => {
    if (voiceSession?.provider === 'retell' && voiceState !== 'DISCONNECTED' && voiceState !== 'ERROR' && voiceState !== 'ENDED') {
      setIsVoiceExpanded(true);
      return voiceSession;
    }
    setVoiceState('CONNECTING');
    setIsVoiceExpanded(true);
    setAuthNotice(null);
    setIsVoiceMuted(false);
    endingRetellCall.current = false;
    try {
      const permission = await navigator.mediaDevices.getUserMedia({ audio: true });
      permission.getTracks().forEach((track) => track.stop());
      const authorization = await createRetellWebCall(customer.id || undefined, webpageVoiceContext(activeProduct));
      const session: VoiceSession = {
        sessionId: authorization.call_id,
        status: 'ACTIVE',
        provider: 'retell',
        customerId: customer.id || undefined,
        customerType: customer.id ? 'REGISTERED' : 'GUEST',
        authLevel: customer.id ? 'LOGGED_IN' : 'ANONYMOUS',
        conversationTurn: 0,
        durationSeconds: 0,
        createdAt: new Date().toISOString(),
        currentProductId: activeProduct?.id,
      };
      setVoiceSession(session);
      retellTranscriptKey.current = '';
      await getRetellClient().startCall({ accessToken: authorization.access_token });
      return session;
    } catch {
      setVoiceState('ERROR');
      try { return await startFallbackVoice(); } catch { setVoiceState('ERROR'); return null; }
    }
  }, [customer.id, getRetellClient, selectedProduct, startFallbackVoice, voiceSession, voiceState, webpageVoiceContext]);
  const sendTranscript = React.useCallback(async (transcript: string, activeProduct: Product | null = selectedProduct) => { const text = transcript.trim(); if (!text) return; const session = voiceSession?.status === 'ACTIVE' ? voiceSession : await startVoice(activeProduct); if (!session) return; if (session.provider === 'retell') { window.speechSynthesis.cancel(); setAuthNotice('The live stylist is connected. Say your request naturally.'); return; } setTurnHistory((history) => [...history, { id: `user-${Date.now()}`, sender: 'user', text, timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }]); setVoiceState('THINKING'); setIsVoiceExpanded(true); const productIntent = voiceFilter(text); if (Object.keys(productIntent).length) { setFilter((current) => ({ ...current, ...productIntent })); setActiveVoiceFilterLabel(text); } const result = await sendVoiceTurn(session, text, products.length ? products : FALLBACK_PRODUCTS, webpageVoiceContext(activeProduct)); if (result.updatedFilter) { setFilter((current) => ({ ...current, ...result.updatedFilter })); setActiveVoiceFilterLabel(text); } setLastTurn(result.message); setTurnHistory((history) => [...history, result.message]); setVoiceState('SPEAKING'); window.speechSynthesis.cancel(); const speech = new SpeechSynthesisUtterance(result.message.text); speech.rate = 1.05; speech.onend = () => setVoiceState('LISTENING'); speech.onerror = () => setVoiceState('LISTENING'); window.speechSynthesis.speak(speech); }, [products, selectedProduct, startVoice, voiceSession, webpageVoiceContext]);
  const toggleVoiceMute = () => {
    const nextMuted = !isVoiceMuted;
    if (voiceSession?.provider === 'retell') {
      if (nextMuted) retellClient.current?.mute(); else retellClient.current?.unmute();
    } else if (nextMuted) window.speechSynthesis.cancel();
    setIsVoiceMuted(nextMuted);
  };
  const endVoice = async () => {
    if (voiceSession?.provider === 'retell') {
      endingRetellCall.current = true;
      retellClient.current?.stopCall();
    } else if (voiceSession) await endVoiceSession(voiceSession.sessionId);
    window.speechSynthesis.cancel();
    setIsVoiceMuted(false);
    setVoiceSession(null);
    setVoiceState('IDLE');
    setLastTurn(null);
    setIsVoiceExpanded(false);
  };
  const selectProduct = async (product: Product) => { const requestId = ++detailRequest.current; setSelectedProduct(product); setIsProductDetailLoading(!usingFallback); setProductDetailError(null); const recommendationPool = Array.from(new Map([...products, ...styledProducts].map((item) => [item.id, item])).values()); try { const rawDetails = usingFallback ? product : await fetchProductDetails(product.id); const details = preserveMatchedVariant(rawDetails, product); if (requestId !== detailRequest.current) return; setSelectedProduct(details); setMatchingProducts(compatibleProducts(details, recommendationPool)); } catch { if (requestId !== detailRequest.current) return; setProductDetailError('Some product information is unavailable.'); setMatchingProducts(compatibleProducts(product, recommendationPool.length ? recommendationPool : FALLBACK_PRODUCTS)); } finally { if (requestId === detailRequest.current) setIsProductDetailLoading(false); } };
  const closeProduct = () => { detailRequest.current += 1; setSelectedProduct(null); setProductDetailError(null); setIsProductDetailLoading(false); };
  const loadMore = async () => { if (!hasMore || isLoadingMore) return; setIsLoadingMore(true); try { const result = await fetchCatalogueProducts(filter, PAGE_SIZE, products.length); setProducts((current) => Array.from(new Map([...current, ...result.items].map((item) => [item.id, item])).values())); setHasMore(result.has_more); } finally { setIsLoadingMore(false); } };
  const selectCategory = (category: string) => { if (category === 'All Items') resetFilters(); else { const requested = category.toLowerCase(); const exact = facets?.categories.find((item) => item.toLowerCase() === requested); const terms = requested.split(/\s+&\s+|\s+/).filter((term) => term.length > 3); const mapped = exact || facets?.categories.find((item) => terms.some((term) => item.toLowerCase().includes(term))) || category; setFilter((current) => ({ ...current, category: mapped, department: requested.includes("women") ? 'WOMAN' : current.department })); } document.getElementById('catalogue')?.scrollIntoView({ behavior: 'smooth' }); };

  if (currentView === 'admin') return <AdminAccess onBackToStorefront={() => navigate('storefront')} />;
  if (currentView === 'account' && !isCustomerSessionReady) return <main className="grid min-h-screen place-items-center bg-[#f2f1ed] text-neutral-950"><div className="text-center"><p className="font-display text-2xl font-bold tracking-[0.28em]">NEXGEN</p><p className="mt-4 text-[10px] font-semibold uppercase tracking-[0.18em] text-neutral-500">Opening your account</p></div></main>;
  if (currentView === 'account' && customer.verified) return <CustomerAuthModal isOpen currentCustomer={customer} onClose={() => navigate('storefront')} onUpdateCustomer={(profile) => { setCustomer(profile); if (!profile.verified) navigate('storefront', true); }} resetToken={resetToken} initialNotice={portalNotice} />;
  const colors = facets?.colors.map((name) => ({ name, hex: fallbackColors.find((color) => color.name === name)?.hex || '#777777' })) || fallbackColors;
  return <div className="flex min-h-screen flex-col bg-[#fcfcfc] text-neutral-900">
    <Navbar currentView="storefront" onNavigate={(view) => navigate(view)} customer={customer} onOpenAuth={() => customer.verified ? navigate('account') : setIsAuthModalOpen(true)} voiceState={voiceState} isVoiceActive={voiceSession?.status === 'ACTIVE'} onToggleVoice={() => voiceSession?.status === 'ACTIVE' ? void endVoice() : void startVoice()} cartCount={cartItems.length} onOpenCart={() => setIsCartOpen(true)} onSearchClick={() => document.getElementById('catalogue')?.scrollIntoView({ behavior: 'smooth' })} onSelectCategory={selectCategory} />
    <Hero featuredProducts={styledProducts.slice(0, 3)} onStartVoice={() => void startVoice()} onExploreCollection={() => document.getElementById('catalogue')?.scrollIntoView({ behavior: 'smooth' })} onSelectPrompt={(prompt) => void sendTranscript(prompt)} />
    <StyledEdit products={styledProducts} onSelectProduct={(product) => void selectProduct(product)} onAskVoice={(prompt, product) => void sendTranscript(prompt, product)} />
    <div id="catalogue"><FilterBar filter={filter} onChangeFilter={setFilter} onResetFilter={resetFilters} renderedCount={products.length} matchingCount={totalProducts} activeVoiceFilterLabel={activeVoiceFilterLabel} onClearVoiceFilter={resetFilters} availableColors={colors} availableCategories={facets?.categories} availableDepartments={facets?.departments} /></div>
    <main className="flex-1"><ProductGrid products={products} isLoading={isLoading} onSelectProduct={(product) => void selectProduct(product)} onAskAboutProduct={(product) => void sendTranscript(`Tell me about ${product.name}`, product)} onResetFilters={resetFilters} onAskVoice={(prompt) => void sendTranscript(prompt)} voiceActionNotice={activeVoiceFilterLabel ? { actionText: `Stylist selected for “${activeVoiceFilterLabel}”`, route: lastTurn?.route, onClear: resetFilters } : null} totalMatchingCount={totalProducts} hasMore={hasMore} isLoadingMore={isLoadingMore} onLoadMore={() => void loadMore()} /></main>
    <ProductDetailModal product={selectedProduct} isLoading={isProductDetailLoading} error={productDetailError} onClose={closeProduct} onAddToCart={(product, size) => { setCartItems((items) => [...items, { id: window.crypto.randomUUID(), product, size }]); setIsCartOpen(true); }} onAskVoicePrompt={(prompt, product) => void sendTranscript(prompt, product)} matchingProducts={matchingProducts} onSelectMatchingProduct={(product) => void selectProduct(product)} onContextChange={setSelectedProduct} />
    <CartDrawer isOpen={isCartOpen} items={cartItems} onClose={() => setIsCartOpen(false)} onRemove={(itemId) => setCartItems((items) => items.filter((item) => item.id !== itemId))} />
    <CustomerAuthModal isOpen={isAuthModalOpen} onClose={() => setIsAuthModalOpen(false)} currentCustomer={customer} onUpdateCustomer={(profile) => { setCustomer(profile); if (profile.verified) { setIsAuthModalOpen(false); navigate('account'); } }} resetToken={resetToken} initialNotice={portalNotice} />
    <VoiceAssistantPanel session={voiceSession} voiceState={voiceState} onStartSession={() => void startVoice()} onEndSession={() => void endVoice()} isMuted={isVoiceMuted} onToggleMute={toggleVoiceMute} onSendTranscript={(text) => void sendTranscript(text)} history={turnHistory} lastTurn={lastTurn} onConfirmAction={() => void sendTranscript('Yes, confirm the action')} onCancelAction={() => void sendTranscript('Cancel that action')} isExpanded={isVoiceExpanded} onToggleExpand={() => setIsVoiceExpanded((expanded) => !expanded)} authNotice={authNotice} />
    <Footer onShop={() => { resetFilters(); document.getElementById('catalogue')?.scrollIntoView({ behavior: 'smooth' }); }} onNewArrivals={() => document.getElementById('styled-edit')?.scrollIntoView({ behavior: 'smooth' })} onSelectCategory={selectCategory} onStartVoice={() => void startVoice()} onAskVoice={(prompt) => void sendTranscript(prompt)} onOpenAccount={() => customer.verified ? navigate('account') : setIsAuthModalOpen(true)} />
  </div>;
};

export default App;
