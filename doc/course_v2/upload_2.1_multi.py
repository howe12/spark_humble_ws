#!/usr/bin/env python3.10
"""Upload 2.1 multi-model inference doc to Spark-实践版 folder."""
import os, sys, json, requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path.home() / '.hermes' / '.env')

r = requests.post('https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal',
    json={'app_id': os.environ['FEISHU_APP_ID'], 'app_secret': os.environ['FEISHU_APP_SECRET']})
token = r.json()['tenant_access_token']
headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

# Create doc in folder
folder_token = 'OSXCfteTLlrWQZdrhrkcTeycnnb'
r = requests.post('https://open.feishu.cn/open-apis/docx/v1/documents',
    headers=headers,
    json={'title': 'Spark实践版 - 2.1 垃圾分类多模型实时推理', 'folder_token': folder_token})
doc = r.json()
doc_id = doc['data']['document']['document_id']
print(f'✅ Doc created: {doc_id}')

# Convert markdown
sys.path.insert(0, '/home/spark/Music/spark_humble/doc/course_v2')
from md2feishu import md_to_blocks

md_path = '/home/spark/Music/spark_humble/doc/course_v2/2.1_multi_model_inference.md'
raw_blocks = md_to_blocks(Path(md_path).read_text())

# Filter unsupported blocks
blocks = []
for b in raw_blocks:
    bt = b.get('block_type')
    if bt == 42:  # divider → empty line
        blocks.append({'block_type': 2, 'text': {'elements': [{'text_run': {'content': ' '}}], 'style': {}}})
    elif bt == 34:  # quote → italic text
        elements = b['quote']['elements']
        for e in elements:
            if 'text_run' in e and 'text_element_style' not in e['text_run']:
                e['text_run']['text_element_style'] = {'italic': True}
            elif 'text_run' in e:
                e['text_run']['text_element_style']['italic'] = True
        blocks.append({'block_type': 2, 'text': {'elements': elements, 'style': {}}})
    else:
        blocks.append(b)

print(f'Blocks: {len(blocks)}')

# Write in chunks
chunk_size = 30
written = 0
for i in range(0, len(blocks), chunk_size):
    chunk = blocks[i:i + chunk_size]
    idx = i // chunk_size + 1
    r = requests.post(
        f'https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks/{doc_id}/children',
        headers=headers, json={'children': chunk, 'index': -1})
    resp = r.json()
    if resp.get('code') != 0:
        print(f'❌ Chunk {idx} FAILED: code={resp["code"]} msg={resp["msg"]}')
        # Debug: try one by one
        for j, b in enumerate(chunk):
            r2 = requests.post(
                f'https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks/{doc_id}/children',
                headers=headers, json={'children': [b], 'index': -1})
            if r2.json().get('code') != 0:
                print(f'  Bad block {i+j}: {json.dumps(b, ensure_ascii=False)[:150]}')
            else:
                written += 1
        break
    else:
        written += len(chunk)
        print(f'  ✅ Chunk {idx}: {written}/{len(blocks)}')

domain = os.environ.get('FEISHU_DOMAIN', 'my.feishu.cn')
print(f'\n📄 https://{domain}/docx/{doc_id}')
