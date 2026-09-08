import React from 'react';
import { AdminAccess } from './components/admin/AdminAccess';
import { CustomerAuthModal } from './components/auth/CustomerAuthModal';
import { Footer } from './components/layout/Footer';
import { Hero } from './components/layout/Hero';
import { Navbar } from './components/layout/Navbar';
import { FilterBar } from './components/storefront/FilterBar';
import { ProductDetailModal } from './components/storefront/ProductDetailModal';
import { ProductGrid } from './components/storefront/ProductGrid';
import { StyledEdit } from './components/storefront/StyledEdit';
import { VoiceAssistantPanel } from './components/voice/VoiceAssistantPanel';
import { createVoiceSession, endVoiceSession, getHealth, sendVoiceTurn } from './lib/api';
import { fetchCatalogueFacets, fetchCatalogueProducts, fetchProductDetails, fetchStyledEdit, type CatalogueFacets } from './lib/catalogueApi';
import { compatibleProducts, isMainFashionProduct, matchesColor, matchesProductSearch } from './lib/catalogue';
import type { CustomerProfile } from './types/auth';
import type { Product, ProductFilter } from './types/catalog';
import type { VoiceSession, VoiceState, VoiceTurnMessage } from './types/voice';

const DEFAULT_FILTER: ProductFilter = { inStockOnly: false, sort: 'featured' };
const PAGE_SIZE = 24;
const FALLBACK_PRODUCTS: Product[] = [];
const fallbackColors = Array.from(new Map(FALLBACK_PRODUCTS.flatMap((product) => product.colors).map((color) => [color.name, color])).values());

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
  if (value.includes('dress')) patch.category = 'Dresses'; else if (value.includes('blazer') || value.includes('jacket')) patch.category = 'Blazers & Jackets'; else if (value.includes('shirt') || value.includes('top')) patch.category = 'Tops & Shirts'; else if (value.includes('pant') || value.includes('trouser') || value.includes('jean')) patch.category = 'Pants & Jeans';
  const color = ['black', 'white', 'blue', 'brown', 'red', 'green', 'pink', 'yellow', 'gray'].find((candidate) => value.includes(candidate)); if (color) patch.color = color;
  const price = value.match(/(?:under|below)\s*\$?\s*(\d+(?:\.\d+)?)/); if (price) patch.maxPrice = Number(price[1]);
  return patch;
};

