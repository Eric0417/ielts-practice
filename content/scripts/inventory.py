#!/usr/bin/env python3
"""
Step 1: Inventory - List all PDFs and audio files, identify book names/numbers,
locate Listening sections, answer keys, and audioscripts pages, and propose
audio-to-Test/Section pairing.
Output: audio_new/_inventory.json
"""

import os
import re
import json
import pdfplumber
from pathlib import Path
from collections import defaultdict

# ============ PATHS ============
PDF_DIR = "/Users/eric/script/IELTS_practice/content/past_paper/4-20/4-20"
AUDIO_DIR = "/Users/eric/script/IELTS_practice/content/past_paper/4-20/audio"
OUT_DIR = "/Users/eric/script/IELTS_practice/content/audio_new"

# ============ PDF FILE MAPPING ============
PDF_MAP = {
    "剑4真题.pdf": (4, "Cambridge IELTS 4"),
    "剑7真题.pdf": (7, "Cambridge IELTS 7"),
    "剑8真题.pdf": (8, "Cambridge IELTS 8"),
    "剑9真题.pdf": (9, "Cambridge IELTS 9"),
    "剑10真题.pdf": (10, "Cambridge IELTS 10"),
    "剑11真题.pdf": (11, "Cambridge IELTS 11"),
    "剑12真题.pdf": (12, "Cambridge IELTS 12"),
    "剑13真题.pdf": (13, "Cambridge IELTS 13"),
    "剑14真题.pdf": (14, "Cambridge IELTS 14"),
    "剑15真题.pdf": (15, "Cambridge IELTS 15"),
    "剑16真题.pdf": (16, "Cambridge IELTS 16"),
    "真题17（A类）.pdf": (17, "Cambridge IELTS 17"),
    "真题18.pdf": (18, "Cambridge IELTS 18"),
    "真题19.pdf": (19, "Cambridge IELTS 19"),
    "A20真题.pdf": (20, "Cambridge IELTS 20"),
    "5.pdf": (5, "Cambridge IELTS 5"),
    "6.pdf": (6, "Cambridge IELTS 6"),
}

# ============ AUDIO DIRECTORY MAPPING ============
AUDIO_DIR_MAP = {
    4: "剑桥雅思4听力音频",
    5: "【5】剑桥雅思5听力音频",
    6: "【6】剑桥雅思6听力音频",
    7: "【7】剑桥雅思7听力音频",
    8: "【8】剑桥雅思8听力音频",
    9: "【9】剑桥雅思9听力音频",
    10: "【10】剑桥雅思10听力音频",
    11: "【11】剑桥雅思11听力音频",
    12: "【12】剑桥雅思12听力音频",
    13: "【13】剑桥雅思13听力音频",
    14: "【14】剑桥雅思14听力音频",
    15: "剑桥15",
    16: "16音频",
       17: "17音频",
    18: "剑18音频",
    19: "A19音频/音频",
    20: "20音频",
}

# Roman numerals for sections 1-4
ROMAN_NUMERALS = {1: "I", 2: "II", 3: "III", 4: "IV"}

# ============ HELPER FUNCTIONS ============

