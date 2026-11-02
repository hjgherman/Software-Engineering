# Windows SSH 配置笔记：新旧密钥共存与 GitHub

整理日期：2026-11-02

## 1. `.ssh` 文件夹的作用

当前用户的 SSH 配置目录为：

```text
C:\Users\Admin\.ssh
```

| 文件 | 作用 | 说明 |
| --- | --- | --- |
| `config` | SSH 客户端连接配置 | 指定服务器别名、地址、用户名、端口、私钥等 |
| `id_rsa` | RSA 私钥 | 必须保密，现有服务器仍在使用 |
| `id_rsa.pub` | RSA 公钥 | 可添加到服务器或 Git 平台 |
| `id_ed25519` | Ed25519 私钥 | 必须保密 |
| `id_ed25519.pub` | Ed25519 公钥 | 可添加到服务器或 Git 平台 |
| `known_hosts` | 已信任服务器的公钥记录 | 用于检查服务器身份变化，不是自己的登录密钥 |
| `known_hosts.old` | `known_hosts` 的备份 | 通常由相关工具修改记录时生成 |
| `a.bat` | Windows 批处理脚本 | 非 SSH 标准文件，作用取决于脚本内容 |

没有 `.pub` 后缀的是上述密钥对中的私钥；有 `.pub` 后缀的是公钥。Windows 将 `.pub` 识别为 Publisher 类型只是文件关联，SSH 公钥仍然是文本文件。

## 2. 为什么原来的 RSA 公钥被 GitHub 拒绝

当时 GitHub 提示：

```text
Key is too short. GitHub recommends using ssh-keygen to generate a RSA key of at least 3072 bits.
```

表示提交的 RSA 密钥位数太低。添加字符或修改文件名无法提升密钥强度，需要生成新密钥。

此次使用 **4096 位 RSA 密钥**。Ed25519 也是常用选择，不能跨算法仅按字符串长度比较安全性。

参考：[GitHub 官方 SSH 密钥生成说明](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent)。

## 3. 生成新密钥，保留已有文件

在 PowerShell 执行以下命令。文件名包含时间和随机后缀，并检查同名文件，避免覆盖旧密钥：

```powershell
New-Item -ItemType Directory -Force "$HOME\.ssh" | Out-Null

$keyName = 'id_rsa_github_' + (Get-Date -Format 'yyyyMMdd_HHmmss') + '_' + [guid]::NewGuid().ToString('N').Substring(0, 8)
$keyPath = Join-Path "$HOME\.ssh" $keyName

if ((Test-Path -LiteralPath $keyPath) -or (Test-Path -LiteralPath "$keyPath.pub")) {
    throw '文件已存在，请更换文件名'
}

ssh-keygen -t rsa -b 4096 -a 100 -C 'github' -f "$keyPath"
```

参数含义：

- `-t rsa`：使用 RSA 算法。
- `-b 4096`：生成 4096 位密钥。
- `-a 100`：设置私钥密码派生的轮数，配合私钥密码使用；不是密钥长度。
- `-C github`：添加用途备注，不是登录账号。
- `-f`：指定输出文件名。

命令会提示设置私钥密码。输入时不显示字符属于正常现象。

验证位数、复制公钥：

```powershell
ssh-keygen -lf "$keyPath.pub"
Get-Content -LiteralPath "$keyPath.pub" -Raw | Set-Clipboard
```

验证输出应以 `4096` 开头。到 GitHub 的 **Settings → SSH and GPG keys → New SSH key**，选择 **Authentication Key**，粘贴完整公钥并保存。RSA 公钥内容以 `ssh-rsa` 开头。

## 4. 本次实际生成的文件

私钥：

```text
C:\Users\Admin\.ssh\id_rsa_github_20261102_125018_6ffeffc8
```

公钥：

```text
C:\Users\Admin\.ssh\id_rsa_github_20261102_125018_6ffeffc8.pub
```

已验证为 **4096 位 RSA**。本次生成的私钥未设置密码，原有密钥文件均保留。

复制本次公钥到剪贴板：

```powershell
Get-Content -LiteralPath 'C:\Users\Admin\.ssh\id_rsa_github_20261102_125018_6ffeffc8.pub' -Raw | Set-Clipboard
```

如需随后为这把私钥设置密码，可执行以下命令；这不会更换密钥对，GitHub 上的公钥无需重加：

```powershell
ssh-keygen -p -f 'C:\Users\Admin\.ssh\id_rsa_github_20261102_125018_6ffeffc8'
```

