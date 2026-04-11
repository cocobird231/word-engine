# Word Engine Phase 1+2 驗收操作手冊

本手冊提供一套系統化的驗收流程，讓椰子大大可以逐項確認 word-engine 的功能是否正確運作。

---

## 環境準備

```bash
cd /home/cococlaw/.openclaw/workspace/word-engine
source .venv/bin/activate
```

---

## 範例檔案總覽

| 檔案 | 用途 |
|------|------|
| `examples/phase2/A_basic_full.md` | 基本元素：heading/paragraph/list/code，無圖表 |
| `examples/phase2/B_caption_demo.md` | 圖表 caption 示範（含圖片與表格） |
| `examples/phase2/C_crossref_demo.md` | 交叉引用示範（含 forward reference） |
| `examples/phase2/D_review_loop_demo.md` | Review loop 測試用文件 |
| `examples/phase2/E_error_cases.md` | 故意包含多種錯誤，用來驗證 QC 攔截 |

## Params 檔案總覽

| 檔案 | 用途 |
|------|------|
| `examples/phase1/params_basic.yaml` | 最小基本參數（Phase 1 驗收用） |
| `examples/phase2/params_cover_toc.yaml` | 啟用封面與目錄 |
| `examples/phase2/params_caption_flat.yaml` | Caption flat 編號（圖 1, 圖 2...） |
| `examples/phase2/params_caption_chapter.yaml` | Caption chapter 編號（圖 1-1, 圖 2-1...） |
| `examples/phase2/params_crossref_ieee.yaml` | 交叉引用 IEEE 風格（圖 N / 表 N / 第 N 節） |
| `examples/phase2/params_crossref_apa.yaml` | 交叉引用 APA 風格（Figure N / Table N / Section N） |
| `examples/phase2/params_review_fast.yaml` | 快速迭代（無封面/目錄，搭配 --skip-postfix） |
| `examples/phase2/params_invalid.yaml` | 故意設計錯誤，預期 QC 應失敗 |

---

## 驗收案例清單

### ✅ 案例 1：基本 QC 成功

**驗收目標**：給定正確的 .md 和 .yaml，QC 應通過。

```bash
python word_engine.py qc \
  --md examples/phase2/A_basic_full.md \
  --params examples/phase1/params_basic.yaml
```

**預期結果**：
```
Result: ✅ PASSED
Errors:   0
```

---

### ✅ 案例 2：QC 失敗攔截（錯誤 Markdown）

**驗收目標**：`E_error_cases.md` 包含多種錯誤，QC 應失敗並列出錯誤。

```bash
python word_engine.py qc \
  --md examples/phase2/E_error_cases.md \
  --params examples/phase1/params_basic.yaml
```

**預期結果**：
```
Result: ❌ FAILED
❌ ERROR: Heading jump ...
❌ ERROR: Unclosed code fence ...
❌ ERROR: Empty heading ...
⚠️  WARN: More than 3 consecutive blank lines
```

---

### ✅ 案例 3：QC 失敗攔截（無效 params.yaml）

**驗收目標**：`params_invalid.yaml` 有多個欄位錯誤，QC 應失敗。

```bash
python word_engine.py qc \
  --md examples/phase2/A_basic_full.md \
  --params examples/phase2/params_invalid.yaml
```

**預期結果**：
```
Result: ❌ FAILED
❌ ERROR: Missing required field: 'meta.spec_name'
❌ ERROR: Missing required field: 'meta.language'
❌ ERROR: Missing required field: 'project.project_id'
❌ ERROR: Invalid value for 'project.status': 'archived'
❌ ERROR: Invalid value for 'page.size': 'B5'
❌ ERROR: Invalid HEX color for 'colors.text_primary': 'black'
```

---

### ✅ 案例 4：渲染含封面與目錄

**驗收目標**：產出的 `.docx` 包含封面與 TOC field。

```bash
python word_engine.py render \
  --md examples/phase2/A_basic_full.md \
  --params examples/phase2/params_cover_toc.yaml \
  --output out_cover_toc.docx
```

**預期結果**：
- 產出 `out_cover_toc.docx`
- 用 Word/LibreOffice 開啟後，可見：
  - 封面頁（含 document_title, project_id, version, date）
  - 目錄 TOC field（顯示佔位文字或可更新的 TOC，按 F9 可展開）
  - 本文標題與段落