def load_pdf_text(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        return [(i, pdf.pages[i].extract_text() or "") for i in range(len(pdf.pages))]


def is_scanned_pdf(pages_text, sample_pages=20):
    text_pages = sum(1 for _, text in pages_text[:sample_pages] if text.strip())
    return text_pages < sample_pages * 0.3


def find_boundary_pages(pages_text, cambridge_num):
    answer_key_page = None
    audioscripts_page = None
    
    for pn, text in pages_text:
        if not text or pn < 50:
            continue
        upper = text.upper()
        lines = [l.strip() for l in text.strip().split('\n')[:8] if l.strip()]
        
        if answer_key_page is None:
            for l in lines[:5]:
                if ("ANSWER KEY" in l.upper() or "Answer key" in l or "Answer Key" in l) and \
                   ("LISTENING" in upper or "READING" in upper):
                    answer_key_page = pn
                    break
        
        if audioscripts_page is None:
            for l in lines[:5]:
                if "AUDIOSCRIPTS" in l.upper() or "TAPESCRIPTS" in l.upper():
                    audioscripts_page = pn
                    break
        
        if answer_key_page is not None and audioscripts_page is not None:
            break
    
    boundary = min(filter(None, [answer_key_page, audioscripts_page]), default=float('inf'))
    return boundary, answer_key_page, audioscripts_page


def locate_listening_tests(pages_text, boundary, cambridge_num):
    tests = []
    seen_test_nums = set()
    
    for idx, (pn, text) in enumerate(pages_text):
        if pn >= boundary:
            break
        if not text:
            continue
        
        lines = [l.strip() for l in text.strip().split('\n')[:12] if l.strip()]
        if len(lines) < 2:
            continue
        
        test_num = None
        for line in lines[:10]:
            m = re.match(r'^(Test|TEST)\s+(\d+)\s*$', line)
            if m:
                test_num = int(m.group(2))
                break
        
        if test_num is None:
            continue
        
        if test_num in seen_test_nums:
            continue
        
        has_listening = any("LISTENING" in l.upper() or "Listening" in l for l in lines[:10])
        
        is_listening = False
        for j in range(idx, min(len(pages_text), idx + 5)):
            _, t = pages_text[j]
            if not t:
                continue
            has_section = bool(re.search(r'(SECTION\s*1|PART\s*1)', t, re.IGNORECASE))
            has_q1 = bool(re.search(r'questions?\s*1[-\u2013\u2212\s]', t, re.IGNORECASE))
            if has_section and has_q1:
                is_listening = True
                break
        
        if is_listening or has_listening:
            seen_test_nums.add(test_num)
            tests.append({
                "test": test_num,
                "start_page": pn,
                "start_page_idx": idx,
                "label": f"Test {test_num}"
            })
    
    if cambridge_num == 12 and tests:
        for i, t in enumerate(sorted(tests, key=lambda x: x["test"])):
            t["test"] = i + 1
            t["label"] = f"Test {i + 1}"
    
    tests.sort(key=lambda x: x["test"])
    return tests[:4]


def find_test_end_pages(pages_text, tests, boundary):
    for test in tests:
        start_idx = test["start_page_idx"]
        end_page = None
        
        for j in range(start_idx + 1, len(pages_text)):
            pn, text = pages_text[j]
            if pn >= boundary:
                end_page = boundary - 1
                break
            if not text:
                continue
            lines = [l.strip() for l in text.strip().split('\n')[:5]]
            
            next_test = test["test"] + 1
            for line in lines[:3]:
                if re.match(rf'^(Test|TEST)\s+{next_test}\s*$', line, re.IGNORECASE):
                    end_page = pn - 1
                    break
            if end_page is not None:
                break
            
            for line in lines[:3]:
                if re.match(r'^READING(\s+PASSAGE\s+1)?\s*$', line, re.IGNORECASE):
                    end_page = pn - 1
                    break
            if end_page is not None:
                break
        
        if end_page is None:
            end_page = boundary - 1
        
        test["end_page"] = end_page
        test["end_page_idx"] = next(
            (idx for idx, (pn, _) in enumerate(pages_text) if pn == end_page),
            len(pages_text) - 1
        )
    
    return tests


def find_section_pages(pages_text, test_start_idx, test_end_idx):
    sections = {}
    section_starts = {}
    
    for idx in range(test_start_idx, test_end_idx + 1):
        pn, text = pages_text[idx]
        if not text:
            continue
        lines = [l.strip() for l in text.strip().split('\n')[:12]]
        for sn in range(1, 5):
            if sn in section_starts:
                continue
            roman = ROMAN_NUMERALS[sn]
            patterns = [
                rf'SECTION\s*{sn}\b',
                rf'SECTION\s*{roman}\b',
                rf'PART\s*{sn}\b',
            ]
            for line in lines:
                if any(re.search(p, line, re.IGNORECASE) for p in patterns):
                    section_starts[sn] = pn
                    break
    
    sorted_sections = sorted(section_starts.items())
    for i, (sn, sp) in enumerate(sorted_sections):
        if i + 1 < len(sorted_sections):
            ep = sorted_sections[i + 1][1] - 1
        else:
            ep = pages_text[test_end_idx][0]
        if ep < sp:
            ep = sp
        sections[sn] = {"start_page": sp, "end_page": ep}
    
    return sections


def find_answer_key_pages(pages_text, cambridge_num):
    ak_start_idx = None
    for idx, (pn, text) in enumerate(pages_text):
        if not text or pn < 50:
            continue
        lines = [l.strip() for l in text.strip().split('\n')[:8] if l.strip()]
        for l in lines[:5]:
            if ("ANSWER KEY" in l.upper() or "Answer key" in l or "Answer Key" in l) and \
               ("LISTENING" in text.upper() or "READING" in text.upper()):
                ak_start_idx = idx
                break
        if ak_start_idx is not None:
            break
    
    if ak_start_idx is None:
        return {}
    
    if cambridge_num == 12:
        label_map = {1: 5, 2: 6, 3: 7, 4: 8}
    else:
        label_map = {1: 1, 2: 2, 3: 3, 4: 4}
    
    result = {}
    for test_num in range(1, 5):
        pdf_label = label_map[test_num]
        for idx in range(ak_start_idx, len(pages_text)):
            pn, text = pages_text[idx]
            if not text:
                continue
            lines = [l.strip() for l in text.strip().split('\n')[:8] if l.strip()]
            has_test = any(re.match(rf'^(TEST|Test)\s+{pdf_label}\s*$', l, re.IGNORECASE) for l in lines[:3])
            has_sec1 = any(re.search(r'Section\s+1[,.\s]', l, re.IGNORECASE) for l in lines[:8])
            if has_test and has_sec1:
                result[test_num] = pn
                break
    
    return result


def scan_audio_files(cambridge_num):
    dir_name = AUDIO_DIR_MAP.get(cambridge_num)
    if not dir_name:
        return []
    
    audio_path = os.path.join(AUDIO_DIR, dir_name)
    if not os.path.isdir(audio_path):
        return []
    
    audio_files = []
    for root, dirs, files in os.walk(audio_path):
        for f in files:
            if not f.lower().endswith('.mp3'):
                continue
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, audio_path)
            audio_files.append({
                "filename": f,
                "relative_path": rel_path,
                "full_path": full_path,
                "size_bytes": os.path.getsize(full_path)
            })
    
    return audio_files


