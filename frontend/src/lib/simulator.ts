import { MOCK_PRODUCTS } from '../data/mockCatalog';
import type { VoiceTurnMessage, VoiceSession, ConfirmationPayload, HandoffDetails } from '../types/voice';
import type { Product } from '../types/catalog';

/**
 * High-fidelity local voice turn simulator for NexGen AI Voice Commerce.
 * Operates on demo product catalogue items and policy reference/demo guidance.
 * Enables 100% interactive demo behavior even when the protected backend requires a server-side proxy.
 */
export function simulateVoiceTurn(
  session: VoiceSession,
  transcript: string,
  allProducts: Product[] = MOCK_PRODUCTS
): {
  message: VoiceTurnMessage;
  updatedFilter?: { category?: string; color?: string; searchQuery?: string };
  openProductDetail?: Product;
  matchingProducts?: Product[];
} {
  const text = transcript.toLowerCase().trim();
  const turnId = `turn_${Date.now()}`;
  const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  // 1. "Show me black dresses" / "dresses"
  if (text.includes('black dress') || text.includes('dresses') || text.includes('dress for a party') || text.includes('party dress')) {
    const dresses = allProducts.filter(p => 
      p.category === 'Dresses' || p.name.toLowerCase().includes('dress')
    );
    const blackDresses = dresses.filter(p => 
      p.name.toLowerCase().includes('black') || p.colors.some(c => c.name.toLowerCase().includes('black'))
    );
    const targetProducts = (text.includes('black') && blackDresses.length > 0) ? blackDresses : dresses;

    return {
      message: {
        id: turnId,
        sender: 'assistant',
        text: `I've found ${targetProducts.length} exquisite evening and party dresses in the collection, including the Ruched Halter Dress in Black. Would you like me to open the details for the first one?`,
        timestamp,
        route: 'DYNAMIC_TOOL_CALL',
        intent: 'SEARCH_PRODUCTS',
        toolName: 'search_products',
        executionStatus: 'SUCCEEDED',
        latencyMs: 218,
        products: targetProducts.slice(0, 8),
      },
      updatedFilter: {
        category: 'Dresses',
        color: text.includes('black') ? 'Black' : undefined,
      }
    };
  }

  // 2. "Show me the second one" / "Open the ruched halter dress" / "Tell me more about this"
  if (text.includes('second one') || text.includes('first one') || text.includes('halter dress') || text.includes('open') || text.includes('detail')) {
    const product = allProducts.find(p => p.name.toLowerCase().includes('halter')) || allProducts[1] || allProducts[0];
    const matching = allProducts.filter(p => product.matchingProductIds?.includes(p.id));

    return {
      message: {
        id: turnId,
        sender: 'assistant',
        text: `Opening the ${product.name} ($${product.price.toFixed(2)} USD). It features a wrapped halter neckline, asymmetric back cutout, and tailored ruching. We have sizes XS through XL in stock.`,
        timestamp,
        route: 'DYNAMIC_TOOL_CALL',
        intent: 'GET_PRODUCT_DETAILS',
        toolName: 'get_product_details',
        executionStatus: 'SUCCEEDED',
        latencyMs: 185,
        selectedProduct: product,
        matchingProducts: matching,
      },
      openProductDetail: product,
      matchingProducts: matching,
    };
  }

  // 3. "What matches with this dress?" / "Complete the look"
  if (text.includes('match') || text.includes('complete the look') || text.includes('outfit') || text.includes('shoes') || text.includes('blazer')) {
    const currentOrFirst = allProducts[0];
    const matching = allProducts.filter(p => currentOrFirst.matchingProductIds?.includes(p.id) || p.category === 'Blazers & Jackets' || p.category === 'Shoes & Bags').slice(0, 3);

    return {
      message: {
        id: turnId,
        sender: 'assistant',
        text: `To complete the look with the ${currentOrFirst.name}, I recommend layering with our Striped Linen Blazer ($129.00) and pairing with Suede Ballet Flats ($75.90) for modern editorial contrast.`,
        timestamp,
        route: 'DYNAMIC_TOOL_CALL',
        intent: 'COMPARE_PRODUCTS',
        toolName: 'compare_products',
        executionStatus: 'SUCCEEDED',
        latencyMs: 242,
        matchingProducts: matching,
      },
      matchingProducts: matching,
    };
  }

  // 4. "What size should I choose?" / "Ask about size"
  if (text.includes('size') || text.includes('fit') || text.includes('measure') || text.includes('true to size')) {
    return {
      message: {
        id: turnId,
        sender: 'assistant',
        text: `Our garments follow standard US/European sizing. This silhouette features a relaxed tailored cut. If you prefer a form-fitting drape, take your true size (S). For a more fluid drape, size up to M. What is your typical dress size?`,
        timestamp,
        route: 'RAG_GROUNDED_RETRIEVAL',
        intent: 'PRODUCT_CARE_AND_SIZING_HELP',
        toolName: 'rag_policy_retrieval',
        executionStatus: 'SUCCEEDED',
        latencyMs: 165,
        clarificationPrompt: {
          field: 'preferred_size',
          prompt: 'Select your regular size:',
          options: ['XS (0-2)', 'S (4-6)', 'M (8-10)', 'L (12-14)', 'XL (16)']
        }
      }
    };
  }

  // 5. "Where is my order?" / "Track order"
  if (text.includes('order') || text.includes('where is my') || text.includes('tracking') || text.includes('package')) {
    const orderNum = session.activeOrderNumber || 'ZUS-2025-00001';
    return {
      message: {
        id: turnId,
        sender: 'assistant',
        text: `Order #${orderNum} has been processed with FedEx Express. Current status is Out for Delivery in New York, NY. Estimated delivery is today by 7:00 PM.`,
        timestamp,
        route: 'DYNAMIC_TOOL_CALL',
        intent: 'TRACK_ORDER',
        toolName: 'track_order',
        executionStatus: 'SUCCEEDED',
        latencyMs: 198,
        trackingData: {
          orderNumber: orderNum,
          carrier: 'FedEx Express',
          trackingNumber: 'FX-928174620US',
          estimatedDelivery: 'Today, 7:00 PM',
          currentStatus: 'OUT_FOR_DELIVERY',
          milestones: [
            { date: 'Sep 05, 08:30 AM', title: 'Order Placed & Confirmed', location: 'Online Store', completed: true },
            { date: 'Sep 06, 14:15 PM', title: 'Departed Fulfillment Hub', location: 'Newark, NJ', completed: true },
            { date: 'Sep 07, 06:45 AM', title: 'Arrived at Local Carrier Depot', location: 'Queens, NY', completed: true },
            { date: 'Sep 07, 09:12 AM', title: 'Out for Delivery with Courier', location: 'Manhattan, NY', completed: true },
          ]
        }
      }
    };
  }

  // 6. "Can I return this?" / "Return order"
  if (text.includes('return') || text.includes('refund') || text.includes('exchange')) {
    const confirmation: ConfirmationPayload = {
      actionName: 'create_return',
      targetId: session.activeOrderNumber || 'ZUS-2025-00001',
      headline: 'Return Authorization Review',
      summary: 'Order #ZUS-2025-00001 is within the 30-day window. Eligible items: Ruched Halter Dress ($69.90). Free in-store return, or $3.95 FedEx drop-off deduction. Would you like me to initiate this return?',
      token: 'hmac_sha256_demo_sec_99182a',
      expiresInSeconds: 600,
      parameters: {
        order_number: session.activeOrderNumber || 'ZUS-2025-00001',
        return_method: 'DROP_OFF',
        refund_amount: 65.95,
      }
    };

    return {
      message: {
        id: turnId,
        sender: 'assistant',
        text: `I've verified your order #ZUS-2025-00001. It is eligible for return within the 30-day policy window. Estimated refund will be $65.95 to your original payment method. Please confirm below if you would like me to generate your return label.`,
        timestamp,
        route: 'CONFIRMATION',
        intent: 'CHECK_RETURN_ELIGIBILITY',
        toolName: 'check_return_eligibility',
        executionStatus: 'AWAITING_EXPLICIT_CONFIRMATION',
        latencyMs: 275,
        confirmationPayload: confirmation,
      }
    };
  }

  // 7. "I received a damaged item"
  if (text.includes('damaged') || text.includes('defective') || text.includes('broken') || text.includes('wrong item')) {
    const handoff: HandoffDetails = {
      reason: 'Customer reported damaged or defective item upon delivery',
      urgency: 'HIGH',
      department: 'Priority Customer Concierge',
      assignedQueue: 'RETURNS_RESOLUTION',
      estimatedWaitMinutes: 1,
    };

    return {
      message: {
        id: turnId,
        sender: 'assistant',
        text: `I sincerely apologize for the inconvenience with your item. I have marked this as high priority and prepared a direct concierge escalation ticket. A representative will review your photos and issue an immediate replacement without requiring return shipping.`,
        timestamp,
        route: 'HANDOFF',
        intent: 'DEFECTIVE_ITEM_RESOLUTION',
        toolName: 'escalate_to_support',
        executionStatus: 'ROUTED_TO_CONCIERGE',
        latencyMs: 310,
        handoffDetails: handoff,
      }
    };
  }

  // 8. "I want a human" / "Talk to representative"
  if (text.includes('human') || text.includes('representative') || text.includes('agent') || text.includes('person') || text.includes('operator')) {
    const handoff: HandoffDetails = {
      reason: 'Customer explicitly requested live human fashion stylist / concierge',
      urgency: 'MEDIUM',
      department: 'NexGen VIP Client Concierge',
      assignedQueue: 'LIVE_STYLING_TEAM',
      estimatedWaitMinutes: 2,
    };

    return {
      message: {
        id: turnId,
        sender: 'assistant',
        text: `Connecting you with our Senior Styling Specialist at the Fifth Avenue Concierge team. Your current cart and viewing history have been securely transferred so you won't need to repeat yourself.`,
        timestamp,
        route: 'HANDOFF',
        intent: 'HUMAN_AGENT_HANDOFF',
        toolName: 'request_human_handoff',
        executionStatus: 'HANDOFF_ESCALATED',
        latencyMs: 140,
        handoffDetails: handoff,
      }
    };
  }

  // 9. General styling advice or fallback search
  const queryProducts = allProducts.filter(p => 
    text.split(' ').some(word => word.length > 3 && (p.name.toLowerCase().includes(word) || p.category.toLowerCase().includes(word)))
  );

  return {
    message: {
      id: turnId,
      sender: 'assistant',
      text: queryProducts.length > 0
        ? `Here are ${queryProducts.length} curated pieces matching your request. Would you like me to filter by color, size, or occasion?`
        : `I'm here to assist your shopping journey. You can ask me to find outfits, check availability, track your orders, or explain our return policies.`,
      timestamp,
      route: 'GENERAL_CONVERSATION',
      intent: 'GENERAL_ASSISTANT_QUERY',
      executionStatus: 'SUCCEEDED',
      latencyMs: 190,
      products: queryProducts.length > 0 ? queryProducts.slice(0, 6) : undefined,
    },
    updatedFilter: queryProducts.length > 0 ? { searchQuery: text } : undefined,
  };
}