---

### ✅ 案例 5：Caption Flat 編號

**驗收目標**：圖表 caption 以全文連續計數（圖 1, 圖 2, 表 1, 表 2）。

```bash
python word_engine.py render \
  --md examples/phase2/B_caption_demo.md \
  --params examples/phase2/params_caption_flat.yaml \
  --output out_flat.docx
```

**預期結果**：
- 圖片下方有「圖 1 ...」「圖 2 ...」等 caption
- 表格上方有「表 1 ...」「表 2 ...」等 caption
- 編號跨章節連續（不重置）

---

### ✅ 案例 6：Caption Chapter 編號

**驗收目標**：圖表 caption 以 H1 章節為前綴（圖 1-1, 圖 2-1）。

```bash
python word_engine.py render \
  --md examples/phase2/B_caption_demo.md \
  --params examples/phase2/params_caption_chapter.yaml \
  --output out_chapter.docx
```

**預期結果**：
- 第一章的圖：「圖 1-1」「圖 1-2」
- 第二章的圖：「圖 2-1」

---

### ✅ 案例 7：Cross-reference IEEE

**驗收目標**：`{{ref:*}}` 在輸出文件中被替換為正確的引用文字。

```bash
python word_engine.py render \
  --md examples/phase2/C_crossref_demo.md \
  --params examples/phase2/params_crossref_ieee.yaml \
  --output out_xref_ieee.docx
```

**預期結果**：
- `{{ref:fig-1}}` → `圖 1`
- `{{ref:tbl-1}}` → `表 1`
- `{{ref:sec-1}}` → `第 1 節`
- **forward reference（圖前面的引用也正確解析）**
- 不出現未解析的 `{{ref:...}}` 字串

---

### ✅ 案例 8：Cross-reference APA 風格

**驗收目標**：切換成 APA 風格後，引用文字格式改變。

```bash
python word_engine.py render \
  --md examples/phase2/C_crossref_demo.md \
  --params examples/phase2/params_crossref_apa.yaml \
  --output out_xref_apa.docx
```

**預期結果**：
- 引用文字改為英文：`Figure 1`, `Table 1`, `Section 1`

---

### ✅ 案例 9：完整 Review Loop

**驗收目標**：一鍵執行完整循環，版本自動遞增，並產出 docx + pdf。

```bash
python word_engine.py review \
  --md examples/phase2/D_review_loop_demo.md \
  --params examples/phase2/params_review_fast.yaml \
  --project-dir . \
  --label "first-review"
```

**預期結果**：
1. 終端輸出 `[REVIEW] QC passed.`
2. 版本號遞增（v1 → v2 → v3...，每次執行 +1）
3. 產出 `documents/report_vN.docx` 和 `documents/report_vN.pdf`
4. `review_state.json` 顯示 4 個步驟 ✅

**再跑一次觀察版本遞增**：

```bash
python word_engine.py review \
  --md examples/phase2/D_review_loop_demo.md \
  --params examples/phase2/params_review_fast.yaml \
  --project-dir . \
  --label "second-review"
```

版本號應再 +1。

---

### ✅ 案例 10：跑所有單元測試

```bash
./.venv/bin/pytest -q tests/unit/
```

**預期結果**：
```
144 passed in X.Xs
```

---

## 能力邊界說明

以下功能目前屬於「已知限制」，不是 bug：

| 功能 | 當前狀態 | 說明 |
|------|---------|------|
| TOC 自動展開 | 需 F9 手動更新 | TOC 是 Word field，Phase 3 UNO 會自動更新 |
| Cross-reference | 靜態文字替換 | 非 Word REF field，不能動態更新 |
| UNO 後處理 | LO headless 重存 | 非 UNO socket bridge，Phase 3 升級 |
| 圖片下載 | 支援本地圖片 | 遠端圖片需 `download_remote_images: true` |
| 雲端同步 | stub（不執行） | Phase 3 Nextcloud 整合 |

---

## 推薦椰子大大優先跑的 3 個案例

1. **案例 2**（QC 錯誤攔截）：確認 QC 系統真的會攔住問題
2. **案例 7**（Cross-reference IEEE）：確認 `{{ref:*}}` forward reference 機制運作
3. **案例 9**（Review Loop）：確認版本化 rerender + export 端到端流程
