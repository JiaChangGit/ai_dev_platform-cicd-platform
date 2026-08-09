# Governance：分支規則（Branch）

## 命名規則

`<type>/<short-description>`，全小寫、單字間用連字號：

| type | 用途 | 範例 |
|---|---|---|
| `feature` | 新功能 | `feature/photo-scene-description` |
| `bugfix` | 修正 bug | `bugfix/null-pointer-on-empty-input` |
| `hotfix` | 正式環境緊急修復，直接從 release 分支切出 | `hotfix/crash-on-startup` |
| `release` | 發布準備分支 | `release/1.4.0` |
| `chore` | 雜項（依賴升級、CI 設定等） | `chore/bump-deps` |

- 分支名不放人名、日期、issue 系統以外的識別碼
- 若有對應 issue 編號，可加在描述前：`feature/123-photo-scene-description`

## 策略選擇

預設建議 **trunk-based development**（單一長期分支 `main`，短生命週期的功能分支，頻繁合併）：適合 AI 輔助下的快速迭代、CI/CD 完整的專案。

若專案有以下特性，改採 **長期維護分支 / git-flow 變體**（適合需要同時維護多個版本的情境，例如 kernel 模組要對應多個核心版本、或需要長期支援 LTS）：
- 需要同時對外支援多個穩定版本
- 發布週期長、且舊版本仍需要收 hotfix

實際採用哪種策略，在產品倉庫的 `docs/domain-standards.md` 或架構文件中明確記錄，不要中途混用不說明。

## 保護規則（建議預設值，依團隊規模調整）

- `main` 與 `release/*` 禁止直接 push，一律經 PR
- `main` 需要通過 CI 才能合併（見 `governance/review.md` 的合併門檻）
- 功能分支存活時間建議 < 2 週，過久應拆小或考慮 feature flag
- 分支合併後即刪除，保持分支列表乾淨
