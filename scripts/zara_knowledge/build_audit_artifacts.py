"""Materialize reviewed policy facts, rule comparisons and grounded evaluation cases.

This is an evidence-indexed editorial artifact builder, not an inference engine.
Evidence phrases must be present verbatim in the normalized official article.
"""
from .common import CORPUS, ROOT, read, write

def main():
    docs = {d['source_id']:d for d in read(CORPUS/'documents.json')}
    facts = []
    specs = [
        ('HowToReturn','online_return_window',30,'days','Online purchase','shipment date'),
        ('HowToReturn','store_return_window',30,'days','Purchase at a store','purchase date'),
        ('HowToReturn','return_condition','original condition and labels',None,'All returns','original condition'),
        ('HowToReturn','return_market','same market/region',None,'All returns','same market/region'),
        ('HowToReturn','store_return_fee',0,'USD','In-store returns; online and store purchases','free of charge'),
        ('HowToReturn','drop_off_return_fee',4.95,'USD','Per return request, deducted from refund; online purchases only','cost per return request'),
        ('Refund','shipping_return_processing',72,'hours','After receipt at Zara facilities','72 hours'),
        ('Refund','bank_refund_maximum',14,'days','After return is made; depends on bank','maximum period'),
        ('Refund','online_refund_method','original payment method',None,'Online purchase return','same payment method you used'),
        ('HowToExchange','exchange_return_period',14,'days','From exchange request; nonreceipt can trigger charge for new items','return period for the merchandise'),
        ('ReturnSpecialConditions','personalized_items_returnable',False,None,'Personalized items; returns and exchanges','Personalized items:'),
        ('ReturnSpecialConditions','pack_separate_returns',False,None,'Items that are part of a pack','Packs:'),
        ('EditOrder','cancellation','status-dependent option',None,'Availability shown in order detail; guest uses confirmation email','You can cancel a purchase'),
        ('EditOrder','post_purchase_item_changes',False,None,'Completed purchase; exchange/return after receipt','not possible to remove or change'),
        ('MySize','measurement_guide_location','product page',None,'Select size to view tailored body measurements','measurement guide on the product page'),
    ]
    for source,name,value,unit,conditions,phrase in specs:
        doc = docs[source]
        line = next(line for line in doc['clean_text'].splitlines() if phrase in line)
        facts.append(dict(policy_type=doc['policy_type'], fact_name=name,fact_value=value,unit=unit,
            conditions=conditions,exceptions=None,exceptions_note='Not exhaustive; consult cited complete article and Special Return Conditions.',
            source_url=doc['source_url'],source_id=source,knowledge_id=doc['knowledge_id'],source_hash=doc['source_hash'],
            section_title=doc['section_title'],evidence_text=line,retrieved_at=doc['retrieved_at']))
    write(CORPUS/'policy_facts.json',facts)
    rules = [
        ('cancellation_eligible_statuses','PENDING, CONFIRMED, PROCESSING are eligible.',
         'Cancellation depends on order status and availability of the option; exact internal status mapping is not published.',
         'PARTIAL','EditOrder','Document a verified fulfillment-state mapping before changing eligible statuses.'),
        ('cancellation_timing','No elapsed-time cutoff exists.',
         'The captured help article specifies status-dependent availability, without a numeric time limit.',
         'UNKNOWN','EditOrder','Do not introduce a 30-minute rule; absence of a number is not proof that no other cutoff exists.'),
        ('return_window','30 days from delivered_at.',
         'Online returns use shipment date; in-store returns use purchase date.',
         'MISMATCH','HowToReturn','Propose channel-aware date anchoring with shipment evidence; leave current rules unchanged.'),
        ('fallback_date_logic','Missing delivered_at falls back to updated_at then placed_at.',
         'The published online anchor is shipment date; neither fallback establishes shipment.',
         'MISMATCH','HowToReturn','Propose unknown eligibility when the authoritative date is absent; never infer shipment from record updates.'),
        ('return_quantity','Remaining quantity = ordered minus all prior return_item quantities; requested quantity checked per request entry.',
         'Packs cannot be returned separately; the source does not document database counting or duplicate request-entry semantics.',
         'PARTIAL','ReturnSpecialConditions','Preserve quantity safeguards; separately review duplicate line aggregation, prior return statuses and pack restrictions.'),
        ('refund_calculation','Estimate uses discounted line total divided by ordered quantity, multiplied by requested quantity; no channel fee deducted.',
         'Drop-off requests incur a fee deducted from refund; in-store returns are free. Tax, discount allocation and rounding are not fully specified here.',
         'PARTIAL','HowToReturn','Audit fee application by return channel; retain UNKNOWN for accounting details without further official evidence.'),
        ('return_condition_restrictions','No original-condition, labels, market or category checks in ReturnRules.',
         'Original condition, labels and same-market requirements apply; the separate conditions article adds category exceptions.',
         'MISMATCH','HowToReturn','Propose explicit condition/market checks together with evidence-backed category exclusions.'),
        ('category_exclusions','Return eligibility considers status, date and quantities, without category exclusions.',
         'Special conditions cover hygiene strips, undergarments, packaging, fragrances, cosmetics, personalized items, HOME, packs and magazines.',
         'MISMATCH','ReturnSpecialConditions','Design category mapping and exception tests before enforcement changes.'),
        ('exchange_rules','Requires return eligibility, replacement variant and available stock.',
         'Published exchange conditions additionally cover date anchors, condition, market, product/payment restrictions and online exchange limits.',
         'PARTIAL','HowToExchange','Propose channel-specific restrictions and exchange return deadline; do not infer US support for every payment name listed globally on the US page.'),
        ('delivery_order_state_assumptions','Returns require DELIVERED or PARTIALLY_RETURNED; cancellation uses internal uppercase statuses.',
         'Public order tracking describes purchase, processing, preparation, shipment, courier and delivery stages, without an internal-code mapping.',
         'UNKNOWN','OrderStatus','Document mapping and separate delivery evidence from the online return-window anchor.'),
        ('refund_processing','Refund service reads synthetic stored status; no official processing SLA enforcement.',
         'The help article describes processing after facility receipt and subsequent bank-dependent credit timing.',
         'PARTIAL','Refund','Use RAG to explain published timing; use the gateway for actual synthetic refund status.'),
    ]
    results=[]
    for name,current,official,status,source,action in rules:
        doc=docs[source]
        results.append(dict(rule_name=name,current_backend_rule=current,official_policy_rule=official,status=status,
            source_url=doc['source_url'],section_title=doc['section_title'],source_hash=doc['source_hash'],
            knowledge_id=doc['knowledge_id'],retrieved_at=doc['retrieved_at'],evidence_summary=official,recommended_action=action))
    write(ROOT/'reports/phase_2d_policy_rule_discrepancy.json',results)
    lines=['# Phase 2D policy rule discrepancy audit','',
        'Reviewed against repository base 670d705. Existing deterministic rules remain unchanged.',
        'Evidence is official-page research-tool text captured on 2026-09-07; upstream freshness and effective dates are unknown.',
        'Status meanings: MATCH = supported equivalence; MISMATCH = conflicting behavior; PARTIAL = incomplete alignment; UNKNOWN = insufficient evidence.',
        'The legal terms PDF has not been captured; findings are bounded by the help corpus. These are engineering comparisons, not a complete legal review.','']
    for r in results:
        lines += ['## '+r['rule_name']+' — '+r['status'],'', '**Current:** '+r['current_backend_rule'],
                  '', '**Official evidence:** '+r['official_policy_rule'], '',
                  '**Source:** ['+r['section_title']+']('+r['source_url']+')', '',
                  '**Action:** '+r['recommended_action'],'']
    (ROOT/'reports/phase_2d_policy_rule_discrepancy.md').write_text('\n'.join(lines),encoding='utf-8')
    cases=[('What is the return window?','HowToReturn'),
           ('Can I return an online purchase in store?','HowToReturn'),
           ('How are refunds processed?','Refund'),
           ('What payment methods are supported?','PaymentMethods'),
           ('Can an order be modified or cancelled?','EditOrder'),
           ('Are there return exceptions?','ReturnSpecialConditions'),
           ('How does delivery work?','DeliveryMethods'),
           ('Where is the measurement guide?','MySize'),
           ('What are the exchange conditions?','HowToExchange')]
    write(CORPUS/'retrieval_eval.json',[dict(question=q,expected_policy_type=docs[s]['policy_type'],
          expected_source=docs[s]['source_url'],expected_section=docs[s]['section_title']) for q,s in cases])
    print({'facts':len(facts),'audit_rules':len(results),'evaluation_cases':len(cases)})

if __name__ == '__main__':
    main()
