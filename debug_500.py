#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'backend')
from pathlib import Path

# Check content paths
print('=== Content paths ===')
for p in ['content', 'content/PDF_new', 'content/PDF_new/Reading/test001']:
    pp = Path(p)
    print(f'{p}: exists={pp.is_dir()}')

# Test the actual load_answer_key execution
from app.services.content_scanner import load_answer_key, _content_root
root = _content_root('reading')
print(f'Content root: {root}')
td = root / 'Reading' / 'test001'
print(f'Test dir exists: {td.is_dir()}')
pas = td / 'passage1_answers.json'
print(f'Answers JSON exists: {pas.is_file()}')
if pas.is_file():
    print(f'Size: {pas.stat().st_size}')

key = load_answer_key('_flat_', 'test001', 'reading', passage='passage1')
print(f'Key result: {key is not None}')
if key:
    print(f'Key entries: {len(key)}')
    items = list(key.items())[:3]
    print(f'First items: {items}')

# Now test grade_answers
from app.services.answer_normalizer import grade_answers
answers = {"1": "B", "2": "interdisciplinary"}
correct, total, graded = grade_answers(answers, key)
print(f'Grading: {correct}/{total}')
for r in graded:
    print(f'  {r}')
