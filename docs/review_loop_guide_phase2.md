# Word Engine Phase 2 — 文書蝦蝦 Review Loop 操作指南

## 1. 什麼是 Review Loop？

Review Loop 是文書蝦蝦修改文件後「重新渲染 → 後處理 → 匯出 → 檢查」的完整循環。每一輪都會建立新的**版本號**，並保留所有中間產物（params 快照、docx、pdf）。

---

## 2. 正式流程圖

```
修改 refine.md 或 params.yaml
        ↓
word-engine review          ← 一鍵執行以下 4 步
        ↓
  [1] QC 檢查               ← 發現錯誤即中止，請修正後重試
        ↓
  [2] rerender (v N)        ← 版本自動遞增，備份 params 快照
        ↓
  [3] postfix               ← LibreOffice 後處理（欄位更新）
        ↓
  [4] export PDF            ← 輸出 report_vN.pdf
        ↓
  [5] 文書蝦蝦人工確認      ← 確認後可執行 mark-reviewed（手動）
```

---

## 3. 指令說明

### 3.1 一鍵 Review Loop（推薦）

在 `word-engine` 目錄下執行：

```bash
./.venv/bin/python word_engine.py review \
  --md examples/phase1/valid_source.md \
  --params examples/phase1/params_basic.yaml \
  --project-dir . \
  --label "fix-heading-style"
```

選項說明：

| 選項 | 說明 |
|------|------|
| `--md` | 修改後的 refine.md 路徑 |
| `--params` | 目前使用的 params.yaml 路徑 |
| `--project-dir` | 專案根目錄（render_state.json 所在位置，預設 `.`）|
| `--label` | 此輪版本的人類可讀標籤（選填）|
| `--skip-postfix` | 跳過 UNO 後處理步驟（快速迭代用）|

### 3.2 分步執行（進階）

若想逐步操作，也可以各別執行：

```bash
# Step 1: QC
./.venv/bin/python word_engine.py qc \
  --md examples/phase1/valid_source.md \
  --params examples/phase1/params_basic.yaml

# Step 2: Rerender（版本化）
./.venv/bin/python word_engine.py rerender \
  --md examples/phase1/valid_source.md \
  --params examples/phase1/params_basic.yaml \
  --project-dir . \
  --label "test-round"

# Step 3: Postfix（UNO 後處理）
./.venv/bin/python word_engine.py postfix \
  --docx documents/report_v3.docx

# Step 4: Export PDF
./.venv/bin/python word_engine.py export \
  --docx documents/report_v3.docx \
  --output documents/report_v3.pdf
```

---

## 4. 狀態記錄

每次執行 `review` 後，系統會產生或更新以下兩個狀態檔：

| 檔案 | 用途 |
|------|------|
| `render_state.json` | 版本化歷史紀錄（每版 params、docx、時間戳） |
| `review_state.json` | 當前 review 輪次的步驟狀態（哪些步驟已完成） |

`review_state.json` 範例：

```json
{
  "current_version": 3,
  "review_rounds": 2,
  "steps": {
    "qc_passed": true,
    "rendered": true,
    "postfixed": true,
    "exported": true,
    "review_checked": false
  },
  "artifacts": {
    "docx": "documents/report_v3.docx",
    "pdf": "documents/report_v3.pdf",
    "params_snapshot": null
  },
  "last_updated": "2026-04-12T01:40:00"
}
```

`review_checked` 是唯一需要人工標記的步驟（文書蝦蝦確認輸出正確後，可手動更新此欄位或透過後續工具標記）。

---

## 5. 產出物說明

| 產出物 | 路徑 | 說明 |
|--------|------|------|
| 版本化 docx | `documents/report_vN.docx` | 每次 rerender 的輸出文件 |
| 版本化 pdf | `documents/report_vN.pdf` | 每次 export 的 PDF |
| params 快照 | `documents/params/params_vN.yaml` | 當次 render 使用的參數備份 |
| QC 報告 | 終端輸出 | 每次 QC 後的結構化報告 |

---

## 6. 快速迭代建議

當你還在頻繁改 params 時，可以加 `--skip-postfix` 加速循環：

```bash
./.venv/bin/python word_engine.py review \
  --md refine.md --params params.yaml \
  --skip-postfix --label "quick-check"
```

等確認方向正確後，再執行一次完整 review（不加 `--skip-postfix`）。

---

## 7. 常見問題

**Q: QC 失敗了怎麼辦？**
修正 `refine.md` 或 `params.yaml` 後重新執行 `review`。

**Q: 我想回到上一個版本？**
查看 `render_state.json` 的 history，找到上一版的 docx 路徑直接使用。

**Q: 版本太多了怎麼清理？**
目前需手動刪除 `documents/` 下不需要的版本。自動清理計畫在 Phase 3。
