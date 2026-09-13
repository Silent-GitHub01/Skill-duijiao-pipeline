# -*- coding: utf-8 -*-
"""解析两本道德经：分章、据底本锚定做经注分离。"""
import re, json, sys, difflib
import zhconv

CN = '零一二三四五六七八九十百'

# 源本 11 处现代广告噪声（非宋徽宗文），须剔除
AD_PATTERNS = [
    re.compile(r'更多内容[，,]?\s*请?关注龙虎山道家养生公众号[！!]?'),
    re.compile(r'道德经八十一章每一章都是一种无为法修炼之法[.。]?想要学习文始派真传无为法可联系至大[:：]?ddjy_zhida'),
]
# 经／注 人工裁定（据文义与底本锚定，见校勘说明）：章号 -> {段序: 标签}
LABEL_OVERRIDE = {
    20: {24: '经'},   # 「飂兮似无所止」底本经文，短句异文致覆盖面过低
    32: {1: '注'},    # 「道者，天地之始，岂得而名？」为注，非经
    36: {4: '经'},    # 「柔之胜刚，弱之胜强」底本经文
    38: {3: '注'},    # 「认而有之，自私以失道，何德之有？」为注
    77: {6: '经'},    # 「孰能损有余而奉不足於天下者，其唯道乎」底本经文
}


def clean_ad(s):
    """剔除段落内嵌的现代广告文字。返回 (清洗后文本, 是否整段为广告)。"""
    if not s:
        return s, False
    t = s
    for p in AD_PATTERNS:
        t = p.sub('', t)
    t = t.strip()
    if not t:
        return '', True
    return t, False



def cn2int(s):
    s = s.strip()
    if not s:
        return None
    if s == '十':
        return 10
    # 处理 第X章 的 X，范围 1..81
    if '百' in s:
        # 如 一百
        return None
    if s[0] == '十':
        return 10 + (CN.index(s[1]) if len(s) > 1 else 0)
    if len(s) == 1:
        return CN.index(s)
    if len(s) == 2:
        if s[1] == '十':
            return CN.index(s[0]) * 10
        if s[0] == '十':
            return 10 + CN.index(s[1])
        return None
    if len(s) == 3:
        if s[1] == '十':
            return CN.index(s[0]) * 10 + CN.index(s[2])
        return None
    return None


PUNCT = set('，。；：！？、（）「」『』｢｣〔〕【】《》〈〉・·—…﹖﹔﹑　 \t\n\r"\'“”‘’()[]{}<>.,;:!?/~\\|-_+=*&^%$#@`')


def fold(s):
    """繁→简 + 去标点空白。"""
    s = zhconv.convert(s, 'zh-cn')
    return ''.join(ch for ch in s if ch not in PUNCT)


# ---------- 底本（王弼注精校） ----------
def parse_base(path):
    lines = open(path, encoding='utf-8').read().split('\n')
    ch_re = re.compile(r'^第([%s]+)章$' % CN)
    chapters = {}
    order = []
    cur = None
    started = False
    for ln in lines:
        t = ln.strip()
        if t in ('上篇道經', '下篇德經', '上篇道经', '下篇德经'):
            started = True
            continue
        m = ch_re.match(t)
        if m:
            n = cn2int(m.group(1))
            if n is None:
                continue
            cur = n
            started = True
            chapters[n] = {'jing': [], 'zhu': []}
            order.append(n)
            continue
        if not started or cur is None:
            continue
        if t.startswith('[經文]') or t.startswith('[经文]'):
            chapters[cur]['jing'].append(t[4:].strip())
        elif t.startswith('[注解]'):
            chapters[cur]['zhu'].append(t[4:].strip())
    return chapters, order


# ---------- 参校本（宋徽宗御解） ----------
def parse_src(path):
    lines = open(path, encoding='utf-8').read().split('\n')
    title_re = re.compile(r'^(.{1,8}?)章第([%s]+)$' % CN)
    lone_re = re.compile(r'^[%s]+$' % CN)
    chapters = {}
    order = []
    cur = None
    for ln in lines:
        t = ln.strip()
        if not t:
            continue
        if t in ('道经上', '道经下', '德经上', '德经下', '上篇', '下篇'):
            continue
        m = title_re.match(t)
        if m:
            n = cn2int(m.group(2))
            if n is None:
                continue
            cur = n
            chapters[n] = {'title': t, 'head': m.group(1), 'paras': []}
            order.append(n)
            continue
        if lone_re.match(t):
            # 孤立数字噪声（原书页码/计数残留）
            continue
        if cur is not None:
            chapters[cur]['paras'].append(t)
    # 清洗现代广告文字（保留占位以免段序漂移）
    for n, ch in chapters.items():
        newp = []
        for p in ch['paras']:
            c, empty = clean_ad(p)
            newp.append('' if empty else c)
        ch['paras'] = newp
    return chapters, order


