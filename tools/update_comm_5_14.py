import re
from pathlib import Path

VALUES = {5:5,6:6,7:7,8:8,9:9,10:10,11:12,12:14,13:16,14:18}

WEALTH_RE = re.compile(r'(wealth_(\d+)\s*=\s*\{[\s\S]*?\n\})', re.MULTILINE)
GOODS_RE = re.compile(r'(goods\s*=\s*\{)([\s\S]*?)(\n\t\})', re.MULTILINE)
LINE_RE = re.compile(r'^\t(popneed_[a-z0-9_]+)\s*=\s*(\d+)\s*$', re.IGNORECASE)
ANNOT_RE = re.compile(r'#\s*Sum\s*=\s*(\d+)')

def adjust_block(block:str, wealth:int)->str:
    if 'popneed_communication' in block:
        return block
    if wealth not in VALUES:
        return block
    gmatch = GOODS_RE.search(block)
    if not gmatch:
        return block
    head, inner, tail = gmatch.groups()
    lines = inner.split('\n')
    # collect need lines indexes
    needs = []  # (idx,name,val)
    for i,l in enumerate(lines):
        m = LINE_RE.match(l)
        if m:
            needs.append((i,m.group(1),int(m.group(2))))
    if not needs:
        return block
    # pick two largest by value (no protection)
    sorted_needs = sorted(needs, key=lambda x:x[2], reverse=True)
    top_two = sorted_needs[:2]
    add_val = VALUES[wealth]
    total_donor = top_two[0][2] + top_two[1][2]
    # proportional deduction
    d1 = round(add_val * (top_two[0][2]/total_donor))
    d2 = add_val - d1
    # apply
    new_lines = lines[:]
    for (orig_idx,name,val),ded in zip(top_two,[d1,d2]):
        new_lines[orig_idx] = f"\t{name} = {val-ded}"
    # insert communication after second donor line position (or at end if ordering not important)
    insert_pos = max(top_two[0][0], top_two[1][0]) + 1
    new_lines.insert(insert_pos, f"\tpopneed_communication = {add_val}")
    new_inner = '\n'.join(new_lines)
    new_block = block[:gmatch.start(2)] + new_inner + block[gmatch.end(2):]
    # sanity: ensure sum preserved vs annotation
    ann = ANNOT_RE.search(block)
    if ann:
        ann_sum = int(ann.group(1))
        # recompute
        cur = 0
        for m in LINE_RE.finditer(new_inner):
            cur += int(m.group(2))
        if cur != ann_sum:
            # adjust rounding drift by modifying first donor
            drift = cur - ann_sum
            # modify first donor line to subtract drift
            # find its line again
            m2 = LINE_RE.match(new_lines[top_two[0][0]])
            if m2:
                corrected = int(m2.group(2)) - drift
                if corrected < 0:
                    pass
                else:
                    new_lines[top_two[0][0]] = f"\t{m2.group(1)} = {corrected}"
                    new_inner = '\n'.join(new_lines)
                    new_block = block[:gmatch.start(2)] + new_inner + block[gmatch.end(2):]
    return new_block

def main():
    root = Path(__file__).resolve().parents[1]
    target = root / 'common' / 'buy_packages' / '00_buy_packages.txt'
    text = target.read_text(encoding='utf-8')
    out_parts = []
    last = 0
    modified = False
    for m in WEALTH_RE.finditer(text):
        start,end = m.span(1)
        out_parts.append(text[last:start])
        wealth = int(m.group(2))
        block = m.group(1)
        new_block = adjust_block(block, wealth)
        if new_block != block:
            modified = True
        out_parts.append(new_block)
        last = end
    out_parts.append(text[last:])
    if modified:
        target.write_text(''.join(out_parts), encoding='utf-8')
        print('Inserted communication for some wealth blocks.')
    else:
        print('No changes made (already present or none applicable).')

if __name__ == '__main__':
    main()
