# 有瑕疵的測試文件

這是一份故意製造了多個語法與結構錯誤的 Markdown 文件。

### 第一個錯誤：標題跳級
如上方所示，我是 `H3`，但在這之前只有 `H1`（沒有 `H2`），這會觸發 QC 的「Heading jump from H1 to H3」錯誤。

#### 另一個錯誤：未閉合的程式碼區塊

```bash
echo "這是一個有問題的指令，因為我忘記把 code fence 給關起來了！"


## 第三個錯誤：空標題
# 

最後，下面故意加了五行空白來測試 Linter。





這是一個測試用段落，您可以執行 `python word_engine.py qc --md examples/phase1/invalid_source.md --params examples/phase1/params_basic.yaml` 來查看系統是否成功捕捉到這些錯誤。
