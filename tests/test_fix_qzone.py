# -*- coding: utf-8 -*-
"""端到端验证 fix_qzone.py 在合成样例上的行为（退出码断言）"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FIXTURE_HTML = os.path.join(HERE, 'fixtures', 'sample_export.html')


def read(p):
    return open(p, 'rb').read().decode('utf-8')


def run(cmd):
    r = subprocess.run([sys.executable] + cmd,
                       capture_output=True, text=True,
                       encoding='utf-8', errors='replace', cwd=ROOT)
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def expect(cond, msg):
    print(('PASS  ' if cond else 'FAIL  ') + msg)
    if not cond:
        sys.exit(1)


def main():
    # 1) dry-run 不落盘
    code, out = run(['fix_qzone.py', FIXTURE_HTML])
    expect(code == 0 and 'dry-run' in out, 'dry-run 正常退出且未写入')

    # 2) apply 到临时副本
    tmpdir = tempfile.mkdtemp(prefix='fqz_test_')
    work_html = os.path.join(tmpdir, 'sample_export.html')
    shutil.copy(FIXTURE_HTML, work_html)
    shutil.copytree(os.path.join(HERE, 'fixtures', 'pic'),
                    os.path.join(tmpdir, 'pic'))
    code, out = run(['fix_qzone.py', work_html, '--apply'])
    expect(code == 0, '--apply 校验通过并写回')
    txt = read(work_html)

    # 3) t 污染清除
    import re
    dirty_zones = re.findall(
        r'class="(?:nickname|time|message)">([^<]*)<', txt)
    bad = [z for z in dirty_zones if re.search(r't{4,}', z)]
    expect(not bad, 'nickname/time/message 无 t{4,} 残留 ' + repr(bad))

    # 4) 可命中的图被本地化、原链接保留在 data-original-src
    expect('pic/示例用户__这是第2条合成说说_.jpg' in txt, '命中关键词的本地图已引用')
    expect('data-original-src="https://photo.store.qq.com/qzpic/DEAD_2.jpg"' in txt,
           '原始失效链接保留于 data-original-src')

    # 5) 未命中的两张替换为占位 data URI
    expect(txt.count('data:image/svg+xml') >= 2, '未命中图片已占位(x2)')

    # 6) 结构完好
    expect(len(re.findall(r'<div\b', txt)) == len(re.findall(r'</div>', txt)),
           'div 开闭平衡保持')
    expect(len(re.findall(r'<div class="post">', txt)) == 3, '3 条说说数量不变')

    # 7) 乱码注释被修复
    expect('为所有图片添加点击事件' in txt, 'GBK 注释已还原')

    shutil.rmtree(tmpdir)
    print('\n全部通过 ✅')


if __name__ == '__main__':
    main()
