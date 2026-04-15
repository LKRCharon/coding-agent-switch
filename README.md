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

- 统一入口：`bin/agent-switch`
- 兼容入口：`bin/claude-switch`、`bin/codex-switch`
- 网关组件：`gateway/claude-gateway-switch`
- 配置模板：`profiles/*/config.toml` + `auth.json.template`
- 本地私有 profile：`profiles-local/*`（默认不进 git）

## 目录结构

```text
coding-agent-switch/
├── bin/
│   ├── agent-switch
│   ├── claude-switch
│   └── codex-switch
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

- `claude` CLI
- `codex` CLI
- `python3`（建议 3.10+）

## 一键安装

在仓库根目录执行：

```bash
./install.sh
```

它会自动完成：
- 初始化 `.env`（不存在时从 `.env.example` 复制）
- 安装 `gateway/.venv` 和 LiteLLM 依赖
- 把 `agent-switch` / `claude-switch` / `codex-switch` 链接到 `~/.local/bin`

## 快速开始

1. 复制环境变量模板：

```bash
cd coding-agent-switch
cp .env.example .env
chmod 600 .env
```

2. 在 `.env` 里填入你需要的 key（比如 `PROVIDER_API_KEY`）。

3. 安装网关依赖（LiteLLM）：

```bash
./gateway/claude-gateway-switch install
```

4. 查看可用 profile：

```bash
./bin/agent-switch list
```

## 常用命令

### 0) 多 profile（ttapi / fox）本地创建（不进 git）

```bash
# 创建 ttapi（写到 profiles-local/ttapi）
./bin/agent-switch profile create ttapi \
  --base-url https://your-ttapi-endpoint/v1 \
  --env-key TTAPI_API_KEY

# 创建 fox（写到 profiles-local/fox）
./bin/agent-switch profile create fox \
  --base-url https://your-fox-endpoint/v1 \
  --env-key FOX_API_KEY

# 查看可用 profile（包含 profiles-local）
./bin/agent-switch profile list
```

在 `.env` 中放 key（示例）：

```bash
TTAPI_API_KEY=...
FOX_API_KEY=...
```

### 1) Codex 切换 provider

```bash
# 临时切换（只对当前命令生效）
./bin/agent-switch codex ttapi
./bin/agent-switch codex fox

# 仅查看当前 profile 解析结果
./bin/agent-switch codex ttapi prepare
./bin/agent-switch codex ttapi env

# 持久切换（修改 ~/.codex/config.toml + ~/.codex/auth.json）
# 适合让 Codex VSCode 扩展也跟随使用同一 provider
./bin/agent-switch codex ttapi persist
```

### 2) Claude 切换底层

```bash
# 原生 Claude（不走网关）
./bin/agent-switch claude native

# 走 profile（经 LiteLLM 代理）
./bin/agent-switch claude ttapi

# 单次提示
./bin/agent-switch claude ttapi -p "Reply with exactly OK."
```

### 3) 网关运维

```bash
./bin/agent-switch claude ttapi serve
./bin/agent-switch claude ttapi status
./bin/agent-switch claude ttapi logs
./bin/agent-switch claude ttapi stop
```

## 配置方式（推荐）

优先使用 `.env` 管理 key，不把密钥写进仓库。

- `profiles/*/config.toml`：放 base_url、model、env_key
- `profiles-local/*/config.toml`：放你的私有 provider（ttapi/fox），默认忽略提交
- `.env`：放真实 key（如 `PROVIDER_API_KEY=...`）

如果你更习惯按 profile 独立放 key，也可以在 `profiles/<name>/auth.json` 放：

```json
{
  "OPENAI_API_KEY": "your_api_key_here"
}
```

`auth.json` 已在 `.gitignore` 里默认忽略。

## 给 AI Coding 助手的部署提示词（可直接贴）

```text
请在本机部署 coding-agent-switch：
1) 复制 .env.example 为 .env 并设置 chmod 600
2) 按我提供的 key 填写 .env
3) 执行 ./gateway/claude-gateway-switch install
4) 运行 ./bin/agent-switch list 验证 profile
5) 运行 ./bin/agent-switch codex ttapi prepare 验证 codex provider
6) 运行 ./bin/agent-switch codex ttapi persist（需要持久切换时）
7) 运行 ./bin/agent-switch claude native status 与 ./bin/agent-switch claude ttapi prepare
8) 不要把 .env、profiles-local/、profiles/*/auth.json、gateway/runtime/ 提交到 git
```

## 安全建议

- 只提交模板，不提交真实 key/token。
- `.env`、`auth.json`、runtime 日志都应本地保存。
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
