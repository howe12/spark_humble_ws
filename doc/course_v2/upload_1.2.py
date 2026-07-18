#!/usr/bin/env python3.10
"""Upload 1.2 data analysis document to Feishu — with chunk debugging."""
import os, sys, json, requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path.home() / '.hermes' / '.env')

APP_ID=os.environ['FEISHU_APP_ID']
APP_SECRET=os.environ['FEISHU_APP_SECRET']

r = requests.post('https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal',
    json={'app_id': APP_ID, 'app_secret': APP_SECRET})
token = r.json()['tenant_access_token']
headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

sys.path.insert(0, '/home/spark/Music/spark_humble/doc/course_v2')
from md2feishu import md_to_blocks

md_path = '/home/spark/Music/spark_humble/doc/course_v2/1.2_data_analysis.md'
raw_blocks = md_to_blocks(Path(md_path).read_text())

# Filter unsupported block types: divider(42) and quote(34) not accepted by docx API
# Convert dividers to empty paragraphs, quotes to italic text
blocks = []
for b in raw_blocks:
    bt = b.get('block_type')
    if bt == 42:  # divider → skip (add empty line instead)
        blocks.append({'block_type': 2, 'text': {
            'elements': [{'text_run': {'content': ' '}}], 'style': {}}})
    elif bt == 34:  # quote → convert to italic text
        elements = b['quote']['elements']
        for e in elements:
            if 'text_run' in e and 'text_element_style' not in e['text_run']:
                e['text_run']['text_element_style'] = {'italic': True}
            elif 'text_run' in e:
                e['text_run']['text_element_style']['italic'] = True
        blocks.append({'block_type': 2, 'text': {
            'elements': elements, 'style': {}}})
    else:
        blocks.append(b)

print(f'Total blocks: {len(blocks)} (filtered from {len(raw_blocks)})')

# Create fresh document
r = requests.post('https://open.feishu.cn/open-apis/docx/v1/documents',
    headers=headers, json={'title': '1.2 数据分析 — 传感器数据加载、清洗与可视化'})
doc_id = r.json()['data']['document']['document_id']
domain = os.environ.get('FEISHU_DOMAIN', 'my.feishu.cn')
print(f'Doc: https://{domain}/docx/{doc_id}')

# Write in chunks of 20
chunk_size = 20
written = 0
for i in range(0, len(blocks), chunk_size):
    chunk = blocks[i:i + chunk_size]
    idx = i // chunk_size + 1
    r = requests.post(
        f'https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks/{doc_id}/children',
        headers=headers, json={'children': chunk, 'index': -1})
    resp = r.json()
    if resp.get('code') != 0:
        print(f'❌ Chunk {idx} FAILED (blocks {i}-{i+len(chunk)-1}): code={resp["code"]} msg={resp["msg"]}')
        # Try one by one to find the bad block
        for j, b in enumerate(chunk):
            r2 = requests.post(
                f'https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks/{doc_id}/children',
                headers=headers, json={'children': [b], 'index': -1})
            resp2 = r2.json()
            if resp2.get('code') != 0:
                print(f'  ❌ Block {i+j} bad: {json.dumps(b, ensure_ascii=False)[:200]}')
                print(f'     Error: code={resp2["code"]} msg={resp2["msg"]}')
            else:
                written += 1
        break
    else:
        written += len(chunk)
        print(f'  ✅ Chunk {idx}: {written}/{len(blocks)}')

print(f'\nDone: {written}/{len(blocks)} blocks')
print(f'📄 https://{domain}/docx/{doc_id}')
