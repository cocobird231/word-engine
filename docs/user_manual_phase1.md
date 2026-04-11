# Word Engine Phase 1 使用手冊

## 簡介
Word Engine 是將 Markdown (`.md`) 轉為 `.docx` 與 `.pdf` 的文件渲染引擎。
目前處於 **Phase 1**，支援基本元素：標題 (H1~H3)、段落、列表、程式碼區塊。

## 安裝與環境準備
確保您的環境位於 `word-engine` 專案目錄下，並已啟動虛擬環境：
```bash
cd /home/cococlaw/.openclaw/workspace/word-engine
source .venv/bin/activate
```

## 測試範例檔案位置
為了讓您能直接驗收，我們準備了以下測試檔案：
- **正確的範例**：`examples/phase1/valid_source.md`
- **錯誤的範例**（會被 QC 擋下）：`examples/phase1/invalid_source.md`
- **參數檔**：`examples/phase1/params_basic.yaml`

---

## 驗收指令說明

本引擎提供「分步執行」與「一鍵執行」模式。

### 1. 執行 QC 檢查 (Quality Control)
此指令會檢查 markdown 的語法問題及 YAML 參數是否合法，並吐出檢驗報告。

**測試正確檔案：**
```bash
python word_engine.py qc --md examples/phase1/valid_source.md --params examples/phase1/params_basic.yaml
```
> 您應會看到 `✅ PASSED`。

**測試錯誤檔案：**
```bash
python word_engine.py qc --md examples/phase1/invalid_source.md --params examples/phase1/params_basic.yaml
```
> 您應會看到 `❌ FAILED`，並指出「標題跳級」、「未閉合的程式碼區塊」等錯誤。

### 2. 渲染 DOCX (Render)
當 QC 通過後，可以將 Markdown 渲染為 Word 文件。
```bash
python word_engine.py render --md examples/phase1/valid_source.md --params examples/phase1/params_basic.yaml --output out.docx
```
> 您可以在目錄下找到 `out.docx`，下載查看其內容是否包含標題、段落、清單與程式碼區塊。

### 3. 匯出 PDF (Export)
將剛才生成的 `.docx` 轉換為 `.pdf`。
```bash
python word_engine.py export --docx out.docx --output out.pdf
```
> 引擎會呼叫 LibreOffice 背景轉檔，完成後您會看到 `out.pdf`。

### 4. 一鍵端到端執行 (Run)
若想一次跑完 `QC -> Render -> Export`，可以使用 run 指令：
```bash
python word_engine.py run --md examples/phase1/valid_source.md --params examples/phase1/params_basic.yaml
```
> 此指令會自動在目錄下產生 `output.docx` 與 `output.pdf`。若 QC 未通過，流程會自動中斷。
