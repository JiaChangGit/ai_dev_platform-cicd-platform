# GitLab CI 轉接器

將 `gitlab-ci/release-evidence.gitlab-ci.yml.template` 複製到產品設定，填入產品指令與建置成品（artifact）儲存位置。發行證據須包含 `CI_COMMIT_SHA`、管線網址（pipeline URL）與成品摘要（artifact digest）。
