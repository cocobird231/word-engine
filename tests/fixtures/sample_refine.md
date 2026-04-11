# 專案概述

本文件為 Word Engine 測試用範例文件。

## 背景說明

這是一份用於驗證 Word Engine Phase 1 各模組功能的測試文件。

### 技術架構

系統採用 Python 開發，主要模組包括：

- Loader：讀取 Markdown 與 YAML
- Linter：結構檢查
- Validator：參數驗證
- Renderer：渲染 .docx

```python
def hello():
    print("Hello, Word Engine!")
```

## 下一步計畫

完成 Phase 1 後將進入 Phase 2，補齊進階功能。

| 階段 | 目標 | 狀態 |
|------|------|------|
| Phase 1 | MVP 閉環 | 進行中 |
| Phase 2 | 品質強化 | 待開始 |