## 5. 新旧密钥如何共存

SSH 不按文件的新旧时间选择密钥。选择受命令行参数、匹配到的 `config` 配置，以及 ssh-agent 中的身份等因素影响。

给 GitHub 新建一个独立别名 `github-new`，原来的 `ubuntu` 和 `carolai` 继续使用旧私钥。

本次已配置的 `C:\Users\Admin\.ssh\config`：

```sshconfig
Host github-new
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_rsa_github_20261102_125018_6ffeffc8
    IdentitiesOnly yes

Host ubuntu
    HostName 192.168.100.27
    User ubuntu
    Port 22
    IdentityFile C:/Users/Admin/.ssh/id_rsa

Host carolai
    HostName 192.168.100.81
    User carolai
    Port 22
    IdentityFile C:/Users/Admin/.ssh/id_rsa
```

| 配置项 | 含义 |
| --- | --- |
| `Host` | 命令中使用的别名，也是匹配配置的名称 |
| `HostName` | 实际连接的服务器地址 |
| `User` | 远程登录用户名，GitHub SSH 连接固定使用 `git` |
| `Port` | SSH 端口，默认是 22 |
| `IdentityFile` | 使用的私钥路径，不能填写 `.pub` 文件 |
| `IdentitiesOnly yes` | 限制为显式配置的身份，避免任意尝试 agent 中的其他密钥 |

注意：`IdentityFile` 可以从多个匹配的配置块累积。以后如果添加 `Host *` 并在其中设置其他私钥，需要检查最终解析结果。

本次修改前已备份原配置：

```text
C:\Users\Admin\.ssh\config.backup_20261102_125330_4eabc955
```

## 6. Windows 中的路径写法

在 Windows OpenSSH 的 `config` 中，`~` 表示当前用户主目录，以下两种写法对当前用户等价：

```sshconfig
IdentityFile ~/.ssh/id_rsa_github_20261102_125018_6ffeffc8
```

```sshconfig
IdentityFile C:/Users/Admin/.ssh/id_rsa_github_20261102_125018_6ffeffc8
```

配置中推荐使用正斜杠 `/`。如果路径包含空格，用双引号包住整个路径。

在 PowerShell 命令中通常使用：

```powershell
"$HOME\.ssh\文件名"
```

## 7. 测试与日常使用

### 检查最终生效的配置

以下命令只解析配置，不连接服务器：

```powershell
ssh -G github-new | Select-String '^(hostname|user|port|identityfile|identitiesonly) '
```

本次已验证：`github-new` 指向 GitHub 并使用新私钥；`ubuntu`、`carolai` 继续使用原来的 `id_rsa`。

### 测试 GitHub 认证

先把新公钥添加到 GitHub，再执行：

```powershell
ssh -T github-new
```

首次连接可能要求确认服务器指纹，应核对 [GitHub 官方 SSH 指纹](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/githubs-ssh-key-fingerprints)后再接受。

成功时会看到类似：

```text
Hi 用户名! You've successfully authenticated, but GitHub does not provide shell access.
```

GitHub 不提供交互式 Shell，以上提示表示认证成功。本次已完成本地配置验证，尚未验证 GitHub 在线认证。

### 克隆新仓库

把 SSH 仓库地址中的 `github.com` 换成配置别名 `github-new`：

```powershell
git clone git@github-new:用户名/仓库名.git
```

### 修改已有仓库的地址

进入对应仓库目录后执行，将示例中的用户名和仓库名替换为实际值：

```powershell
git remote -v
git remote set-url origin git@github-new:用户名/仓库名.git
git remote -v
```

这只修改当前仓库的 `origin` 地址。HTTPS 地址不会使用这里的 SSH 配置；`git@github.com:...` 也不会匹配 `Host github-new`。

### 连接原有服务器

```powershell
ssh ubuntu
ssh carolai
```

这两个别名继续使用原来的服务器地址、用户名和旧私钥。

## 8. 核心要点

- 公钥提供给 GitHub 或服务器，私钥留在本机保管。
- 新建密钥使用独立文件名，保留其他服务正在使用的旧密钥。
- 用不同的 `Host` 别名，为不同用途指定不同私钥。
- Git 仓库的 SSH 地址必须使用对应别名，才能匹配该别名的配置。
- 修改配置后用 `ssh -G 别名` 检查，用 `ssh -T 别名` 测试 GitHub 认证。
