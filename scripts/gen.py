# -*- coding: utf-8 -*-
"""生成：校订本 Markdown、逐章校记 Markdown、校本异文对比报告 HTML。"""
import json, html, re
import zhconv

D = json.load(open('parsed.json', encoding='utf-8'))
DIFFS = json.load(open('diffs.json', encoding='utf-8'))
MARKS = json.load(open('marks.json', encoding='utf-8'))

CN = '〇一二三四五六七八九十'


def cn_num(n):
    if n <= 10:
        return CN[n]
    if n < 20:
        return '十' + CN[n % 10]
    a, b = divmod(n, 10)
    return CN[a] + '十' + (CN[b] if b else '')


def simp(s):
    return zhconv.convert(s, 'zh-cn')


def norm_punct(s):
    return (s.replace('﹖', '？').replace('﹔', '；').replace('﹕', '：')
             .replace('﹗', '！').replace('﹑', '、'))


# 特识（须具说者，人工裁断）
SPECIAL = {
    '4': ['源本此章末羼入現代廣告文字一段，非宋徽宗文，已剔除。'],
    '14': ['源本經文作「繩繩兮不可名，復歸於無物。故復歸於無物。」，其下句與上句重出，文義不屬；底本此處作「是謂無狀之狀，無物之象，是謂惚恍」。源本注文正引「是謂无状之状，无物之象，是谓恍惚」，可證源本此句當是涉上句「復歸於無物」而誤複，奪去「是謂無狀之狀，無物之象，是謂惚恍」一句。（疑案）',
             '源本「传之不得名曰微」，「传」當為「搏」之形訛，底本正作「搏之不得」。'],
    '23': ['源本「而瓦於人乎」，「瓦」當為「況」之形訛，底本正作「而況於人乎」。',
           '底本三處並有「樂」字（道亦樂得之、德亦樂得之、失亦樂得之），源本三處皆無。'],
    '31': ['源本「故有道者不處。另外而非難是以君子居則貴左」，中「另外而非難是以」七字文義不屬，底本無之，當係源本羼入之訛文。',
           '底本「勝而不美，而美之者，是樂殺人」，源本作「恬淡為上故不美也。若美必樂之。樂之者，是樂殺人也」；底本「偏將軍居左，上將軍居右」，源本作「偏将军处左，上将军处右」——此章源本經文羼入注語氣甚多，兩本分句大異。'],
    '32': ['底本「樸雖小，天下莫能臣也」，源本作「朴雖小，天下莫能臣」，脫「也」字。',
           '源本「譬道之在天下，由川各之与江海也」，底本作「譬道之在天下，猶川谷之於江海」：「由」通「猶」；「川各」當為「川谷」之形訛。'],
    '39': ['底本「侯王得一以為天下貞」，源本作「王侯得一以为天下正」：既倒（侯王／王侯）且異（貞／正）。',
           '源本此章末羼入現代廣告文字一段，已剔除。'],
    '41': ['底本「明道若昧，進道若退，夷道若纇」，源本作「明道若昧，夷道若颣，進道若退」：二句互倒。',
           '「纇」源本作「颣」，異體字。'],
    '51': ['底本「是以萬物莫不尊道而貴德」一句，源本不別出為經文，而羼入其下注文之首（源本注：「其勢然也。是以萬物莫不尊道而貴德。萬物莫不首之者，道也……」）。或源本羼經入注，或源本此章經文原無此句，兩存待考。'],
    '59': ['底本「是謂深根固柢，長生久視之道」一句，源本經文無之，而見於源本注文之首（「道為萬物母，有道者萬世無弊。是謂深根固柢，長生久視之道」）。羼經入注之例，與第五十一章同，兩存待考。'],
    '66': ['底本「以其不爭，故天下莫能與之爭」一句，源本經文無之，而見於源本注文之末（「《易》曰：百姓與能。以其不爭，故天下莫能與之爭」）。羼經入注之例，與第五十一、五十九章同。'],
    '67': ['底本「我有三寶，持而保之」，源本作「我有三寶，寶而持之」：既倒（持而保之／寶而持之）且異（保／寶）。'],
    '76': ['底本「萬物草木之生也柔脆」，源本作「草木之生也柔脆」，脫「萬物」二字。',
           '底本「木強則兵」，源本作「木強則共」（王弼本作「兵」，河上公系本作「共」，異文）；底本「強大處下」，源本作「故堅強居下」。'],
    '78': ['底本「弱之勝強，柔之勝剛」，源本作「柔之勝剛，弱之勝強」：二句互倒。',
           '底本「而攻堅強者莫之能勝」，源本作「而攻堅強者，莫之能先」。'],
}

