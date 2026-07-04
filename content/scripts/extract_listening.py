#!/usr/bin/env python3
"""Phase 2: Extract Cambridge 04 test-1 and Cambridge 12 test-1 as samples."""

import pdfplumber, pypdf, os, re, json, shutil
from collections import defaultdict

PDF_DIR = "/Users/eric/script/IELTS_practice/content/past_paper/4-20/4-20"
AUDIO_DIR = "/Users/eric/script/IELTS_practice/content/past_paper/4-20/audio"
OUT_DIR = "/Users/eric/script/IELTS_practice/content/audio_new"

AUDIO_DIR_MAP = {
    "剑桥雅思4听力音频":4, "【5】剑桥雅思5听力音频":5, "【6】剑桥雅思6听力音频":6,
    "【7】剑桥雅思7听力音频":7, "【8】剑桥雅思8听力音频":8, "【9】剑桥雅思9听力音频":9,
    "【10】剑桥雅思10听力音频":10, "【11】剑桥雅思11听力音频":11, "【12】剑桥雅思12听力音频":12,
    "【13】剑桥雅思13听力音频":13, "【14】剑桥雅思14听力音频":14, "剑桥15":15,
    "16音频":16, "17音频":17, "剑18音频":18, "A19音频":19, "20音频":20,
}


def load_pages_text(pdf):
    return [(i, pdf.pages[i].extract_text() or "") for i in range(len(pdf.pages))]