export const App: React.FC = () => {
  const [currentView, setCurrentView] = React.useState<'storefront' | 'admin'>('storefront');
  const [isAuthModalOpen, setIsAuthModalOpen] = React.useState(false);
  const [customer, setCustomer] = React.useState<CustomerProfile>({ id: '', name: 'Guest', email: '', type: 'GUEST', authLevel: 'ANONYMOUS', verified: false });
  const [cartItems, setCartItems] = React.useState<Array<{ product: Product; size: string }>>([]);
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
  const [matchingProducts, setMatchingProducts] = React.useState<Product[]>([]);
  const [voiceSession, setVoiceSession] = React.useState<VoiceSession | null>(null);
  const [voiceState, setVoiceState] = React.useState<VoiceState>('IDLE');
  const [turnHistory, setTurnHistory] = React.useState<VoiceTurnMessage[]>([]);
  const [lastTurn, setLastTurn] = React.useState<VoiceTurnMessage | null>(null);
  const [isVoiceExpanded, setIsVoiceExpanded] = React.useState(false);
  const [authNotice, setAuthNotice] = React.useState<string | null>(null);
  const [activeVoiceFilterLabel, setActiveVoiceFilterLabel] = React.useState<string | null>(null);

  React.useEffect(() => { const controller = new AbortController(); void Promise.all([fetchCatalogueFacets(controller.signal), fetchStyledEdit(controller.signal)]).then(([nextFacets, edit]) => { setFacets(nextFacets); if (edit.length) setStyledProducts(edit.filter(isMainFashionProduct)); }).catch(() => undefined); void getHealth().then((health) => { if (health.proxyRequiredNotice) setAuthNotice('Voice service details are available in Call details.'); }); return () => controller.abort(); }, []);
  React.useEffect(() => { const controller = new AbortController(); const timer = window.setTimeout(() => { setIsLoading(true); void fetchCatalogueProducts(filter, PAGE_SIZE, 0, controller.signal).then((result) => { setProducts(result.items.filter(isMainFashionProduct)); setTotalProducts(result.total); setHasMore(result.has_more); setUsingFallback(false); }).catch((error: unknown) => { if (error instanceof DOMException && error.name === 'AbortError') return; const fallback = localResults(filter); setProducts(fallback); setTotalProducts(fallback.length); setHasMore(false); setUsingFallback(true); }).finally(() => setIsLoading(false)); }, 250); return () => { window.clearTimeout(timer); controller.abort(); }; }, [filter]);

  const resetFilters = React.useCallback(() => { setFilter(DEFAULT_FILTER); setActiveVoiceFilterLabel(null); }, []);
  const startVoice = React.useCallback(async () => { if (voiceSession?.status === 'ACTIVE') { setIsVoiceExpanded(true); return voiceSession; } setVoiceState('CONNECTING'); try { const session = await createVoiceSession('mock', customer.id); setVoiceSession(session); setVoiceState('LISTENING'); setIsVoiceExpanded(true); const welcome: VoiceTurnMessage = { id: `welcome-${Date.now()}`, sender: 'assistant', text: `Welcome to NexGen, ${customer.name.split(' ')[0]}. What are you shopping for today?`, timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }), route: 'GENERAL_CONVERSATION', intent: 'GREETING', executionStatus: 'SUCCEEDED' }; setLastTurn(welcome); setTurnHistory((history) => history.length ? history : [welcome]); return session; } catch { setVoiceState('IDLE'); return null; } }, [customer.id, customer.name, voiceSession]);
  const sendTranscript = React.useCallback(async (transcript: string) => { const text = transcript.trim(); if (!text) return; setTurnHistory((history) => [...history, { id: `user-${Date.now()}`, sender: 'user', text, timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }]); setVoiceState('THINKING'); setIsVoiceExpanded(true); const productIntent = voiceFilter(text); if (Object.keys(productIntent).length) { setFilter((current) => ({ ...current, ...productIntent })); setActiveVoiceFilterLabel(text); } const session = voiceSession?.status === 'ACTIVE' ? voiceSession : await startVoice(); if (!session) return; const result = await sendVoiceTurn(session, text, products.length ? products : FALLBACK_PRODUCTS); if (result.updatedFilter) { setFilter((current) => ({ ...current, ...result.updatedFilter })); setActiveVoiceFilterLabel(text); } setLastTurn(result.message); setTurnHistory((history) => [...history, result.message]); setVoiceState('SPEAKING'); window.speechSynthesis.cancel(); const speech = new SpeechSynthesisUtterance(result.message.text); speech.rate = 1.05; speech.onend = () => setVoiceState('LISTENING'); speech.onerror = () => setVoiceState('LISTENING'); window.speechSynthesis.speak(speech); }, [products, startVoice, voiceSession]);
  const endVoice = async () => { if (voiceSession) await endVoiceSession(voiceSession.sessionId); window.speechSynthesis.cancel(); setVoiceSession(null); setVoiceState('IDLE'); setLastTurn(null); setIsVoiceExpanded(false); };
  const selectProduct = async (product: Product) => { setSelectedProduct(product); const recommendationPool = Array.from(new Map([...products, ...styledProducts].map((item) => [item.id, item])).values()); try { const details = usingFallback ? product : await fetchProductDetails(product.id); setSelectedProduct(details); setMatchingProducts(compatibleProducts(details, recommendationPool)); } catch { setMatchingProducts(compatibleProducts(product, recommendationPool.length ? recommendationPool : FALLBACK_PRODUCTS)); } };
  const loadMore = async () => { if (!hasMore || isLoadingMore) return; setIsLoadingMore(true); try { const result = await fetchCatalogueProducts(filter, PAGE_SIZE, products.length); setProducts((current) => [...current, ...result.items.filter(isMainFashionProduct)]); setHasMore(result.has_more); } finally { setIsLoadingMore(false); } };
  const selectCategory = (category: string) => { setFilter((current) => ({ ...current, category: category === 'All Items' ? undefined : category })); document.getElementById('catalogue')?.scrollIntoView({ behavior: 'smooth' }); };

  if (currentView === 'admin') return <AdminAccess onBackToStorefront={() => setCurrentView('storefront')} />;
  const colors = facets?.colors.map((name) => ({ name, hex: fallbackColors.find((color) => color.name === name)?.hex || '#777777' })) || fallbackColors;
  return <div className="flex min-h-screen flex-col bg-[#fcfcfc] text-neutral-900">
    <Navbar currentView={currentView} onNavigate={setCurrentView} customer={customer} onOpenAuth={() => setIsAuthModalOpen(true)} voiceState={voiceState} isVoiceActive={voiceSession?.status === 'ACTIVE'} onToggleVoice={() => voiceSession?.status === 'ACTIVE' ? void endVoice() : void startVoice()} cartCount={cartItems.length} onSearchClick={() => document.getElementById('catalogue')?.scrollIntoView({ behavior: 'smooth' })} onSelectCategory={selectCategory} />
    <Hero featuredProducts={styledProducts.slice(0, 3)} onStartVoice={() => void startVoice()} onExploreCollection={() => document.getElementById('catalogue')?.scrollIntoView({ behavior: 'smooth' })} onSelectPrompt={(prompt) => void sendTranscript(prompt)} />
    <StyledEdit products={styledProducts} onSelectProduct={(product) => void selectProduct(product)} onAskVoice={(prompt) => void sendTranscript(prompt)} />
    <div id="catalogue"><FilterBar filter={filter} onChangeFilter={setFilter} onResetFilter={resetFilters} totalResults={totalProducts} totalCatalogueCount={facets?.total_products || totalProducts} activeVoiceFilterLabel={activeVoiceFilterLabel} onClearVoiceFilter={resetFilters} availableColors={colors} availableCategories={facets?.categories} availableDepartments={facets?.departments} /></div>
    <main className="flex-1"><ProductGrid products={products} isLoading={isLoading} onSelectProduct={(product) => void selectProduct(product)} onAskAboutProduct={(product) => void sendTranscript(`Tell me about ${product.name}`)} onResetFilters={resetFilters} onAskVoice={(prompt) => void sendTranscript(prompt)} voiceActionNotice={activeVoiceFilterLabel ? { actionText: `Stylist selected for “${activeVoiceFilterLabel}”`, route: lastTurn?.route, onClear: resetFilters } : null} totalCatalogueCount={facets?.total_products || totalProducts} hasMore={hasMore} isLoadingMore={isLoadingMore} onLoadMore={() => void loadMore()} /></main>
    <ProductDetailModal product={selectedProduct} onClose={() => setSelectedProduct(null)} onAddToCart={(product, size) => setCartItems((items) => [...items, { product, size }])} onAskVoicePrompt={(prompt) => void sendTranscript(prompt)} matchingProducts={matchingProducts} onSelectMatchingProduct={(product) => void selectProduct(product)} />
    <CustomerAuthModal isOpen={isAuthModalOpen} onClose={() => setIsAuthModalOpen(false)} currentCustomer={customer} onUpdateCustomer={setCustomer} />
    <VoiceAssistantPanel session={voiceSession} voiceState={voiceState} onStartSession={() => void startVoice()} onEndSession={() => void endVoice()} onSendTranscript={(text) => void sendTranscript(text)} history={turnHistory} lastTurn={lastTurn} onConfirmAction={() => void sendTranscript('Yes, confirm the action')} onCancelAction={() => void sendTranscript('Cancel that action')} isExpanded={isVoiceExpanded} onToggleExpand={() => setIsVoiceExpanded((expanded) => !expanded)} authNotice={authNotice} />
    <Footer />
  </div>;
};

export default App;
