# 通用 Word 引擎設計規範 v1.0

## 1. 目標

建立一套可重複使用、可參數化、可驗證品質的文件產製系統，用於將 Markdown 專案筆記轉換為高品質的 `.docx` 與 `.pdf` 專案文件，並支援雲端同步、版本化管理與後續修訂。

本引擎的核心設計原則如下：

1. **語意編修與格式渲染分離**
   - `refine.md` 的生成由文書蝦蝦（模型）負責。
   - `word-engine` 負責檢查、正規化、渲染、匯出、同步與紀錄。
2. **可參數化**
   - 所有文件風格與輸出規則由 `params.yaml` 控制。
3. **可驗證**
   - 引擎需具備類似 CI 的 lint / validate / quality control 能力。
4. **可修正**
   - 初次 render 後，允許文書蝦蝦透過參數修正或 LibreOffice UNO API 後修。
5. **可追蹤**
   - 所有輸出、參數、refine 檔與 log 必須保留於專案目錄中，便於重製與稽核。

---

## 2. 責任邊界

### 2.1 文書蝦蝦（模型層）負責

1. 讀取完整 `source.md`
2. 語意理解與重構
3. 修正標題階層與段落組織
4. 改寫前言
5. 潤飾語句通順度與正式程度
6. 產出：
   - `refine_vX.Y.md`
   - `params_vX.Y.yaml`
7. 根據 QC 報告進行人工智慧式修正

### 2.2 通用 Word 引擎（程式層）負責

1. 讀取 `refine.md` 與 `params.yaml`
2. 進行 lint / validate / normalize
3. 將內容渲染為 `.docx`
4. 必要時執行 UNO API 後修
5. 匯出 `.pdf`
6. 產生 render / review log
7. 上傳 Nextcloud
8. 產生分享連結（若可用）

### 2.3 不應由引擎處理的事項

以下項目不應作為純 rule-based engine 的主要責任：

- 前言內容創作
- 語意摘要
- 大幅改寫段落語氣
- 對內容做主觀論述增刪
- 判斷哪一段更有說服力

---

## 3. 工作流程

### Phase 1：來源準備

輸入：
- `source.md`
- `assets/`（若已有）
- 專案 metadata

### Phase 2：Refine

由文書蝦蝦執行：
1. 閱讀完整 Markdown
2. 修標題階層
3. 重寫前言
4. 重整段落與語句
5. 產出 `refine_vX.Y.md`
6. 產出 `params_vX.Y.yaml`

### Phase 3：QC / Validate / Normalize

由引擎執行：
1. `lint`：檢查 markdown 與結構規範
2. `validate`：檢查 YAML schema、路徑、字型、模式選項
3. `normalize`：修正低風險格式問題
4. 產出 `qc_report`

### Phase 4：Render

1. 套用參數檔樣式
2. 生成封面
3. 套用目錄與標題層級
4. 插入圖片、圖說、表格、程式碼區塊
5. 建立 cross-reference 標記
6. 產出 `.docx`

### Phase 5：Post-fix

1. 由文書蝦蝦檢查 render 結果
2. 若需修正：
   - 優先修改 `params.yaml`
   - 次要使用 UNO API 直接修文件
3. 重新 render 或直接 post-edit

### Phase 6：Export & Sync

1. 更新目錄 / 欄位
2. 匯出 `.pdf`
3. 上傳到 Nextcloud
4. 產生分享連結
5. 寫入 log

---

## 4. 引擎模組設計

建議模組：

### 4.1 `loader`
負責：
- 讀取 `refine.md`
- 讀取 `params.yaml`
- 掃描 `assets/`
- 載入專案 metadata

### 4.2 `linter`
負責：
- 檢查標題跳級
- 檢查空標題
- 檢查 code fence 是否閉合
- 檢查圖片連結語法
- 檢查 markdown table 是否可解析
- 檢查引用與 bibliography 是否可匹配

### 4.3 `validator`
負責：
- 驗證 YAML schema
- 驗證必要參數是否存在
- 驗證色碼、字型、路徑、枚舉值是否合法
- 驗證 numbering mode、citation style 是否支援

### 4.4 `normalizer`
負責低風險自動修正：
- 清除多餘空白行
- 修尾端空白
- 補 default params
- 修正非法顏色值為 fallback
- 整理空白段落

### 4.5 `renderer`
負責：
- Markdown AST 轉文件結構
- 段落渲染
- 標題渲染
- code block 渲染
- 表格渲染
- 圖片與 caption 渲染
- 書籤與 cross-reference 標記
- `.docx` 輸出

### 4.6 `post_processor_uno`
負責：
- 開啟 `.docx`
- 修欄位、目錄、頁碼、段落細節
- 進行必要的局部格式修正
- 另存 `.docx`

### 4.7 `exporter`
負責：
- 利用 LibreOffice 匯出 `.pdf`
- 檢查輸出成功與檔案完整性

### 4.8 `syncer`
負責：
- 上傳 refine / params / docx / pdf / logs 至 Nextcloud
- 建立分享連結
- 回報雲端路徑與狀態

