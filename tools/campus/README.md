# 独立 master 数据同步

此目录提取并改编自 [vertesan/campus](https://github.com/vertesan/campus)，
源版本为 `a7f5b047b47594761c9623117f4f8aa159ba38c6`，代码按 AGPL-3.0 发布，见 LICENSE。
只保留 master 下载、SQLCipher 解密及协议通信功能。
登录 API 的生成 protobuf 类型通过 go.mod 中的 campus 依赖引用。
master 定义已从当前 Android 3.4.1 客户端补齐，压缩保存在
`master/client_schema.b64`，由 Go 的 dynamicpb 解码；不依赖上游更新表映射。
这些都是编译时依赖，运行时不访问 campus 或 gakumasu-diff 仓库。

## 启用自动更新

1. 将这次改动提交、推送到本仓库 main。
2. 在 GitHub 仓库 Settings → Secrets and variables → Actions 中添加
   `CAMPUS_REFRESH_TOKEN` Secret（游戏 Firebase refresh token）。不要将 token 写进文件或聊天。
3. 在 Actions 中手动运行 `Independent master data update`，检查首次运行结果。

## 认证流程

采用 campus 原有路线：已有 Firebase refresh token → 换取 idToken →
System.Check → Auth.Login → Master.Get。首次仍需提供一个有效账号的 refresh token。
若 Auth.Login 返回 `retrySignInToken`，程序按 Firebase 官方
`signInWithCustomToken` 流程交换新凭据后再登录一次；本次实测已验证此分支。
每次 Actions 运行都从 Secret 读取 refresh token，自动换取新的 idToken，
不需要手动更新短期 idToken。

Firebase idToken 通常有效一小时，refresh token 没有固定的一小时有效期。
账号被删除、禁用、发生重大账号变更，或服务端撤销凭据时，refresh token 会失效。
失效后需要重新取得账号凭据并更新 CAMPUS_REFRESH_TOKEN Secret。
刷新接口返回的 refresh token 只用于当前进程，不会自动改写 GitHub Secret。
有效期依据：[Firebase 会话说明](https://firebase.google.com/docs/auth/admin/manage-sessions)。

工作流每小时第 17 分钟检查游戏 master 版本。GitHub 定时运行可能延迟。
只有版本变化时才下载、解密并生成 YAML，全部成功后提交 `gakumasu-diff/orig/*.yaml`
和 `gakumasu-diff/master-version.txt` 到 main。JSON 转换留在本机，远端工作流不安装
Python/PyYAML，也不修改或提交 `gakumasu-diff/json`。
也支持 `repository_dispatch` 的 `master-updated` 事件；需要调用方发送该事件。
其他仓库的 push 不会直接触发本仓库 Actions。

`orig` 已改为本仓库管理的普通目录，首次启用时沿用迁移前的 YAML。
游戏版本文件在首次成功下载后生成。任何下载、解密或字段检查错误都会阻止自动提交，
仓库保留上次成功的 YAML。
游戏新增 master 表或字段时，需要从新版客户端更新 master schema，
工作流会报出缺失的表或解码后无法识别的字段；不会把被 protobuf 默认忽略的字段悄悄丢掉。
Git 只能比较已输出的数据，无法识别解码器根本没有输出的字段，因此检查实际解码结果。
登录 API 的协议变化则需要更新 go.mod 中的 campus 依赖。
若 Google Play 无法解析 app 版本，可添加 `CAMPUS_APP_VERSION` Repository variable 作为回退值。
若 main 的分支保护禁止 bot 直接推送，需要允许该工作流写入，或者改成 PR 流程。

## 从客户端账号文件取得凭据

campus 本身接收 refresh token，不能直接使用任意游戏存档或账号文件。
若 Android 客户端保存了 Firebase Auth 登录状态，可从其私有 SharedPreferences
中的 `com.google.firebase.auth.api.Store.*.xml` 提取 `cachedTokenState.refresh_token`。
需要已经登录的客户端，以及对该文件的读取权限；具体文件仍需在设备上确认。
模拟器只用于首次读取凭据，Actions 运行时不需要模拟器。

Firebase Android Auth 23.2.1 起为本地登录数据增加了加密。
如果 XML 值以 `ENCRYPTED:` 开头，复制账号 XML 和 crypto XML 到电脑上仍不足以解密：
密钥还受原设备上的 Android Keystore 保护。下面的文件解析工具只支持明文登录状态。
`CampusAccountDecryptor.java` 是针对本次设备文件格式准备的独立只读辅助程序，
用于在原设备、对应应用 UID 下调用 Keystore，不加载或修改游戏代码；
设备端解密和 Firebase 令牌验证已在 MuMu 12 上完成。
依据：[Firebase Android 更新记录](https://firebase.google.com/support/release-notes/android)。

`read_android_account.py --device 127.0.0.1:16448 --decrypt-on-device` 通过 ADB 读取账号文件，
执行随代码分发的 `account_helper.b64` 中的 DEX，验证游戏项目的令牌，然后仅保存
`cache/firebase-refresh-token.dpapi`（Windows 当前用户 DPAPI 加密）。
需要原模拟器可供 root ADB 读取；运行结束会删除设备上的临时辅助程序。
端口应替换为当前实例的 ADB 端口。此流程不会启动或操作游戏，不需要重新搭建抓包代理。

### 一键读取并更新 GitHub Secret

在 Windows 的 PowerShell Core 7 中，从仓库根目录打开工具：

```powershell
& '.\tools\campus\open_token_tool.ps1'
```

也可双击同目录的 `campus_token_tool.pyw`（需要 Windows 已关联 Python）。

需要 Python 3（含 Tkinter）、模拟器的 `adb.exe`、GitHub CLI。
此电脑已有这些依赖；换电脑后先安装，并用 `gh auth login` 登录有仓库 Secrets 写入权限的账号。
工具自动查找 MuMu 12、PATH 或 Android SDK 中的 ADB，也可在界面选择 `adb.exe`。

1. 在模拟器开启 root 和 ADB 调试，自行打开游戏并进入大厅。
2. 输入模拟器 IP 和当前实例的 ADB 端口，核对 GitHub 的 `owner/repo`。
   默认值为 `127.0.0.1:16448`、`chihya72/gakumas-master-translation-pm`。
3. 点击“读取并验证”。工具连接 ADB，读取明文或使用原设备 Keystore 解密加密账号，
   通过 Firebase 验证并取得返回的 refresh token；成功后保存当前 Windows 用户的 DPAPI 加密缓存。
4. 点击“上传 / 更新 Secret”，写入目标仓库的 Actions Secret `CAMPUS_REFRESH_TOKEN`。
   GitHub CLI 从标准输入接收令牌并加密上传，不在命令参数、界面或日志中显示。
   读取完成不会自动上传。修改 IP、端口、ADB 路径或仓库后必须重新读取。

工具不启动、重启或操作游戏；必要时只请求 ADB root（重启 adbd），随后重连。
设备上的独立解密辅助程序执行结束会删除；游戏 APK、账号文件、密钥均不修改。
需要原登录模拟器和可读私有目录的 root ADB；普通非 root 安卓设备不支持该流程。
加密凭据不能依靠复制 XML 到新模拟器恢复，必须在持有 Android Keystore 的原设备读取。

账号凭据失效时，在原模拟器中重新登录游戏，再执行上述读取和上传步骤。
读取或验证失败不会覆盖旧缓存，也不会修改 GitHub Secret；上传错误可重试。
网络超时时服务器可能已接受更新，界面会提示未确认成功，重复上传同一凭据是安全的。
成功上传后，下次 Actions 使用新 Secret；此工具不会触发工作流或生成本机 JSON。

`account_helper.b64` 仅包含由同目录 `CampusAccountDecryptor.java` 编译的 DEX 代码，不含凭据。
日常使用无需 Java 或 Android SDK。修改 Java 解密实现时，应以 JDK 和 Android SDK
编译 Java（目标 Java 8），用 D8（min API 26）生成 DEX，并同步更新 base64 文件。
Windows 上的凭据边界和界面测试：

```powershell
[string[]]$arguments = @('-m', 'unittest', 'discover', '-s', 'tools\campus', '-p', 'test_token_tool.py')
& python @arguments
if ($LASTEXITCODE -ne 0) { throw 'Token tool tests failed' }
```

测试中的 GitHub 写入均使用模拟，不更新真实 Secret。
Secret 的标准输入、仓库级 Actions 参数与加密行为依据
[GitHub CLI 官方说明](https://cli.github.com/manual/gh_secret_set)。

`read_firebase_account.ps1` 可解析导出的 Firebase Auth XML 或 JSON，
不会打印令牌或保存解析结果。`-Validate` 通过 Firebase 验证令牌及游戏项目编号；
`-CopyToClipboard` 验证成功后把返回的 refresh token 放到剪贴板，供粘贴到 Secret。
解析工具只验证 Firebase 凭据；本次已另外完成游戏 Auth.Login 和 295 张 master 表下载、解密验证。

在当前目录执行以下命令，AccountFile 指向已导出的文件：

```powershell
& '.\read_firebase_account.ps1' -AccountFile '.\cache\firebase-auth.xml' -Validate -CopyToClipboard
```

账号文件本身包含凭据，应仅存放在忽略的 cache 内，不要上传到仓库或聊天。
Firebase Installations 文件中的 `RefreshToken` 属于另一套服务，不能用于 campus 登录。

## 本机使用

Actions 已把原始 YAML 提交到本仓库 `gakumasu-diff/orig`，本地 git pull 即可取得，
不需要复制数据。更新脚本负责拉取后调用原有脚本转换 JSON。
在仓库根目录执行：

```powershell
[string[]]$arguments = @('scripts\update_master_data.py')
& python @arguments
if ($LASTEXITCODE -ne 0) { throw 'Local JSON conversion failed' }
```

本地转换使用 Python/PyYAML，输出 `gakumasu-diff/json`；检查成功后再生成待翻译内容。
GitHub Actions 无法直接改写本机的 D 盘目录。
如果原有目录仍是子模块，应在拉取迁移提交前确认子模块没有本地修改，
移除其工作目录中的 `.git` 指针文件（保留主仓库 `.git/modules` 中的历史），再拉取。
`make update` 只调用上述脚本。脚本先执行本仓库 `git pull --ff-only`，再调用
原有转换脚本的 `--strict` 模式。拉取失败不开始转换，转换失败返回非零退出码。
如只需最新 YAML，直接 git pull 即可；如已拉取，可直接运行 `gakumasu_diff_to_json.py`，
继续使用 `--strict` 或自定义输入输出路径。脚本不自动暂存、合并或提交本地修改。

本地手动下载 YAML 需要 Go 1.25+ 和 64 位 GCC：

```powershell
Set-Location -LiteralPath 'D:\GIT\gakumas-master-translation-pm\tools\campus'
$env:CGO_ENABLED = '1'
$env:CC = 'gcc'
[string[]]$arguments = @('build', '-mod=mod', '-o', 'campus.exe', '.')
& go @arguments
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
# 通过安全的本地环境变量提供 CAMPUS_REFRESH_TOKEN 后执行：
& '..\..\scripts\sync_master_data.ps1'
```

运行中的 token 只保存在进程内存；本机持久凭据仅以 DPAPI 加密保存。
cache 是临时数据，不会提交或上传为 artifact。
Git diff 就是每次游戏 master 更新的差异记录，不另外生成补丁基线。

## 更新 master schema

1. 只读取得同一版本 APK 中的 `libil2cpp.so` 与 `global-metadata.dat`，放入忽略的 cache。
2. 执行 `decode_client_metadata.py`，仅在 cache 生成解混淆的 metadata 副本。
   mask 定位方法参考 [vilebbit/campus-meta](https://github.com/vilebbit/campus-meta)，按 AGPL-3.0 改编。
3. 用 [Il2CppDumper](https://github.com/Perfare/Il2CppDumper) 对这两个副本生成 `dump.cs`。
   非交互运行时，在工具配置中关闭 `RequireAnyKey`。
4. `schema_from_dump.py --dump <dump.cs>` 检查字段及类型是否能完整解析。
   `--patch` 输出用于更新 `master/client_schema.b64` 的 apply_patch 内容，避免直接覆盖源码。
   字段分析参考 campus 及 [SolisClient](https://github.com/vilebbit/SolisClient) 的方法，
   SolisClient 面向 IDOLY PRIDE，不能直接使用其游戏接口或协议文件。
5. 执行 Go 测试并实际运行下载、解密，通过后提交 schema 改动。
   JSON 转换另在本机检查。

此维护流程只在客户端协议变化时需要；日常 Actions 直接使用内置 schema，
无需 APK、模拟器、Il2CppDumper 或 Python protobuf。