STAT = {'异文': 0, '脱文': 0, '衍文': 0, '倒文': 0}
for n in range(1, 82):
    for x in DIFFS[str(n)]:
        STAT[x['type']] += 1          # 校记条目数
SAME_CH = [n for n in range(1, 82) if not DIFFS[str(n)]]
DIFF_CH = [n for n in range(1, 82) if DIFFS[str(n)]]
RAW_TOTAL = {'异文': 0, '脱文': 0, '衍文': 0, '倒文': 0}
for n in range(1, 82):
    for x in DIFFS[str(n)]:
        RAW_TOTAL[x['type']] += x['n']  # 逐处出现次数


_P = set('，。；：！？、﹖﹔﹕﹗　 ')


def _np(s):
    return ''.join(c for c in s if c not in _P)


def diff_lines(n):
    out = []
    for x in DIFFS[str(n)]:
        if x['type'] == '异文':
            out.append('異文：底本「%s」，源本作「%s」。' % (x['base'], x['src']))
        elif x['type'] == '脱文':
            if _np(x['base']) == _np(x['core']):
                out.append('脫文：源本無「%s」（底本有）。' % x['core'])
            elif x['n'] > 1:
                out.append('脫文：源本凡 %d 處無「%s」字（底本有）。' % (x['n'], x['core']))
            else:
                out.append('脫文：底本「%s」，源本無「%s」。' % (x['base'], x['core']))
        elif x['type'] == '衍文':
            if _np(x['src']) == _np(x['core']):
                out.append('衍文：源本增「%s」（底本無）。' % x['core'])
            elif x['n'] > 1:
                out.append('衍文：源本凡 %d 處增「%s」字（底本無）。' % (x['n'], x['core']))
            else:
                out.append('衍文：源本「%s」，底本無「%s」。' % (x['src'], x['core']))
        else:
            out.append('倒文：底本「%s」，源本作「%s」。' % (x['base'], x['src']))
    for s in SPECIAL.get(str(n), []):
        out.append('特識：' + s)
    return out


def render_chapter_md(n, heading_level=3):
    v = D[str(n)]
    bj = norm_punct(''.join(v['base_jing']))
    zhu = [p for p in v['zhu'] if p.strip()]
    lines = []
    lines.append('%s 第%s章' % ('#' * heading_level, cn_num(n)))
    lines.append('')
    lines.append('**【經文（校訂）】**　%s' % simp(bj))
    lines.append('')
    if zhu:
        lines.append('**【原注】**　%s' % ''.join(zhu))
    else:
        lines.append('**【原注】**　（源本此章無注）')
    lines.append('')
    ds = diff_lines(n)
    if ds:
        lines.append('**【校記】**')
        for d in ds:
            lines.append('- %s' % d)
    else:
        lines.append('**【校記】**　本章底本與源本經文全同。')
    lines.append('')
    return '\n'.join(lines)


# ---------- 校订本 ----------
head = []
head.append('# 《老子道德經》校訂本')
head.append('')
head.append('> 底本：《老子道德經王弼注精校》　參校本：《宋徽宗御解道德真經》')
head.append('')
head.append('## 校勘說明')
head.append('')
head.append('### 一、底本與參校本')
head.append('')
head.append('- **底本**：《老子道德經王弼注精校》（繁體；原書以「[經文]」「[注解]」標識經注，八十一章完具）。')
head.append('- **參校本**：《宋徽宗御解道德真經》（簡體；北宋徽宗御解，分道經、德經，八十一章）。')
head.append('')
head.append('### 二、凡例')
head.append('')
head.append('一、經文依底本讀，轉寫為簡體並施標點；凡底本與源本文字之異，悉記於【校記】，不輕改底本一字（存真原則）。')
head.append('二、源本注文（宋徽宗御解）照錄其舊，僅剔今人羼入之廣告文字，不改一字。')
head.append('三、繁體／簡體、異體之異形僅用於比對折合，不作校改依據（異體摺疊不改原文）。')
head.append('四、校記分五目：**異文**（底本作某、源本作某）、**脫文**（源本脫）、**衍文**（源本衍）、**倒文**（字序互乙）、**特識**（須具說者）。')
head.append('五、源本正文夾有現代廣告文字十二處（十處附於注文之末，二處獨立成段），概屬今人羼入，已一律剔除，不出校記。')
head.append('六、源本或羼經入注（見第五十一、五十九、六十六章特識），凡不能定者兩存待考，不強作說通（多聞闕疑）。')
head.append('')
head.append('### 三、所用校法（方法棧）')
head.append('')
head.append('**對校**（逐章字元級序列對齊，錄兩本經文全部異同，不判是非）→ **本校**（以底本經文為錨，分判源本之經與注；以源本前後文例互證）→ **他校**（以源本自注所引經句、源本注文之引書相證）→ **理校**（形近致訛、涉上而誤複之類，必另有旁證方下斷語）。')
head.append('')
head.append('### 四、校勘統計')
head.append('')
head.append('- 全書八十一章。**經文有異者 %d 章；經文全同者 %d 章**（%s）。' % (
    len(DIFF_CH), len(SAME_CH), '、'.join('第%s章' % cn_num(n) for n in SAME_CH)))
