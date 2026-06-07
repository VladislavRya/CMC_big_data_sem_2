import re
from abc import ABC, abstractmethod
from typing import Any, Optional


def _none_if_blank(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    s = str(s).strip()
    return s or None


class BaseTransformer(ABC):
    SOURCE_NAME: str = ''

    @staticmethod
    def _to_int(raw: Any) -> Optional[int]:
        if raw is None:
            return None
        s = str(raw).strip()
        if not s:
            return None
        m = re.search(r'-?\d+', s)
        return int(m.group()) if m else None

    @staticmethod
    def _to_float(raw: Any) -> Optional[float]:
        if raw is None:
            return None
        s = str(raw).strip().replace(',', '.')
        if not s:
            return None
        m = re.search(r'-?\d+(?:\.\d+)?', s)
        return float(m.group()) if m else None

    @classmethod
    def _parse_length_mm(cls, raw: Any) -> Optional[int]:
        if raw is None:
            return None
        s = str(raw).strip().lower().replace(',', '.')
        m = re.search(r'(-?\d+(?:\.\d+)?)\s*(мм|см|м)?', s)
        if not m:
            return None
        n = float(m.group(1))
        unit = m.group(2)
        if unit == 'см':
            n *= 10
        elif unit == 'м':
            n *= 1000
        return int(round(n))

    @classmethod
    def _parse_weight_kg(cls, raw: Any) -> Optional[float]:
        if raw is None:
            return None
        s = str(raw).strip().lower().replace(',', '.')
        m = re.search(r'(-?\d+(?:\.\d+)?)\s*(кг|г)?', s)
        if not m:
            return None
        n = float(m.group(1))
        unit = m.group(2)
        if unit == 'г' or unit is None:
            n /= 1000
        return round(n, 3)

    @classmethod
    def _split_dimensions(cls, raw: Any) -> tuple[Optional[int], Optional[int], Optional[int]]:
        if raw is None:
            return (None, None, None)
        s = str(raw).strip().lower().replace(',', '.')
        nums = re.findall(r'\d+(?:\.\d+)?', s)
        unit_match = re.search(r'(мм|см|м)\b', s)
        unit = unit_match.group(1) if unit_match else None
        scale = {'мм': 1, 'см': 10, 'м': 1000, None: 1}[unit]
        vals: list[Optional[int]] = []
        for v in nums[:3]:
            vals.append(int(round(float(v) * scale)))
        while len(vals) < 3:
            vals.append(None)
        return (vals[0], vals[1], vals[2])

    @abstractmethod
    def extract_source_id(self, record: dict) -> str: ...
    @abstractmethod
    def extract_url(self, record: dict) -> str: ...
    @abstractmethod
    def extract_title(self, record: dict) -> str: ...
    @abstractmethod
    def extract_description(self, record: dict) -> Optional[str]: ...
    @abstractmethod
    def extract_brand(self, record: dict) -> str: ...
    @abstractmethod
    def extract_price_rub(self, record: dict) -> int: ...
    @abstractmethod
    def extract_color(self, record: dict) -> str: ...
    @abstractmethod
    def extract_keys_count(self, record: dict) -> Optional[int]: ...
    @abstractmethod
    def extract_keys_size(self, record: dict) -> Optional[str]: ...
    @abstractmethod
    def extract_keys_weight(self, record: dict) -> Optional[str]: ...
    @abstractmethod
    def extract_polyphony(self, record: dict) -> Optional[int]: ...
    @abstractmethod
    def extract_timbres(self, record: dict) -> Optional[int]: ...
    @abstractmethod
    def extract_weight_kg(self, record: dict) -> Optional[float]: ...
    @abstractmethod
    def extract_width_mm(self, record: dict) -> Optional[int]: ...
    @abstractmethod
    def extract_height_mm(self, record: dict) -> Optional[int]: ...
    @abstractmethod
    def extract_depth_mm(self, record: dict) -> Optional[int]: ...
    @abstractmethod
    def extract_country(self, record: dict) -> Optional[str]: ...

    def extract_model(self, record: dict) -> str:
        title = self.extract_title(record) or ''
        brand = self.extract_brand(record) or ''
        s = title.split(',', 1)[0]
        COMMON_TITLE_NOISE: tuple[str, ...] = (
            'характеристики:',
            'цифровое пианино',
            'цифровое фортепиано',
            'пианино цифровое',
            'фортепиано',
            'пианино',
            'синтезатор',
        )
        for noise in COMMON_TITLE_NOISE:
            s = re.sub(re.escape(noise), '', s, flags=re.IGNORECASE)
        if brand:
            s = re.sub(re.escape(brand), '', s, flags=re.IGNORECASE)
        s = re.sub(r'\s+', ' ', s).strip(' ,.:;-–—()[]')
        return s

    def transform(self, record: dict) -> dict:
        result = {
            'marketplace': self.SOURCE_NAME,
            'source_id':   self.extract_source_id(record),
            'url':         self.extract_url(record),
            'title':       self.extract_title(record),
            'description': _none_if_blank(self.extract_description(record)),
            'brand':       self.extract_brand(record).lower(),
            'model':       self.extract_model(record),
            'price_rub':   self.extract_price_rub(record),
            'color':       self.extract_color(record).lower(),
            'keys_count':  self.extract_keys_count(record),
            'keys_size':   _none_if_blank(self.extract_keys_size(record)),
            'keys_weight': _none_if_blank(self.extract_keys_weight(record)),
            'polyphony':   self.extract_polyphony(record),
            'timbres':     self.extract_timbres(record),
            'weight_kg':   self.extract_weight_kg(record),
            'width_mm':    self.extract_width_mm(record),
            'height_mm':   self.extract_height_mm(record),
            'depth_mm':    self.extract_depth_mm(record),
            'country':     _none_if_blank(self.extract_country(record)),
        }
        self.validate(result)
        return result

    def validate(self, record: dict) -> None:
        assert record['source_id'], (self.SOURCE_NAME, record)
        assert record['url'], (self.SOURCE_NAME, record)
        assert record['title'], (self.SOURCE_NAME, record)
        assert record['brand'], (self.SOURCE_NAME, record)
        assert record['model'], (self.SOURCE_NAME, record)
        assert record['price_rub'], (self.SOURCE_NAME, record)
        assert record['color'], (self.SOURCE_NAME, record)



# ---------------------------------------------------------------------------
# Ozon
# ---------------------------------------------------------------------------

class OzonTransformer(BaseTransformer):
    SOURCE_NAME = 'ozon'

    @staticmethod
    def _char(record: dict, key: str) -> Optional[str]:
        for block in record.get('characteristics', []):
            for section in ('short', 'long'):
                for entry in block.get(section, []):
                    if entry.get('key') == key:
                        values = entry.get('values', [])
                        if values:
                            return values[0].get('text')
        return None

    def extract_source_id(self, record):
        return self._char(record, 'Sku')

    def extract_url(self, record):
        return record.get('link')

    def extract_title(self, record):
        t = record.get('productTitle') or ''
        return re.sub(r'^Характеристики:\s*', '', t).strip() or None

    def extract_description(self, record):
        return None

    def extract_brand(self, record):
        return self._char(record, 'Brand')

    def extract_price_rub(self, record):
        return self._to_int(record.get('price'))

    def extract_color(self, record):
        return self._char(record, 'Color')

    def extract_keys_count(self, record):
        return self._to_int(self._char(record, 'KeysQtyUnique'))

    def extract_keys_size(self, record):
        return self._char(record, 'KeysSize')

    def extract_keys_weight(self, record):
        return self._char(record, 'KeysWeight')

    def extract_polyphony(self, record):
        return self._to_int(self._char(record, 'PolyphonicRingtones'))

    def extract_timbres(self, record):
        return self._to_int(self._char(record, 'Timbres'))

    def extract_weight_kg(self, record):
        grams = self._to_float(self._char(record, 'Weight'))
        return round(grams / 1000, 3) if grams is not None else None

    def _dims(self, record) -> tuple[Optional[int], Optional[int], Optional[int]]:
        return self._split_dimensions(self._char(record, 'Dimensions'))

    def extract_width_mm(self, record):
        return self._dims(record)[0]

    def extract_height_mm(self, record):
        return self._dims(record)[1]

    def extract_depth_mm(self, record):
        return self._dims(record)[2]

    def extract_country(self, record):
        return self._char(record, 'Country')


# ---------------------------------------------------------------------------
# WB
# ---------------------------------------------------------------------------

class WBTransformer(BaseTransformer):
    SOURCE_NAME = 'wb'

    URL_TEMPLATE = 'https://www.wildberries.ru/catalog/{nm_id}/detail.aspx'

    @staticmethod
    def _option(record: dict, name: str) -> Optional[str]:
        for opt in record.get('options', []):
            if opt.get('name') == name:
                v = opt.get('value')
                return None if v is None else str(v)
        return None

    def extract_source_id(self, record):
        return str(record['nm_id'])

    def extract_url(self, record):
        nm_id = record.get('nm_id')
        return self.URL_TEMPLATE.format(nm_id=nm_id) if nm_id else 'FAKE'

    def extract_title(self, record):
        return record.get('imt_name')

    def extract_description(self, record):
        return record.get('description')

    def extract_brand(self, record):
        selling = record.get('selling') or {}
        return selling.get('brand_name')

    def extract_model(self, record):
        return record.get('vendor_code') or super().extract_model(record)

    def extract_price_rub(self, record):
        return self._to_int(record.get('price'))

    def extract_color(self, record):
        return record.get('nm_colors_names') or self._option(record, 'Цвет')

    def extract_keys_count(self, record):
        return self._to_int(self._option(record, 'Количество клавиш'))

    def extract_keys_size(self, record):
        return None

    def extract_keys_weight(self, record):
        return self._option(record, 'Жесткость клавиатуры')

    def extract_polyphony(self, record):
        return self._to_int(self._option(record, 'Полифония'))

    def extract_timbres(self, record):
        return self._to_int(self._option(record, 'Количество тембров'))

    def extract_weight_kg(self, record):
        return self._to_float(self._option(record, 'Вес с упаковкой (кг)'))

    def extract_width_mm(self, record):
        return self._parse_length_mm(self._option(record, 'Ширина предмета'))

    def extract_height_mm(self, record):
        return self._parse_length_mm(self._option(record, 'Высота предмета'))

    def extract_depth_mm(self, record):
        return self._parse_length_mm(self._option(record, 'Глубина предмета'))

    def extract_country(self, record):
        return self._option(record, 'Страна производства')


# ---------------------------------------------------------------------------
# Yandex Market
# ---------------------------------------------------------------------------

class YMTransformer(BaseTransformer):
    SOURCE_NAME = 'ym'

    def extract_source_id(self, record):
        return record['артикул_маркета']

    def extract_url(self, record):
        return record.get('ссылка')

    def extract_title(self, record):
        return record.get('карточка_названия')

    def extract_description(self, record):
        return None

    def extract_brand(self, record):
        return record.get('бренд')

    def extract_price_rub(self, record):
        return self._to_int(record.get('цена'))

    def extract_color(self, record):
        return record.get('цвет')

    def extract_keys_count(self, record):
        return self._to_int(record.get('количество_клавиш'))

    def extract_keys_size(self, record):
        return record.get('размер_клавиш')

    def extract_keys_weight(self, record):
        return record.get('жесткость_клавиатуры')

    def extract_polyphony(self, record):
        return self._to_int(record.get('полифония'))

    def extract_timbres(self, record):
        return self._to_int(record.get('количество_тембров'))

    def extract_weight_kg(self, record):
        return self._parse_weight_kg(record.get('вес'))

    def extract_width_mm(self, record):
        return self._parse_length_mm(record.get('ширина'))

    def extract_height_mm(self, record):
        return self._parse_length_mm(record.get('высота'))

    def extract_depth_mm(self, record):
        return self._parse_length_mm(record.get('глубина'))

    def extract_country(self, record):
        return None


TRANSFORMERS: dict[str, type[BaseTransformer]] = {
    'ozon': OzonTransformer,
    'wb':   WBTransformer,
    'ym':   YMTransformer,
}