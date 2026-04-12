# 圖表 Caption 與編號示範

本文件示範 word-engine 的圖表 caption 功能，包含 `flat` 與 `chapter` 兩種編號模式。

## 第一章：無序圖表（Flat 模式）

使用 `flat` 模式時，圖表從整份文件頭開始連續計數，不受章節影響。

### 圖片範例

下方為示範圖片（若圖片檔案不存在，會顯示佔位符）：

![系統整體架構圖](assets/diagram_01.png)

系統架構如上圖所示，分為三個主要層級。

### 表格範例

下方為功能比較表：

| 功能 | Phase 1 | Phase 2 |
|------|---------|---------|
| Markdown 渲染 | ✅ | ✅ |
| 封面頁 | ❌ | ✅ |
| 目錄 | ❌ | ✅ |
| 圖表 Caption | ❌ | ✅ |

## 第二章：章節圖表（Chapter 模式）

使用 `chapter` 模式時，圖表編號以章節號為前綴，如「圖 2-1」。

> **注意**：使用本文件搭配 `params_caption_chapter.yaml` 可觀察 chapter 模式效果。

### 圖片（Chapter 模式下的圖 2-1）

![Phase 2 架構示意圖](assets/diagram_02.png)

### 表格（Chapter 模式下的表 2-1）

| 模組 | 功能描述 |
|------|---------|
| caption.py | 提供 `CaptionCounter`，管理 flat/chapter 編號 |
| cross_reference.py | 提供 `ReferenceRegistry`，管理 `{{ref:*}}` 解析 |
