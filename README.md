# coding-agent-switch

CLI-first switcher for coding agents.

目标：让你用一个项目同时完成两件事。

1. 随时切换 Codex 的 API 提供商。
2. 随时切换 Claude Code 的底层：
   - `native`（原生 Claude）
   - `profile`（走 LiteLLM 网关，底层转到 Codex/OpenAI 兼容提供商）

本仓库仅包含模板和逻辑，不包含任何敏感数据。

## 背景

最初做这个工具很简单：官方的 Codex 和 Claude 成本不低，我自己买了几个 code 中转站来分担费用。  
但现实问题是，日常使用里需要在不同 provider 之间来回切换，手动改配置非常繁琐，节奏也会被打断。

另外还有一个很常见的情况：Codex 这边的中转额度有时候用不完，而 Claude 那边额度更紧张。  
所以我把 Claude 的底层链路也改成可切换模式，让它在需要时可以走同一套 OpenAI 兼容 provider，把已有额度利用起来。

整个项目的逻辑就是：用一套统一命令，把 Codex 和 Claude 的切换、配置和运行链路都整理成低摩擦流程，减少重复操作。

## 功能概览

- 统一入口：`agent-switch`
- 兼容入口：`claude-switch`、`codex-switch`
- 配置助手：`add-profile`（交互或参数式创建 profile）
- 安装分流：默认 `Codex-only`，`Claude + LiteLLM` 按需启用
- 网关组件：`gateway/claude-gateway-switch`
- 配置模板：`profiles/*/config.toml` + `auth.json.template`
- 本地私有 profile：`profiles-local/*`（默认不进 git，Codex/Claude 都支持）

## 当前约定

- 常用私有 profile 可以直接放到 `profiles-local/*`

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
├── profiles-local/           # 本地私有，不提交
├── .env.example
└── .gitignore
```

## 前置条件

Codex-only（默认）：

- `codex` CLI
- `python3`（建议 3.10+）

Claude 网关（可选）：

- `claude` CLI
- 运行 `./install-claude-gateway.sh` 安装 LiteLLM 依赖

## 安装（默认 Codex-only）

在仓库根目录执行：

```bash
./install.sh
```

它会自动完成：
- 初始化 `.env`（不存在时从 `.env.example` 复制，作为可选 fallback）
- 不安装 LiteLLM 网关依赖（默认跳过）
- 把 `agent-switch` / `codex-switch` / `add-profile` 链接到 `~/.local/bin`

如果你还需要 Claude 网关代理，再执行：

```bash
./install-claude-gateway.sh
```

这一步会安装 LiteLLM 依赖并链接 `claude-switch`。

## 配置 PATH（关键）

安装后建议把 `~/.local/bin` 加进 shell 的 `PATH`，之后就能直接使用
`agent-switch` / `codex-switch` / `add-profile`，不需要写 `./bin/...`。

zsh（macOS 默认）：

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

如果你启用了 Claude 网关，再额外验证：

```bash
command -v claude-switch
```

## 快速开始

1. 执行安装：

```bash
cd coding-agent-switch
./install.sh
```

2. 推荐在各 profile 的 `auth.json` 中填写 key；`.env` 只作为兼容 fallback。

3. 查看可用 profile：

```bash
agent-switch list
```

4. （可选）如果需要 Claude 网关代理：

```bash
./install-claude-gateway.sh
```

## 常用命令

### 0) 一键添加 profile（推荐）

直接填参数：

```bash
add-profile --name pro \
  --base-url https://api.example.com/v1 \
  --api-key sk-xxxx \
  --wire-api responses \
  --requires-openai-auth true
```

也可以直接喂 TOML 片段（适合你现在这种配置）：

```bash
cat <<'EOF' | add-profile --api-key sk-xxxx --provider-snippet-file -
[model_providers.pro]
name = "pro"
base_url = "https://api.example.com/v1"
wire_api = "responses"
requires_openai_auth = true
EOF
```

如果你不想记参数，可以直接交互：

```bash
add-profile
```

兼容入口（等价）：

```bash
agent-switch profile add --name pro --base-url https://api.example.com/v1 --api-key sk-xxxx
agent-switch profile create pro --base-url https://api.example.com/v1 --api-key sk-xxxx
```

### 1) 多 profile（provider-a / provider-b / provider-c）本地创建（不进 git）

已验证的常用示例：

```bash
# 创建 provider-a（写到 profiles-local/provider-a）
agent-switch profile create provider-a \
  --base-url https://api-a.example.com/v1 \
  --env-key PROVIDER_A_API_KEY \
  --api-key your_provider_a_key
```

```bash
# 创建 provider-b（写到 profiles-local/provider-b）
agent-switch profile create provider-b \
  --base-url https://api-b.example.com/v1 \
  --env-key PROVIDER_B_API_KEY \
  --api-key your_provider_b_key

# 创建 provider-c（写到 profiles-local/provider-c）
agent-switch profile create provider-c \
  --base-url https://api-c.example.com/v1 \
  --env-key PROVIDER_C_API_KEY \
  --api-key your_provider_c_key

