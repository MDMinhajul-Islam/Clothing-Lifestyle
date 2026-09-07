import React from 'react';
import { MOCK_PRODUCTS } from './data/mockCatalog';
import type { Product, ProductFilter } from './types/catalog';
import type { CustomerProfile } from './types/auth';
import type { VoiceSession, VoiceState, VoiceTurnMessage } from './types/voice';
import { Navbar } from './components/layout/Navbar';
import { Hero } from './components/layout/Hero';
import { Footer } from './components/layout/Footer';
import { FilterBar } from './components/storefront/FilterBar';
import { ProductGrid } from './components/storefront/ProductGrid';
import { ProductDetailModal } from './components/storefront/ProductDetailModal';
import { VoiceAssistantPanel } from './components/voice/VoiceAssistantPanel';
import { CustomerAuthModal } from './components/auth/CustomerAuthModal';
import { AdminDashboard } from './components/admin/AdminDashboard';
import { createVoiceSession, sendVoiceTurn, endVoiceSession, getHealth } from './lib/api';

const DEFAULT_FILTER: ProductFilter = {
  department: undefined,
  category: undefined,
  occasion: undefined,
  searchQuery: undefined,
  minPrice: undefined,
  maxPrice: undefined,
  color: undefined,
  size: undefined,
  inStockOnly: false,
  sort: 'featured',
};

