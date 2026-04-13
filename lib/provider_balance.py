#!/usr/bin/env python3
"""Fetch provider balance/usage snapshots for local CLI usage.

Security posture:
- Does not persist username/password.
- Supports bearer token directly to avoid password handling.
- Reads credentials from env when provided.
"""

from __future__ import annotations

import argparse
import datetime as dt
import getpass
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


PROVIDERS: dict[str, dict[str, Any]] = {
    "provider": {
        "display_name": "provider",
        "web_base": "https://example.com",
        "api_prefix": "/web/api/v1",
        "login_endpoint": "/users/login",
        "summary_endpoint": "/users/summary",
        "usage_endpoint": "/users/usage-stats",
        "token_env": ["PROVIDER_AUTH_TOKEN"],
        "username_env": ["PROVIDER_USERNAME"],
        "password_env": ["PROVIDER_PASSWORD"],
    }
}


def _fail(msg: str, code: int = 1) -> "NoReturn":
    print(msg, file=sys.stderr)
    raise SystemExit(code)


def _provider_or_die(name: str) -> dict[str, Any]:
    provider = PROVIDERS.get(name)
    if provider is None:
        supported = ", ".join(sorted(PROVIDERS.keys()))
        _fail(f"unsupported provider '{name}'. supported: {supported}")
    return provider


def _clean_base_url(raw: str) -> str:
    value = raw.strip().rstrip("/")
    if not value:
        _fail("base URL cannot be empty")
    if not value.startswith("http://") and not value.startswith("https://"):
        _fail(f"base URL must start with http:// or https://, got: {raw!r}")
    return value


def _pick_env(names: list[str]) -> str:
    for name in names:
        val = os.getenv(name, "").strip()
        if val:
            return val
    return ""


def _safe_json_loads(raw: str) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw}


