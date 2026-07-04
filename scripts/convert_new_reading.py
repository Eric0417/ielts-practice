"""
Convert new_reading/*.md + reading_answers.json → content/reading/passage-NN/meta.json

Reads manifest.json for the passage list, reads each .md file, extracts
questions from it, and pairs with answers from reading_answers.json.
"""
import json, os, re

CONTENT_DIR = "/Users/eric/script/IELTS_practice/content/reading"
NEW_DIR = "/Users/eric/script/IELTS_practice/content/new_reading"

manifest = json.load(open(os.path.join(NEW_DIR, "manifest.json")))
answers_db = json.load(open(os.path.join(NEW_DIR, "reading_answers.json")))

# Clear old reading content
import shutil
if os.path.exists(CONTENT_DIR):
    shutil.rmtree(CONTENT_DIR)
os.makedirs(CONTENT_DIR, exist_ok=True)

idx = 0
for p in manifest["passages"]:
    book = p["book"]          # e.g. "cambridge04"
    test = p["test"]          # e.g. "test1"
    passage_num = p["passage"] # e.g. "1"
    file = p["file"]

    md_path = os.path.join(NEW_DIR, file)
    if not os.path.exists(md_path):
        print(f"SKIP: {file} not found")
        continue

    md_text = open(md_path).read()

    # Extract title from first line
    first_line = md_text.split('\n')[0].strip()
    # Remove leading 'READING PASSAGE X' prefix if present
    title = re.sub(r'^READING\s+PASSAGE\s+\d+\s*', '', first_line).strip()
    if not title:
        title = f"{book} {test} passage {passage_num}"

    # Find the question sections in the markdown
    # Pattern: "Questions X-Y" or "Questions X" followed by content
    # Supports both hyphen (-) and en-dash (–)
    q_sections = list(re.finditer(
        r'Questions\s+(\d+)(?:\s*[–-]\s*(\d+))?\s*\n(.+?)(?=\nQuestions\s+\d|\n\Z)',
        md_text, re.DOTALL
    ))

    # Build answer key from reading_answers.json
    book_answers = answers_db.get(book, {}).get(test, {})
    # Map passage number → partX
    part_key = f"part{passage_num}"
    answer_key = book_answers.get(part_key, {})

    questions = []
    if q_sections:
        for qm in q_sections:
            q_start = int(qm.group(1))
            q_end = int(qm.group(2)) if qm.group(2) else q_start
            q_content = qm.group(3).strip()

            # Parse individual questions from this section
            # Questions are numbered like "1 text..." or preceded by number+dot
            q_lines = re.split(r'\n(?=\d+\s+)', q_content)
            for ql in q_lines:
                ql = ql.strip()
                if not ql:
                    continue
                # Extract question number
                m = re.match(r'(\d+)\s+(.+)', ql, re.DOTALL)
                if not m:
                    continue
                q_num = int(m.group(1))
                q_text = m.group(2).strip()
                # Truncate long question text for prompt
                prompt = q_text[:200]
                # Determine question type
                choices = []
                # Check for MCQ: "A ... B ... C ... D ..." pattern
                letters_found = re.findall(r'\b([A-D])\s{2,}(.+?)(?=\s{2,}[A-D]\s|$)', q_text)
                if letters_found:
                    for letter, text in letters_found:
                        choices.append(f"{letter}. {text.strip()}")
                    # Remove choices from prompt
                    prompt = re.sub(r'\s{2,}[A-D]\s{2,}.+', '', q_text).strip()[:200]

                qid = f"q{q_num}"
                answer = answer_key.get(str(q_num), "")
                if isinstance(answer, list):
                    answer = answer[0] if answer else ""

                questions.append({
                    "id": qid,
                    "number": q_num,
                    "prompt": prompt,
                    "choices": choices,
                    "answer": str(answer).strip(),
                })
    else:
        # No question sections found - use answer_key directly as simple Q&A
        for qnum_str, answer in sorted(answer_key.items(), key=lambda x: int(re.sub(r'[^0-9].*', '', x[0])) if x[0] and re.match(r'\d', x[0]) else 0):
            if '&' in qnum_str or not qnum_str.strip().isdigit():
                # Handle multi-answer keys like "23&24"
                for part in qnum_str.split('&'):
                    part = part.strip()
                    if part.isdigit():
                        qnum = int(part)
                        questions.append({
                            "id": f"q{qnum}",
                            "number": qnum,
                            "prompt": f"Question {qnum}",
                            "choices": [],
                            "answer": str(answer).strip(),
                        })
                continue
            qnum = int(qnum_str)
            questions.append({
                "id": f"q{qnum}",
                "number": qnum,
                "prompt": f"Question {qnum}",
                "choices": [],
                "answer": str(answer).strip(),
            })

    # Create passage directory
    idx += 1
    dir_name = f"passage-{idx:03d}"
    os.makedirs(os.path.join(CONTENT_DIR, dir_name), exist_ok=True)

    # Write passage.md (just the article part, before first Questions section)
    article = md_text
    first_q = md_text.find("Questions ")
    if first_q > 0:
        article = md_text[:first_q].strip()
    with open(os.path.join(CONTENT_DIR, dir_name, "passage.md"), "w") as f:
        f.write(article)

    # Write meta.json
    meta = {
        "id": f"reading-passage-{idx:03d}",
        "type": "reading",
        "title": f"{book.upper()} Test {test.replace('test','')} Passage {passage_num}: {title}",
        "pdf": None,
        "audio": None,
        "questions": questions,
    }
    with open(os.path.join(CONTENT_DIR, dir_name, "meta.json"), "w") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    status = "✓" if questions else "⚠ NO QS"
    has_ans = sum(1 for q in questions if q["answer"])
    print(f"[{idx:03d}] {file} → {dir_name}  {status} ({len(questions)} questions, {has_ans} with answers)")

print(f"\nDone. Created {idx} passages in {CONTENT_DIR}")
