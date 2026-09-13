# -*- coding: utf-8 -*-
"""直读 docx 的 word/document.xml，按段落抽取纯文本。"""
import zipfile, sys, os
from xml.etree import ElementTree as ET

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


def para_text(p):
    parts = []
    for node in p.iter():
        tag = node.tag
        if tag == W + 't':
            parts.append(node.text or '')
        elif tag == W + 'tab':
            parts.append('\t')
        elif tag in (W + 'br', W + 'cr'):
            parts.append('\n')
    return ''.join(parts)


def extract(path):
    z = zipfile.ZipFile(path)
    names = z.namelist()
    xml = z.read('word/document.xml')
    root = ET.fromstring(xml)
    out = []
    for p in root.iter(W + 'p'):
        out.append(para_text(p))
    return out


if __name__ == '__main__':
    src = sys.argv[1]
    dst = sys.argv[2]
    paras = extract(src)
    with open(dst, 'w', encoding='utf-8') as f:
        f.write('\n'.join(paras))
    nonempty = [x for x in paras if x.strip()]
    print('file:', os.path.basename(src))
    print('paragraphs total:', len(paras), ' nonempty:', len(nonempty))
    print('chars(nonempty joined):', sum(len(x) for x in nonempty))
    print('--- first 25 nonempty paragraphs ---')
    for i, x in enumerate(nonempty[:25]):
        print(i, repr(x[:120]))