def _http_json(method: str, url: str, headers: dict[str, str] | None = None, body: dict[str, Any] | None = None, timeout: int = 20) -> tuple[int, Any]:
    payload = None
    req_headers = dict(headers or {})

    if body is not None:
        payload = json.dumps(body, ensure_ascii=True).encode("utf-8")
        req_headers.setdefault("Content-Type", "application/json")

    req = urllib.request.Request(url=url, data=payload, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            status = int(resp.getcode())
            return status, _safe_json_loads(raw)
    except urllib.error.HTTPError as err:
        raw = err.read().decode("utf-8", errors="replace")
        data = _safe_json_loads(raw)
        msg = ""
        if isinstance(data, dict):
            msg = str(data.get("error") or data.get("message") or "")
        _fail(f"HTTP {err.code} {url} {msg}".strip())
    except urllib.error.URLError as err:
        _fail(f"network error while requesting {url}: {err}")


def _unwrap_payload(data: Any) -> Any:
    # Some endpoints return { data: {...} }, some return direct object.
    if isinstance(data, dict) and isinstance(data.get("data"), dict):
        return data["data"]
    return data


def _extract_token(login_payload: Any) -> str:
    candidates = []
    if isinstance(login_payload, dict):
        candidates.extend([
            login_payload.get("token"),
            login_payload.get("access_token"),
            login_payload.get("jwt"),
        ])
        data_field = login_payload.get("data")
        if isinstance(data_field, dict):
            candidates.extend([
                data_field.get("token"),
                data_field.get("access_token"),
                data_field.get("jwt"),
            ])
    for item in candidates:
        if isinstance(item, str) and item.strip():
            return item.strip()
    _fail("login succeeded but no token field found in response")


def _first_present(obj: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        value = obj.get(key)
        if value is not None and value != "":
            return value
    return None


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None


def _fmt_money(value: Any) -> str:
    num = _to_float(value)
    if num is None:
        return "-"
    return f"${num:.2f}"


def _fmt_int(value: Any) -> str:
    num = _to_int(value)
    if num is None:
        return "-"
    return f"{num:,}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="provider-balance",
        description="Fetch month fee / remaining budget / usage snapshot for supported providers",
    )
    parser.add_argument("provider", choices=sorted(PROVIDERS.keys()), help="provider key, e.g. provider")
    parser.add_argument("--base-url", default="", help="override provider web base URL")

    auth = parser.add_argument_group("auth")
    auth.add_argument("--token", default="", help="bearer token (preferred over password)")
    auth.add_argument("--username", default="", help="login username")
    auth.add_argument("--password", default="", help="login password (avoid; may leak into shell history)")
    auth.add_argument("--password-stdin", action="store_true", help="read password from stdin first line")
    auth.add_argument("--prompt-password", action="store_true", help="securely prompt password with no echo")
    auth.add_argument("--force-login", action="store_true", help="ignore existing token and always login")
    auth.add_argument("--emit-token", action="store_true", help="output resolved token and exit")

    parser.add_argument("--days", type=int, default=30, help="days window for usage-stats (default: 30)")
    parser.add_argument("--json", action="store_true", help="print normalized JSON")
    parser.add_argument("--include-raw", action="store_true", help="include raw summary/usage payload in JSON output")
    return parser


def resolve_auth(args: argparse.Namespace, provider: dict[str, Any]) -> tuple[str, str]:
    username = args.username.strip() or _pick_env(provider["username_env"])
    password = args.password

    if args.password_stdin:
        password = sys.stdin.readline().rstrip("\n")
    elif not password:
        password = _pick_env(provider["password_env"])

    if not args.force_login:
        token = args.token.strip() or _pick_env(provider["token_env"])
        if token:
            return token, "token"

    if not password and (args.prompt_password or (username and sys.stdin.isatty())):
        password = getpass.getpass("Provider password: ")

    if not username:
        _fail("missing auth: provide --token or --username (or set PROVIDER_USERNAME)")
    if not password:
        _fail("missing auth: provide --token or --password/--password-stdin/--prompt-password (or set PROVIDER_PASSWORD)")

    return login_for_token(provider, args.base_url, username, password), "login"


def login_for_token(provider: dict[str, Any], base_url_override: str, username: str, password: str) -> str:
    base_url = _clean_base_url(base_url_override) if base_url_override else _clean_base_url(provider["web_base"])
    api_url = f"{base_url}{provider['api_prefix']}{provider['login_endpoint']}"

    _, login_resp = _http_json(
        "POST",
        api_url,
        body={"user_name": username, "password": password},
    )
    return _extract_token(login_resp)


def fetch_snapshot(provider_key: str, provider: dict[str, Any], token: str, base_url_override: str, days: int) -> dict[str, Any]:
    if days <= 0:
        _fail("--days must be > 0")

    base_url = _clean_base_url(base_url_override) if base_url_override else _clean_base_url(provider["web_base"])
    api_root = f"{base_url}{provider['api_prefix']}"

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    summary_url = f"{api_root}{provider['summary_endpoint']}"
    _, summary_resp = _http_json("GET", summary_url, headers=headers)
    summary = _unwrap_payload(summary_resp)
    if not isinstance(summary, dict):
        _fail("unexpected summary response shape")

    usage_qs = urllib.parse.urlencode({"days": days})
    usage_url = f"{api_root}{provider['usage_endpoint']}?{usage_qs}"
    _, usage_resp = _http_json("GET", usage_url, headers=headers)
    usage = _unwrap_payload(usage_resp)
    if not isinstance(usage, dict):
        _fail("unexpected usage-stats response shape")

    month_fee = _first_present(summary, ["this_month_total_amount", "month_total_amount", "monthly_total_amount"])
    remaining_budget = _first_present(summary, ["card_balance", "remaining_budget", "balance"])
    today_requests = _first_present(summary, ["today_request_count", "today_calls"])
    today_tokens = _first_present(
        summary,
        [
            "today_token_count",
            "today_tokens",
            "today_total_tokens",
            "today_token_usage",
            "today_tokens_used",
            "today_total_token_count",
        ],
    )

    snapshot = {
        "provider": provider_key,
        "provider_name": provider.get("display_name", provider_key),
        "base_url": base_url,
        "fetched_at": dt.datetime.now().isoformat(timespec="seconds"),
        "month_fee": month_fee,
        "month_fee_display": _fmt_money(month_fee),
        "remaining_budget": remaining_budget,
        "remaining_budget_display": _fmt_money(remaining_budget),
        "today_requests": today_requests,
        "today_requests_display": _fmt_int(today_requests),
        "today_tokens": today_tokens,
        "today_tokens_display": _fmt_int(today_tokens),
        "usage_window_days": days,
        "usage_total_requests": usage.get("total_requests"),
        "usage_total_requests_display": _fmt_int(usage.get("total_requests")),
        "usage_average_requests": usage.get("average_requests"),
        "usage_today_date": usage.get("today_date"),
    }

    snapshot["_raw_summary"] = summary
    snapshot["_raw_usage"] = usage
    return snapshot


def print_human(snapshot: dict[str, Any], auth_mode: str) -> None:
    print(f"Provider: {snapshot['provider']} ({snapshot['provider_name']})")
    print(f"Auth mode: {auth_mode}")
    print(f"Fetched at: {snapshot['fetched_at']}")
    print(f"This month fee: {snapshot['month_fee_display']}")
    print(f"Remaining budget: {snapshot['remaining_budget_display']}")
    print(f"Today requests: {snapshot['today_requests_display']}")
    print(f"Today tokens: {snapshot['today_tokens_display']}")
    print(
        f"Usage ({snapshot['usage_window_days']}d): total {snapshot['usage_total_requests_display']}, "
        f"avg/day {snapshot.get('usage_average_requests', '-') }"
    )


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    provider = _provider_or_die(args.provider)
    token, auth_mode = resolve_auth(args, provider)

    if args.emit_token:
        if args.json:
            print(
                json.dumps(
                    {
                        "provider": args.provider,
                        "provider_name": provider.get("display_name", args.provider),
                        "auth_mode": auth_mode,
                        "token": token,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            print(token)
        return 0

    snapshot = fetch_snapshot(args.provider, provider, token, args.base_url, args.days)

    if args.json:
        output = dict(snapshot)
        if not args.include_raw:
            output.pop("_raw_summary", None)
            output.pop("_raw_usage", None)
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print_human(snapshot, auth_mode)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
