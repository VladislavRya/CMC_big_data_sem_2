from typing import Any, Optional

import helpers


WEIGHTS = {
    'brand':  0.20,
    'model':  0.30,
    'title':  0.25,
    'price':  0.10,
    'specs':  0.15,
}

THRESHOLD = 0.60
TITLE_SHORTCIRCUIT_JACCARD = 0.85


def _jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


def _price_closeness(a: Optional[int], b: Optional[int]) -> float:
    if a is None and b is None:
        return 1.0
    if a is None or b is None:
        return 0.5
    if a <= 0 or b <= 0:
        return 0.0
    return 1.0 - min(1.0, abs(a - b) / max(a, b))


def _specs_score(a: dict, b: dict) -> float:
    fields_exact_int = ('keys_count', 'polyphony', 'timbres')
    matches: list[float] = []
    for f in ('color',):
        va, vb = a.get(f), b.get(f)
        if va and vb:
            matches.append(1.0 if str(va).strip().lower() == str(vb).strip().lower() else 0.0)
    for f in fields_exact_int:
        va, vb = a.get(f), b.get(f)
        if va is not None and vb is not None:
            matches.append(1.0 if va == vb else 0.0)
    if not matches:
        return 0.5
    return sum(matches) / len(matches)


def _same_source_id(a: dict, b: dict) -> bool:
    if a.get('marketplace') != b.get('marketplace'):
        return False
    sa, sb = str(a.get('source_id') or ''), str(b.get('source_id') or '')
    return sa == sb and sa not in ('', '0')


def score(a: dict, b: dict, threshold: float = THRESHOLD) -> dict[str, Any]:
    if _same_source_id(a, b):
        return {
            'matched': True,
            'score': 1.0,
            'breakdown': {},
            'reason': 'same_source_id',
        }

    ba, bb = helpers.get_clean_brand(a.get('brand')), helpers.get_clean_brand(b.get('brand'))
    title_a, title_b = helpers.title_canonical(a), helpers.title_canonical(b)
    qa, qb = helpers.qgrams(title_a), helpers.qgrams(title_b)
    title_j = _jaccard(qa, qb)

    if ba and ba == bb and title_j >= TITLE_SHORTCIRCUIT_JACCARD:
        return {
            'matched': True,
            'score': 1.0,
            'breakdown': {'title_jaccard': round(title_j, 3), 'brand_match': True},
            'reason': 'brand_and_title_shortcircuit',
        }

    digits_a = helpers.model_digit_runs(a)
    digits_b = helpers.model_digit_runs(b)
    if digits_a and digits_b and digits_a.isdisjoint(digits_b):
        return {
            'matched': False,
            'score':   0.0,
            'breakdown': {'veto': 'model_digits_disagree',
                          'a_digits': sorted(digits_a),
                          'b_digits': sorted(digits_b)},
            'reason':  'veto_model_digits',
        }

    brand_m = 1.0 if (ba and bb and ba == bb) else 0.0
    ma, mb = set(helpers.model_tokens(a)), set(helpers.model_tokens(b))
    model_j = _jaccard(ma, mb)
    price_c = _price_closeness(a.get('price_rub'), b.get('price_rub'))
    specs_s = _specs_score(a, b)

    breakdown = {
        'brand':  brand_m,
        'model':  round(model_j, 3),
        'title':  round(title_j, 3),
        'price':  round(price_c, 3),
        'specs':  round(specs_s, 3),
    }
    total = (
        WEIGHTS['brand'] * brand_m
        + WEIGHTS['model'] * model_j
        + WEIGHTS['title'] * title_j
        + WEIGHTS['price'] * price_c
        + WEIGHTS['specs'] * specs_s
    )
    return {
        'matched': total >= threshold,
        'score':   round(total, 4),
        'breakdown': breakdown,
        'reason':  'weighted',
    }
