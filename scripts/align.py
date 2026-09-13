# -*- coding: utf-8 -*-
"""逐章经文对齐：底本（王弼本） vs 源本（宋徽宗本）。
输出：
  diffs.json —— 归并去重后的校记条目（异文／脱文／衍文／倒文）
  marks.json —— 逐处差异及其在底本／源本经文中的原串位置（供对比报告高亮）
"""
import json, difflib, sys
import zhconv

PUNCT_SET = set('，。；：！？、（）「」『』｢｣〔〕【】《》〈〉・·—…﹖﹔﹑　 \t\n\r"\'“”‘’()[]{}<>.,;:!?/~\\|-_+=*&^%$#@`')
PUNCT_END = set('，。；：！？、﹖﹔')


def fold_map(s):
    conv = zhconv.convert(s, 'zh-cn')
    out, idx = [], []
    for i, ch in enumerate(conv):
        if ch in PUNCT_SET:
            continue
        out.append(ch)
        idx.append(i)
    return ''.join(out), idx


def span_to_orig(fmap, a, b):
    if not fmap:
        return 0, 0
    if a >= len(fmap):
        return fmap[-1] + 1, fmap[-1] + 1
    return fmap[a], fmap[b - 1] + 1


def expand(orig, s, e, maxlen=32):
    L = s
    while L > 0 and orig[L - 1] not in PUNCT_END and s - L < maxlen:
        L -= 1
    R = e
    while R < len(orig) and orig[R] not in PUNCT_END and R - e < maxlen:
        R += 1
    if R < len(orig) and orig[R] in PUNCT_END:
        R += 1
    return L, R


def is_anagram(a, b):
    a = ''.join(c for c in zhconv.convert(a, 'zh-cn') if c not in PUNCT_SET)
    b = ''.join(c for c in zhconv.convert(b, 'zh-cn') if c not in PUNCT_SET)
    if not a or not b:
        return False
    if a == b:
        return True
    return len(a) == len(b) and sorted(a) == sorted(b)


def align_chapter(bj, sj):
    """返回 (diffs, marks)。diffs 未去重。"""
    bfold, bmap = fold_map(bj)
    sfold, smap = fold_map(sj)
    sm = difflib.SequenceMatcher(None, bfold, sfold, autojunk=False)
    raw = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            continue
        bs, be = span_to_orig(bmap, i1, i2)
        ss, se = span_to_orig(smap, j1, j2)
        ebs, ess = expand(bj, bs, be), expand(sj, ss, se)
        raw.append({'tag': tag, 'core_b': bj[bs:be], 'core_s': sj[ss:se],
                    'pos_b': (bs, be), 'pos_s': (ss, se),
                    'ctx_b': bj[ebs[0]:ebs[1]], 'ctx_s': sj[ess[0]:ess[1]]})

    used = [False] * len(raw)
    diffs, marks = [], []
    for i in range(len(raw)):
        if used[i]:
            continue
        if raw[i]['tag'] == 'replace':
            used[i] = True
            diffs.append({'type': '异文', 'base': raw[i]['core_b'], 'src': raw[i]['core_s'],
                          'ctx_base': raw[i]['ctx_b'], 'ctx_src': raw[i]['ctx_s']})
            marks.append({'type': '异文', 'b': list(raw[i]['pos_b']), 's': list(raw[i]['pos_s'])})
            continue
        merged = False
        for j in range(i + 1, len(raw)):
            if used[j] or raw[j]['tag'] == raw[i]['tag'] or raw[j]['tag'] == 'replace':
                continue
            d_op = raw[i] if raw[i]['tag'] == 'delete' else raw[j]
            s_op = raw[j] if raw[i]['tag'] == 'delete' else raw[i]
            X, Y = d_op['core_b'], s_op['core_s']
            if X and Y and len(X) >= 2 and is_anagram(X, Y):
                used[i] = used[j] = True
                diffs.append({'type': '倒文', 'base': X, 'src': Y,
                              'ctx_base': d_op['ctx_b'], 'ctx_src': s_op['ctx_s']})
                marks.append({'type': '倒文', 'b': list(d_op['pos_b']), 's': list(s_op['pos_s'])})
                merged = True
            break
        if merged:
            continue
        used[i] = True
        if raw[i]['tag'] == 'delete':
            diffs.append({'type': '脱文', 'base': raw[i]['ctx_b'], 'core': raw[i]['core_b'],
                          'src': '', 'ctx_base': raw[i]['ctx_b'], 'ctx_src': raw[i]['ctx_s']})
            marks.append({'type': '脱文', 'b': list(raw[i]['pos_b']), 's': []})
        else:
            diffs.append({'type': '衍文', 'src': raw[i]['ctx_s'], 'core': raw[i]['core_s'],
                          'base': '', 'ctx_base': raw[i]['ctx_b'], 'ctx_src': raw[i]['ctx_s']})
            marks.append({'type': '衍文', 'b': [], 's': list(raw[i]['pos_s'])})
    return diffs, marks


def dedup(diffs):
    """归并：异文／倒文按（底本、源本）去重；脱文／衍文按所脱所衍之文去重。"""
    out, seen = [], {}
    for d in diffs:
        if d['type'] in ('脱文', '衍文'):
            key = (d['type'], d.get('core', ''))
        else:
            key = (d['type'], d.get('base', ''), d.get('src', ''))
        if key in seen:
            seen[key]['n'] += 1
        else:
            e = dict(d)
            e['n'] = 1
            seen[key] = e
            out.append(e)
    return out


if __name__ == '__main__':
    d = json.load(open('parsed.json', encoding='utf-8'))
    total = {'异文': 0, '脱文': 0, '衍文': 0, '倒文': 0}
    out, marks = {}, {}
    for n in range(1, 82):
        v = d[str(n)]
        diffs, mk = align_chapter(''.join(v['base_jing']), ''.join(v['jing']))
        out[str(n)] = dedup(diffs)
        marks[str(n)] = mk
        for x in out[str(n)]:
            total[x['type']] += x['n']
    json.dump(out, open('diffs.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    json.dump(marks, open('marks.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('差异合计:', total, ' 总计', sum(total.values()))
    print('有异之章:', sum(1 for n in range(1, 82) if out[str(n)]), '/81')
    lo = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    hi = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    th = {'异文': '异文', '脱文': '脱文', '衍文': '衍文', '倒文': '倒文'}
    for n in range(lo, hi + 1):
        print('--- 第%d章 ---' % n)
        for x in out[str(n)]:
            suf = '（凡%d见）' % x['n'] if x['n'] > 1 else ''
            if x['type'] == '异文':
                print('  异文：底本「%s」，源本作「%s」%s' % (x['base'], x['src'], suf))
            elif x['type'] == '脱文':
                print('  脱文：底本「%s」，源本无「%s」%s' % (x['base'], x['core'], suf))
            elif x['type'] == '衍文':
                print('  衍文：源本「%s」，底本无「%s」%s' % (x['src'], x['core'], suf))
            else:
                print('  倒文：底本「%s」，源本作「%s」%s' % (x['base'], x['src'], suf))
