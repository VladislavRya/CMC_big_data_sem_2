import json
import csv
import copy
from typing import Any
from pathlib import Path

import yaml


# TODO: не забыть подменить циферки и что-нибудь ещё в дубликатах рукотворных
# TODO: можно для дублей специально выставить нуловый урл, чтобы мы их нашли во время резолва
# TODO: для WB url формировать потом в следующем задании. Там легко. https://www.wildberries.ru/catalog/{nm_id}/detail.aspx


def _parse_ozon_json_line(line: str) -> dict[str, Any]:
    json_str = line.split(':', 1)[1]
    if json_str.endswith(','):
        json_str = json_str[:-1]
    json_str = json_str.strip()
    if json_str.startswith('"') and json_str.endswith('"'):
        json_str = json_str[1:-1]
    json_str = json_str.replace('\\"', '"')
    obj = json.loads(json_str)
    obj.pop('totalCount')
    obj.pop('lexemes')
    obj.pop('cellTrackingInfo')
    obj.pop('params')

    # TODO: здесь наверное мы хотим ещё что-то сделать с характеристиками

    return obj

def parse_ozon() -> list[dict[str, Any]]:
    with open(Path(__file__).parent / 'input_data' / 'ozon.txt', 'r') as fin:
        lines = fin.readlines()

    i, result = 0, []
    while i < len(lines):
        item = _parse_ozon_json_line(lines[i].strip())
        item['price'] = int(lines[i + 1].strip())
        result.append(item)
        i += 2

    return result


def _parse_wb_single_obj(obj: dict[str, Any]) -> dict[str, Any]:
    new_obj = copy.deepcopy(obj)
    # TODO: здесь что-нибудь повыкидываем обязательно
    return new_obj

def parse_wb() -> list[dict[str, Any]]:
    with open(Path(__file__).parent / 'input_data' / 'wb.json', 'r') as fin:
        data = json.load(fin)
    return [_parse_wb_single_obj(obj) for obj in data]


def _parse_ym_single_obj(obj: dict[str, Any]) -> dict[str, Any]:
    new_obj = copy.deepcopy(obj)
    # TODO: здесь что-нибудь повыкидываем обязательно
    return new_obj

def parse_ym() -> list[dict[str, Any]]:
    with open(Path(__file__).parent / 'input_data' / 'ym.json', 'r') as fin:
        data = json.load(fin)
    return [_parse_ym_single_obj(obj) for obj in data]

def main():
    ozon_data = parse_ozon()
    with open(Path(__file__).parent / 'output_data' / 'ozon.json', 'w') as fout:
        json.dump(ozon_data, fout, ensure_ascii=False, indent=2)

    wb_data = parse_wb()
    with open(Path(__file__).parent / 'output_data' / 'wb.yaml', 'w') as fout:
        yaml.dump(wb_data, fout, allow_unicode=True, default_flow_style=False, indent=2)

    ym_data = parse_ym()
    with open(Path(__file__).parent / 'output_data' / 'ym.csv', 'w', newline='') as fout:
        fieldnames = set()
        for obj in ym_data:
            fieldnames.update(obj.keys())
        writer = csv.DictWriter(fout, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(ym_data)


if __name__ == '__main__':
    main()