# 查看可用 profile（包含 profiles-local）
agent-switch profile list
```

推荐放到 `profiles-local/<name>/auth.json`：

```json
{
  "OPENAI_API_KEY": "your_api_key_here"
}
```

`.env` 里的 `PROVIDER_A_API_KEY` / `PROVIDER_B_API_KEY` / `PROVIDER_C_API_KEY` 仍可作为兼容 fallback，但不再是首选。

### 2) Codex 切换 provider

```bash
# 临时切换（只对当前命令生效）
agent-switch codex provider-a
agent-switch codex provider-b
agent-switch codex provider-c

# 仅查看当前 profile 解析结果
agent-switch codex provider-a prepare
agent-switch codex provider-b prepare
agent-switch codex provider-b env

# 持久切换（修改 ~/.codex/config.toml + ~/.codex/auth.json）
# 适合让 Codex VSCode 扩展也跟随使用同一 provider
agent-switch codex provider-a persist
agent-switch codex provider-b persist

# 备份/恢复官方登录态（复制 ~/.codex/auth.json + ~/.codex/config.toml）
agent-switch codex native export-auth official-main
agent-switch codex native restore-auth official-main

# 退出登录（调用 codex logout，并清理 ~/.codex/config.toml 中当前 provider 残留，回到未登录默认模式）
agent-switch codex logout
```

### 3) Claude 切换底层

先确保你已执行过 `./install-claude-gateway.sh`。

```bash
# 原生 Claude（不走网关）
agent-switch claude native

# 走 profile（经 LiteLLM 代理，支持 profiles 和 profiles-local）
agent-switch claude provider-a
agent-switch claude provider-b

# 单次提示
agent-switch claude provider-b -p "Reply with exactly OK."
```

### 4) 网关运维

```bash
agent-switch claude provider-b serve
agent-switch claude provider-b status
agent-switch claude provider-b logs
agent-switch claude provider-b stop
```

## 配置方式（推荐）

优先使用各 profile 自己的 `auth.json` 管理 key，不把密钥写进仓库。

- `profiles/*/config.toml`：放 base_url、model、env_key
- `profiles-local/*/config.toml`：放你的私有 provider（如 provider-a/provider-b/provider-c），默认忽略提交
- `profiles-local/*/auth.json`：放真实 key，推荐使用
- `.env`：兼容 fallback（如 `CFM_API_KEY=...`）

`auth.json` 示例：

```json
{
  "OPENAI_API_KEY": "your_api_key_here"
}
```

`auth.json` 已在 `.gitignore` 里默认忽略。运行时优先级是：

1. `profiles-local/<name>/auth.json`
2. profile 配置里的 `env_key` 对应环境变量
3. 通用 `OPENAI_API_KEY`

官方登录态快照单独存放在 `profiles-local/<name>/codex-native/`：

- `agent-switch codex native export-auth <name>`：备份当前 `~/.codex/auth.json` 和 `~/.codex/config.toml`
- `agent-switch codex native restore-auth <name>`：把该快照恢复回 `~/.codex/`
- 导出和恢复都会自动给已有文件打时间戳 `.bak.YYYYMMDD-HHMMSS`

## 给 AI Coding 助手的部署提示词（可直接贴）

```text
请在本机部署 coding-agent-switch：
1) 复制 .env.example 为 .env 并设置 chmod 600
2) 创建 profile：add-profile --name <name> --base-url ... --api-key ...（或 agent-switch profile add ...）
3) 执行 ./install.sh（Codex-only）
4) 运行 agent-switch list 验证 profile
5) 运行 agent-switch codex provider-a prepare 或 agent-switch codex provider-b prepare 验证 codex provider
6) 运行 agent-switch codex provider-a persist（需要持久切换时）
7) 仅当要用 Claude 网关时：执行 ./install-claude-gateway.sh，再运行 agent-switch claude provider-a prepare / agent-switch claude provider-b prepare
8) 不要把 .env、profiles-local/、profiles/*/auth.json、gateway/runtime/ 提交到 git
```

## 安全建议

- 只提交模板，不提交真实 key/token。
- `auth.json`、`.env`、runtime 日志都应本地保存。
- `profiles-local/` 只用于本机私有 profile，不进 git。
- 推荐把 `gateway` 仅绑定到本地回环地址（默认本地端口）。
- 升级后先跑 `prepare/status` 再切换正式流量。

## 开源说明

这是 CLI 工具，定位是 GUI 工具（如 cc switch）的脚本化补位，不是 GUI 替代品。

## 推荐站点

如果你在找可用的中转站，可以看看：

- FoxCode: <https://foxcode.rjj.cc/auth/register?aff=4YNPP>
- Codex For Me: <https://codex-for.me/?invite=9608>

### 利益披露

通过上面的邀请链接注册的用户，在平台完成兑换并产生消费后，项目维护者可能获得平台提供的相应奖励。
