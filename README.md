# coding-agent-switch

CLI-first switcher for coding agents.

目标：让你用一个项目同时完成两件事。

1. 随时切换 Codex 的 API 提供商。
2. 随时切换 Claude Code 的底层：
   - `native`（原生 Claude）
   - `profile`（走 LiteLLM 网关，底层转到 Codex/OpenAI 兼容提供商）

本仓库仅包含模板和逻辑，不包含任何敏感数据。

## 功能概览

- 统一入口：`bin/agent-switch`
- 兼容入口：`bin/claude-switch`、`bin/codex-switch`
- 网关组件：`gateway/claude-gateway-switch`
- 配置模板：`profiles/*/config.toml` + `auth.json.template`
- 余额查询（可选）：`balance` / `balance-login`（当前内置 cfm）

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
│   ├── cfm/
│   ├── cfm-asia/
│   ├── fox/
│   ├── ttapi/
│   └── sub2api/
├── .env.example
└── .gitignore
```

## 前置条件

- `claude` CLI
- `codex` CLI
- `python3`（建议 3.10+）

## 快速开始

1. 复制环境变量模板：

```bash
cd coding-agent-switch
cp .env.example .env
chmod 600 .env
```

2. 在 `.env` 里填入你需要的 key（比如 `CFM_API_KEY`）。

3. 安装网关依赖（LiteLLM）：

```bash
./gateway/claude-gateway-switch install
```

4. 查看可用 profile：

```bash
./bin/agent-switch list
```

## 常用命令

### 1) Codex 切换 provider

```bash
# 直接以 cfm profile 启动 codex
./bin/agent-switch codex cfm

# 仅查看当前 profile 解析结果
./bin/agent-switch codex cfm prepare
./bin/agent-switch codex cfm env
```

### 2) Claude 切换底层

```bash
# 原生 Claude（不走网关）
./bin/agent-switch claude native

# 走 cfm profile（经 LiteLLM 代理）
./bin/agent-switch claude cfm

# 单次提示
./bin/agent-switch claude cfm -p "Reply with exactly OK."
```

### 3) 网关运维

```bash
./bin/agent-switch claude cfm serve
./bin/agent-switch claude cfm status
./bin/agent-switch claude cfm logs
./bin/agent-switch claude cfm stop
```

### 4) cfm 余额查询（可选）

```bash
./bin/agent-switch balance cfm --json
./bin/agent-switch balance-login cfm --username your_name --prompt-password
```

## 配置方式（推荐）

优先使用 `.env` 管理 key，不把密钥写进仓库。

- `profiles/*/config.toml`：放 base_url、model、env_key
- `.env`：放真实 key（如 `CFM_API_KEY=...`）

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
5) 运行 ./bin/agent-switch codex cfm prepare 验证 codex provider
6) 运行 ./bin/agent-switch claude native status 与 ./bin/agent-switch claude cfm prepare
7) 不要把 .env、profiles/*/auth.json、gateway/runtime/ 提交到 git
```

## 安全建议

- 只提交模板，不提交真实 key/token。
- `.env`、`auth.json`、runtime 日志都应本地保存。
- 推荐把 `gateway` 仅绑定到本地回环地址（默认本地端口）。
- 升级后先跑 `prepare/status` 再切换正式流量。

## 开源说明

这是 CLI 工具，定位是 GUI 工具（如 cc switch）的脚本化补位，不是 GUI 替代品。

