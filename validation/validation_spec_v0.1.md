# word-engine 驗證規範 v0.1

## 驗證目標
確保 `word-engine` 在每次迭代中維持：
- 結構正確
- 參數可驗證
- 渲染結果可重現
- 匯出可成功
- 雲端同步可追蹤

## 驗證層級
1. Unit Test
2. Integration Test
3. Render Validation
4. Export Validation
5. Sync Validation

## 最低驗收要求
- YAML schema 載入成功
- Markdown heading lint 成功
- docx 成功產出
- pdf 成功匯出
- Nextcloud 上傳成功
