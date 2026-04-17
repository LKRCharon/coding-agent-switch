#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_DIR="${SCRIPT_DIR}"
BIN_DIR="${PROJECT_DIR}/bin"
GATEWAY_INSTALL="${PROJECT_DIR}/gateway/claude-gateway-switch"

PREFIX="${PREFIX:-${HOME}/.local/bin}"
INSTALL_LINKS="${INSTALL_LINKS:-1}"
INSTALL_CLAUDE_GATEWAY="${INSTALL_CLAUDE_GATEWAY:-0}"
INSTALL_CLAUDE_LINK="${INSTALL_CLAUDE_LINK:-0}"

say() {
  printf '[install] %s\n' "$*"
}

warn() {
  printf '[install][warn] %s\n' "$*" >&2
}

die() {
  printf '[install][error] %s\n' "$*" >&2
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Missing required command: $1"
}

usage() {
  cat <<'EOF'
Usage:
  ./install.sh [--with-claude-gateway] [--with-claude-link]

Default behavior:
  - Installs Codex-focused commands only (agent-switch/codex-switch/add-profile)
  - Does NOT install LiteLLM gateway dependencies
  - Does NOT link claude-switch by default

Options:
  --with-claude-gateway  Install LiteLLM gateway dependencies
  --with-claude-link     Also link claude-switch to ~/.local/bin
  -h, --help             Show this help

Equivalent env flags:
  INSTALL_CLAUDE_GATEWAY=1
  INSTALL_CLAUDE_LINK=1
EOF
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --with-claude-gateway)
        INSTALL_CLAUDE_GATEWAY=1
        INSTALL_CLAUDE_LINK=1
        shift
        ;;
      --with-claude-link)
        INSTALL_CLAUDE_LINK=1
        shift
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        die "Unknown option: $1"
        ;;
    esac
  done
}

main() {
  parse_args "$@"
  require_cmd python3

  if ! command -v codex >/dev/null 2>&1; then
    warn "codex is not in PATH yet."
  fi

  chmod +x "${BIN_DIR}/agent-switch" "${BIN_DIR}/claude-switch" "${BIN_DIR}/codex-switch" "${BIN_DIR}/add-profile" "${GATEWAY_INSTALL}"

  if [[ ! -f "${PROJECT_DIR}/.env" ]]; then
    cp "${PROJECT_DIR}/.env.example" "${PROJECT_DIR}/.env"
    chmod 600 "${PROJECT_DIR}/.env"
    say "Created .env from .env.example"
  else
    chmod 600 "${PROJECT_DIR}/.env" 2>/dev/null || true
    say "Found existing .env"
  fi

  if [[ "${INSTALL_CLAUDE_GATEWAY}" == "1" ]]; then
    if ! command -v claude >/dev/null 2>&1; then
      warn "claude is not in PATH yet."
    fi
    say "Installing gateway dependencies (litellm virtualenv)..."
    "${GATEWAY_INSTALL}" install
  else
    say "Skipped LiteLLM gateway dependencies (Codex-only mode)"
  fi

  if [[ "${INSTALL_LINKS}" == "1" ]]; then
    mkdir -p "${PREFIX}"
    ln -sf "${BIN_DIR}/agent-switch" "${PREFIX}/agent-switch"
    ln -sf "${BIN_DIR}/codex-switch" "${PREFIX}/codex-switch"
    ln -sf "${BIN_DIR}/add-profile" "${PREFIX}/add-profile"
    if [[ "${INSTALL_CLAUDE_LINK}" == "1" ]]; then
      ln -sf "${BIN_DIR}/claude-switch" "${PREFIX}/claude-switch"
    fi
    say "Installed command links to ${PREFIX}"
  else
    say "Skipped command links (INSTALL_LINKS=${INSTALL_LINKS})"
  fi

  if [[ ":${PATH}:" != *":${PREFIX}:"* ]]; then
    warn "${PREFIX} is not in PATH. Add this line to your shell profile:"
    printf 'export PATH="%s:$PATH"\n' "${PREFIX}"
  fi

  cat <<EOF

Done.

Next:
  1) Create your first profile:
     add-profile --name your-provider --base-url https://api.example.com --api-key sk-...
  2) Verify profiles:
     agent-switch profile list
  3) Test codex profile:
     agent-switch codex provider prepare
  4) Optional (Claude gateway):
     ./install-claude-gateway.sh

EOF
}

main "$@"