export const App: React.FC = () => {
  // Navigation & View State
  const [currentView, setCurrentView] = React.useState<'storefront' | 'admin'>('storefront');
  const [isAuthModalOpen, setIsAuthModalOpen] = React.useState(false);

  // Customer State
  const [customer, setCustomer] = React.useState<CustomerProfile>({
    id: 'ae7cdeee-b0a3-5c13-9f18-6a57187fea1e',
    name: 'Elena Vance',
    email: 'elena.vance@example.com',
    type: 'VIP_LOYALTY',
    authLevel: 'VIP_VERIFIED',
    verified: true,
    activeOrderNumber: 'ZUS-2025-00001',
  });

  // Cart State
  const [cartItems, setCartItems] = React.useState<Array<{ product: Product; size: string }>>([]);

  // Catalog & Filter State
  const [catalog] = React.useState<Product[]>(MOCK_PRODUCTS);
  const [filter, setFilter] = React.useState<ProductFilter>(DEFAULT_FILTER);
  const [selectedProduct, setSelectedProduct] = React.useState<Product | null>(null);
  const [matchingProducts, setMatchingProducts] = React.useState<Product[]>([]);

  // Voice Commerce State
  const [voiceSession, setVoiceSession] = React.useState<VoiceSession | null>(null);
  const [voiceState, setVoiceState] = React.useState<VoiceState>('IDLE');
  const [turnHistory, setTurnHistory] = React.useState<VoiceTurnMessage[]>([]);
  const [lastTurn, setLastTurn] = React.useState<VoiceTurnMessage | null>(null);
  const [isVoiceExpanded, setIsVoiceExpanded] = React.useState(false);
  const [authNotice, setAuthNotice] = React.useState<string | null>(null);

  // Check health on mount
  React.useEffect(() => {
    getHealth().then((h) => {
      if (h.proxyRequiredNotice) {
        setAuthNotice(
          'Protected backend endpoints require server-side proxy for production. Running in interactive browser demo mode.'
        );
      }
    });
  }, []);

  // Filter computation
  const filteredProducts = React.useMemo(() => {
    return catalog
      .filter((p) => {
        if (filter.department && p.department !== filter.department) return false;
        if (filter.category && p.category !== filter.category) return false;
        if (filter.occasion && (!p.occasion || !p.occasion.includes(filter.occasion))) return false;
        if (filter.color && !p.colors.some((c) => c.name.toLowerCase() === filter.color!.toLowerCase())) return false;
        if (filter.minPrice && p.price < filter.minPrice) return false;
        if (filter.maxPrice && p.price > filter.maxPrice) return false;
        if (filter.searchQuery) {
          const q = filter.searchQuery.toLowerCase();
          const matchName = p.name.toLowerCase().includes(q);
          const matchDesc = p.description.toLowerCase().includes(q);
          const matchCat = p.category.toLowerCase().includes(q);
          if (!matchName && !matchDesc && !matchCat) return false;
        }
        return true;
      })
      .sort((a, b) => {
        if (filter.sort === 'price-asc') return a.price - b.price;
        if (filter.sort === 'price-desc') return b.price - a.price;
        if (filter.sort === 'newest') return (b.isNew ? 1 : 0) - (a.isNew ? 1 : 0);
        return 0;
      });
  }, [catalog, filter]);

  // Voice Session Management
  const handleStartVoice = async () => {
    setVoiceState('CONNECTING');
    try {
      const sess = await createVoiceSession('retell', customer.id);
      setVoiceSession(sess);
      setVoiceState('LISTENING');
      setIsVoiceExpanded(false);

      const welcomeMsg: VoiceTurnMessage = {
        id: `turn_welcome_${Date.now()}`,
        sender: 'assistant',
        text: `Welcome to NexGen, ${customer.name.split(' ')[0]}. I can find garments, check store availability, track orders, or help with sizing. What can I do for you today?`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        route: 'GENERAL_CONVERSATION',
        intent: 'GREETING',
        executionStatus: 'SUCCEEDED',
      };
      setLastTurn(welcomeMsg);
      setTurnHistory([welcomeMsg]);
    } catch {
      setVoiceState('IDLE');
    }
  };

  const handleEndVoice = async () => {
    if (voiceSession) {
      await endVoiceSession(voiceSession.sessionId);
    }
    setVoiceSession(null);
    setVoiceState('IDLE');
    setLastTurn(null);
  };

  // Dynamic Turn Processing & Website Updates
  const handleSendTranscript = async (transcript: string) => {
    if (!transcript.trim()) return;

    // 1. Add user speech to transcript
    const userTurn: VoiceTurnMessage = {
      id: `turn_user_${Date.now()}`,
      sender: 'user',
      text: transcript,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
    setTurnHistory((prev) => [...prev, userTurn]);

    // 2. Set state to thinking
    setVoiceState('THINKING');

    // Ensure session exists
    let activeSess = voiceSession;
    if (!activeSess) {
      activeSess = await createVoiceSession('retell', customer.id);
      setVoiceSession(activeSess);
    }

    // 3. Dispatch to API adapter
    const result = await sendVoiceTurn(activeSess, transcript, catalog);

    // 4. Update website state based on AI response!
    if (result.updatedFilter) {
      setFilter((prev) => ({
        ...prev,
        category: result.updatedFilter?.category ?? prev.category,
        color: result.updatedFilter?.color ?? prev.color,
        searchQuery: result.updatedFilter?.searchQuery ?? prev.searchQuery,
      }));
    }

    if (result.openProductDetail) {
      setSelectedProduct(result.openProductDetail);
      const matches = catalog.filter((p) => result.openProductDetail?.matchingProductIds?.includes(p.id));
      setMatchingProducts(matches);
    }

    if (result.matchingProducts && result.matchingProducts.length > 0) {
      setMatchingProducts(result.matchingProducts);
    }

    // 5. Update assistant speech & voice state
    setVoiceState('SPEAKING');
    setLastTurn(result.message);
    setTurnHistory((prev) => [...prev, result.message]);

    // Read response with browser speech synthesis if available and not muted
    if ('speechSynthesis' in window) {
      try {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(result.message.text);
        utterance.rate = 1.05;
        utterance.pitch = 1.0;
        utterance.onend = () => {
          setVoiceState('LISTENING');
        };
        utterance.onerror = () => {
          setVoiceState('LISTENING');
        };
        window.speechSynthesis.speak(utterance);
      } catch {
        setTimeout(() => setVoiceState('LISTENING'), 2500);
      }
    } else {
      setTimeout(() => setVoiceState('LISTENING'), 2500);
    }
  };

  const handleConfirmAction = (actionName: string) => {
    const confirmationTurn: VoiceTurnMessage = {
      id: `turn_conf_${Date.now()}`,
      sender: 'assistant',
      text: `Action ${actionName} has been authorized and securely executed in the database. A confirmation email with your return label and QR code has been sent.`,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      route: 'DYNAMIC_TOOL_CALL',
      intent: 'CONFIRMATION_COMPLETED',
      executionStatus: 'SUCCEEDED',
      latencyMs: 310,
    };
    setLastTurn(confirmationTurn);
    setTurnHistory((prev) => [...prev, confirmationTurn]);
    setVoiceState('SPEAKING');
    setTimeout(() => setVoiceState('LISTENING'), 2000);
  };

  const handleCancelAction = () => {
    const cancelTurn: VoiceTurnMessage = {
      id: `turn_cancel_${Date.now()}`,
      sender: 'assistant',
      text: 'Action cancelled. Your order remains unchanged. What else can I assist you with?',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      route: 'GENERAL_CONVERSATION',
      intent: 'ACTION_CANCELLED',
      executionStatus: 'CANCELLED_BY_USER',
    };
    setLastTurn(cancelTurn);
    setTurnHistory((prev) => [...prev, cancelTurn]);
    setVoiceState('LISTENING');
  };

  const handleSelectProduct = (product: Product) => {
    setSelectedProduct(product);
    const matches = catalog.filter((p) => product.matchingProductIds?.includes(p.id));
    setMatchingProducts(matches);
  };

  const handleAddToCart = (product: Product, size: string) => {
    setCartItems((prev) => [...prev, { product, size }]);
  };

  // Render Admin Console if selected
  if (currentView === 'admin') {
    return <AdminDashboard onBackToStorefront={() => setCurrentView('storefront')} />;
  }

  // Render Storefront
  return (
    <div className="min-h-screen flex flex-col bg-[#fcfcfc] text-neutral-900">
      {/* Top Navbar */}
      <Navbar
        currentView={currentView}
        onNavigate={setCurrentView}
        customer={customer}
        onOpenAuth={() => setIsAuthModalOpen(true)}
        voiceState={voiceState}
        isVoiceActive={Boolean(voiceSession && voiceSession.status === 'ACTIVE')}
        onToggleVoice={() => {
          if (voiceSession && voiceSession.status === 'ACTIVE') {
            handleEndVoice();
          } else {
            handleStartVoice();
          }
        }}
        cartCount={cartItems.length}
        onSearchClick={() => {
          window.scrollTo({ top: 400, behavior: 'smooth' });
        }}
      />

      {/* Hero Section */}
      <Hero
        onStartVoice={handleStartVoice}
        onExploreCollection={() => {
          window.scrollTo({ top: 580, behavior: 'smooth' });
        }}
      />
      {/* Sticky Interactive Filter Bar */}
      <FilterBar
        filter={filter}
        onChangeFilter={setFilter}
        onResetFilter={() => setFilter(DEFAULT_FILTER)}
        totalResults={filteredProducts.length}
      />

      {/* Main Product Catalog Grid */}
      <main className="flex-1">
        <ProductGrid
          products={filteredProducts}
          onSelectProduct={handleSelectProduct}
          onAskAboutProduct={(prod) => {
            if (!voiceSession) {
              handleStartVoice().then(() => {
                handleSendTranscript(`Tell me about the ${prod.name}`);
              });
            } else {
              handleSendTranscript(`Tell me about the ${prod.name}`);
            }
          }}
          onResetFilters={() => setFilter(DEFAULT_FILTER)}
          onAskVoice={(prompt) => {
            if (!voiceSession) {
              handleStartVoice().then(() => {
                handleSendTranscript(prompt);
              });
            } else {
              handleSendTranscript(prompt);
            }
          }}
        />
      </main>

      {/* Product Detail Modal */}
      <ProductDetailModal
        product={selectedProduct}
        onClose={() => setSelectedProduct(null)}
        onAddToCart={handleAddToCart}
        onAskVoicePrompt={(prompt) => {
          if (!voiceSession) {
            handleStartVoice().then(() => {
              handleSendTranscript(prompt);
            });
          } else {
            handleSendTranscript(prompt);
          }
        }}
        matchingProducts={matchingProducts}
        onSelectMatchingProduct={handleSelectProduct}
      />

      {/* Customer Verification Modal */}
      <CustomerAuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        currentCustomer={customer}
        onUpdateCustomer={setCustomer}
      />

      {/* Voice Commerce Assistant Panel */}
      <VoiceAssistantPanel
        session={voiceSession}
        voiceState={voiceState}
        onStartSession={handleStartVoice}
        onEndSession={handleEndVoice}
        onSendTranscript={handleSendTranscript}
        history={turnHistory}
        lastTurn={lastTurn}
        onConfirmAction={handleConfirmAction}
        onCancelAction={handleCancelAction}
        isExpanded={isVoiceExpanded}
        onToggleExpand={() => setIsVoiceExpanded(!isVoiceExpanded)}
        authNotice={authNotice}
      />

      {/* Footer */}
      <Footer />
    </div>
  );
};

export default App;
