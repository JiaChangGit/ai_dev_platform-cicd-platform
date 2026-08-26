# 平台架構、流程與資料流

本文件說明平台實際保存的檔案、產品建立方式、工作流程與發布邊界。圖中的 `product` 是使用者建立的產品名稱，不代表本平台內含產品程式碼。

## 1. 工作區架構

維護來源、安裝後的平台、產品開發儲存庫與發行儲存庫是不同目錄：

```text
Work/
├── ai_dev_platform-cicd-platform/  # 平台維護來源；只有修改平台時使用
├── ai-dev-platform/                # 從 Release ZIP 安裝；產品以唯讀方式讀取
├── product-cicd-platform/          # 產品原始碼、測試、文件與 CI
└── product-release/                # Release Note、evidence 與 tag
```

```mermaid
flowchart LR
    M["平台維護來源<br/>ai_dev_platform-cicd-platform"] -->|"release-build<br/>ZIP、SHA-256、SBOM、attestation"| A["成品平台<br/>GitHub Release"]
    A -->|"驗證後安裝"| P["唯讀平台<br/>ai-dev-platform"]
    P -.->|"規則、流程、模板、工具"| D["產品開發庫<br/>product-cicd-platform"]
    D -->|"產品成品與建置證據"| C["產品 CI／成品平台"]
    C -->|"URI、SHA-256、source commit、CI run"| R["產品發行庫<br/>product-release"]
```

相依方向只有「產品讀取唯讀平台」。產品不修改 `ai-dev-platform/`，發行儲存庫也不讀取或複製產品原始碼。

## 2. 平台元件

| 路徑 | 用途 | 不處理的內容 |
|---|---|---|
| `AGENTS.md` | 任務入口、共用邊界與文件載入規則 | 產品需求與領域決策 |
| `registry/` | workflow、CI adapter、domain profile 索引 | 執行 CI 或下載 SDK |
| `workflow/` | feature、bugfix、debug、review、release 步驟 | 產品專屬命令 |
| `governance/` | branch、commit、review、security、release 規則 | 取代 branch protection 或人工審查 |
| `templates/` | issue、PR、ADR、交接與 evidence 格式 | 自動產生正確的產品內容 |
| `adapters/ci/` | GitHub、GitLab、Jenkins、internal CI 的 evidence 契約 | 驗證未連線的 runner、權限或 secret |
| `scripts/` | 初始化、稽核、安裝、打包與發行驗證 | 安裝 Android SDK、編譯器或產品依賴 |
| `examples/` | SSD trace、Android、規格筆記三個可執行案例 | 正式韌體、商店 App、受授權規格原文 |

## 3. 建立產品的控制流

`scripts/init_product.py` 同時建立兩個獨立 Git 儲存庫。它先完成所有輸入與目標路徑檢查，才把暫存目錄移到 `Work/`，遇到既有目錄會停止。

```mermaid
sequenceDiagram
    actor O as 開發者
    participant I as init_product.py
    participant P as ai-dev-platform
    participant T as 暫存目錄
    participant W as Work
    O->>I: name、domain、CI、產品命令、--dry-run
    I->>P: 檢查安裝位置、入口、模板與範例
    I->>W: 檢查兩個目標目錄都不存在
    I-->>O: 顯示預計建立的絕對路徑
    O->>I: 移除 --dry-run 後重跑
    I->>T: 產生開發庫與發行庫
    I->>T: 選擇性複製對應範例
    I->>T: 驗證 release layout
    I->>W: 原子移入兩個目錄
    I->>W: 分別 git init 與建立初始 commit
```

初始化器會產生可編輯的產品骨架，不會建立遠端 repository、不會設定 branch protection、不會建立 CI secret，也不會把除錯案例轉成正式產品。

## 4. 任務控制流

```mermaid
flowchart TD
    U["需求或問題"] --> C{"registry/workflow.yaml<br/>任務類型"}
    C --> W["讀取一份 workflow"]
    C --> G["讀取必要 governance"]
    C --> T["使用必要 template"]
    W --> I["修改產品原始碼、測試、文件"]
    G --> I
    T --> I
    I --> L["lint／靜態檢查"]
    L --> Q["test"]
    Q --> B["build"]
    B --> S["security／package"]
    S --> PR["PR 與獨立審查"]
    PR --> M["受保護 main"]
```