head.append('- 校記條目：**異文 %d 條、脫文 %d 條、衍文 %d 條、倒文 %d 條，合 %d 條**（同文重出者已歸併）；若以逐處計，兩本經文相異凡 %d 處。' % (
    STAT['异文'], STAT['脱文'], STAT['衍文'], STAT['倒文'], sum(STAT.values()), sum(RAW_TOTAL.values())))
head.append('- 避諱改字：底本、源本經文均未見實例（《道德經》正文無宋、清諱改之跡），依「諱字表僅供參照、必以正文實有實例為準」之例，不列諱例。')
head.append('')
head.append('---')
head.append('')
head.append('## 上篇　道經（第一至三十七章）')
head.append('')
for n in range(1, 38):
    head.append(render_chapter_md(n))
head.append('---')
head.append('')
head.append('## 下篇　德經（第三十八至八十一章）')
head.append('')
for n in range(38, 82):
    head.append(render_chapter_md(n))

md = '\n'.join(head)
open('老子道德經校訂本.md', 'w', encoding='utf-8').write(md)
print('校订本 md 字数:', len(md))

# ---------- 逐章校记 ----------
jk = ['# 《老子道德經》逐章校記', '',
      '> 底本：《老子道德經王弼注精校》　參校本：《宋徽宗御解道德真經》', '',
      '校記分異文／脫文／衍文／倒文／特識五目。凡異文，均作「底本『A』，源本作『B』」；脫文記源本所無，衍文記源本所增，倒文記字序互乙。', '']
for n in range(1, 82):
    ds = diff_lines(n)
    jk.append('## 第%s章' % cn_num(n))
    jk.append('')
    if ds:
        for d in ds:
            jk.append('- %s' % d)
    else:
        jk.append('- 本章底本與源本經文全同。')
    jk.append('')
open('逐章校記.md', 'w', encoding='utf-8').write('\n'.join(jk))
print('逐章校记 md 字数:', len('\n'.join(jk)))

# ---------- 对比报告 HTML ----------
COLOR = {'异文': 'r', '脱文': 'd', '衍文': 'y', '倒文': 'p'}


def hl(text, marks, side, clsmap):
    """在 text 上按 marks 插入高亮 span；side: 'b' 或 's'。"""
    segs = []
    for m in marks:
        rng = m[side]
        if rng:
            segs.append((rng[0], rng[1], clsmap.get(m['type'], 'r'), m['type']))
    if not segs:
        return html.escape(text)
    segs.sort()
    out, pos = [], 0
    for s, e, cls, typ in segs:
        if s < pos:
            continue
        out.append(html.escape(text[pos:s]))
        inner = html.escape(text[s:e])
        if typ == '脱文':
            inner = '〔脫〕' + inner
        if typ == '衍文':
            inner = '〔衍〕' + inner
        out.append('<span class="%s">%s</span>' % (cls, inner))
        pos = e
    out.append(html.escape(text[pos:]))
    return ''.join(out)


rows2 = []
for n in range(1, 82):
    v = D[str(n)]
    bj = norm_punct(''.join(v['base_jing']))
    sj = ''.join(v['jing'])
    mk = MARKS[str(n)]
    ds = diff_lines(n)
    rows2.append('<section class="ch" id="c%d">' % n)
    rows2.append('<h3>第%s章 <span class="st">源本題「%s」</span></h3>' % (cn_num(n), html.escape(v['title'])))
    rows2.append('<table class="cmp"><thead><tr><th>底本（王弼本）</th><th>參校本（宋徽宗本）</th></tr></thead><tbody><tr>')
    rows2.append('<td class="base">%s</td>' % hl(bj, mk, 'b', COLOR))
    rows2.append('<td class="src">%s</td>' % hl(sj, mk, 's', COLOR))
    rows2.append('</tr></tbody></table>')
    if ds:
        rows2.append('<div class="note"><b>校記</b><ul>%s</ul></div>' % ''.join('<li>%s</li>' % html.escape(d) for d in ds))
    else:
        rows2.append('<div class="note same"><b>校記</b>　本章底本與源本經文全同。</div>')
    rows2.append('</section>')

