# 交叉引用示範文件

## 說明

本文件展示 word-engine 的 `{{ref:*}}` 交叉引用語法，包含：
- 圖片引用（forward reference：引用在圖之前）
- 表格引用
- 章節引用
- 多重引用

---

# 第一章：系統架構

本章介紹系統的整體架構。系統架構如 {{ref:fig-1}} 所示（forward reference，圖在段落之後）。

## 1.1 架構圖

![系統架構示意](assets/arch.png)

如 {{ref:fig-1}} 所示，系統分為前、中、後三個層次。

## 1.2 模組清單

{{ref:tbl-1}} 列出了系統中的主要模組：

| 模組名稱 | 所在目錄 | 主要職責 |
|---------|---------|---------|
| loader | src/loader | 讀取 MD 與 YAML |
| linter | src/linter | Markdown 結構檢查 |
| validator | src/validator | YAML 參數驗證 |
| renderer | src/renderer | 文件渲染 |

---

# 第二章：功能詳解

本章說明各模組的詳細功能，如 {{ref:sec-1}} 所述，整個架構以三層為基礎。

## 2.1 Renderer 功能

Renderer 模組的功能如 {{ref:tbl-2}} 所示：

| 功能 | 說明 | Phase |
|------|------|-------|
| Heading 渲染 | H1~H3 | Phase 1 |
| Table 渲染 | 含 caption | Phase 2 |
| Cross-reference | {{ref:*}} 語法 | Phase 2 |

詳細的 renderer 架構圖請見 {{ref:fig-2}}。

## 2.2 第二張圖

![Renderer 架構圖](assets/renderer.png)

---

# 第三章：總結

如 {{ref:sec-1}} 至 {{ref:sec-2}} 所述，本系統涵蓋了從 Markdown 輸入到 Word/PDF 輸出的完整流程。

{{ref:tbl-1}} 中列出的所有模組均已完成 Phase 2 實作，並通過所有單元測試。
