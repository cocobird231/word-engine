# Word Engine 測試文件

這是一份完全符合 Phase 1 規範的 Markdown 文件。它的結構正確，可以用來驗證 `word-engine qc` 和 `word-engine render`。

## 功能展示

以下是目前 Phase 1 支援的基本元素：

### 1. 段落
Word Engine 會把相連的文字解析為同一個段落，並且支援 `params.yaml` 中的對齊方式與縮排設定。

### 2. 無序列表
以下是一個無序列表範例：
- 這是第一項
- 這是第二項
  - 這是第二項的子項目
  - 這是第二項的另一個子項目
- 這是第三項

### 3. 有序列表
以下是一個有序列表範例：
1. 第一步：載入 `refine.md`
2. 第二步：載入 `params.yaml`
3. 第三步：執行 QC 檢查
   1. Linter 檢查
   2. Validator 檢查
4. 第四步：渲染成 `.docx`

### 4. 程式碼區塊
這是 Phase 1 的最後一項功能，程式碼會被包裝在等寬字型中，並且有縮排：

```python
def hello_word_engine():
    message = "Welcome to Phase 1!"
    print(message)
```

本文件到底結束，您可以透過這份檔案驗證端到端 `md → docx → pdf` 的生成流程。