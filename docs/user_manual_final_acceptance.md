# word-engine Phase 1~3 總驗收手冊

本手冊讓您完整驗證 word-engine 從 Phase 1 到 Phase 3 的所有功能。

---

## 環境準備

```bash
cd /home/cococlaw/.openclaw/workspace/word-engine
source .venv/bin/activate
```

---

## 驗收檔案說明

| 檔案 | 路徑 | 用途 |
|------|------|------|
| 正確案例 md | `examples/final/correct_full.md` | 包含所有功能的正確文件 |
| 錯誤案例 md | `examples/final/error_full.md` | 故意包含 6 個錯誤 + 1 個警告 |
| 驗收用 params | `examples/final/params_full.yaml` | 啟用所有 Phase 1~3 功能 |

---

## Part A：錯誤案例 QC 驗收（驗 linter 是否正確攔截）

### A1 執行 QC
```bash
python word_engine.py qc \
  --md examples/final/error_full.md \
  --params examples/final/params_full.yaml
```

**預期結果：**
```
Result: ❌ FAILED
Errors:   6
Warnings: 1
❌ ERROR: Line 7:  Heading jump from H1 to H3
❌ ERROR: Line 17: Unclosed inline code (odd number of backticks)
❌ ERROR: Line 21: Unclosed bold marker (**)
❌ ERROR: Line 25: Empty heading (H1)
❌ ERROR: Line 29: Heading jump from H1 to H3
❌ ERROR: Line 38: Unclosed code fence (``` not closed)
⚠️  WARN: Line 33: More than 3 consecutive blank lines
```

### A2 修正後驗收
修改 `error_full.md` 修正上述錯誤後，再次執行 QC，直到看到：
```
Result: ✅ PASSED
```

---

## Part B：完整功能 Render 驗收（一次驗 Phase 1~3 全部）

### B1 QC 確認
```bash
python word_engine.py qc \
  --md examples/final/correct_full.md \
  --params examples/final/params_full.yaml
```
預期：`Result: ✅ PASSED`

### B2 Render（產生 docx）
```bash
python word_engine.py render \
  --md examples/final/correct_full.md \
  --params examples/final/params_full.yaml \
  --output out_acceptance.docx
```
預期：`[RENDER] Successfully rendered: out_acceptance.docx`

### B3 Export（產生 pdf）
```bash
python word_engine.py export \
  --docx out_acceptance.docx \
  --output out_acceptance.pdf
```
預期：`[EXPORT] Successfully exported: out_acceptance.pdf`

### B4 開啟 out_acceptance.docx 目視驗收
用 Word 或 LibreOffice 開啟，逐項確認：

| 功能 | 預期結果 |
|------|---------|
| **封面** | 有標題「word-engine Phase 1~3 驗收文件」、subtitle、project_id、版本、日期 |
| **目錄** | 有目錄標題「目錄」，內容顯示佔位文字或按 F9 後展開 |
| **H1/H2/H3** | 標題層級對應不同字體大小 |
| **段落** | 正常中文段落顯示 |
| **無序/有序列表** | 列表項目正確顯示，含格式化 |
| **程式碼區塊** | 等寬字型 + 灰色背景 |
| **inline code** | `Consolas 字型 + 灰色底` |
| **粗體** | **文字以粗體顯示** |
| **斜體** | *文字以斜體顯示* |
| **表格** | 有表頭 + 資料列，第一欄帶粗體格式 |
| **圖片佔位符** | 圖片不存在時顯示 `[圖片: ...]` 佔位符 |
| **圖表 Caption** | 圖片下方有「圖 1 ...」、表格上方有「表 1 ...」(Phase 3: SEQ field) |
| **按 F9 更新** | Caption 數字、目錄條目正確顯示（SEQ/TOC/REF field 更新） |
| **交叉引用** | 文內 {{ref:*}} 已替換（Phase 3: REF field，需 F9 更新） |

---

## Part C：完整 Review Loop 驗收

### C1 一鍵 review（QC → Render → Postfix → Export）
```bash
python word_engine.py review \
  --md examples/final/correct_full.md \
  --params examples/final/params_full.yaml \
  --project-dir . \
  --label "final-acceptance"
```
預期：所有步驟成功，末尾顯示 review_state 報告

### C2 查看狀態
```bash
python word_engine.py status --project-dir .
```
預期：4 個步驟顯示 ✅，最後一步 review_checked 顯示 ⏳（等人工確認）

### C3 人工確認後標記
```bash
python word_engine.py mark-reviewed --project-dir .
```
預期：提示 `Version vN marked as reviewed.`

### C4 再次查看狀態確認完成
```bash
python word_engine.py status --project-dir .
```
預期：所有 5 個步驟顯示 ✅，最後顯示 `🎉 Review round complete!`

---

## Part D：執行所有單元測試
```bash
./.venv/bin/pytest -q tests/unit/
```
預期：`178 passed`

---

## 功能覆蓋對照表

| 功能 | Phase | Part A | Part B | Part C |
|------|-------|--------|--------|--------|
| Heading 層級 | 1 | ✅ | ✅ | ✅ |
| 段落渲染 | 1 | | ✅ | |
| 無序/有序列表 | 1 | | ✅ | |
| 程式碼區塊 + 網底 | 1 | | ✅ | |
| inline code + 網底 | 1+3 | ✅ | ✅ | |
| 封面頁 | 2 | | ✅ | |
| TOC field | 2 | | ✅ | |
| 圖片渲染 + caption | 2+3 | | ✅ | |
| 表格渲染 + caption | 2+3 | | ✅ | |
| caption SEQ field | 3 | | ✅ | |
| 粗體/斜體 | 3 | ✅ | ✅ | |
| 交叉引用 REF field | 3 | | ✅ | |
| Lint：heading jump | 1 | ✅ | | |
| Lint：unclosed fence | 1 | ✅ | | |
| Lint：inline code unclosed | 3 | ✅ | | |
| Lint：bold unclosed | 3 | ✅ | | |
| Lint：empty heading | 1 | ✅ | | |
| Versioned rerender | 2 | | | ✅ |
| UNO postfix (socket bridge) | 3 | | ✅ | ✅ |
| mark-reviewed / status | 3 | | | ✅ |

---

## 能力邊界說明

| 項目 | 說明 |
|------|------|
| TOC/SEQ/REF field 顯示 | 需 F9 或 UNO postfix 更新後才顯示最終值 |
| 圖片 | 目前僅支援本地圖片路徑；不存在時顯示佔位符 |
| 雲端同步（Nextcloud） | stub（尚未實作），未來 Phase 可接入 |
| chapter mode SEQ | 支援 per-chapter SEQ name；STYLEREF 模式保留未來 |
