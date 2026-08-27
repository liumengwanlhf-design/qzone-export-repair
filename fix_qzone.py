#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""fix_qzone.py -- 修复 GetQzonehistory 老版本导出的说说网页

解决三类历史遗留问题：
1. 文本去污：nickname/time/message 中成片的垃圾字符 'tttt...'
   （根因：导出工具曾把消息里 \t 转义的反斜杠删掉，残留字面量 t）
2. 图片本地化：将已失效的 QQ 远程图链替换为 pic/ 目录中的本地文件；
   完全没有本地图的图片替换为"图片已失效"占位图，并保留原始链接于
   data-original-src 属性中。
3. 乱码注释：脚本区被 GBK 错误转码的两条中文注释改回正常文本。

图片映射无需手工配置：脚本按命名约定自动扫描 pic/ 目录建立
"正文关键词 -> 本地文件" 映射（兼容 昵称__关键词_时间戳.jpg 等
GetQzonehistory 默认下载命名变体）。

用法：
  python fix_qzone.py <导出.html> [--pic <pic目录>] [--apply]
                      [--expect-posts <N>] [--quiet]

不带 --apply 时仅预演(dry-run)，打印将要做的改动；带 --apply 时校验通过
(<div> 开闭平衡且说说数量不变) 才写回，失败则拒绝写入。
"""
import argparse
import os
import re
import sys

MISS_PLACEHOLDER = (
    "data:image/svg+xml;charset=utf-8,%3Csvg%20xmlns='http://www.w3.org/"
    "2000/svg'%20width='300'%20height='200'%3E%3Crect%20width='100%25'"
    "%20height='100%25'%20fill='%23222'/%3E%3Ctext%20x='50%25'%20y='50%25'"
    "%20fill='%23888'%20font-size='15'%20text-anchor='middle'%3E"
    "%E5%9B%BE%E7%89%87%E5%B7%B2%E5%A4%B1%E6%95%88%3C/text%3E%3C/svg%3E"
)
# 老版本模板自带的 JS 注释被 GBK 转坏后的样子 -> 正确文本
FIX_COMMENTS = [
    ("// 涓烘墍鏈夊浘鐗囨坊鍔犵偣鍑讳簨浠?", "// 为所有图片添加点击事件"),
    ("// 鎵撳紑鍥剧墖閾炬帴骞跺湪鏂版爣绛鹃〉涓睍绀?", "// 打开图片链接并在新标签页中展示"),
]

T_RUN = re.compile(r"t{4,}")
MSG_DIV = re.compile(
    r'<div class="(nickname|time|message)">((?:(?!</div>).)*)(</div>)', re.S)
DEAD_SRC = re.compile(
    r'(?<![A-Za-z-])src="(https?://(?:a1\.qpic\.cn|[^"]*photo\.store\.qq\.com)[^"]*)"')
IMG_EXT = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp')


def derive_keys(stem):
    """从文件名(去扩展名)推断正文关键词候选，长候选在前"""
    s = stem.strip()
    tail = s.split('__', 1)[1] if '__' in s else s   # 惯例：前缀__正文[__时间戳]
    tail = re.sub(r'[_\-]?\d{9,}$', '', tail)        # 去程序附加的时间戳后缀
    pieces = [p for p in re.split(r'[_\-]+', tail) if p]
    out = []
    if len(pieces) > 1:
        out.append(''.join(pieces))
    out.extend(pieces)
    out.append(tail.replace('_', ''))
    seen, uniq = set(), []
    for k in out:
        k = k.strip()
        if len(k) >= 4 and k not in seen:            # 过短词条误伤率高
            seen.add(k)
            uniq.append(k)
    uniq.sort(key=len, reverse=True)
    return uniq


def build_pic_index(pic_dir):
    """扫描 pic 目录 -> (全部关键词候选集合, 关键词->[文件名,...] 保持顺序)"""
    if not os.path.isdir(pic_dir):
        return set(), {}
    cands, table = set(), {}
    for name in sorted(os.listdir(pic_dir)):
        stem, ext = os.path.splitext(name)
        if ext.lower() not in IMG_EXT:
            continue
        for k in derive_keys(stem):
            table.setdefault(k, []).append(name)
            cands.add(k)
    return cands, table


def detect_key(cands, window):
    """取窗口中位置最靠后的命中（离当前图片最近，避免串到上一条说说）；
    同一位置取更长的词"""
    best, best_pos = None, -1
    for k in sorted(cands, key=len, reverse=True):
        p = window.rfind(k)
        if p > best_pos or (p == best_pos and best is not None and len(k) > len(best)):
            best_pos, best = p, k
    return best


def clean_t_runes(text):
    """清除 nickname/time/message 节点内的连续 t 残留"""
    counter = {'nodes': 0}

    def _sub(m):
        cls, inner, close = m.groups()
        counter['nodes'] += 1
        if not T_RUN.search(inner):
            return m.group()
        inner = re.sub(r"[ \u3000]*t{4,}", "", inner)
        inner = re.sub(r"\s+t\s*(?=</|$)", "", inner, flags=re.M)
        return f'<div class="{cls}">{inner}{close}'

    return MSG_DIV.sub(_sub, text), counter['nodes']


def localize_images(text, cands, table, pic_rel):
    """失效远程图 -> 本地文件；无可用本地图时用占位图并保留原链接"""
    files_of_key = {k: list(v) for k, v in table.items()}
    tags = list(DEAD_SRC.finditer(text))
    stat = {'total': len(tags), 'local': 0, 'miss': []}
    edits = []
    for m in tags:
        window = text[max(0, m.start() - 800):m.start()]
        key = detect_key(cands, window)
        pool = files_of_key.get(key) if key else None
        fname = pool.pop(0) if pool else None
        if fname:
            src_attr = f"{pic_rel}/{fname}"
            stat['local'] += 1
        else:
            src_attr = MISS_PLACEHOLDER
            line_no = text[:m.start()].count("\n") + 1
            note = "[占位] 图片已失效"
            if key:
                note += f"（关键词「{key}」本地无剩余对应文件）"
            stat['miss'].append((line_no, note))
        new_tag = f'src="{src_attr}" data-original-src="{m.group(1)}"'
        edits.append((m.span(1), new_tag))
    for (a, b), rep in reversed(edits):
        text = text[:a] + rep + text[b:]
    return text, stat


def fix_mojibake_comments(text):
    hits = []
    for bad, good in FIX_COMMENTS:
        if bad in text:
            text = text.replace(bad, good)
            hits.append(good)
    return text, hits


def count_posts(text):
    return len(re.findall(r'<div class="post">', text))


def div_balance(text):
    return len(re.findall(r"<div\b", text)), len(re.findall(r"</div>", text))


def repair_structure(text, nl="\n"):
    """在每条新说说起始处补齐上一条遗留的未闭合 </div>（兼容坏旧导出）；
    返回 (新文本, 插入数量)"""
    struct_re = re.compile(r'<div\b[^>]*>|</div>')
    insertions = []
    depth = 0
    for m in struct_re.finditer(text):
        tok = m.group()
        if tok.startswith("</"):
            depth -= 1
        elif tok.startswith('<div class="post"'):
            if depth > 0:
                for _ in range(depth):
                    insertions.append((m.start(), "</div>" + nl + "    "))
                depth = 0
            depth += 1
        else:
            depth += 1
    tail_anchor = text.rfind("<script>")
    if depth > 0:
        if tail_anchor == -1:
            tail_anchor = len(text)
        for _ in range(depth):
            insertions.append((tail_anchor, "</div>" + nl))
    fixed = 0
    for pos, s in sorted(insertions, reverse=True):
        text = text[:pos] + s + text[pos:]
        fixed += 1
    return text, fixed


def main(argv=None):
    ap = argparse.ArgumentParser(description="修复 GetQzonehistory 老版本导出网页")
    ap.add_argument("html", help="待修复的说说网页 html 路径")
    ap.add_argument("--pic", default=None, help="本地图片目录(默认 html 同级 pic/)")
    ap.add_argument("--apply", action="store_true", help="实际写回文件")
    ap.add_argument("--expect-posts", type=int, default=None,
                    help="期望说说数量(默认自动取修复前数量)")
    ap.add_argument("--quiet", action="store_true", help="精简输出")
    args = ap.parse_args(argv)

    html_path = os.path.abspath(args.html)
    if not os.path.isfile(html_path):
        print(f"[错误] 文件不存在: {html_path}", file=sys.stderr)
        return 2
    pic_dir = (os.path.abspath(args.pic) if args.pic
               else os.path.join(os.path.dirname(html_path), "pic"))

    raw = open(html_path, "rb").read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as e:
        print(f"[错误] 文件不是 UTF-8 编码: {e}", file=sys.stderr)
        return 2

    logs = []
    nl = "\r\n" if raw.count(b"\r\n") >= raw.count(b"\n") else "\n"
    opens0, closes0 = div_balance(text)
    if opens0 > closes0:                      # 老版工具导出的常见缺陷，自动补齐
        text, n_ins = repair_structure(text, nl)
        logs.append(f"[结构] 自动补齐 {n_ins} 个缺失的 </div>")
    elif closes0 > opens0:
        print("[错误] 多余的 </div>，疑似已损坏或非目标文件，拒绝处理。",
              file=sys.stderr)
        return 2

    posts_before = count_posts(text)
    expect = args.expect_posts or posts_before

    cands, table = build_pic_index(pic_dir)
    text, nodes = clean_t_runes(text)
    logs.append(f"[去污] 扫描节点 {nodes} 个")
    text, stat = localize_images(text, cands, table, os.path.basename(pic_dir))
    logs.append(f"[图片] 失效远程图 {stat['total']} 张 -> 本地化 {stat['local']} / 占位 {len(stat['miss'])}")
    for ln, note in stat['miss']:
        logs.append(f"       {note} (@{ln} 行)")
    text, fixed = fix_mojibake_comments(text)
    for good in fixed:
        logs.append(f"[注释] 已恢复: {good}")

    posts_after = count_posts(text)
    opens, closes = div_balance(text)
    ok = (opens == closes) and (posts_after == expect)

    print("=" * 60)
    if not args.quiet:
        print(f"图片索引 : 自动建立 {len(table)} 个关键词候选 "
              f"(pic 目录{'存在' if os.path.isdir(pic_dir) else '缺失'})")
        print(f"修复前   : {posts_before} 条说说, <div> {opens0}开/{closes0}闭")
    for line in logs:
        print(line)
    print("-" * 60)
    print(f"说说数量 : {posts_after} (期望 {expect}) {'✅' if posts_after == expect else '❌'}")
    print(f"div 平衡 : {opens}开/{closes}闭 {'✅' if opens == closes else '❌'}")

    if args.apply:
        if ok:
            with open(html_path, "wb") as f:
                f.write(text.encode("utf-8"))
            print("\n✅ 已写回 (--apply)")
            return 0
        print("\n❌ 校验未通过，拒绝写入。")
        return 1
    print("\n(dry-run 未写入。确认后追加 --apply 生效)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

