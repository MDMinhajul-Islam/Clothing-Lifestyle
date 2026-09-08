# NexGen Customer Knowledge Base

## Purpose

This collection is the customer knowledge handbook for NexGen AI Fashion & Voice Commerce. It supports consistent shopping guidance across voice and digital service channels.

The documents contain stable customer guidance. Current availability, commercial terms, order details, eligibility decisions, and other changing information must always be checked through the active NexGen service.

## Source of Truth

The Knowledge Base is supplementary guidance. NexGen backend systems are authoritative.

Current product information, inventory, prices, promotions, customer records, order status, returns, exchanges, refunds, shipping estimates, and policies must always come from NexGen backend systems.

If Knowledge Base guidance differs from a current backend result, use the backend result. If current information cannot be verified, explain that clearly and offer an appropriate next step.

## Navigation

- [Brand identity](01_brand_identity.md): brand character, service principles, and tone.
- [Customer journey](02_customer_journey.md): discovery through post-purchase support.
- [Product discovery](03_product_discovery.md): search, refinement, and comparison guidance.
- [Fashion knowledge](04_fashion_knowledge.md): garments, fabrics, construction, and care concepts.
- [Styling guide](05_styling_guide.md): occasion-led and wardrobe-led recommendations.
- [Size and fit guide](06_size_fit_guide.md): measurements, silhouettes, and fit clarification.
- [Color guide](07_color_guide.md): color description and coordination.
- [Orders and shipping](08_orders_shipping.md): general order and delivery guidance.
- [Returns and exchanges](09_returns_exchanges.md): general service journey and verification boundaries.
- [Customer accounts](10_customer_accounts.md): account access and customer self-service.
- [Store information](11_store_information.md): store discovery and visit preparation.
- [Conversation examples](12_voice_conversation_examples.md): natural retail dialogues.
- [Assistant behavior](13_assistant_behavior.md): service, clarification, confirmation, and handoff standards.
- [Security and privacy](14_security_privacy.md): safe customer interaction principles.
- [Retail glossary](15_retail_glossary.md): fashion and commerce terminology.
- [Semantic retrieval examples](16_semantic_retrieval_examples.md): intent phrases and expected understanding.

## Maintenance

Assign an owner to every document. Review brand and fashion guidance quarterly, and review customer-service material whenever approved terms change. Record the review date outside customer-facing content and retire superseded copies.

Do not add changing product information, commercial offers, private customer information, or unapproved policy claims. Keep headings descriptive, paragraphs short, and each section focused on one subject.

## Uploading to Retell Knowledge Base

Create one dedicated knowledge base named `NexGen Enterprise Knowledge Base` and upload the numbered documents as separate Markdown sources.

### Recommended Upload Order

1. `01_brand_identity.md`
2. `13_assistant_behavior.md`
3. `14_security_privacy.md`
4. `02_customer_journey.md`
5. `03_product_discovery.md`
6. `04_fashion_knowledge.md`
7. `05_styling_guide.md`
8. `06_size_fit_guide.md`
9. `07_color_guide.md`
10. `08_orders_shipping.md`
11. `09_returns_exchanges.md`
12. `10_customer_accounts.md`
13. `11_store_information.md`
14. `12_voice_conversation_examples.md`
15. `15_retail_glossary.md`
16. `16_semantic_retrieval_examples.md`

Upload `README.md` last only if maintainers want its navigation content available during retrieval. It may be retained outside the active sources to reduce retrieval noise.

### Retell Processing and Validation

1. Wait until every uploaded source reports successful processing.
2. Attach the completed knowledge base to the intended NexGen agent version.
3. Begin with three retrieved passages and a moderate similarity threshold.
4. Test the intents in `16_semantic_retrieval_examples.md`.
5. Confirm that stable guidance is retrieved from the relevant source.
6. Confirm that changing, transactional, or private questions are redirected to the active NexGen service.
7. Repeat the evaluation after every content revision.

## Content Boundary

This handbook explains stable retail concepts and customer journeys. It does not establish a current price, availability promise, delivery commitment, eligibility decision, or completed transaction.