Registry 只決定這項任務要讀哪些平台文件。它不會縮短產品需求、不會自動執行測試，也不保證固定的上下文或 Token 節省比例。

## 5. 產品資料流

```mermaid
flowchart LR
    R["產品需求／核准規格"] --> S["產品原始碼與文件"]
    S --> V["lint、test、build、security"]
    V --> P["package"]
    P --> A["成品平台"]
    A --> E["release evidence<br/>URI、hash、來源與 checks"]
    E --> N["Release Note"]
    E --> G["release tag"]
```

成品資料與發行中繼資料分開保存：

| 資料 | 保存位置 | 不得保存的位置 |
|---|---|---|
| 原始碼、測試、產品文件 | `product-cicd-platform` | `product-release` |
| ZIP、APK、AAB、ELF、韌體映像 | CI／成品平台 | Git 儲存庫 |
| Release Note、evidence、tag | `product-release` | 無 |
| CI Token、簽章私鑰 | 平台 secret store／HSM | 原始碼、log、evidence |
| 非公開規格 | 獲准的內部系統 | 公開 GitHub／GitLab |

## 6. 發行時序

```mermaid
sequenceDiagram
    actor D as 開發者
    participant S as source repo
    participant B as release-build
    actor A as 核准者
    participant R as release repo
    participant P as release-promotion
    D->>S: 合併版本 PR，在乾淨 main 建 vX.Y.Z tag
    S->>B: tag 觸發建置
    B-->>A: 等待 release-build environment 核准
    A->>B: 核准
    B->>B: check、test、package、SBOM、attestation
    B->>S: 建立 prerelease candidate
    D->>R: 提交同版 Release Note 與 evidence PR
    A->>R: 獨立審查後合併並建立同版 tag
    D->>P: 手動指定 version 與 source tag
    P-->>A: 等待 release-promotion environment 核准
    A->>P: 核准
    P->>P: 重驗 metadata tag、hash、SBOM、provenance
    P->>S: 更新標題／說明並取消 prerelease
```

`release-build` 與 `release-promotion` 都使用 environment reviewer。若同一個人同時控制來源、核准與發布，流程仍可執行，但不能列為雙人控管。

## 7. 三個案例的資料邊界

```mermaid
flowchart TB
    subgraph SSD["SSD PCIe FW 除錯案例"]
      SQ["虛構 read request"] --> SV["C11 欄位／LBA 驗證"] --> ST["8 筆 trace ring"] --> SX["host test／ELF"]
    end
    subgraph AND["Android 案例"]
      AC["固定的 BuildCheck 清單"] --> AR["純 Kotlin render"] --> AT["TextView"] --> AX["debug APK／JVM test"]
    end
    subgraph SPEC["規格手冊案例"]
      PS["虛構 sample-spec.md"] --> PN["reading-notes.md"] --> PH["離線 index.html"]
      PS --> PV["REQ 識別字驗證"]
      PN --> PV
      PH --> PV
    end
```

SSD 案例沒有 PCIe/NVMe 命令與硬體存取；Android 案例沒有後端、正式簽章與上架設定；規格案例不是 PCIe 或 NVMe 原文。各案例的實作步驟與限制見：

- [`../examples/ssd-pcie-fw/SAMPLE.md`](../examples/ssd-pcie-fw/SAMPLE.md)
- [`../examples/android-app/SAMPLE.md`](../examples/android-app/SAMPLE.md)
- [`../examples/spec-notes/SAMPLE.md`](../examples/spec-notes/SAMPLE.md)

## 8. 信任邊界

GitHub artifact attestation 可把成品連回 workflow、repository、commit 與觸發事件。它不是弱點掃描結果，也不保證成品安全；Android App Signing、韌體供應商簽章、裝置 secure boot 與量產金鑰管理仍由產品實作。此邊界與 [GitHub 官方說明](https://docs.github.com/en/actions/concepts/security/artifact-attestations)一致，查詢日期為 2026-08-25。
