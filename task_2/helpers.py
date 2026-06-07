import re
from typing import Optional


_CATEGORY_NOISE: tuple[str, ...] = (
    'характеристики',
    'цифровое пианино',
    'цифровое фортепиано',
    'пианино цифровое',
    'фортепиано',
    'пианино',
    'синтезатор',
)

_COLOUR_NOISE: tuple[str, ...] = (
    'чёрный', 'черный', 'белый', 'белое', 'белая',
    'коричневый', 'дымчатый', 'розовое', 'розовый',
    'red', 'black', 'white', 'brown', 'walnut', 'walnat',
)

_PUNCT_RE = re.compile(r'[^\w\s]', re.UNICODE)
_WS_RE = re.compile(r'\s+')
_TOKEN_SPLIT_RE = re.compile(r'[\s\-_/.,]+')
_COMPACT_DROP_RE = re.compile(r'[\s\-_/.,]+')
_DIGIT_RUN_RE = re.compile(r'\d+')


def _strip_noise(s: str, extra_brand: Optional[str] = None) -> str:
    for noise in _CATEGORY_NOISE:
        s = re.sub(re.escape(noise), ' ', s, flags=re.IGNORECASE)
    if extra_brand:
        s = re.sub(re.escape(extra_brand), ' ', s, flags=re.IGNORECASE)
    s = _PUNCT_RE.sub(' ', s)
    s = _WS_RE.sub(' ', s).strip()
    return s


def get_clean_brand(b: Optional[str]) -> str:
    if not b:
        return ''
    s = b.lower().strip()
    s = _PUNCT_RE.sub('', s)
    s = _WS_RE.sub('', s)
    return s


def title_canonical(rec: dict) -> str:
    title = rec.get('title') or ''
    brand = rec.get('brand') or ''
    s = title.lower()
    s = _strip_noise(s, extra_brand=brand)
    return s


def _is_noise_token(t: str, clean_brand: str) -> bool:
    if not t:
        return True
    if t == clean_brand:
        return True
    if t in {n.lower() for n in _CATEGORY_NOISE}:
        return True
    if t in _COLOUR_NOISE:
        return True
    return False


def model_tokens(rec: dict) -> list[str]:
    model = rec.get('model') or ''
    brand = rec.get('brand') or ''
    clean_brand = get_clean_brand(brand)
    raw = [t.lower() for t in _TOKEN_SPLIT_RE.split(model) if t]
    toks = [t for t in raw if not _is_noise_token(t, clean_brand)]
    if toks:
        return toks
    canon = title_canonical(rec)
    raw_t = [t.lower() for t in _TOKEN_SPLIT_RE.split(canon) if t]
    return [t for t in raw_t if not _is_noise_token(t, clean_brand)]


def model_compact(rec: dict) -> str:
    model = rec.get('model') or ''
    return _COMPACT_DROP_RE.sub('', model).lower()


def model_digit_runs(rec: dict) -> set[str]:
    return set(_DIGIT_RUN_RE.findall(model_compact(rec)))


def qgrams(s: str, n: int = 3) -> set[str]:
    if not s:
        return set()
    padded = ' ' * (n - 1) + s + ' ' * (n - 1)
    return {padded[i:i + n] for i in range(len(padded) - n + 1)}


def sort_key_brand_model(rec: dict) -> str:
    brand = get_clean_brand(rec.get('brand'))
    toks = sorted(model_tokens(rec))
    key_tail = '_'.join(toks)[:32]
    return f'{brand}|{key_tail}' if (brand or key_tail) else ''


def sort_key_model(rec: dict) -> str:
    return '_'.join(sorted(model_tokens(rec)))[:32]


def sort_key_title(rec: dict) -> str:
    return title_canonical(rec)


def partition_id(bkv: str) -> str:
    return bkv[:1] if bkv else ''


SORT_KEYS = {
    'brand_model': sort_key_brand_model,
    'model':       sort_key_model,
    'title':       sort_key_title,
}
