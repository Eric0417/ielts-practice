# IELTS Listening Extraction SOP v1.0

## 0. Scope

從 Cambridge IELTS 真題書 PDF 中抽取聽力 (Listening) 題目，產出：
- `questions.pdf`（該 section 的題目頁截取）
- `audio.mp3`（對應音檔）
- `data.json`（題號、題型、題目文字、標準答案）

## 1. Answer Key Parsing（答案解析）

### 1.1 Page Detection

搜尋 PDF 後半部（page > 50）出現 `Answer Key`／`Listening and Reading Answer Keys` 字樣的頁面，且該頁包含 `LISTENING` 以及對應 Test 編號（如 `TEST 1`、`TEST 5`）。

### 1.2 Line-Based Column Splitting

答案頁為兩欄排版（左欄 Q1–20，右欄 Q21–40）。每行文字以右欄 Q 號（21–40）的第一個出現位置為分割點：
- 分割點前的文字 → 左欄
- 分割點後的文字 → 右欄
- 無右欄 Q 號的行 → 根據內容判斷欄位：
  - 單一小寫字母（如 `c`）→ 右欄（多選題答案）
  - 其他文字 → 左欄

### 1.3 Question-Answer Pairing

每欄獨立解析：
1. 行首出現 Q 號（`^\d{1,2}`）→ 開始新題
2. 無 Q 號的行 → 延續到當前題的答案文字
3. `IN EITHER ORDER`／`BOTH REQUIRED`／`FOR ONE MARK` → 標記為配對題或備註
4. `If you score...` → 終止解析

### 1.4 OCR Correction

當解析到的 Q 號小於預期 Q 號（`v < expected`）時，判斷為 PDF 文字層錯誤（如 `7` 被 OCR 為 `1`），使用預期 Q 號替代。

### 1.5 Implicit Q Advance

右欄中，當當前 Q 已有答案文字（`buf` 非空），且出現單一小寫字母延續行時，該字母屬於下一個 Q（Q+1），而非當前 Q。自動建立隱式下一題，等待後續正規 Q 號出現時合併。

### 1.6 Cleaning

- ` I `（OCR 將 `/` 誤讀為 `I`）→ 替換為 ` / `
- 連續空格正規化
- 配對題（含 EITHER ORDER 備註）的多個答案以 ` / ` 連接

## 2. Question Type Classification（題型判定）

### 2.1 Type Enum（十個互斥值）

| 值 | 說明 |
|---|---|
| `multiple_choice` | 單選（Choose the correct letter） |
| `multiple_select` | 多選（Choose TWO letters） |
| `fill_blank` | 填空／句子完成（Complete the notes/sentences/summary below） |
| `form_completion` | 表單完成（Complete the form below） |
| `table_completion` | 表格完成（Complete the table below） |
| `matching` | 配對題（Choose your answers from the box，無 Label） |
| `map_labelling` | 地圖／平面圖／圖表標示（Label the map/plan/diagram/chart below） |
| `short_answer` | 簡答（Answer the questions below，問答格式） |
| `true_false_notgiven` | 是非判斷（Do the following statements agree） |
| `unknown` | 無法判定 → `needs_review: true` |

### 2.2 Trigger Keyword Table

判定順序依下表從上到下，命中即停止：

| 優先序 | 觸發字串（case-insensitive） | Type |
|--------|---------------------------|------|
| 1 | `Label the map below` | `map_labelling` |
| 1 | `Label the plan below` | `map_labelling` |
| 1 | `Label the diagram below` | `map_labelling` |
| 1 | `Label the chart below` | `map_labelling` |
| 2 | `Choose {N} letters` (regex: `choose\s+\w+\s+letters`, \w+ safe — anchored by trailing `letters`) | `multiple_select` |
| 2 | `Which TWO` / `Which THREE` / `Which FOUR` / `Which FIVE` (regex: `which\s+(TWO|THREE|FOUR|FIVE)\b`, enumeration required — `which` alone is a common relative pronoun, \w+ would false-match "which have", "which was") | `multiple_select` |
| 3 | `Choose the correct letter` | `multiple_choice` |
| 4 | `Choose your answers from the box`（無 Label） | `matching` |
| 5 | `Complete the form below` | `form_completion` |
| 6 | `Complete the table below` | `table_completion` |
| 7 | `Complete the notes below` | `fill_blank` |
| 7 | `Complete the sentences below` | `fill_blank` |
| 8 | `Do the following statements agree` | `true_false_notgiven` |
| 9 | `Answer the questions below` | `short_answer` |
| 10 | 以上皆不匹配 | `unknown` |

### 2.3 Collision Rule（撞車優先序）

當同一題組同時命中 `Label the X below` 和 `Choose your answers from the box` 兩組觸發條件時：
- `Label the X below` 定義的是**題型**（看圖定位作答）
- `from the box + write letters` 定義的是**答案格式**（從指定集合選答案）
- **Label 優先**。存在任何 Label 關鍵字 → `map_labelling`，無論是否有 box-selection 指示

## 3. Prompt Extraction（題目文字抽取）

### 3.1 基本方法

