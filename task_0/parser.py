import json
import csv
from pathlib import Path

import yaml


def _parse_ozon_json_line(line: str) -> dict:
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


def parse_ozon():
    with open(Path(__file__).parent / 'input_data' / 'ozon.txt', 'r') as fin:
        lines = fin.readlines()

    i, result = 0, []
    while i < len(lines):
        item = _parse_ozon_json_line(lines[i].strip())
        item['price'] = int(lines[i + 1].strip())
        result.append(item)
        i += 2

    return result


def parse_wb():
    return [{'price': 100, 'name': 'test'}, {'price': 200, 'name': 'test2'}]


def parse_ym():
    return [{'price': 100, 'name': 'test'}, {'price': 200, 'name': 'test2'}]


def main():
    ozon_data = parse_ozon()
    with open(Path(__file__).parent / 'output_data' / 'ozon.json', 'w') as fout:
        json.dump(ozon_data, fout, ensure_ascii=False, indent=2)

    wb_data = parse_wb()
    with open(Path(__file__).parent / 'output_data' / 'wb.yaml', 'w') as fout:
        yaml.dump(wb_data, fout, allow_unicode=True, default_flow_style=False, indent=2)

    ym_data = parse_ym()
    with open(Path(__file__).parent / 'output_data' / 'ym.csv', 'w', newline='') as fout:
        writer = csv.DictWriter(fout, fieldnames=ym_data[0].keys())
        writer.writeheader()
        writer.writerows(ym_data)

if __name__ == '__main__':
    main()