CSS = '''<!DOCTYPE html>
<html lang="zh-Hans"><head><meta charset="utf-8">
<title>《老子道德經》校本異文對比報告</title>
<style>
:root{--ink:#1f2328;--sub:#5b6470;--line:#e3e6ea;--bg:#fbfcfd;--card:#fff;
--r:#c0392b;--y:#c47f17;--d:#1f6feb;--p:#7b3fa0;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
font-family:"Source Han Serif SC","Noto Serif CJK SC","Songti SC",serif;line-height:1.9}
header{background:#fff;border-bottom:1px solid var(--line);padding:34px 40px 26px}
h1{margin:0 0 8px;font-size:26px;letter-spacing:.06em}
.sub{color:var(--sub);font-size:14px}
.legend{margin-top:16px;font-size:13px;color:var(--sub)}
.legend span{display:inline-block;margin-right:16px}
.k{padding:0 4px;border-radius:3px}
.k.r{color:var(--r);border-bottom:2px solid var(--r)}
.k.y{color:var(--y);border-bottom:2px solid var(--y)}
.k.d{color:var(--d);border-bottom:2px dashed var(--d)}
.k.p{color:var(--p);border-bottom:2px dotted var(--p)}
main{max-width:1180px;margin:0 auto;padding:26px 40px 80px}
.toc{background:#fff;border:1px solid var(--line);border-radius:10px;padding:18px 22px;margin-bottom:26px;font-size:14px}
.toc a{color:#1f6feb;text-decoration:none;margin-right:10px;display:inline-block}
section.ch{background:var(--card);border:1px solid var(--line);border-radius:12px;
padding:18px 22px 14px;margin:0 0 18px}
section.ch h3{margin:0 0 12px;font-size:17px;letter-spacing:.04em}
.st{font-size:12px;color:var(--sub);font-weight:400;margin-left:8px}
table.cmp{width:100%;border-collapse:collapse;font-size:15.5px}
table.cmp th{width:50%;text-align:left;font-size:12.5px;color:var(--sub);font-weight:600;
border-bottom:1px solid var(--line);padding:5px 10px;background:#f7f9fb}
table.cmp td{vertical-align:top;padding:10px;border-bottom:1px solid var(--line);
border-right:1px solid var(--line)}
table.cmp td:last-child{border-right:none}
td.base{font-size:15.5px}
td.src{font-size:15px;color:#2b3138}
.r{color:var(--r);background:#fdf0ee;border-bottom:1px solid #f0c8c2;border-radius:2px}
.y{color:var(--y);background:#fdf6e8;border-bottom:1px solid #f0dcae;border-radius:2px}
.d{color:var(--d);background:#eef4fe;border-bottom:1px dashed #b9d2fb;border-radius:2px}
.p{color:var(--p);background:#f7f0fb;border-bottom:1px dotted #d9c2ea;border-radius:2px}
.note{margin-top:10px;font-size:14px;background:#f7f9fb;border-left:3px solid #c9d3de;
border-radius:0 8px 8px 0;padding:8px 14px}
.note ul{margin:6px 0 2px;padding-left:20px}
.note li{margin:3px 0}
.note.same{color:var(--sub)}
footer{color:var(--sub);font-size:13px;text-align:center;padding:30px}
</style></head><body>
<header>
<h1>《老子道德經》校本異文對比報告</h1>
<div class="sub">底本：《老子道德經王弼注精校》　參校本：《宋徽宗御解道德真經》　全八十一章</div>
<div class="legend">
<span><b class="k r">紅色</b> 異文</span><span><b class="k y">橙色</b> 衍文（源本增）</span>
<span><b class="k d">藍色</b> 脫文（源本脫）</span><span><b class="k p">紫色</b> 倒文（字序互乙）</span>
</div>
</header>
<main>
<div class="toc"><b>章次導覽：</b>'''

TAIL = '''</main>
<footer>共校出異文 %d、脫文 %d、衍文 %d、倒文 %d 條；有異之章 %d／81。</footer>
</body></html>''' % (STAT['异文'], STAT['脱文'], STAT['衍文'], STAT['倒文'],
                    sum(1 for n in range(1, 82) if DIFFS[str(n)]))

html_doc = (CSS
            + ' '.join('<a href="#c%d">%d</a>' % (n, n) for n in range(1, 82))
            + '</div>\n' + '\n'.join(rows2) + '\n' + TAIL)
open('校本異文對比報告.html', 'w', encoding='utf-8').write(html_doc)
print('对比报告 html 字数:', len(html_doc))
