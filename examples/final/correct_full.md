# word-engine 完整驗收文件

本文件涵蓋 Phase 1~3 所有核心功能，是一份**正確**的 Markdown 文件。

---

## 第一章：基本排版元素（Phase 1）

### 標題層級

以下段落展示 H3 小節。

### 段落

這是一段普通的文字段落，包含中文、英文以及 `inline code` 混合排版。Word Engine 會根據 `params.yaml` 中的段落設定決定字體與行距。

### 列表

**無序列表：**

- 第一個項目
- 第二個項目包含 `code 片段`
- 第三個項目包含 **粗體** 和 *斜體*

**有序列表：**

1. 執行 QC 檢查
2. 執行 Render
3. 執行 Export

### 程式碼區塊

```python
def render_pipeline(md_path, params_path):
    """Phase 1 核心流程示範"""
    qc_result = run_qc(md_path, params_path)
    if qc_result["qc_passed"]:
        docx = run_render(md_path, params_path)
        pdf = run_export(docx)
        return pdf
```

---

## 第二章：圖表 Caption（Phase 2）

### 圖片示範

下圖展示系統整體架構，請見 {{ref:fig-1}}（forward reference 測試）。

![系統架構示意圖](assets/diagram.png)

如 {{ref:fig-1}} 所示，系統分為 QC、Render 與 Export 三個主要層次。

### 表格示範

請參考 {{ref:tbl-1}} 中的功能對照表：

| 功能 | Phase 1 | Phase 2 | Phase 3 |
|------|---------|---------|---------|
| Markdown 渲染 | ✅ | ✅ | ✅ |
| 封面頁 | ❌ | ✅ | ✅ |
| 目錄（TOC field） | ❌ | ✅ | ✅ |
| Caption（SEQ field） | ❌ | ❌ | ✅ |
| 粗體/斜體 | ❌ | ❌ | ✅ |
| UNO socket bridge | ❌ | ❌ | ✅ |

---

## 第三章：inline 格式（Phase 3 Task 1）

### 粗體與斜體

這段展示 **粗體文字** 和 *斜體文字* 在段落中的正確渲染。

混合格式：**粗體** 搭配 *斜體* 再加上 `code` 全部出現在同一行。

### 表格內的 inline 格式

| 項目 | 說明 |
|------|------|
| **粗體欄位** | 這是普通說明文字 |
| *斜體說明* | `code_value` |
| 混合 | **粗** *斜* `code` 三種同時 |

### 列表內的 inline 格式

- **粗體**列表項目
- *斜體*列表項目
- `code`列表項目
- **粗體** + *斜體* + `code` 三合一

---

## 第四章：交叉引用（Phase 2+3）

### 章節引用

如 {{ref:sec-1}} 所述（第一章），Phase 1 奠定了基本渲染能力。

如 {{ref:sec-2}} 所述（第二章），Phase 2 新增了圖表 caption 功能。

### 組合引用

根據 {{ref:tbl-1}} 的功能對照表，以及 {{ref:fig-1}} 的架構示意圖，可以看出 word-engine 的功能是逐版累積的。

---

## 第五章：第二張圖

第二章有補充說明圖，請見 {{ref:fig-2}}。

![流程示意圖](assets/flow.png)

如 {{ref:fig-2}} 所示，完整流程為 QC → Render → Postfix → Export。
