# Review Loop 測試文件

此文件用於驗收 word-engine 的 review loop 功能。
可以多次修改此文件或對應的 params.yaml，並反覆執行 `word-engine review` 觀察版本遞增與狀態記錄。

## 版本記錄

以下是本次修訂的主要內容：

| 版本 | 修改日期 | 修改內容 |
|------|---------|---------|
| v1.0 | 2026-04-12 | 初版建立 |
| v1.1 | 2026-04-12 | 修正標題層級 |

## 驗收說明

執行以下指令進行 review loop：

```bash
python word_engine.py review \
  --md examples/phase2/D_review_loop_demo.md \
  --params examples/phase2/params_review_fast.yaml \
  --project-dir . \
  --label "review-test"
```

執行後，請確認：

1. 出現 `[REVIEW] QC passed.` 訊息
2. 出現 `[RERENDER] Version vN complete: ...` 訊息（版本號每次 +1）
3. 出現 `review_state.json` 中步驟全部標為 `true`（除最後的 review_checked）
4. `documents/` 目錄下產生 `report_vN.docx` 與 `report_vN.pdf`
