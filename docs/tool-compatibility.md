# 開發工具入口相容性

本文件說明 Codex、Claude Code 與 opencode 如何讀取同一份專案規則。工具行為可能改版，設定前應重新查官方文件。

## 單一入口

`AGENTS.md` 是唯一維護的主要規則。`CLAUDE.md` 與 `opencode.json` 只負責載入，不重複保存 workflow 或 governance。

| 工具 | 入口 | 平台做法 |
|---|---|---|
| Codex | 專案根目錄 `AGENTS.md` | 產品入口明確要求再讀 `../ai-dev-platform/AGENTS.md` |
| Claude Code | `CLAUDE.md` | 用 `@../ai-dev-platform/AGENTS.md` 匯入 |
| opencode | `opencode.json` | 用 `instructions` 指向平行平台入口 |

三個工具原生探索都不應被假設會自動掃描 sibling 目錄，所以 `scripts/init_product.py` 會在每個產品建立最小入口檔。產品不複製平台規則，也不建立平台版本 lock；所有產品讀取已安裝的目前穩定包。

## 模型、skills 與外掛

平台不提供模型 ID、API Token、第三方 skill 或外掛安裝。這些項目由開發者在所用工具或組織核准的設定中管理，不能寫進公開產品入口檔。工具自動載入多少上下文也由工具決定；平台只能藉由 `registry/workflow.yaml` 限縮「應該讀哪些文件」。

## 驗收

初始化產品後，分別用實際工具開啟產品根目錄，要求它回報已讀到的平台版本、當前任務類型與對應 workflow 路徑。能回答不代表所有規則都會被強制執行；CI 與 branch protection 才是可強制的合併門檻。
