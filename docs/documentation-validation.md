# 文件聲明與驗證依據

本頁記錄主要文件聲明的依據、查詢日期與驗證邊界。日期是最後一次實際核對時間，不代表未來狀態不會改變。

## 1. 判定方式

| 等級 | 可接受依據 | 文件寫法 |
|---|---|---|
| 已實作 | repository 內可定位的原始碼、設定或測試 | 說明檔案與具體行為 |
| 本機已驗證 | 當次實際執行命令成功 | 記錄命令、日期與未執行項目 |
| 線上已驗證 | GitHub／GitLab API、CI run 或 Release 頁的當前狀態 | 記錄 repository、物件與日期 |
| 官方相容性 | 產品官方或標準組織的一手頁面 | 固定查詢日期，不寫成永久事實 |
| 未驗證／未實作 | 缺工具、權限、硬體或程式碼 | 明確列為限制，不以預期結果代替 |

## 2. 平台與 Release

核對日期：2026-08-25。

| 聲明 | 依據 | 邊界 |
|---|---|---|
| `v1.5.0` 是正式 Release | [GitHub Release](https://github.com/JiaChangGit/ai_dev_platform-cicd-platform/releases/tag/v1.5.0) 的 `isDraft=false`、`isPrerelease=false`；標題已改為 `AI Dev Platform v1.5.0` | `latest` 與頁面內容仍可能由 owner 後續修改 |
| `v1.5.0` 有 ZIP、checksum、SBOM、provenance | 同一 Release 的六個 assets；ZIP digest 為 `cf27d907e1ed9e2a1f1bcecafab5da78e837a1580e513fe115f20945c5d84191` | Asset 存在不等於內容正確，仍需 checksum 與 attestation verify |
| release metadata 已核准 | release repo 的 [`release-evidence/1.5.0.json`](https://github.com/JiaChangGit/ai_dev_platform-release/blob/v1.5.0/release-evidence/1.5.0.json)與 [`release-notes/1.5.0.md`](https://github.com/JiaChangGit/ai_dev_platform-release/blob/v1.5.0/release-notes/1.5.0.md)，release repo 有 annotated `v1.5.0` tag | Evidence 是聲明；readiness 仍須以實體檔案重驗 |
| promotion 會更新正式標題與說明 | `.github/workflows/promote-release.yml` 的 `gh release edit`；`tests/test_release_workflows.py` 檢查 title、notes、Release Note 與 evidence 連結 | `v1.5.0` 原流程未更新文字，已在 2026-08-25 手動修正；後續每版仍須核對 promotion run 與 Release JSON，不能只引用測試 |
| Attestation 是 provenance，不是安全保證 | [GitHub artifact attestation 官方說明](https://docs.github.com/en/actions/concepts/security/artifact-attestations) | 不取代弱點分析、Android App Signing、韌體簽章或 secure boot |

## 3. GitHub 與 GitLab 狀態

2026-08-25 以 GitHub API 重新讀取兩個 repository：

- source `main` required checks：`self-check`、`android-example`、`analyze-actions`、`analyze-python`；strict mode 開啟。
- release `main` required checks：`repository-policy`、`analyze-python`；strict mode 開啟。
- 兩者都要求 1 位核准者、CODEOWNERS、dismiss stale review、last push approval、conversation resolution、linear history；禁止 force push 與刪除，管理員也受保護。
- 兩者都允許 rebase merge；`release/*` 用它保留已驗證的原子 commits。Squash merge 仍可供一般功能分支使用，但不適用於要求保留逐 commit 稽核紀錄的發行分支。
- source 有 `release-build` 與 `release-promotion` environments；兩者 reviewer 是 `louisxchangtw`、prevent self-review 開啟、admin bypass 關閉。
- Actions 預設 `GITHUB_TOKEN` 權限為 read，不能核准 PR。

GitLab API 顯示 `JiaChangGit` 的公開 projects 仍沒有兩個平台 repository，因此文件只描述手動鏡像設定，不寫成鏡像已完成。GitLab 官方文件在 2026-08-25 仍把 pull mirroring 列為 Premium／Ultimate，Free approvals 是 optional，required approvals 是 Premium／Ultimate：

- [GitLab pull mirroring](https://docs.gitlab.com/user/project/repository/mirror/pull/)
- [GitLab merge request approvals](https://docs.gitlab.com/user/project/merge_requests/approvals/)

詳細設定見 [`repository-operations.md`](repository-operations.md)。

## 4. Android 案例

| 聲明 | 程式依據 | 官方依據／限制 |
|---|---|---|
| AGP 9.2.0 | `examples/android-app/build.gradle.kts` | [AGP 9.2 release notes](https://developer.android.com/build/releases/agp-9-2-0-release-notes) |
| Gradle 9.4.1、JDK 17 | 平台 workflow 與初始化器；module compile options 為 Java 17 | 官方相容表列最低／預設 Gradle 9.4.1 與 JDK 17 |
| built-in Kotlin | module 沒有 `org.jetbrains.kotlin.android` | [built-in Kotlin 官方遷移文件](https://developer.android.com/build/migrate-to-built-in-kotlin)說明 AGP 9.0 起預設啟用 |
| compile／target SDK 36 | `app/build.gradle.kts` | 這是案例選擇，不是 AGP 9.2 的唯一選擇 |
| render 規則有 JVM test | `BuildStatus.kt` 與 `BuildStatusTest.kt` | 不涵蓋 Activity lifecycle、裝置、網路或正式簽章 |

本次工作環境沒有可用的 `gradle` 命令，因此本機未重新執行 Android build。結構與版本由 Python tests 檢查；實際 Android build 必須以 GitHub Actions `android-example` 或具備 JDK／SDK／Gradle 的環境驗證。

## 5. SSD PCIe FW 案例

| 聲明 | 依據 | 未涵蓋 |
|---|---|---|
| trace 容量 8 | `FW_TRACE_CAPACITY` | 容量估算、SRAM 空間分配 |
| 每次驗證記錄 received 與 accepted/rejected | `fw_validate_read_traced()` | ISR／task concurrency、timestamp |
| ring 覆寫後保留 sequence 4～11 | `tests/test_fw_core.c` 先產生 12 筆事件後 assert | `uint32_t` sequence wrap-around |
| null、namespace 0、越界、加法溢位有測試 | `tests/test_fw_core.c` | 真實 NVMe command decode、DMA、queue、硬體 |
| ELF 是 host 模擬 | `Makefile` 使用本機 `cc`，沒有 cross compiler／linker script | 不可燒錄，不代表 PCIe／NVMe compliance |

PCI-SIG 公開頁在 2026-08-25 列出 PCI Express Base Specification Revision 7.0 為 current approved；NVM Express 公開頁列出 NVMe 2.4 為多文件規格組。本案例沒有實作兩者：

- [PCI-SIG PCI Express Base](https://pcisig.com/specification-overview/pci-express-base)
- [NVM Express specifications](https://nvmexpress.org/specifications/)

## 6. 規格手冊案例

`examples/spec-notes/validate.py` 會檢查：

- 規格至少有一個 `REQ-###`；
- 筆記與 HTML 的 REQ ID 集合與規格完全相同；
- 四份文件都有 `SAMPLE-EVENT-EXPORT 1.0`；
- HTML 沒有 script，也不載入 HTTP(S) 外部資源。

這些檢查只能證明格式與識別字一致，不能證明條文解讀正確、測試充分或允許公開。`sample-spec.md` 是虛構內容，不作為 PCIe／NVMe 教學結論。

## 7. 文件自動檢查

`tests/test_documentation_contract.py` 固定下列契約：

- manifest 與離線手冊版本一致；
- Android 文件版本與 build files 一致；
- SSD 文件的容量、事件與 Make targets 對得上程式；
- 規格文件列出 validator 實際檢查與所有來源檔；
- 三份案例都明列「已實作」與「未實作」；
- 主要說明文件不含列管的宣傳式語句。

執行：

```bash
python3 -B -m unittest tests.test_documentation_contract -v
bash scripts/check.sh
python3 -B -m unittest discover -s tests -v
```

自動檢查不能取代領域 reviewer。文件涉及真實控制器、Android 發布、付費規格或內部政策時，仍要由有權限的人核對。
