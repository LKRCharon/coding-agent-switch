# coding-agent-switch

[English](./README.md)

面向 Linux/Unix 环境的 CLI-first coding agent 切换工具。

## 概览

`coding-agent-switch` 主要解决两类需求：

1. 在不同 OpenAI 兼容 provider 之间切换 Codex。
2. 按需切换 Claude Code 的底层模式：
   - `native`：原生 Claude
   - `profile`：通过 LiteLLM 网关转到 OpenAI 兼容 provider

仓库只包含模板和切换逻辑，不包含敏感信息。

## 为什么做这个工具

官方 Codex 和 Claude 很好用，但日常成本并不低。很多用户手上同时有多个第三方兼容 provider，希望通过一个简单 CLI 在它们之间切换。

这个工具把主路径收得很明确：

- Codex profile 切换是核心功能
- Claude gateway 切换是可选增强
- 私有 provider profile 留在本地，不进 git

## 功能概览

- 主入口：`agent-switch`
- 兼容入口：`codex-switch`、`claude-switch`
- 支持 TTY 交互菜单
- profile 创建助手：`add-profile`
- 默认安装模式：Codex-only
- 可选网关组件：`gateway/claude-gateway-switch`
- 配置模板：`profiles/*/config.toml` 和 `auth.json.template`
- 本地私有 profile：`profiles-local/*`

## 目录结构

```text
coding-agent-switch/
├── bin/
│   ├── agent-switch
│   ├── add-profile
│   ├── claude-switch
│   └── codex-switch
├── install.sh
├── install-claude-gateway.sh
├── gateway/
│   ├── claude-gateway-switch
│   ├── lib/render_runtime.py
│   └── runtime/
├── lib/provider_balance.py
├── profiles/
│   └── provider/
├── profiles-local/
├── .env.example
└── .gitignore
```

`profiles/` 用来放模板或共享配置，`profiles-local/` 用来放本机私有 provider，不提交到 git。

## 依赖要求

### 默认模式：Codex-only

- `codex`
- `python3` 3.10+

### 可选模式：Claude gateway

- `claude`
- 执行 `./install-claude-gateway.sh` 安装 LiteLLM 依赖

## 安装

在仓库根目录执行：

```bash
./install.sh
```

它会：

- 在需要时从 `.env.example` 初始化 `.env`
- 默认跳过 LiteLLM
- 把 `agent-switch`、`codex-switch`、`add-profile` 链接到 `~/.local/bin`

如果你还要启用 Claude gateway：

```bash
./install-claude-gateway.sh
```

这一步会安装 LiteLLM 依赖并链接 `claude-switch`。

## PATH 配置

把 `~/.local/bin` 加进 PATH，之后就可以直接运行命令。

zsh：

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

bash：

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

fish：

```fish
set -U fish_user_paths $HOME/.local/bin $fish_user_paths
```

验证：

```bash
command -v agent-switch
command -v codex-switch
command -v add-profile
```

如果启用了 Claude gateway，再额外验证：

```bash
command -v claude-switch
```

## 快速开始

1. 安装工具：

```bash
cd coding-agent-switch
./install.sh
```

2. 推荐把 provider key 放进各自 profile 的 `auth.json`，`.env` 只作为兼容 fallback。
3. 查看可用 profile：

```bash
agent-switch list
```

4. 如果需要，再安装 Claude gateway：

```bash
./install-claude-gateway.sh
```

## 常用命令

### 0) 交互菜单

```bash
agent-switch
```

菜单内支持：

- 数字键
- `↑/↓`
- `Enter`
- `q`

这是纯 TTY 菜单，适合没有 GUI 的 Linux/Unix 服务器环境。

### 1) 创建 Profile

直接传参数：

```bash
add-profile --name pro \
  --base-url https://api.example.com/v1 \
  --api-key sk-xxxx \
  --wire-api responses \
  --requires-openai-auth true
```

或者传 TOML 片段：

```bash
cat <<'EOF' | add-profile --api-key sk-xxxx --provider-snippet-file -
[model_providers.pro]
name = "pro"
base_url = "https://api.example.com/v1"
wire_api = "responses"
requires_openai_auth = true
EOF
```

交互方式：

```bash
add-profile
```

兼容命令：

```bash
agent-switch profile add --name pro --base-url https://api.example.com/v1 --api-key sk-xxxx
agent-switch profile create pro --base-url https://api.example.com/v1 --api-key sk-xxxx
```

### 2) 创建多个本地 Profile

示例：

