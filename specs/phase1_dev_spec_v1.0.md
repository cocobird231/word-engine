# Word Engine Phase 1 開發規範與架構 (MVP) v1.0

## 1. 階段目標

建立「最小可跑通閉環 (MVP)」，確保系統能從 Markdown 與 YAML 參數檔，經過檢查與渲染，最終輸出 `.docx` 與 `.pdf`。

Phase 1 **不涉及**：
- LibreOffice UNO API 後修（Phase 2）
- Nextcloud 雲端同步（Phase 3）
- 封面排版（Phase 2）
- 目錄 / 圖表編號 / 交叉引用 / 參考文獻（Phase 2）

---

## 2. 使用者流程（文書蝦蝦視角）

```
椰子大大提供 source.md
        ↓
文書蝦蝦閱讀 → 產出 refine.md + params.yaml
        ↓
word-engine qc → lint / validate / normalize → 產出 qc_report
        ↓
    ┌─ QC 沒過 → 文書蝦蝦修正 refine.md → 重跑 qc
    └─ QC 通過 ↓
        ↓
word-engine render → 產出 .docx
        ↓
文書蝦蝦檢查 .docx
        ↓
    ┌─ 有問題 → 修改 params.yaml 重新 render
    └─ 沒問題 ↓
        ↓
word-engine export → 產出 .pdf
```

---

## 3. 模組範圍與職責

### 3.1 Loader
- 讀取 `refine.md`（或 `source.md`）與 `params.yaml`
- 掃描 `assets/` 目錄
- 載入專案 metadata
- 回傳結構化的載入結果供後續模組使用

### 3.2 Linter
- 對 Markdown 進行結構檢查：
  - 標題跳級（H1 → H3）
  - 空標題
  - Code fence 未閉合
  - 圖片連結語法錯誤
  - 表格語法是否可解析
- 輸出：錯誤與警告列表

### 3.3 Validator
- 驗證 `params.yaml` 是否符合 Schema：
  - 資料型別正確性
  - 必要參數是否存在
  - 色碼格式合法（HEX）
  - 枚舉值合法（如 numbering_mode: flat / chapter）
  - 字型名稱與路徑有效性
- 實作：基於 `jsonschema` 或自訂檢查邏輯

### 3.4 Normalizer
- 低風險自動修正：
  - 清除多餘空白行
  - 修正尾端空白
  - 補齊預設參數值（params fallback）
  - 清理空白段落
- **不修改** Markdown 核心語意與結構

### 3.5 Renderer (Basic)
- 將正規化後的 Markdown AST 與參數轉換為 `.docx`
- **Phase 1 支援元素**：
  - 標題（Heading 1~3）
  - 段落（Paragraph，含 body_1 樣式）
  - 列表（Bullet & Numbered List）
  - 程式碼區塊（Code Block，含背景色與等寬字型）
  - 圖片（Image，僅本地圖片）
  - 表格（Table，含表頭粗體與背景色）
- **Phase 1 不支援（留 Stub）**：
  - 封面（Cover）
  - 目錄（TOC）
  - 圖表編號與交叉引用（Cross-reference）
  - 參考文獻（Bibliography）
  - 附錄（Appendix）
  - 註腳（Footnotes）
  - 方程式（Equations）

### 3.6 Exporter (Basic)
- 將 `.docx` 匯出為 `.pdf`
- 實作：LibreOffice CLI Headless（`soffice --headless --convert-to pdf`）
- 不涉及 UNO API 內部操作
- 需驗證輸出檔案存在且完整

### 3.7 Reporter
- 統整 Linter 與 Validator 結果，產出結構化 `qc_report`
- QC 報告須讓文書蝦蝦能明確知道「哪裡要改」
- 產出基本 `render_log`（記錄渲染過程與結果）

---

## 4. CLI 介面設計

分步命令為 **主介面**，一鍵 run 為 **輔助介面**。

```bash
# 主介面（分步操作）
word-engine qc     --md refine.md --params params.yaml    # 執行 QC 流程，產出報告
word-engine render --md refine.md --params params.yaml    # 執行渲染，產出 .docx
word-engine export --docx output.docx                     # 匯出 .pdf

# 輔助介面（一鍵串起）
word-engine run    --md refine.md --params params.yaml    # qc → render → export 全跑
```

