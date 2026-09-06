"""Conservative category-end decision from browser observations, not a page fetcher."""


def completion_reason(observations):
    if not observations:
        return None
    latest = observations[-1]
    if latest.get('technical_restriction'):
        return 'TECHNICAL_RESTRICTION'
    if latest.get('error'):
        return 'ERROR'
    # Initial viewport never certifies a category, including apparent emptiness.
    if len(observations) < 2 or latest.get('scroll_iteration', 0) < 1:
        return None
    if latest.get('loading') or latest.get('load_more_available'):
        return None
    if latest.get('explicit_empty') and latest.get('products_seen') == 0:
        return 'CATEGORY_EMPTY'
    if latest.get('explicit_end') and latest.get('at_bottom'):
        return 'END_OF_LIST'
    # Three consecutive settled post-scroll bottom checks, no growth or new IDs.
    if len(observations) >= 4:
        last_three = observations[-3:]
        if all(o.get('scroll_iteration', 0) > 0 and o.get('at_bottom') and
               o.get('settled') and o.get('new_unique_products') == 0 and
               not o.get('loading') and not o.get('load_more_available')
               for o in last_three) and len({o.get('document_height') for o in last_three}) == 1:
            if latest.get('products_seen', 0) > 0:
                return 'NO_NEW_PRODUCTS'
    return None
