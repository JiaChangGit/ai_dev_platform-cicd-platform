# Jenkins 轉接器

以 `jenkins/Jenkinsfile.template` 為起點，將產品指令、成品儲存區（artifact repository）與憑證識別字（credential ID）替換為 Jenkins 管理的值。機密只由 Jenkins 憑證儲存區（credential store）注入，不得寫入發行證據或 Git。
