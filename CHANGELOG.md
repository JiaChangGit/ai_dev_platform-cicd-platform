# Changelog

本檔案記錄 `ai-dev-platform` 框架本身的版本演進，讓引用它的產品倉庫可以回答「當初是照哪一版規則蓋的」。

格式參考 [Keep a Changelog](https://keepachangelog.com/)，版本號採語意化版本（見 `governance/release.md`）。

## [1.0.0]

首次公開版本。

涵蓋範圍：
- 三倉庫協作模型（`ai-dev-platform` / `product-cicd-platform` / `product-release`），適用於任意 product 領域
- Codex CLI、Claude Code、opencode 三工具的入口檔與相容性設計
- `workflow/`（任務流程）與 `governance/`（治理規則）的分工架構
- `registry/` 機器可讀索引（AI 供應商、workflow、skill、外部框架）
- `external/` 的 git subtree 同步機制，含完整倉庫與子資料夾兩種同步方式
- 三個選用的外部框架整合：OpenSpec（規格管理）、superpowers（執行紀律）、grill-with-docs（語意對齊），詳見 `docs/external-frameworks.md`
- 既有專案導入指南、跨倉庫規則落地機制、領域知識查證流程
