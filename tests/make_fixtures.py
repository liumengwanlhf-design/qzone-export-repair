# -*- coding: utf-8 -*-
"""生成完全合成的脱敏测试样例（无任何真实用户数据）"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIXDIR = os.path.join(HERE, 'fixtures')
os.makedirs(os.path.join(FIXDIR, 'pic'), exist_ok=True)

POSTS = []
for i in range(1, 4):
    POSTS.append(f'''
<div class="post">
    <div class="avatar"><img src="https://a1.qpic.cn/avatar_fake{i}.jpg"></div>
    <div class="nickname">示例用户tttttt示例用户</div>
    <div class="time">2025年6月10日 16:{i:02d}ttt</div>
    <div class="message">这是第{i}条合成说说\t内容含中文标点。ttt</div>
    <img class="content-img" src="https://photo.store.qq.com/qzpic/DEAD_{i}.jpg">
    <div class="comments">
        <div class="comment">
            <div class="nickname">评论者甲tttt</div>
            <div class="time">2025年6月11日 08:00</div>
            <div class="message">支持一下！</div>
        </div>
    </div>
</div>
''')

html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8"><title>合成导出样例</title></head>
<body>
<div id="container">{"".join(POSTS)}
<script>
// \u6d93烘墍鏈夊浘鐗囨坊鍔犵偣鍑讳簨浠?
var imgs = document.querySelectorAll(".content-img");
imgs.forEach(function(img){{
    // 鎵撳紑鍥剧墖閾炬帴骞跺湪鏂版爣绛鹃〉涓睍绀?
    img.addEventListener("click", function(){{ window.open(img.src); }});
}});
</script>
</body>
</html>'''

with open(os.path.join(FIXDIR, 'sample_export.html'), 'wb') as f:
    f.write(html.encode('utf-8'))

# 假图：只要扩展名和文件名参与映射逻辑，内容无所谓
with open(os.path.join(FIXDIR, 'pic', '示例用户__这是第2条合成说说_.jpg'), 'wb') as f:
    f.write(b'\xff\xd8\xff\xe0FAKE-JPEG-BYTES')
print('fixtures ready:', FIXDIR)