def lcs_ratio(a, b):
    """a 在 b 中的最长公共子串长度 / len(a)。"""
    if not a:
        return 0.0
    la, lb = len(a), len(b)
    prev = [0] * (lb + 1)
    best = 0
    for i in range(1, la + 1):
        cur = [0] * (lb + 1)
        ai = a[i - 1]
        for j in range(1, lb + 1):
            if ai == b[j - 1]:
                cur[j] = prev[j - 1] + 1
                if cur[j] > best:
                    best = cur[j]
        prev = cur
    return best / la


def coverage(a, b):
    """a 被 b 覆盖的比例（SequenceMatcher 匹配块总长 / len(a)），处理散在异文。"""
    if not a:
        return 0.0
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    m = sum(bl.size for bl in sm.get_matching_blocks())
    return m / len(a)


def classify_src(src_ch, base_ch, cov_th=0.60, chapter_no=None):
    """以底本经文为锚，逐段算覆盖度分类。返回 (labels, covs)。"""
    fb = fold(''.join(base_ch['jing']))
    labels = []
    covs = []
    for i, p in enumerate(src_ch['paras']):
        fp = fold(p)
        if not p.strip():
            labels.append('噪')
            covs.append(0.0)
            continue
        c = coverage(fp, fb)
        covs.append(c)
        lab = '经' if c >= cov_th else '注'
        ov = LABEL_OVERRIDE.get(chapter_no, {})
        if i in ov:
            lab = ov[i]
        labels.append(lab)
    return labels, covs


if __name__ == '__main__':
    base, border = parse_base('base_raw.txt')
    src, sorder = parse_src('src_raw.txt')
    print('底本章数:', len(base), '编号范围:', min(border), '-', max(border))
    print('参校本章数:', len(src), '编号范围:', min(sorder), '-', max(sorder))
    print('底本缺章:', sorted(set(range(1, 82)) - set(base)))
    print('参校本缺章:', sorted(set(range(1, 82)) - set(src)))
    print()
    # 逐章分类
    result = {}
    disagreements = []
    print('=== 经注分离结果校验 ===')
    for n in sorted(src):
        if n in base:
            labels, covs = classify_src(src[n], base[n], chapter_no=n)
        else:
            labels, covs = ['?'] * len(src[n]['paras']), [0.0] * len(src[n]['paras'])
        paras = src[n]['paras']
        jing = [p for p, l in zip(paras, labels) if l == '经']
        zhu = [p for p, l in zip(paras, labels) if l == '注']
        noise = sum(1 for l in labels if l == '噪')
        result[n] = {'title': src[n]['title'], 'head': src[n]['head'],
                     'jing': jing, 'zhu': zhu, 'paras': paras,
                     'labels': labels, 'covs': covs,
                     'base_jing': base[n]['jing'] if n in base else [],
                     'base_zhu': base[n]['zhu'] if n in base else []}
        # 校验：源本经文应覆盖底本经文
        if n in base:
            bj = fold(''.join(base[n]['jing']))
            sj = fold(''.join(jing))
            c1 = coverage(bj, sj)      # 底本经文被源本覆盖
            c2 = coverage(sj, bj)      # 源本经文被底本覆盖
            # 顺序校验
            pos, ok = -1, True
            for p in jing:
                fp = fold(p)
                if not fp:
                    continue
                sm = difflib.SequenceMatcher(None, fp, bj, autojunk=False)
                blks = [b for b in sm.get_matching_blocks() if b.size]
                st = blks[0].b if blks else -1
                if st < pos:
                    ok = False
                pos = max(pos, st)
            if c1 < 0.80 or c2 < 0.80 or not ok:
                print('  ch%-3d %-16s 覆盖底本%.2f 被覆盖%.2f 顺序%s' % (n, src[n]['title'], c1, c2, 'OK' if ok else '乱'))
        seq = ''.join('J' if l == '经' else ('Z' if l == '注' else '.') for l in labels)
        if noise:
            print('  ch%-3d %s 剔除噪声段 %d' % (n, src[n]['title'], noise))
    print()
    for n in sorted(result):
        v = result[n]
        print('ch%-3d 经%2d 注%2d  %s' % (n, len(v['jing']), len(v['zhu']), v['title']))
    print()
    tot_j = sum(len(v['jing']) for v in result.values())
    tot_z = sum(len(v['zhu']) for v in result.values())
    print('参校本 经段:', tot_j, ' 注段:', tot_z)
    nolabel = [(n, v['labels']) for n, v in result.items() if any(l == '?' for l in v['labels'])]
    print('含未定段章:', nolabel[:10])
    with open('parsed.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print('已写出 parsed.json')
