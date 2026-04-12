# Word Engine Phase 3 任務切分與實作順序 v1.0

## 總體目標
Phase 3 核心方向：把 Phase 2 已跑通的功能升級為**更原生、更完整、更可驗收**的狀態。

---

## 任務列表（依建議執行順序）

### Task 1：粗體 / 斜體 / inline code 完整 inline render
**優先級：最高（Phase 3 第一批）**

**目標：**
- `**粗體**` → docx 中以 bold 顯示
- `*斜體*` → docx 中以 italic 顯示
- `` `inline code` `` → docx 中以 Consolas + 網底顯示（Phase 2 已部分支援）
- 以上三者在**所有文字路徑**（段落、列表、表格 cell、heading）均正確渲染

**依賴：** 無（可直接開始）

**實作方式：**
- `_render_inline_content()` 已有 `strong_open/close`、`em_open/close`、`code_inline` 處理
- `_render_text_to_paragraph()` 目前只處理 backtick，需擴展支援 `**` 和 `*`
- 或改為統一使用 markdown-it 的 inline children 解析（更可靠）

**驗收方式：**
- 產出含粗體、斜體、inline code 的 docx
- 用 LibreOffice 開啟確認三種格式皆正確顯示
- python-docx 讀回驗證 run 屬性（bold/italic/font）
- 全文件搜索不殘留 `**`、`*`、`` ` `` 原始標記

---

### Task 2：Inline 相關 lint / QC 補強
**優先級：高（Task 1 完成後接續）**

**目標：**
- Linter 新增檢查：
  - 未閉合的粗體標記 `**...(缺少結尾)`
  - 未閉合的斜體標記 `*...(缺少結尾)`
  - 未閉合的 inline code 反引號 `` `...(缺少結尾) ``
- QC 報告中能列出上述問題

**依賴：** Task 1（需先確認 inline render 邏輯再定義 lint 規則）

**實作方式：**
- 在 `linter.py` 新增 inline token 分析
- 使用 markdown-it parse 後檢查 inline children 是否有異常

**驗收方式：**
- 準備包含未閉合標記的測試 md
- 執行 `word-engine qc` 驗證能列出對應錯誤
- 新增 unit test 覆蓋各種未閉合情境

---

### Task 3：Caption 升級為 Word SEQ field
**優先級：中高**

**目標：**
- 圖 / 表 caption 從靜態文字升級為 Word SEQ field
- 在 Word / LibreOffice 中按 F9 可自動更新編號
- 如刪除中間一張圖，後續編號可自動重排

**依賴：** 無直接依賴，但建議在 Task 1 後進行（inline render 穩定後再碰 field）

**實作方式：**
- 使用 OOXML `w:fldChar` + `w:instrText` 插入 `SEQ Figure` / `SEQ Table` field
- 類似 TOC field 的做法（Phase 2 已有經驗）
- chapter 模式需搭配 `STYLEREF` 或自訂 chapter 計數器

**驗收方式：**
- 產出含 SEQ field caption 的 docx
- 在 Word/LibreOffice 按 F9 驗證編號正確更新
- 刪除中間圖片後再按 F9，確認後續編號自動遞減
- python-docx 讀回檢查 `w:instrText` 包含 `SEQ`

**已知風險：**
- chapter 模式 SEQ field 較複雜，可能需搭配 `STYLEREF`
- 建議 MVP 先做 flat 模式 SEQ，再做 chapter 模式

---

### Task 4：Cross-reference 升級為 Word REF field
**優先級：中（依賴 Task 3）**

**目標：**
- `{{ref:fig-1}}` 從靜態文字替換升級為 Word REF field
- 引用指向 caption 的 SEQ bookmark
- 在 Word 中按 F9 可自動更新引用文字

**依賴：** Task 3（需要 SEQ field 的 bookmark 作為 REF 目標）

**實作方式：**
- 使用 OOXML `w:fldChar` + `w:instrText` 插入 `REF fig_1 \h`
- 指向 Task 3 中 SEQ field 建立的 bookmark
- 保留 Phase 2 的兩階段掃描架構，但渲染時改為 field 而非純文字

**驗收方式：**
- 產出含 REF field 的 docx
- 在 Word/LibreOffice 按 F9 驗證引用文字正確更新
- 刪除被引用的圖後按 F9，確認引用文字相應變化
- python-docx 讀回檢查 `w:instrText` 包含 `REF`

**已知風險：**
- REF field 需要精確的 bookmark name 對應，容易出錯
- 建議先做 figure ref MVP，穩了再擴展到 table / heading

---

### Task 5：更細粒度的 UNO / Word 後處理
**優先級：中低**

**目標：**
- 從「LibreOffice headless 重存」升級為真正的 UNO socket bridge
- 能精準執行：UpdateAllIndexes、UpdateFields
- 能做局部段落格式修正

**依賴：** Task 3, 4（SEQ / REF field 需要 field update 才能顯示）

**實作方式：**
- 使用 python-uno 建立 socket 連線到 LibreOffice
- 透過 UNO API 開啟文件 → dispatch UpdateFields → 另存

**驗收方式：**
- 執行 `word-engine postfix` 後，TOC / SEQ / REF field 均自動更新
- 用 LibreOffice 開啟確認不需再手動按 F9
- 對比 postfix 前後的 docx 內容差異

**已知風險：**
- UNO socket bridge 在不同環境設定差異大
- 若環境不支援，需能 fallback 回 headless 重存方式

---

### Task 6：Review / 交付流程補完
**優先級：低（Phase 3 最後）**

**目標：**
- review_checked 自動標記機制
- 更完整的 artifact 狀態追蹤
- 版本清理工具

**依賴：** 前 5 項完成後再補完

**實作方式：**
- 在 review loop 中加入 `mark-reviewed` CLI 子命令
- 擴充 review_state.json 的狀態欄位
- 加入 `word-engine clean` 清理舊版本

**驗收方式：**
- 完整跑一次 review → mark-reviewed → 確認狀態正確
- 清理後確認舊版本檔案被移除但歷史紀錄保留

---

## Phase 3 第一批實作建議

我建議先做 **Task 1 + Task 2**，理由：
- 粗體/斜體是使用者最直接能感知的缺失
- 不涉及複雜的 Word field 機制，風險低
- 修完後可以立刻讓椰子大大驗收
- Task 3~6 涉及 Word 原生 field，需要更多設計與測試，適合第二批

**第一批交付物：**
- 粗體/斜體/inline code 在所有路徑正確渲染
- QC 能檢測未閉合的 inline 標記
- 更新使用手冊與範例