def propose_audio_pairing(cambridge_num, audio_files):
    pairings = defaultdict(list)
    
    for af in audio_files:
        fname = af["filename"]
        fl = fname.lower()
        
        test_num = None
        section_num = None
        
        if cambridge_num <= 13:
            m = re.search(r'test(\d+)[._-]section(\d+)', fl)
            if m:
                test_num = int(m.group(1))
                section_num = int(m.group(2))
            else:
                m = re.search(r'test(\d+)', fl)
                if m:
                    test_num = int(m.group(1))
                m = re.search(r'section(\d+)', fl)
                if m:
                    section_num = int(m.group(1))
        
        elif cambridge_num == 14:
            m = re.search(r'test\s*(\d+)[-_\s/](\d+)', fl)
            if m:
                test_num = int(m.group(1))
                section_num = int(m.group(2))
        
        elif cambridge_num == 15:
            m = re.search(r'test(\d+)_audio(\d+)', fl)
            if m:
                test_num = int(m.group(1))
                section_num = int(m.group(2))
        
        elif cambridge_num == 16:
            m = re.search(r'test(\d+)_audio(\d+)', fl)
            if m:
                test_num = int(m.group(1))
                section_num = int(m.group(2))
        
        elif cambridge_num == 17:
            m = re.search(r'c17[-_]t(\d+)[-_]p(\d+)', fl)
            if m:
                test_num = int(m.group(1))
                section_num = int(m.group(2))
        
        elif cambridge_num == 18:
            m = re.search(r'18[-_](\d+)[-_](\d+)', fl)
            if m:
                test_num = int(m.group(1))
                section_num = int(m.group(2))
        
        elif cambridge_num == 19:
            m = re.search(r'test(\d+)\s+part(\d+)', fl)
            if m:
                test_num = int(m.group(1))
                section_num = int(m.group(2))
        
        elif cambridge_num == 20:
            m = re.search(r'20t(\d+)s(\d+)', fl)
            if m:
                test_num = int(m.group(1))
                section_num = int(m.group(2))
        
        if cambridge_num == 12 and test_num is not None:
            if 5 <= test_num <= 8:
                test_num = test_num - 4
        
        if test_num is not None and section_num is not None:
            # Fix section 5 -> 4 (typo in some audio filenames)
            if section_num > 4:
                section_num = 4
            key = (test_num, section_num)
            pairings[key].append(af)
    
    return dict(pairings)


