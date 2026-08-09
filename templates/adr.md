# ADR 模板（Architecture Decision Record）

檔名建議：`docs/adr/NNNN-short-title.md`（NNNN 為流水號）

若專案已安裝 grill-with-docs（見 `docs/external-frameworks.md`），它會依此檔名慣例自動產出 ADR，內容結構可能與下方模板略有差異；沒裝的話依下方模板手動填寫。

```markdown
# NNNN. （決策標題）

## 狀態
Proposed / Accepted / Deprecated / Superseded by NNNN

## 背景（Context）
（要解決什麼問題？有什麼限制條件？為什麼現在需要做這個決定？）

## 決策（Decision）
（最終選擇了什麼方案，具體描述）

## 考慮過的替代方案（Alternatives Considered）
### 方案 A：
- 優點：
- 缺點：

### 方案 B：
- 優點：
- 缺點：

## 後果（Consequences）
（這個決定帶來的正面與負面影響，包含技術債、日後遷移成本等）

## 相關連結
（相關 issue / PR / 外部參考資料）

---
日期：
作者：
```
