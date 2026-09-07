# NexGen — AI Retail Voice Commerce Frontend

NexGen is an editorial, modern fashion e-commerce storefront powered by a voice-first conversational AI shopping assistant. Built with **React 19**, **TypeScript**, **Vite 8**, and **Tailwind CSS v4**, the application combines high-fashion minimalism with real-time duplex voice commerce capabilities.

---

## Legal Notice

> [!IMPORTANT]
NexGen is an independent AI retail commerce system. Brand assets, catalogue data, and policies should be replaced or licensed for production deployment.

---

## Architecture Overview

```
                        Customer Speech / Text
                                  │
                                  ▼
                    ┌───────────────────────────┐
                    │    Voice Assistant HUD    │
                    │   (Listening / Speaking)  │
                    │   Animated Waveform Orb   │
                    └─────────────┬─────────────┘
                                  │
               ┌──────────────────┴──────────────────┐
               │                                     │
               ▼                                     ▼
     Web Speech Recognition               Deterministic Simulator
     / Retell Turn Adapter                (Offline / Fallback Mode)
               │                                     │
               └──────────────────┬──────────────────┘
                                  │
                                  ▼
               ┌─────────────────────────────────────┐
               │     Unified Voice Response Flow     │
               │  - Spoken Response Synthesizer      │
               │  - Storefront UI Action Dispatcher  │
               │  - Confirmation / Escalation Engine │
               └──────────────────┬──────────────────┘
                                  │
         ┌────────────────────────┼────────────────────────┐
         │                        │                        │
         ▼                        ▼                        ▼
  Filter Storefront         Product Detail           Concierge Stylist
(Category / Occasion)    (Sizes, Look Pairing)        Escalation Card
```

### Voice-First Principles
1. **Live AI Call Experience**: Persistent voice shopping call interface featuring an animated multi-ring waveform orb, live running call timer, state progression (Connected / Caller Speaking / Stylist Thinking / Assistant Speaking), audio equalizer, and dedicated mute/end controls.
2. **Push-to-Speak & Web Speech API**: Browser-native voice input directly captures speech and passes transcripts to the assistant engine.
3. **Developer Text Fallback**: Text input is secondary and clearly designated as a developer testing fallback.
4. **Retell-Ready Architecture**:
   - Designed for seamless Retell audio streaming & speech-to-text integration in future phases.
   - The backend session initializes with provider `"mock"`.
   - The voice turn request strictly follows the backend schema (`POST /v1/voice/turn` with `{ session_id, transcript, context }`), omitting the `provider` field.
5. **Interactive Action Contracts**:
   - **Confirmation Cards**: Two-step HMAC action confirmations for sensitive operations (order cancellations, returns, account changes).
   - **Clarification Chips**: Interactive option buttons when intent or size preferences require user input.
   - **Concierge Handoffs**: Graceful escalation cards with wait time and synchronized shopping cart context.
   - **Debug Inspector**: Collapsible technician drawer showing routing path, detected intent, tool execution, latency, and raw payload.

---

## Security & Backend Architecture

The backend service is protected by `TOOL_GATEWAY_SECRET` (`X-Tool-Secret`). In accordance with security best practices:
- **Zero secrets in client-side code**: Browser bundles never contain administrative API keys, confirmation secrets, or database connection strings (`TOOL_GATEWAY_SECRET`, `CONFIRMATION_SECRET`, `SUPABASE_SERVICE_ROLE_KEY`, and `SUPABASE_DB_URL` are strictly excluded).
- **Production Architecture**: In production, voice turns and private customer operations route through a trusted backend/BFF (Backend-for-Frontend) or edge serverless proxy that securely injects `X-Tool-Secret`.
- **Interactive Browser Mode**: When running directly against a public endpoint without a proxy or when offline, the frontend's built-in deterministic simulator handles voice shopping and customer service scenarios with zero downtime without faking protected server credentials.

---

## Getting Started

### Prerequisites
- Node.js 18+ (tested on Node.js 24)
- npm 9+

### Installation & Run

1. Navigate to the `frontend/` directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the Vite development server:
   ```bash
   npm run dev
   ```
   Open [http://localhost:5173](http://localhost:5173) in your browser.

4. Check code quality:
   ```bash
   npm run lint
   ```

5. Build for production:
   ```bash
   npm run build
   ```

---

## Environment Variables

Create a `.env` file in `frontend/` if connecting to a custom backend or proxy:

```env
# Optional: URL of your backend or proxy service (default points to deployed backend)
VITE_BACKEND_API_URL=http://nexgenclothing-lifestyle-nexgenbackend-t-dab46e-206-189-183-167.sslip.io
```

---

## Voice Scenarios to Try

Click **"Start Live AI Call"** or use the quick voice action prompts:

| Voice Prompt | UI Action Triggered |
| :--- | :--- |
| **"Show me black dresses for an evening event"** | Storefront filters dynamically to evening black dresses |
| **"Tell me more about the satin halter gown"** | Opens product slide-over drawer with high-resolution imagery |
| **"What matches with this?"** | Displays "Complete the Look" curated outfit pairings |
| **"What size should I choose?"** | AI size advisor analyzes garment fit and customer profile |
| **"Where is my order?"** | Pulls guest/member shipment status with live carrier tracking |
| **"Can I return a damaged blazer?"** | Displays return assistance & HMAC confirmation card |
| **"I want to speak with a human stylist"** | Triggers VIP Concierge escalation card with queue status |

---

## Codebase Structure

```
frontend/
├── index.html                 # Luxury Google Fonts (Cinzel, Cormorant Garamond, Plus Jakarta Sans)
├── package.json               # Scripts and dependencies (React 19, Tailwind v4, Lucide)
├── tsconfig.json              # Strict TypeScript configuration
├── vite.config.ts             # Tailwind CSS v4 Vite plugin setup
└── src/
    ├── types/                 # Type contracts for catalog, voice, auth, and admin
    ├── lib/                   # API client, simulator, and Retell turn adapter
    ├── data/                  # Curated product collection items and admin analytics
    ├── components/
    │   ├── layout/            # Navbar, Hero banner, Footer
    │   ├── storefront/        # FilterBar, ProductCard, ProductGrid, ProductDetailModal
    │   ├── voice/             # VoiceAssistantPanel, VoiceOrb, ConfirmationCard, ClarificationPrompt, HandoffCard, VoiceDebugDrawer
    │   ├── auth/              # CustomerAuthModal (Guest order lookup, VIP login)
    │   └── admin/             # Omnichannel Ops Console and Session Inspector
    ├── App.tsx                # Master orchestration & reactive UI updates
    └── main.tsx               # Application root
```