def process_pdf(pdf_filename, cambridge_num, book_name):
    pdf_path = os.path.join(PDF_DIR, pdf_filename)
    
    print(f"Processing {book_name} ({pdf_filename})...")
    
    pages_text = load_pdf_text(pdf_path)
    total_pages = len(pages_text)
    
    is_scanned = is_scanned_pdf(pages_text)
    
    boundary, ak_page, as_page = find_boundary_pages(pages_text, cambridge_num)
    
    tests = locate_listening_tests(pages_text, boundary, cambridge_num)
    tests = find_test_end_pages(pages_text, tests, boundary)
    
    for test in tests:
        test["sections"] = find_section_pages(
            pages_text, test["start_page_idx"], test["end_page_idx"]
        )
    
    answer_keys = find_answer_key_pages(pages_text, cambridge_num)
    for test in tests:
        tn = test["test"]
        if tn in answer_keys:
            test["answer_key_page"] = answer_keys[tn]
    
    audio_files = scan_audio_files(cambridge_num)
    audio_pairings = propose_audio_pairing(cambridge_num, audio_files)
    
    result = {
        "cambridge_number": cambridge_num,
        "book_name": book_name,
        "pdf_filename": pdf_filename,
        "total_pages": total_pages,
        "is_scanned": is_scanned,
        "boundary_page": boundary if boundary != float('inf') else None,
        "answer_key_section_page": ak_page,
        "audioscripts_page": as_page,
        "tests": tests,
        "audio_files": audio_files,
        "audio_pairings": {
            f"test_{tn}_section_{sn}": [a["relative_path"] for a in alist]
            for (tn, sn), alist in audio_pairings.items()
        }
    }
    
    return result


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    
    inventory = {
        "generated_at": "2026-07-04",
        "pdf_directory": PDF_DIR,
        "audio_directory": AUDIO_DIR,
        "books": []
    }
    
    for pdf_filename, (cn, book_name) in sorted(PDF_MAP.items(), key=lambda x: x[1][0]):
        pdf_path = os.path.join(PDF_DIR, pdf_filename)
        if not os.path.exists(pdf_path):
            print(f"  WARNING: {pdf_filename} not found, skipping")
            continue
        
        try:
            book_data = process_pdf(pdf_filename, cn, book_name)
            inventory["books"].append(book_data)
        except Exception as e:
            import traceback
            print(f"  ERROR processing {pdf_filename}: {e}")
            traceback.print_exc()
            inventory["books"].append({
                "cambridge_number": cn,
                "book_name": book_name,
                "pdf_filename": pdf_filename,
                "error": str(e)
            })
    
    output_path = os.path.join(OUT_DIR, "_inventory.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(inventory, f, indent=2, ensure_ascii=False)
    
    print(f"\nInventory saved to {output_path}")
    
    print("\n=== INVENTORY SUMMARY ===")
    for book in inventory["books"]:
        if "error" in book:
            print(f"  {book['book_name']}: ERROR - {book['error']}")
            continue
        print(f"  {book['book_name']} (C{book['cambridge_number']:02d}):")
        print(f"    PDF: {book['pdf_filename']} ({book['total_pages']} pages)")
        print(f"    Scanned: {'SCANNED (needs OCR)' if book['is_scanned'] else 'Text extractable'}")
        print(f"    Boundary: p.{book['boundary_page']+1 if book['boundary_page'] else 'N/A'}")
        print(f"    Answer Key: p.{book['answer_key_section_page']+1 if book['answer_key_section_page'] else 'N/A'}")
        print(f"    Audioscripts: p.{book['audioscripts_page']+1 if book['audioscripts_page'] else 'N/A'}")
        print(f"    Tests found: {len(book['tests'])}")
        for test in book["tests"]:
            sections = test.get("sections", {})
            sec_str = ', '.join(f"S{sn}: p.{sec['start_page']+1}-p.{sec['end_page']+1}" for sn, sec in sections.items())
            ak = f", Answer Key: p.{test['answer_key_page']+1}" if "answer_key_page" in test else ""
            print(f"      Test {test['test']}: p.{test['start_page']+1}-p.{test['end_page']+1} ({sec_str}){ak}")
        print(f"    Audio files: {len(book['audio_files'])}")
        for key, paths in book["audio_pairings"].items():
            print(f"      {key}: {paths}")


if __name__ == "__main__":
    main()
