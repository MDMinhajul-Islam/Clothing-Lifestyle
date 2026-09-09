"""Deterministic, voice-safe rendering of grounded capability results."""

from backend.app.config import settings
from backend.app.orchestrator.schemas import Route


class VoiceResponseComposer:
    def general(self, text, intent):
        if intent == "SECURITY_REFUSAL":
            return "I can't access another customer's private information because your privacy comes first. I can still help with your own shopping or order."
        if text in {"hello", "hi", "hey", "good morning", "good afternoon"}:
            return f"Hello, I'm the {settings.agent_name}, your personal stylist. What can I help you find today?"
        if text in {"thanks", "thank you", "thank you very much"}:
            return "My pleasure."
        if text in {"bye", "goodbye", "see you"}:
            return "It was a pleasure helping you today. I'll be here whenever you're ready."
        if "help" in text:
            return "I can help you find the right pieces, build an outfit, check availability, or assist with an order. Where shall we begin?"
        return "Live shopping information is temporarily unavailable. Please try again in a moment."

    def compose(self, decision, data, status):
        if status in {"AUTHORIZATION_REQUIRED", "AUTH_TOKEN_INVALID", "AUTH_TOKEN_EXPIRED"}:
            return "I'll need to verify your identity before I can look into that."
        if status == "CAPABILITY_ADAPTER_NOT_CONFIGURED":
            return "I'm unable to check that just now. Would you like to try something else?"
        if decision.route == Route.POLICY_RAG:
            if data.get("status") == "INSUFFICIENT_EVIDENCE":
                return "I couldn't verify that from the reference policy information available in this demo. Would you like human support to review it?"
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
            introduction = ((str(data.get("fallback_message")).rstrip(".") + ". Here are a few: ")
                            if data.get("fallback_message") else
                            "I found a few pieces worth considering: ")
            follow_up = (" Would you like me to find pieces to complete the look?"
                         if decision.intent == "RECOMMEND_MATCHING_PRODUCTS"
                         else " Would you like details on any of them?")
            return introduction + "; ".join(labels) + "." + follow_up
        if status == "SUCCESS" and decision.intent in {
            "SEARCH_PRODUCTS", "FIND_SIMILAR_PRODUCTS", "RECOMMEND_MATCHING_PRODUCTS",
        }:
            if data.get("fallback_message"):
                return data["fallback_message"]
            return "I couldn't find matching products in that selection. Would you like me to broaden the search or try another color?"
        if decision.intent == "GET_PRODUCT_DETAILS":
            name=data.get("name","This item"); details=data.get("materials_care") or data.get("description")
            facts=[]
            if data.get("price") is not None:
                facts.append(f"The current price is {data['price']} {data.get('currency', 'USD')}")
            colors=[]
            for color in data.get("colors") or []:
                value=(color.get("color_name") or color.get("name")) if isinstance(color,dict) else color
                if value and value not in colors: colors.append(str(value))
            if colors: facts.append("The available colors are " + ", ".join(colors))
            if details: facts.append(str(details))
            return f"{name}. " + ". ".join(facts) + "." if facts else f"I have the latest details for {name}. What would you like to know?"
        if decision.intent in {"CHECK_INVENTORY", "CHECK_PICKUP_AVAILABILITY", "CHECK_EXCHANGE_INVENTORY"}:
            if decision.intent == "CHECK_EXCHANGE_INVENTORY" and not data.get("eligible", False):
                reason=data.get("reason") or "Exchange eligibility or replacement stock could not be verified."
                return f"{reason} Would you like me to help with a return or human support?"
            state=data.get("overall_status") or data.get("status") or "UNKNOWN"
            quantity=data.get("total_network_available",data.get("quantity_available"))
            suffix=f" with {quantity} available" if quantity is not None else ""
            if decision.intent == "CHECK_PICKUP_AVAILABILITY":
                return f"The synthetic store stock status is {str(state).replace('_',' ').lower()}{suffix}. This does not reserve the item or confirm that an order is ready for pickup."
            return f"It's currently {str(state).replace('_',' ').lower()}{suffix}. Would you like me to check another size or color?"
        if decision.intent == "GET_SIZE_GUIDANCE":
            sizes=", ".join(data.get("documented_sizes") or [])
            advisory=data.get("advisory") or "Check the documented measurements before choosing."
            return (f"The documented sizes are {sizes}. " if sizes else "") + advisory
        if decision.intent == "GET_CUSTOMER_ORDERS":
            orders=data.get("orders") or []
            items=orders[0].get("items",[]) if orders else []
            size=(items[0].get("size") or items[0].get("size_name")) if items else None
            return f"Your most recent item was size {size}. Fit can vary by style, so I can also check this piece's guidance." if size else "I found your order history. Which order would you like help with?"
        if decision.intent == "GET_LOYALTY_STATUS":
            return f"Your demo rewards balance is {data.get('points_balance', 0)} points at the {data.get('tier','current')} tier."
        if decision.intent == "CHECK_PROMOTION":
            reasons=", ".join(str(x).replace("_"," ").lower() for x in data.get("reason_codes",[]))
            return ("That demo promotion is eligible." if data.get("eligible") else "That demo promotion is not eligible.") + (f" Reason: {reasons}." if reasons else "")
        if decision.intent == "TRACK_ORDER":
            return f"Your shipment is currently {str(data.get('shipment_status') or data.get('order_status') or data.get('status','unknown')).replace('_',' ').lower()}."
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
            return "I've prepared the details for our support team, so you won't need to repeat everything."
        if status == "SUCCESS":
            return "That's taken care of."
        return "I couldn't complete that with the information available. Would you like to try another approach?"
