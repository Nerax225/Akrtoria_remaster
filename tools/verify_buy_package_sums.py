import re
from pathlib import Path
import json

"""Verify that each wealth_X goods block's actual numeric sum matches the annotated '# Sum = N'.
Outputs JSON summary with failures list.
"""

FILE_REL = Path('common/buy_packages/00_buy_packages.txt')

WEALTH_BLOCK_RE = re.compile(r'(wealth_(\d+)\s*=\s*\{[\s\S]*?\n\})', re.MULTILINE)
GOODS_RE = re.compile(r'goods\s*=\s*\{([\s\S]*?)\n\t\}', re.MULTILINE)
NEED_LINE_RE = re.compile(r'^\t+([a-zA-Z0-9_]+)\s*=\s*(\d+)\s*$', re.MULTILINE)
ANNOT_SUM_RE = re.compile(r'#\s*Sum\s*=\s*(\d+)')

def extract_blocks(text: str):
    for m in WEALTH_BLOCK_RE.finditer(text):
        block = m.group(1)
        wealth = int(m.group(2))
        yield wealth, block

def compute_sum(block: str):
    goods_match = GOODS_RE.search(block)
    if not goods_match:
        return None, None, 'no_goods'
    goods_inner = goods_match.group(1)
    annot = ANNOT_SUM_RE.search(block)
    annot_val = int(annot.group(1)) if annot else None
    total = 0
    for nm, val in NEED_LINE_RE.findall(goods_inner):
        if nm.startswith('popneed_') or nm in ('popneed_medical_items', 'popneed_housing'):
            try:
                total += int(val)
            except ValueError:
                return annot_val, None, f'invalid_int:{nm}'
    return annot_val, total, None

def main():
    root = Path(__file__).resolve().parents[1]
    file_path = root / FILE_REL
    text = file_path.read_text(encoding='utf-8')
    failures = []
    count = 0
    for wealth, block in extract_blocks(text):
        annot, total, err = compute_sum(block)
        count += 1
        if err:
            failures.append({'wealth': wealth, 'error': err})
            continue
        if annot is None:
            failures.append({'wealth': wealth, 'error': 'missing_annotation', 'actual': total})
        elif annot != total:
            failures.append({'wealth': wealth, 'annotated': annot, 'actual': total, 'delta': total-annot})
    summary = {
        'blocks': count,
        'failures': len(failures),
        'details': failures[:50],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
