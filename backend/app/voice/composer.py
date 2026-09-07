"""Deterministic, voice-safe rendering of grounded capability results."""

from backend.app.config import settings
from backend.app.orchestrator.schemas import Route


class VoiceResponseComposer:
    def general(self, text, intent):
        if intent == "SECURITY_REFUSAL":
            return "I can’t bypass privacy controls or access another customer’s information."
        if text in {"hello", "hi", "hey", "good morning", "good afternoon"}:
            return f"Hello, I’m the {settings.agent_name}. How can I help?"
        if text in {"thanks", "thank you", "thank you very much"}:
            return "You’re welcome."
        if text in {"bye", "goodbye", "see you"}:
            return "Goodbye."
        if "help" in text:
            return "I can help with products, availability, orders, returns, rewards, promotions, and reference policy questions."
        return "I can help with retail shopping and support requests, but general question answering is not configured yet."

    def compose(self, decision, data, status):
        if status in {"AUTHORIZATION_REQUIRED", "AUTH_TOKEN_INVALID", "AUTH_TOKEN_EXPIRED"}:
            return "Please verify your identity before I access that information."
        if status == "CAPABILITY_ADAPTER_NOT_CONFIGURED":
            return "That service is not configured for local execution yet."
        if decision.route == Route.POLICY_RAG:
            if data.get("status") == "INSUFFICIENT_EVIDENCE":
                return "I couldn’t verify that from the reference policy information available in this demo. Would you like human support to review it?"
            evidence = data.get("evidence") or []
            if evidence:
                answer = str(evidence[0].get("chunk_text", "")).strip()
                return "Using the reference policy information available in this demo, " + answer[:420]
        products = data.get("results") or data.get("products") or []
        if products:
            labels=[]
            for item in products[:3]:
                label=str(item.get("name") or "an item")
                if item.get("price") is not None:
                    label += f" at {item['price']} {item.get('currency', 'USD')}"
                labels.append(label)
            return "I found " + "; ".join(labels) + "."
        if status == "SUCCESS" and decision.intent in {
            "SEARCH_PRODUCTS", "FIND_SIMILAR_PRODUCTS", "RECOMMEND_MATCHING_PRODUCTS",
        }:
            return "I couldn’t find matching products for that. Would you like me to broaden the search or try another color?"
        if decision.intent == "GET_PRODUCT_DETAILS":
            name=data.get("name","This item"); details=data.get("materials_care") or data.get("description")
            return f"{name}: {details}" if details else f"I found the current details for {name}."
        if decision.intent in {"CHECK_INVENTORY", "CHECK_PICKUP_AVAILABILITY", "CHECK_EXCHANGE_INVENTORY"}:
            if decision.intent == "CHECK_EXCHANGE_INVENTORY" and not data.get("eligible", False):
                reason=data.get("reason") or "Exchange eligibility or replacement stock could not be verified."
                return f"{reason} Would you like me to help with a return or human support?"
            state=data.get("overall_status") or data.get("status") or "UNKNOWN"
            quantity=data.get("total_network_available",data.get("quantity_available"))
            suffix=f" with {quantity} available" if quantity is not None else ""
            if decision.intent == "CHECK_PICKUP_AVAILABILITY":
                return f"The synthetic store stock status is {str(state).replace('_',' ').lower()}{suffix}. This does not reserve the item or confirm that an order is ready for pickup."
            return f"The verified availability is {str(state).replace('_',' ').lower()}{suffix}."
        if decision.intent == "GET_SIZE_GUIDANCE":
            sizes=", ".join(data.get("documented_sizes") or [])
            advisory=data.get("advisory") or "Check the documented measurements before choosing."
            return (f"The documented sizes are {sizes}. " if sizes else "") + advisory
        if decision.intent == "GET_CUSTOMER_ORDERS":
            orders=data.get("orders") or []
            items=orders[0].get("items",[]) if orders else []
            size=(items[0].get("size") or items[0].get("size_name")) if items else None
            return f"Your most recent recorded item was size {size}. Fit can vary by item." if size else "I found your authorized order history."
        if decision.intent == "GET_LOYALTY_STATUS":
            return f"Your demo rewards balance is {data.get('points_balance', 0)} points at the {data.get('tier','current')} tier."
        if decision.intent == "CHECK_PROMOTION":
            reasons=", ".join(str(x).replace("_"," ").lower() for x in data.get("reason_codes",[]))
            return ("That demo promotion is eligible." if data.get("eligible") else "That demo promotion is not eligible.") + (f" Reason: {reasons}." if reasons else "")
        if decision.intent == "TRACK_ORDER":
            return f"The current shipment status is {str(data.get('shipment_status') or data.get('order_status') or data.get('status','unknown')).replace('_',' ').lower()}."
        if decision.intent == "CHECK_CANCELLATION_ELIGIBILITY":
            if data.get("eligible"):
                return "The current NexGen fulfillment state allows cancellation. Would you like me to prepare the cancellation for confirmation?"
            reason=data.get("reason") or "The order cannot be cancelled in its current state."
            return f"{reason} Would you like tracking, return guidance, or human support?"
        if status == "ORDER_NOT_CANCELLABLE":
            reason=(data.get("error") or {}).get("message") or "The order cannot be cancelled in its current state."
            return f"{reason} Would you like me to track it or explain the return option after delivery?"
        if decision.intent == "CHECK_RETURN_ELIGIBILITY":
            reason=data.get("reason") or "Return eligibility could not be verified."
            if data.get("eligible"):
                return f"{reason} Which return method would you prefer: a free store return or a $4.95 drop-off return?"
            return f"{reason} Would you like human support to review the exception?"
        if status == "RETURN_NOT_ELIGIBLE":
            reason=(data.get("error") or {}).get("message") or "This return or exchange is not eligible for automated processing."
            return f"{reason} If the item is damaged, wrong, or missing, I can help prepare a support review."
        if decision.intent == "GET_REFUND_STATUS":
            refunds=data.get("refunds") or []
            if not refunds:
                return "No refund is currently recorded for that order. Would you like me to check the return status or prepare human support?"
            state=refunds[0].get("refund_status","unknown")
            return f"The newest recorded refund status is {str(state).replace('_',' ').lower()}. Timing depends on the recorded processing state and payment provider."
        if decision.intent == "CREATE_INCIDENT" and status == "SUCCESS":
            return "I recorded the item issue for review. This does not promise a refund or replacement; would you like human support next?"
        if decision.intent == "PREPARE_HANDOFF":
            return "I prepared a support handoff using the verified context available."
        if status == "SUCCESS":
            return "The request completed successfully."
        return "I couldn’t safely complete that request with the information available."