def locate_listening_blocks(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        pts = load_pages_text(pdf)
    
    # Find audioscripts (must be after page 50, not from TOC)
    boundary = None
    for pn, text in pts:
        if text and pn > 50 and "AUDIOSCRIPTS" in text.upper():
            boundary = pn
            break
    if boundary is None:
        # Fallback: find answer keys boundary
        for pn, text in pts:
            if text and pn > 50 and "ANSWER KEY" in text.upper() and "LISTENING" in text.upper():
                boundary = pn
                break
    if boundary is None:
        boundary = float('inf')
    
    # Find blocks: SECTION/PART 1 + Questions 1, before boundary
    blocks = []
    for idx, (pn, text) in enumerate(pts):
        if pn >= boundary:
            break
        if not text:
            continue
        first_lines = [l.strip() for l in text.strip().split('\n')[:6]]
        has_s1 = any(re.search(r'(SECTION\s*1|PART\s*1)', l, re.IGNORECASE) for l in first_lines)
        has_q1 = bool(re.search(r'questions?\s*1[-\u2013\u2212\s]', text, re.IGNORECASE))
        if has_s1 and has_q1:
            # Exclude General Training
            is_gt = False
            for ci in range(max(0, idx-1), min(len(pts), idx+3)):
                ct = pts[ci][1]
                if ct and "GENERAL TRAINING" in ct.upper() and "READING" in ct.upper():
                    is_gt = True
                    break
            if not is_gt:
                blocks.append((pn, idx))
    
    blocks = blocks[:4]
    
    # Find end for each block
    result = []
    for test_idx, (sp, ti) in enumerate(blocks):
        ep = None
        for j in range(ti + 1, len(pts)):
            _, nt = pts[j]
            if not nt:
                continue
            fl = [l.strip() for l in nt.strip().split('\n')[:4]]
            for line in fl:
                if re.match(r'^(READING|READING\s+PASSAGE\s+1)', line, re.IGNORECASE):
                    ep = pts[j-1][0]
                    break
            if ep is not None:
                break
            # Check for next test marker
            next_test = test_idx + 2
            for line in fl:
                if re.match(rf'^\s*Test\s+{next_test}\s*$', line, re.IGNORECASE):
                    ep = pts[j-1][0]
                    break
            if ep is not None:
                break
        if ep is None:
            # Fallback: find SECTION/PART 4
            for j in range(ti+1, min(len(pts), ti+20)):
                _, nt = pts[j]
                if nt:
                    if re.search(r'(SECTION\s*4|PART\s*4)', nt, re.IGNORECASE) and                        re.search(r'questions 31', nt, re.IGNORECASE):
                        ep = pts[j][0]
                        if j+1 < len(pts) and pts[j+1][1]:
                            fl2 = pts[j+1][1].strip().split('\n')[0].split()
                            if fl2 and fl2[0].upper() not in ('READING', 'TEST', 'WRITING'):
                                ep = pts[j+1][0]
                        break
        if ep is None:
            ep = sp + 7
        result.append((test_idx + 1, sp, ep))
    return result


def find_answer_key_pages(pdf_path, cambridge_num=0):
    with pdfplumber.open(pdf_path) as pdf:
        pts = load_pages_text(pdf)
    
    # Find answer key section (after page 50, not TOC)
    ak_start = None
    for idx, (pn, text) in enumerate(pts):
        if not text or pn < 50:
            continue
        if "ANSWER KEY" in text.upper() and "LISTENING" in text.upper():
            ak_start = idx
            break
    if ak_start is None:
        return []
    
    # Cambridge 12 uses "Test 5-8" labels
    if cambridge_num == 12:
        label_map = {1: 5, 2: 6, 3: 7, 4: 8}
    else:
        label_map = {1: 1, 2: 2, 3: 3, 4: 4}
    
    result = []
    for test_num in range(1, 5):
        pdf_label = label_map[test_num]
        p1 = re.compile(rf'TEST\s+{pdf_label}\s*$', re.IGNORECASE)
        p2 = re.compile(rf'TEST\s*{pdf_label}[^0-9]', re.IGNORECASE)
        for idx in range(ak_start, len(pts)):
            _, text = pts[idx]
            if not text:
                continue
            has_test = bool(p1.search(text) or p2.search(text))
            has_sec = bool(re.search(r'Section\s+1[,.\s]', text, re.IGNORECASE))
            # Check that this is listing answers (not reading answers)
            # Reading answers pages have "Reading Passage" near the top
            not_reading = "READING PASSAGE" not in text[:500] and "READING" not in text[:100]
            # Also check for answer-like content: Section headers with question numbers
            has_answer_content = bool(re.search(r'Section\s+\d[,.\s]+\s*Questions\s+\d', text, re.IGNORECASE))
            if has_test and has_sec and not_reading and has_answer_content:
                result.append((test_num, idx))
                break
    return result


def parse_answer_key_page(pdf, page_idx, test_num):
    page = pdf.pages[page_idx]
    words = page.extract_words()
    
    q_xs = [(w['x0'], int(w['text'].strip())) for w in words
            if w['text'].strip().isdigit() and 1 <= int(w['text'].strip()) <= 40]
    if not q_xs:
        return {}
    
    left_xs = [x for x, q in q_xs if q <= 20]
    right_xs = [x for x, q in q_xs if q >= 21]
    col_split = (max(left_xs) + min(right_xs)) / 2 if left_xs and right_xs else 200
    
    answers = {}
    for col_pref, tq in [('left', set(range(1,21))), ('right', set(range(21,41)))]:
        cw = [w for w in words if (col_pref == 'left' and w['x0'] < col_split) or
              (col_pref == 'right' and w['x0'] > col_split)]
        cw.sort(key=lambda w: (round(w['top']), w['x0']))
        
        lines = defaultdict(list)
        for w in cw:
            lines[round(w['top'])].append(w)
        
        cur_q = None
        cur_parts = []
        cur_notes = []
        
        for yk, lw in sorted(lines.items()):
            lw.sort(key=lambda w: w['x0'])
            lt = ' '.join(w['text'] for w in lw).strip()
            if not lt:
                continue
            if re.match(r'^Section\s+\d', lt, re.IGNORECASE):
                continue
            if re.match(r'^If you score', lt, re.IGNORECASE):
                break
            qm = re.match(r'^(\d{1,2})\s+(.*)', lt)
            if qm:
                qn = int(qm.group(1))
                rest = qm.group(2).strip()
                if cur_q is not None and cur_q in tq:
                    ans = ' '.join(cur_parts).strip()
                    ans = re.sub(r'\s+I\s+', ' / ', ans)
                    if cur_notes:
                        ans = '; '.join(cur_notes) + ' | ' + ans
                    answers[cur_q] = ans
                if qn in tq:
                    cur_q = qn
                    cur_parts = [rest] if rest else []
                    cur_notes = []
                else:
                    cur_q = None
                    cur_parts = []
                    cur_notes = []
            else:
                if cur_q is not None and cur_q in tq and lt:
                    if re.match(r'^(IN EITHER ORDER|BOTH REQUIRED|FOR ONE MARK|IN ANY ORDER)', lt, re.IGNORECASE):
                        cur_notes.append(lt)
                    else:
                        cur_parts.append(lt)
        
        if cur_q is not None and cur_q in tq:
            ans = ' '.join(cur_parts).strip()
            ans = re.sub(r'\s+I\s+', ' / ', ans)
            if cur_notes:
                ans = '; '.join(cur_notes) + ' | ' + ans
            answers[cur_q] = ans
    
    return answers


def extract_answers(pdf_path, cambridge_num=0):
    ak_pages = find_answer_key_pages(pdf_path, cambridge_num)
    with pdfplumber.open(pdf_path) as pdf:
        return {tn: parse_answer_key_page(pdf, pi, tn) for tn, pi in ak_pages}


def find_audio_file(cambridge_num, test_num, section_num):
    ad = None
    for dn, bn in AUDIO_DIR_MAP.items():
        if bn == cambridge_num:
            ad = dn
            break
    if not ad:
        return None, None
    ab = os.path.join(AUDIO_DIR, ad)
    if not os.path.isdir(ab):
        return None, None
    
    if cambridge_num == 12:
        at_map = {1:"5", 2:"6", 3:"7", 4:"8"}
        at = at_map.get(test_num, str(test_num))
    else:
        at = str(test_num)
    ss = str(section_num)
    
    for root, dirs, files in os.walk(ab):
        for f in files:
            if not f.lower().endswith('.mp3'):
                continue
            fl = f.lower()
            cm = os.path.join(root, f)
            # Pattern matching
            if re.search(rf'\.?section\s*{ss}\.mp3', fl) and f'Test{at}' in f:
                return cm, f
            if re.search(rf'test\s*{at}[\s-]{ss}\.mp3', fl):
                return cm, f
            if re.search(rf'test{at}_audio{ss}\.mp3', fl):
                return cm, f
            if re.search(rf't{at}[-_]p{ss}\.mp3', fl):
                return cm, f
            if re.search(rf'-{at}-{ss}\.mp3', fl):
                return cm, f
            if re.search(rf'test{at}\s+part{ss}\.mp3', fl):
                return cm, f
            if re.search(rf't{at}s{ss}\.mp3', fl):
                return cm, f
    return None, None


def find_section_pages(pdf_path, s0, e0):
    with pdfplumber.open(pdf_path) as pdf:
        ss = {}
        for i in range(s0, e0+1):
            text = pdf.pages[i].extract_text() or ""
            fl = [l.strip() for l in text.strip().split('\n')[:5]]
            for sn in range(1,5):
                if sn in ss:
                    continue
                for line in fl:
                    if re.search(rf'(SECTION\s*{sn}|PART\s*{sn})', line, re.IGNORECASE):
                        ss[sn] = i
                        break
    res = {}
    sk = sorted(ss.items())
    for idx, (sn, sp) in enumerate(sk):
        ep = sk[idx+1][1]-1 if idx+1 < len(sk) else e0
        res[sn] = (sp, max(sp, ep))
    return res


def extract_pdf_pages(src, dst, s, e):
    r = pypdf.PdfReader(src)
    w = pypdf.PdfWriter()
    for i in range(s, e+1):
        if i < len(r.pages):
            w.add_page(r.pages[i])
    with open(dst, 'wb') as f:
        w.write(f)


def validate_block(pdf_path, test_num, s0, e0):
    with pdfplumber.open(pdf_path) as pdf:
        at = ""
        for i in range(s0, e0+1):
            t = pdf.pages[i].extract_text() or ""
            at += t + "\n"
    issues = []
    for s in range(1,5):
        if not re.search(rf'(SECTION\s*{s}|PART\s*{s})', at, re.IGNORECASE):
            issues.append(f"Section {s} label missing")
    for q in range(1,41):
        if not re.search(rf'\b{q}\b', at):
            issues.append(f"Q{q} missing")
    return issues


def process_section(cn, tn, sn, pdf_path, blocks, answers, out_base):
    _, s0, e0 = blocks[tn-1]
    sp = find_section_pages(pdf_path, s0, e0)
    if sn in sp:
        ss0, se0 = sp[sn]
    else:
        tp = e0 - s0 + 1
        pps = tp // 4
        ss0 = s0 + (sn-1)*pps
        se0 = min(e0, ss0+pps-1)
    
    sdir = os.path.join(out_base, f"cambridge-{cn:02d}", f"test-{tn}", f"section-{sn}")
    os.makedirs(sdir, exist_ok=True)
    
    extract_pdf_pages(pdf_path, os.path.join(sdir, "questions.pdf"), ss0, se0)
    
    asrc, afn = find_audio_file(cn, tn, sn)
    audio_ok = False
    if asrc and os.path.exists(asrc):
        shutil.copy2(asrc, os.path.join(sdir, "audio.mp3"))
        audio_ok = True
    
    sec_ans = answers.get(tn, {})
    qs, qe = (sn-1)*10+1, sn*10
    sid = f"cambridge-{cn:02d}-test-{tn}-section-{sn}"
    
    questions = []
    for qn in range(qs, qe+1):
        raw = sec_ans.get(qn)
        questions.append({
            "id": f"{sid}-q{qn}",
            "number": qn,
            "question_type": "fill_blank",
            "prompt": "",
            "choices": [],
            "answer": raw,
            "answer_raw": raw,
            "answer_key_source": f"answer_key_test_{tn}",
            "audio_source_file": afn,
            "needs_review": True
        })
    
    data = {
        "id": sid, "cambridge": cn, "test": tn, "section": sn,
        "type": "listening", "audio_file": "audio.mp3",
        "questions_pdf": "questions.pdf",
        "page_range": f"p.{ss0+1}-p.{se0+1}",
        "questions": questions
    }
    with open(os.path.join(sdir, "data.json"), 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    return audio_ok


# ============ MAIN ============

os.makedirs(OUT_DIR, exist_ok=True)

targets = [(4, "剑4真题.pdf"), (12, "剑12真题.pdf")]

for cn, fn in targets:
    pp = os.path.join(PDF_DIR, fn)
    print(f"\n{'='*60}")
    print(f"Cambridge {cn:02d}: {fn}")
    print(f"{'='*60}")
    
    with pdfplumber.open(pp) as pdf:
        # 1. Locate blocks
        blocks = locate_listening_blocks(pp)
        print(f"\nListening blocks: {len(blocks)}")
        for tn, sp, ep in blocks:
            print(f"  Test {tn}: pages {sp+1}-{ep+1}")
        
        # 2. Boundary evidence for Test 1
        print(f"\n--- Test 1 Boundaries ---")
        t1b = blocks[0]
        s_text = pdf.pages[t1b[1]].extract_text() or ""
        sl = [l.strip() for l in s_text.split('\n') if l.strip()]
        print(f"  START p.{t1b[1]+1}: {sl[:3]}")
        e_text = pdf.pages[t1b[2]].extract_text() or ""
        el = [l.strip() for l in e_text.split('\n') if l.strip()]
        print(f"  END p.{t1b[2]+1}: {el[-3:]}")
        if t1b[2]+1 < len(pdf.pages):
            n_text = pdf.pages[t1b[2]+1].extract_text() or ""
            nl = [l.strip() for l in n_text.split('\n') if l.strip()]
            print(f"  NEXT p.{t1b[2]+2}: {nl[:3]}")
        
        # 3. Validation
        issues = validate_block(pp, 1, t1b[1], t1b[2])
        if issues:
            for iss in issues:
                print(f"  \u26a0\ufe0f  {iss}")
        else:
            print(f"  \u2705 All sections present, Q1-40 confirmed")
    
    # 4. Extract answers
    answers = extract_answers(pp, cn)
    t1a = answers.get(1, {})
    print(f"\n--- Answer Keys: Test 1 ---")
    print(f"  Questions with answers: {len(t1a)}")
    for q in sorted(t1a.keys())[:12]:
        print(f"    Q{q:2d}: {t1a[q][:100]}")
    variants = [(q, a) for q, a in t1a.items() if '/' in str(a) or 'EITHER' in str(a).upper()]
    if variants:
        print(f"\n  Variants ({len(variants)} questions):")
        for q, a in variants[:8]:
            print(f"    Q{q}: {a[:120]}")
    
    # 5. Audio mapping
    print(f"\n--- Audio Mapping ---")
    for s in range(1,5):
        asrc, afn = find_audio_file(cn, 1, s)
        ok = "\u2705" if (asrc and os.path.exists(asrc)) else "\u274c"
        sz = os.path.getsize(asrc)/(1024*1024) if (asrc and os.path.exists(asrc)) else 0
        print(f"  Section {s}: {ok} {afn} ({sz:.1f}MB)")
    
    # Cambridge 12 special verification
    if cn == 12:
        print(f"\n--- C12 Audio Mapping Verification ---")
        print(f"  PDF Test 1 \u2194 Audio Test5 directories")
        print(f"  Answer count = {len(t1a)} (expected 40)")
        # Compare with C04 durations
        c4_a = find_audio_file(4, 1, 1)
        c12_a = find_audio_file(12, 1, 1)
        if c4_a[0] and c12_a[0]:
            print(f"  C04 S1: {c4_a[1]} ~{os.path.getsize(c4_a[0])//1024}KB")
            print(f"  C12 S1: {c12_a[1]} ~{os.path.getsize(c12_a[0])//1024}KB")
    
    # 6. Process all 4 sections
    print(f"\n--- Processing Sections ---")
    for s in range(1,5):
        ok = process_section(cn, 1, s, pp, blocks, answers, OUT_DIR)
        print(f"  Section {s}: {'\u2705' if ok else '\u274c'}")
    
    # 7. Show sample JSON
    sj = os.path.join(OUT_DIR, f"cambridge-{cn:02d}", "test-1", "section-1", "data.json")
    if os.path.exists(sj):
        print(f"\n--- data.json (section-1, first 3 Qs) ---")
        with open(sj) as f:
            d = json.load(f)
        for q in d['questions'][:3]:
            print(json.dumps(q, indent=2, ensure_ascii=False))

print(f"\nDone. Output: {OUT_DIR}")