```bash
agent-switch profile create provider-a \
  --base-url https://api-a.example.com/v1 \
  --env-key PROVIDER_A_API_KEY \
  --api-key your_provider_a_key
```

```bash
agent-switch profile create provider-b \
  --base-url https://api-b.example.com/v1 \
  --env-key PROVIDER_B_API_KEY \
  --api-key your_provider_b_key

agent-switch profile create provider-c \
  --base-url https://api-c.example.com/v1 \
  --env-key PROVIDER_C_API_KEY \
  --api-key your_provider_c_key

agent-switch profile list
```

推荐的本地 `auth.json`：

```json
{
  "OPENAI_API_KEY": "your_api_key_here"
}
```

`.env` 里的 `PROVIDER_A_API_KEY` 这类值仍可作为 fallback，但不是首选路径。

### 3) Codex Provider 切换

持久切换是主路径。

```bash
agent-switch codex provider-a
agent-switch codex provider-b
agent-switch codex provider-c
```

显式等价写法：

```bash
agent-switch codex provider-a use
agent-switch codex provider-b use
```

查看解析结果：

```bash
agent-switch codex provider-a show
agent-switch codex provider-b env
```

单次调试运行，不修改 `~/.codex`：

```bash
agent-switch codex provider-a run -p "Reply with exactly OK."
```

备份和恢复原生 Codex 登录态/配置：

```bash
agent-switch codex native export-auth official-main
agent-switch codex native restore-auth official-main
```

退出登录并清理当前 provider 残留：

```bash
agent-switch codex logout
```

### 4) Claude 后端切换

先确保执行过：

```bash
./install-claude-gateway.sh
```

原生 Claude：

```bash
agent-switch claude native
```

通过 LiteLLM 的 profile 模式：

```bash
agent-switch claude provider-a
agent-switch claude provider-b
```

单次 prompt：

```bash
agent-switch claude provider-b -p "Reply with exactly OK."
```

### 5) 网关运维

```bash
agent-switch claude provider-b serve
agent-switch claude provider-b status
agent-switch claude provider-b logs
agent-switch claude provider-b stop
```

这部分只有启用 Claude gateway 时才需要。

## 配置模型

推荐的密钥管理方式：

- `profiles/*/config.toml`：base URL、model、env key
- `profiles-local/*/config.toml`：本地私有 provider profile
- `profiles-local/*/auth.json`：真实 API key
- `.env`：仅作兼容 fallback

`auth.json` 示例：

```json
{
  "OPENAI_API_KEY": "your_api_key_here"
}
```

运行时查找优先级：

1. `profiles-local/<name>/auth.json`
2. `config.toml` 里定义的 provider 专用环境变量
3. 通用 `OPENAI_API_KEY`

原生 Codex 登录态快照存放在：

```text
profiles-local/<name>/codex-native/
```

可用命令：

- `agent-switch codex native export-auth <name>`
- `agent-switch codex native restore-auth <name>`

已有文件会自动备份为 `.bak.YYYYMMDD-HHMMSS`。

## 给 AI Coding Assistant 的提示词

```text
Deploy coding-agent-switch on this machine:
1) Copy .env.example to .env and chmod 600
2) Create a profile with add-profile --name <name> --base-url ... --api-key ... (or agent-switch profile add ...)
3) Run ./install.sh for Codex-only mode
4) Run agent-switch list to verify profiles
5) Run agent-switch codex provider-a show or agent-switch codex provider-b show to verify profile resolution
6) Run agent-switch codex provider-a for persistent switching; use agent-switch codex provider-a run ... for one-off debugging
7) Only if Claude gateway is needed: run ./install-claude-gateway.sh, then use agent-switch claude provider-a prepare or agent-switch claude provider-b prepare
8) Do not commit .env, profiles-local/, profiles/*/auth.json, or gateway/runtime/
```

## 安全建议

- 只提交模板，不提交真实 key 或 token
- `auth.json`、`.env`、runtime 日志都应保存在本地
- `profiles-local/` 不进 git
- gateway 仅绑定本地回环地址
- 切正式流量前先用 `show` 或 `status` 验证

## 定位

这是一个 CLI-first 工具，定位是对 GUI 风格切换器（如 cc switch）的脚本化补位，而不是 GUI 替代品。

## 推荐 Provider

如果你在找兼容 provider，可以参考：

- FoxCode: <https://foxcode.rjj.cc/auth/register?aff=4YNPP>
- Codex For Me: <https://codex-for.me/?invite=9608>

### 利益披露

如果有人通过上面的邀请链接注册并后续消费，项目维护者可能会获得平台返利。