### 4.9 `reporter`
負責：
- 產出 render log
- 產出 qc report
- 產出 review log
- 提供人類可閱讀報告

---

## 5. QC / CI 風格檢查規範

### 5.1 結構檢查

- 標題不得跳級（H1 → H3）
- 標題後必須有內容或子節
- 不可有空標題
- 不可有連續過多空白段
- 章節長度不得異常失衡（可列 warning）

### 5.2 內容檢查

- 文件需有前言（若設定要求）
- 若有圖片引用，圖片必須存在或可下載
- 若有表格，表格必須可解析
- 若有程式碼區塊，fence 必須配對完整

### 5.3 格式檢查

- 字型映射需存在 fallback
- 顏色必須為合法 HEX
- numbering mode 必須為 `flat` 或 `chapter`
- 參考文獻格式必須為 `ieee` 或 `apa`

### 5.4 參照檢查

- 所有圖表引用都必須有對應實體
- 所有 bibliography 引用都必須可對應
- TOC 階層不得超出定義範圍

### 5.5 輸出檢查

- `.docx` 必須成功生成
- `.pdf` 必須成功匯出
- Nextcloud 上傳必須成功
- 分享連結（若啟用）必須成功回傳

---

## 6. 修正策略

### 6.1 自動修正（引擎可做）

- 補預設值
- 清理空白行
- 修正簡單格式錯誤
- 清理尾端多餘段落
- 將無效參數替換為預設 fallback

### 6.2 模型修正（文書蝦蝦負責）

- 前言重寫
- 語句潤飾
- 標題語意重組
- 內容結構調整
- 引用與論述補強

### 6.3 UNO 後修

適合處理：
- 頁碼/頁首頁尾微調
- 目錄更新
- 局部格式修補
- 最終版面確認

---

## 7. 專案資料夾建議結構

```text
word-engine/
├─ README.md
├─ .gitignore
├─ specs/
│  └─ word_engine_design_spec_v1.0.md
├─ configs/
│  └─ params.schema.v1.0.yaml
├─ docs/
│  ├─ architecture.md
│  ├─ qc_rules.md
│  └─ nextcloud_sync.md
├─ src/
│  ├─ loader/
│  ├─ linter/
│  ├─ validator/
│  ├─ normalizer/
│  ├─ renderer/
│  ├─ post_processor_uno/
│  ├─ exporter/
│  ├─ syncer/
│  └─ reporter/
├─ tests/
│  ├─ fixtures/
│  ├─ unit/
│  └─ integration/
├─ examples/
│  ├─ sample_project/
│  ├─ sample_refine.md
│  └─ sample_params.yaml
└─ scripts/
   ├─ render_doc.py
   ├─ export_pdf.py
   └─ sync_nextcloud.py
```

---

## 8. Git 管理原則

1. `specs/` 放正式規格，不放隨手草稿
2. `configs/` 放 schema 與預設樣式檔
3. `src/` 只放核心程式
4. `examples/` 放最小可重現案例
5. `tests/` 區分 unit / integration
6. 所有版本號需反映於：
   - spec 檔名
   - params schema 檔名
   - release tag

---

## 9. 模型與代理人設計建議

### 9.1 不建議直接把主腦升級成 Opus 4.6 來長期寫程式
原因：
- 主腦負責總控、協調、記憶與對外溝通
- 程式開發會大量消耗上下文與專注力
- 將總控與實作拆開，更利於管理與擴充

### 9.2 建議新增一隻「程式蝦蝦」
建議建立專職 agent，例如：`code_shrimp`

職責：
- 開發 `word-engine`
- 撰寫測試
- 驗證 UNO / Nextcloud / render pipeline
- 維護 CI 與版本管理

主腦龍蝦負責：
- 設計規範
- 任務拆解
- 驗收與整合
- 監督文書蝦蝦與程式蝦蝦協作

### 9.3 模型建議
- **主腦龍蝦**：維持目前總控角色即可
- **文書蝦蝦**：維持文件優化與 refine 任務
- **程式蝦蝦**：可配置較強模型進行程式開發與驗證

若要在成本與品質平衡：
- 日常開發：`openai/gpt-5.4` 或 `anthropic/claude-sonnet-4-6`
- 難題設計 / 大重構 / 複雜除錯：`anthropic/claude-opus-4-6`

**建議結論**：
先新增 `程式蝦蝦` 比直接把主腦整體升級成 Opus 更合理。

---

## 10. v1.0 定案結論

本規範定義以下核心原則：

1. `refine.md` 由模型負責，不由引擎主動改寫。
2. `word-engine` 提供 CI 式 lint / validate / normalize / render / export / sync。
3. 參數檔使用 YAML，並作為唯一樣式與輸出控制來源。
4. 圖表編號需支援 `flat` / `chapter`。
5. 參考文獻與文內參照需支援 `IEEE` / `APA`。
6. 允許 LibreOffice UNO API 作為後修層。
7. 建議新增專職程式代理人負責後續開發。
