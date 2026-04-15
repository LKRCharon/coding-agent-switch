#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_DIR="${SCRIPT_DIR}"
BIN_DIR="${PROJECT_DIR}/bin"
GATEWAY_INSTALL="${PROJECT_DIR}/gateway/claude-gateway-switch"

PREFIX="${PREFIX:-${HOME}/.local/bin}"
INSTALL_LINKS="${INSTALL_LINKS:-1}"

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

main() {
  require_cmd python3

  if ! command -v codex >/dev/null 2>&1; then
    warn "codex is not in PATH yet."
  fi
  if ! command -v claude >/dev/null 2>&1; then
    warn "claude is not in PATH yet."
  fi

  chmod +x "${BIN_DIR}/agent-switch" "${BIN_DIR}/claude-switch" "${BIN_DIR}/codex-switch" "${GATEWAY_INSTALL}"

  if [[ ! -f "${PROJECT_DIR}/.env" ]]; then
    cp "${PROJECT_DIR}/.env.example" "${PROJECT_DIR}/.env"
    chmod 600 "${PROJECT_DIR}/.env"
    say "Created .env from .env.example"
  else
    chmod 600 "${PROJECT_DIR}/.env" 2>/dev/null || true
    say "Found existing .env"
  fi

  say "Installing gateway dependencies (litellm virtualenv)..."
  "${GATEWAY_INSTALL}" install

  if [[ "${INSTALL_LINKS}" == "1" ]]; then
    mkdir -p "${PREFIX}"
    ln -sf "${BIN_DIR}/agent-switch" "${PREFIX}/agent-switch"
    ln -sf "${BIN_DIR}/claude-switch" "${PREFIX}/claude-switch"
    ln -sf "${BIN_DIR}/codex-switch" "${PREFIX}/codex-switch"
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
  1) Edit ${PROJECT_DIR}/.env and fill your provider keys
  2) Verify profiles:
     ${BIN_DIR}/agent-switch profile list
  3) Test codex profile:
     ${BIN_DIR}/agent-switch codex provider prepare

EOF
}

main "$@"
