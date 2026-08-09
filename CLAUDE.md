# CLAUDE.md

> 這是 Claude Code 的轉接器，不重複維護內容。真正的規則都在 `AGENTS.md`。

@AGENTS.md

## Claude Code 專屬補充

以下是只有 Claude Code 需要知道、其他工具用不到的行為設定，刻意不寫進 `AGENTS.md`（保持它 tool-agnostic）：

- 開始任務前先跑 `/memory` 確認上面的 `@AGENTS.md` 匯入確實載入成功（若專案很久沒開，偶爾會遇到需要重啟 session 才會重新載入的情況）
- 第一次在這個專案載入 `@AGENTS.md` 這類外部匯入時，Claude Code 會跳出一次核准對話框列出要匯入的檔案；若當時選了拒絕，匯入會保持關閉且之後不會再自動跳出詢問。若 `/memory` 顯示 `AGENTS.md` 沒有被載入，先檢查是不是這個原因，而不是假設 `CLAUDE.md` 本身壞了
- 涉及會員本地環境設定的個人偏好（編輯器、shell 習慣），寫在 `~/.claude/CLAUDE.md`（使用者層級），不要寫進本檔案污染團隊共用規則
- Auto memory（Claude Code 自動記憶）僅用來記錄「這個環境特有的操作細節」（例如某個指令在這台機器上要多帶什麼參數），不要用它記錄 `governance/` 已經規定的規則——那些應該直接修 `governance/`，不要讓兩份規則來源分岔
