"""
Updated reading content converter v2.

Strategy: reading_answers.json is the source of truth for question numbers.
For each passage, we locate those question numbers in the markdown text and
extract surrounding context as the question prompt.
Also detects question type (MC, T/F/NG, fill-blank) from the markdown structure.
"""
import json, os, re, shutil

CONTENT_DIR = "/Users/eric/script/IELTS_practice/content/reading"
NEW_DIR = "/Users/eric/script/IELTS_practice/content/new_reading"

manifest = json.load(open(os.path.join(NEW_DIR, "manifest.json")))
answers_db = json.load(open(os.path.join(NEW_DIR, "reading_answers.json")))

if os.path.exists(CONTENT_DIR):
    shutil.rmtree(CONTENT_DIR)
os.makedirs(CONTENT_DIR, exist_ok=True)

def classify_choice(text):
    """Check if text looks like a multiple-choice or T/F/NG question."""
    text_upper = text.upper()
    if any(kw in text_upper for kw in ['TRUE', 'FALSE', 'NOT GIVEN']):
        return 'tfng'
    if re.search(r'\b[A-D]\s', text):
        return 'mc'
    return 'text'

def build_question(md, qnum, qnum_str, answer, section_info):
    """Build a question entry for a given question number."""
    # Search for the question number in the markdown
    # Try multiple patterns
    patterns = [
        re.compile(r'(?:^|\n)\s*' + re.escape(qnum_str) + r'\s+(.+)', re.MULTILINE),
        re.compile(r'(?:^|\n)\s*' + re.escape(qnum_str) + r'[\s ]+(.+)', re.MULTILINE),
        re.compile(r'\b' + re.escape(qnum_str) + r'\b'),
    ]

    prompt = f"Question {qnum}"
    q_type = 'text'

    for pattern in patterns:
        matches = list(pattern.finditer(md))
        for match in matches:
            pos = match.start()
            context = md[max(0, pos - 5):pos + 200].replace('\n', ' ').strip()
            # Skip if this is in a "Questions X-Y" header
            if re.match(r'Questions\s+\d+', context):
                continue

            if pattern is patterns[0] or pattern is patterns[1]:
                # Captured the text after the number
                raw_text = match.group(1).strip()
                # Clean up
                raw_text = re.sub(r'\s+', ' ', raw_text)
                prompt = raw_text[:250]
                q_type = classify_choice(raw_text)
                break
            elif pattern is patterns[2]:
                # Just found the number — use surrounding context
                start_pos = max(0, pos - 60)
                end_pos = min(len(md), pos + 180)
                context = md[start_pos:end_pos].replace('\n', ' ').strip()
                # Remove "Questions X-Y" preamble
                context = re.sub(r'Questions\s+\d+[–-]\d+.*?(?=\w{3,})', '', context)
                context = re.sub(r'\s+', ' ', context).strip()
                prompt = f"Complete: {context}"[:250]
                q_type = 'text'
                break

        if prompt != f"Question {qnum}":
            break

    choices = []
    # Extract choices if this is an MCQ
    if q_type == 'mc':
        choice_pattern = re.compile(r'\b([A-D])\s{2,}(.+?)(?=\s{2,}[A-D]\s|$)', re.DOTALL)
        for cm in choice_pattern.finditer(md):
            letter = cm.group(1)
            text = cm.group(2).strip()[:100]
            choices.append(f"{letter}. {text}")

    return {
        "id": f"q{qnum}",
        "number": qnum,
        "prompt": prompt,
        "choices": choices,
        "answer": str(answer).strip(),
        "type": q_type,
    }


idx = 0
for p in manifest["passages"]:
    book = p["book"]
    test = p["test"]
    passage_num = p["passage"]
    file = p["file"]

    md_path = os.path.join(NEW_DIR, file)
    if not os.path.exists(md_path):
        continue

    md_text = open(md_path, encoding='utf-8').read()

    # Title
    first_line = md_text.split('\n')[0].strip()
    title = re.sub(r'^READING\s+PASSAGE\s+\d+\s*', '', first_line).strip()
    if not title:
        title = f"{book} {test} passage {passage_num}"

    # Extract article (everything before first Questions)
    article = md_text
    first_q = md_text.find("Questions ")
    if first_q > 0:
        article = md_text[:first_q].strip()

    # Get answer key
    book_answers = answers_db.get(book, {}).get(test, {})
    part_key = f"part{passage_num}"
    answer_key = book_answers.get(part_key, {})

    # Find question sections for context
    q_pattern = re.compile(r'Questions\s+(\d+)[–-](\d+)\s*\n(.*?)(?=\nQuestions\s+\d|\nReading\b|\Z)', re.DOTALL)
    sections = list(q_pattern.finditer(md_text))

    # Build questions from answer_key (source of truth)
    questions = []
    for qnum_str, answer in sorted(answer_key.items(),
                                     key=lambda x: int(re.sub(r'[^0-9].*', '', x[0])) if x[0] and re.match(r'\d', x[0]) else 0):
        if '&' in qnum_str:
            for part in qnum_str.split('&'):
                part = part.strip()
                if part.isdigit():
                    questions.append(build_question(md_text, int(part), part, answer, sections))
            continue
        if not qnum_str.strip().isdigit():
            continue
        qnum = int(qnum_str)
        questions.append(build_question(md_text, qnum, qnum_str, answer, sections))

    # Fallback: parse from sections if no answer key
    if not questions and sections:
        for m in sections:
            start_q = int(m.group(1))
            end_q = int(m.group(2))
            body = m.group(3)
            for line in body.split('\n'):
                line = line.strip()
                qm = re.match(r'(\d+)\s+(.+)', line)
                if qm:
                    qnum = int(qm.group(1))
                    qtext = qm.group(2)[:250]
                    if start_q <= qnum <= end_q:
                        questions.append({
                            "id": f"q{qnum}",
                            "number": qnum,
                            "prompt": qtext,
                            "choices": [],
                            "answer": "",
                        })

    # Create directory
    idx += 1
    dir_name = f"passage-{idx:03d}"
    dir_path = os.path.join(CONTENT_DIR, dir_name)
    os.makedirs(dir_path, exist_ok=True)

    # Write passage.md
    with open(os.path.join(dir_path, "passage.md"), "w", encoding='utf-8') as f:
        f.write(article)

    # Write meta.json
    meta = {
        "id": f"reading-passage-{idx:03d}",
        "type": "reading",
        "title": f"{book.upper()} Test {test.replace('test','')} Passage {passage_num}: {title}",
        "pdf": None,
        "audio": None,
        "questions": [{
            "id": q["id"],
            "number": q["number"],
            "prompt": q["prompt"],
            "choices": q.get("choices", []),
            "answer": q.get("answer", ""),
        } for q in questions],
    }
    with open(os.path.join(dir_path, "meta.json"), "w", encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    has_ans = sum(1 for q in questions if q.get("answer"))
    print(f"[{idx:03d}] {file} → {dir_name}  questions={len(questions)}  with_answers={has_ans}")

print(f"\nDone. {idx} passages in {CONTENT_DIR}")