---

## 5. Stub 預留介面

以下功能在 Phase 1 建立空殼函式，確保 pipeline 骨架完整：

| 模組 | Stub 函式 | Phase 1 行為 | 預計實作階段 |
|------|----------|-------------|------------|
| `post_processor_uno` | `run_post_process(docx_path, params)` | 直接 pass-through | Phase 2 |
| `syncer` | `sync_to_cloud(files, config)` | 回傳 skip 狀態 | Phase 3 |
| Renderer 內部 | `insert_toc()`, `insert_cover()`, `insert_cross_ref()`, `insert_bibliography()` | pass / no-op | Phase 2 |
| Normalizer 內部 | `normalize_punctuation()`, `convert_fullwidth()` | pass | Phase 2 |

---

## 6. 技術選型

| 項目 | 選擇 | 理由 |
|------|------|------|
| 語言 | Python | 生態最適合 docx 操控 + LibreOffice 整合 |
| Markdown 解析 | `markdown-it-py` | AST 可控性高，plugin 擴展性好 |
| docx 產生 | `python-docx` | 成熟穩定，足以支撐 basic renderer |
| PDF 匯出 | LibreOffice CLI Headless | 避開 UNO 複雜度，Phase 1 足夠 |
| YAML 驗證 | `jsonschema` | 可直接對 params schema 做結構化驗證 |

---

## 7. 架構設計原則

1. **鬆耦合**：CLI 層、Pipeline 層、各模組之間必須透過明確介面溝通，不可緊耦合寫死
2. **可擴充**：每個模組介面須保留未來接入 UNO 後修與 Nextcloud syncer 的擴充點
3. **可獨立測試**：每個模組都能獨立進行 unit test，不依賴其他模組才能跑
4. **Pipeline 骨架不變**：後續 Phase 只是「填入」stub 的實作，不需改動主 pipeline 流程

---

## 8. 專案目錄結構（Phase 1）

```text
word-engine/
├── README.md
├── .gitignore
├── specs/
│   ├── word_engine_design_spec_v1.0.md
│   └── phase1_dev_spec_v1.0.md          ← 本文件
├── configs/
│   └── params.schema.v1.0.yaml
├── src/
│   ├── __init__.py
│   ├── cli.py                           ← CLI 入口（argparse / click）
│   ├── pipeline.py                      ← Pipeline 串接邏輯
│   ├── loader/
│   │   ├── __init__.py
│   │   └── loader.py
│   ├── linter/
│   │   ├── __init__.py
│   │   └── linter.py
│   ├── validator/
│   │   ├── __init__.py
│   │   └── validator.py
│   ├── normalizer/
│   │   ├── __init__.py
│   │   └── normalizer.py
│   ├── renderer/
│   │   ├── __init__.py
│   │   └── renderer.py
│   ├── exporter/
│   │   ├── __init__.py
│   │   └── exporter.py
│   ├── reporter/
│   │   ├── __init__.py
│   │   └── reporter.py
│   ├── post_processor_uno/              ← Phase 1 stub
│   │   ├── __init__.py
│   │   └── post_processor.py
│   └── syncer/                          ← Phase 1 stub
│       ├── __init__.py
│       └── syncer.py
├── tests/
│   ├── fixtures/
│   │   ├── sample_refine.md
│   │   └── sample_params.yaml
│   ├── unit/
│   └── integration/
├── validation/
│   └── validation_spec_v0.1.md
├── changelog/
│   └── CHANGELOG.md
└── scripts/
```

---

## 9. 驗證與交付標準

Phase 1 完成時必須滿足：

1. **端到端閉環**：輸入測試用 `refine.md` + `params.yaml`，執行 `word-engine run`，成功產出 `.docx` 與 `.pdf`
2. **分步可用**：`qc`、`render`、`export` 三個指令各自可獨立執行
3. **QC 報告有效**：給予格式錯誤的 YAML 或 Markdown 時，qc_report 能正確指出錯誤位置與類型
4. **渲染品質**：產出的 `.docx` 與 `.pdf` 可正常開啟，且包含所有 Phase 1 支援的元素（heading / paragraph / list / code / image / table）
5. **測試覆蓋**：每個模組至少有基本 unit test
