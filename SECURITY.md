# 安全性問題通報

請不要用公開 Issue 回報尚未修正的弱點、憑證、金鑰或內部網址。

## 通報方式

1. 開啟 GitHub 儲存庫的 **Security** 頁籤。
2. 選擇 **Report a vulnerability**，使用私密弱點通報（private vulnerability reporting）。
3. 提供受影響版本、重現步驟、影響範圍與建議緩解方式。

若 GitHub 私密弱點通報尚未啟用，儲存庫擁有者必須先在 **Settings → Security → Code security and analysis** 啟用，再公開接受弱點通報。

## 範圍

平台自有腳本、發行邊界、憑證處理與 CI／CD 轉接器屬於通報範圍。`external/` 保留第三方上游快照；弱點若來自上游內容，維護者會同時記錄來源與同步狀態。
