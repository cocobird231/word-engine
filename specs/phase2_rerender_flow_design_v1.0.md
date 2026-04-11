# Word Engine Phase 2 - Rerender Flow 設計稿 v1.0

## 1. 設計目標

提供一套讓文書蝦蝦可以安全、可追蹤地進行「修改 params → 重新 render → UNO 後修 → export」的工作流程。核心要求：

1. **可重複執行**：同一份 refine.md 可以多次 render，不同版本的 params 對應不同版本輸出
2. **不互相覆蓋**：每次 render 輸出都有版本號，可以追溯到對應的 params
3. **UNO 後修可選**：render 完成後，文書蝦蝦可選擇是否進入 UNO 修正層，再 export

---

## 2. 版本化輸出機制

### 2.1 版本號定義
每次執行 render 會自動遞增一個 **render 版本號**，格式為 `v<N>`。

版本號由 `render_state.json`（存放在 project 目錄下）負責管理：

```json
{
  "project_id": "TEST001",
  "current_version": 3,
  "history": [
    {
      "version": 1,
      "params_snapshot": "documents/params/params_v1.yaml",
      "output_docx": "documents/report_v1.docx",
      "render_log": "code/logs/render_v1.log",
      "timestamp": "2026-04-12T00:00:00"
    }
  ]
}
```

### 2.2 每次 render 保留的 artifacts

| 類型 | 路徑格式 | 說明 |
|------|----------|------|
| params 快照 | `documents/params/params_v<N>.yaml` | render 當下所使用的 params 備份 |
| 輸出 docx | `documents/report_v<N>.docx` | render 輸出 |
| render log | `code/logs/render_v<N>.log` | render 過程與 QC 結果 |
| refine.md 快照 | `documents/refine_v<N>.md` | （若 refine 有更新）對應版本的 markdown |

最新版本另外保留 symlink 或直接路徑給 export 使用：
- `documents/latest.docx` → 指向最新版本 docx

---

## 3. 工作流程圖（文字版）

```
文書蝦蝦工作流程
─────────────────────────────────────────────────────────────────

[1] 準備階段
    refine.md + params.yaml (初始版本 v1)
            │
            ▼
[2] word-engine qc
    └── QC PASS? ──NO──→ 文書蝦蝦修正 refine.md 重跑 QC
            │ YES
            ▼
[3] word-engine render [--version]
    ├── 自動遞增版本號 (v1, v2, ...)
    ├── 備份 params.yaml → documents/params/params_vN.yaml
    ├── 輸出 documents/report_vN.docx
    └── 寫入 render_state.json
            │
            ▼
[4] 文書蝦蝦檢查 .docx
    ├── 不滿意 params 樣式？
    │   └──→ 修改 params.yaml → 回到 [3] (版本 +1)
    │
    └── 需要局部修正？
        └──→ word-engine postfix (UNO 後修) → [5]
            │ 滿意
            ▼
[5] word-engine export
    ├── 匯出 documents/report_vN.pdf
    └── (Phase 3) 上傳 Nextcloud
```

---

## 4. CLI 設計

### 4.1 新增指令：`word-engine rerender`

這是 Phase 2 新增的核心指令，語意明確為「我已修改 params，請重新 render」：

```bash
# 使用當前 params.yaml 重新 render（自動遞增版本）
word-engine rerender --params documents/refine_params.yaml

# 重新 render 並指定輸出目標版本名稱（可選）
word-engine rerender --params documents/refine_params.yaml --label "adjust-heading-indent"
```

### 4.2 新增指令：`word-engine postfix`

提供 UNO 後修的入口（Phase 2 先為 stub，Phase 3 真正實作）：

```bash
word-engine postfix --docx documents/report_v3.docx
```

### 4.3 沿用指令：`word-engine export`

export 可從最新版 docx 或指定版本匯出：

```bash
# 匯出最新版
word-engine export --docx documents/latest.docx --output documents/final.pdf

# 匯出指定版本
word-engine export --docx documents/report_v3.docx --output documents/final_v3.pdf
```

---

## 5. `post_processor_uno` 插入點

```
render 完成 (.docx 產出)
        │
        ▼
post_processor_uno.run_post_process(docx_path, params)
        │
        ├── Phase 1 / Phase 2 初期：pass-through，直接回傳 docx_path
        │
        └── Phase 2 完整版：
            ├── 開啟 docx
            ├── 更新 TOC fields
            ├── 更新 heading 頁碼
            ├── 局部格式補正（文書蝦蝦透過 CLI 下修正指令）
            └── 另存 docx
        │
        ▼
exporter.export_pdf(docx_path, pdf_path)
```

UNO 後修作為一個**可選層**，設計原則：
- 不在 `run_all` 預設流程中強制跑（避免沒有 LibreOffice UNO 環境的情況炸掉）
- 透過 `word-engine postfix` 獨立觸發
- 後修完成後的 docx 直接取代原版本，或另存為 `report_vN_postfixed.docx`

---

## 6. 版本衝突防護

- 若 `render_state.json` 不存在（全新 project），從 v1 開始
- 若同一版本號的輸出已存在，**不自動覆蓋**，而是報錯並提示：
  - 建議使用 `--force` 覆蓋
  - 或讓系統自動遞增到下一版本
- 設計原則：**寧願多一個版本，也不要靜默覆蓋**

---

## 7. Phase 2 第一批實作建議

基於上述設計，我建議 Phase 2 的第一批實作按以下順序進行：

### Priority 1 (本輪)
- `render_state.py`：版本化狀態管理模組（讀寫 render_state.json）
- `word-engine rerender` 指令實作
- params 版本快照機制（render 時自動備份 params）

### Priority 2 (下輪)
- `cover` 基本版（封面：標題 + 版本 + 日期）
- `toc` 基本版（目錄插入）

### Priority 3 (後續)
- `post_processor_uno` 真正實作（LibreOffice UNO API）
- `caption / numbering`
- `cross-reference`

---

## 8. 設計原則小結

1. **rerender = 版本 +1 + artifacts 保存**，不是蓋掉前一版
2. **params snapshot 是 render 的一部分**，要一起存
3. **UNO 後修是可選的獨立步驟**，不強制綁在主流程
4. **CLI 語意要清楚**：rerender vs render 語意不同，各有其用