1. 對每個 section 的對應頁面，逐行掃描文字
2. 以題號（`^\d{1,2}\s` 或 `\s\d{1,2}\s`）為錨點定位
3. 抽取題號所在行中，題號前後的可讀文字（去除題號本身及長點號 `[.…·]{3,}`）
4. 若某行同時有題號和實質文字（非僅點號），取該行文字為 prompt

### 3.2 抽取失敗處理

若題號所在行無法抽取到實質文字（例如：題號僅出現在圖形圖層而文字層不可見，或題號所在行僅含點號無其他文字）：
- 該題 prompt 設為 `null`
- 標記 `needs_review: true`
- 原因記為 `"prompt not extractable from text layer"`

**禁止行為**：不允許從相鄰題目猜測 prompt、不允許從答案反推 prompt、不允許填入任何非原文提取的字串。

## 4. Diagram-Label Questions（圖形標籤題）

### 4.1 問題描述

`map_labelling` 題型中，部分題號僅存在於圖形圖層（平面圖、地圖、圖表），pdfplumber 的文字層提取無法取得其 prompt 文字。典型受影響題號：plan 圖上 Q15–Q19、chart 圖上 Q28–Q30。

### 4.2 補救方案（已定案：選項 C）

prompt 留 `null`，`needs_review: true`，question_type 照常判定（從 instruction 文字匹配，不受 prompt 可否抽取影響）。網站前端顯示為「圖形題，請參考 questions.pdf」。

## 5. Audio File Mapping（音檔配對）

### 5.1 Naming Patterns

| Pattern | Books | Example |
|---------|-------|---------|
| `IELTS{N}_Test{M}/IELTS{N}_Test{M}.Section{K}.mp3` | 4–15 | `IELTS4_Test1.Section1.mp3` |
| `IELTS{N}_test{M}_audio{K}.mp3` | 16 | `IELTS16_test1_audio1.mp3` |
| `C{N}-T{M}-P{K}.mp3` | 17 | `C17-T1-P1.mp3` |
| `{N}-{M}-{K}.mp3` | 18 | `18-1-1.mp3` |
| `Test{M} Part{K}.mp3` | 19 | `Test1 Part1.mp3` |
| `{N}T{M}S{K}.mp3` | 20 | `20T1S1.mp3` |

### 5.2 Cambridge 12 Exception

C12 音檔目錄使用 `Test5`–`Test8` 命名（對應 PDF 內部 Test 1–4），屬於全域編號體系。配對時將 `Test5` 對應到 Test 1。

### 5.3 Unmatched Audio

無法確定對應的音檔放入 `_unmatched/` 目錄，並在處理報告中列出。

## 6. Output Structure

```
audio_new/
  cambridge-{NN}/
    test-{M}/
      section-{K}/
        questions.pdf
        audio.mp3
        data.json
  _unmatched/
  manifest.json
  EXTRACTION_REPORT.md
  VALIDATION_REPORT.md
```

### 6.1 data.json Schema

```json
{
  "id": "cambridge-04-test-1-section-1",
  "cambridge": 4, "test": 1, "section": 1,
  "type": "listening",
  "audio_file": "audio.mp3",
  "questions_pdf": "questions.pdf",
  "page_range": "p.11-p.12",
  "questions": [
    {
      "id": "cambridge-04-test-1-section-1-q1",
      "number": 1,
      "question_type": "fill_blank",
      "prompt": "good 1 [...]",
      "choices": [],
      "answer": "shopping / variety of shopping",
      "answer_raw": "shopping / variety of shopping",
      "answer_key_source": "answer_key_test_1",
      "audio_source_file": "IELTS4_Test1.Section1.mp3",
      "needs_review": false
    }
  ]
}
```

## 7. Validation Rules

- 每 test 必須有 40 題（Q1–40 連續），缺題標記 needs_review
- 每題必有 `answer` 欄位，無法解析時設 `null` + `needs_review: true`
- 禁止臆測答案，禁止填入非原文提取的字串
- 每 section 的 question_type 必須來自 instruction 文字匹配，不允許從題目結構猜測

---

*Version 1.0 — 2026-07-04*
*Draft pending approval*


### 3.3 Zero-Group Multi-Type Guard

當 `find_q_groups()` 回傳 0 個有效 group（無 standalone `Questions X-Y` 標記）時，section 會使用 section-level fallback 型別。為防止「本應有多個子型別但全部 marker 抽取失敗→靜默套用錯誤單一型別」的場景，增加安全檢查：

```python
if len(groups) == 0:
    distinct_count, _ = count_distinct_type_keywords(text)
    fb = classify_type(text)
    for q in range(q_start, q_end+1):
        q_types[q] = fb
    if distinct_count > 1:
        # Multiple types detected but no sub-group markers found
        # Flag all Qs as needs_review: zero_group_multitype
        for q in range(q_start, q_end+1):
            needs_review_flags[q] = 'zero_group_multitype'
```

`count_distinct_type_keywords(text)` 對整段文字掃描所有型別觸發字串，回傳相異型別數。若 > 1 且 groups=0，代表該節理應有多個子型別但 marker 全部未被 regex 匹配，觸發 flag。

單型別節（distinct_count == 1）不掛 flag，行為不變。零誤傷。
