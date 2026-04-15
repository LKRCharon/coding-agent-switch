#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import secrets
import stat
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    import tomli as tomllib


def eprint(message: str) -> None:
    print(message, file=sys.stderr)


def profile_search_roots(primary_root: Path, local_root: str | None) -> list[Path]:
    roots = [primary_root]
    if local_root:
        roots.insert(0, Path(local_root))
    return roots


def resolve_profile_dir(profile: str, roots: list[Path]) -> Path:
    for root in roots:
        profile_dir = root / profile
        if profile_dir.is_dir():
            return profile_dir
    raise SystemExit(f"Profile not found: {profile}")


def iter_profile_dirs(roots: list[Path]) -> list[Path]:
    seen: set[str] = set()
    dirs: list[Path] = []
    for root in roots:
        if not root.is_dir():
            continue
        for profile_dir in sorted(root.iterdir()):
            if not profile_dir.is_dir():
                continue
            profile = profile_dir.name
            if profile in seen:
                continue
            seen.add(profile)
            dirs.append(profile_dir)
    return dirs


def load_profile_config(roots: list[Path], profile: str) -> tuple[Path, dict, dict]:
    profile_dir = resolve_profile_dir(profile, roots)

    config_path = profile_dir / "config.toml"
    if not config_path.is_file():
        raise SystemExit(f"Missing config.toml for profile: {profile}")

    with config_path.open("rb") as fh:
        config = tomllib.load(fh)

    providers = config.get("model_providers", {})
    provider = providers.get(profile)
    if not provider:
        raise SystemExit(
            f"Profile {profile} is missing [model_providers.{profile}] in config.toml"
        )

    wire_api = provider.get("wire_api")
    if wire_api != "responses":
        raise SystemExit(
            f"Profile {profile} uses wire_api={wire_api!r}; expected 'responses'"
        )

    return profile_dir, config, provider


def resolve_upstream_api_key(
    *, profile_dir: Path, profile: str, provider: dict
) -> tuple[str, str]:
    auth_path = profile_dir / "auth.json"
    env_key = str(provider.get("env_key", "OPENAI_API_KEY"))

    # Priority 1: profile-local auth file (never committed).
    if auth_path.is_file():
        with auth_path.open("r", encoding="utf-8") as fh:
            auth = json.load(fh)
        api_key = str(auth.get("OPENAI_API_KEY", "")).strip()
        if api_key:
            return api_key, f"auth.json:{auth_path}"

    # Priority 2: env key declared in provider.
    api_key = str(os.getenv(env_key, "")).strip()
    if api_key:
        return api_key, f"env:{env_key}"

    # Priority 3: generic OPENAI_API_KEY fallback.
    api_key = str(os.getenv("OPENAI_API_KEY", "")).strip()
    if api_key:
        return api_key, "env:OPENAI_API_KEY"

    raise SystemExit(
        "Missing upstream API key. Provide one of:\n"
        f"  1) {auth_path} with OPENAI_API_KEY\n"
        f"  2) environment variable {env_key}\n"
        "  3) environment variable OPENAI_API_KEY"
    )


def yaml_scalar(value: object) -> str:
    return json.dumps(value, ensure_ascii=True)


def write_secure(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    path.chmod(stat.S_IRUSR | stat.S_IWUSR)


def load_or_create_state(path: Path, profile: str, upstream_name: str) -> dict:
    if path.is_file():
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)

    state = {
        "profile": profile,
        "upstream_name": upstream_name,
        "master_key": f"sk-litellm-{secrets.token_urlsafe(24)}",
    }
    write_secure(path, json.dumps(state, indent=2) + "\n")
    return state


def render_yaml(
    *,
    upstream_base_url: str,
    default_model: str,
    mini_model: str,
    master_key: str,
) -> str:
    entries = [
        ("sonnet", default_model),
        ("opus", default_model),
        ("haiku", mini_model),
        (default_model, default_model),
        (mini_model, mini_model),
    ]

    lines = ["model_list:"]
    for model_name, target_model in entries:
        lines.extend(
            [
                f"  - model_name: {yaml_scalar(model_name)}",
                "    litellm_params:",
                f"      model: {yaml_scalar(f'openai/{target_model}')}",
                f"      api_base: {yaml_scalar(upstream_base_url)}",
                "      api_key: os.environ/UPSTREAM_OPENAI_API_KEY",
                "      drop_params: true",
                "      additional_drop_params:",
                "        - user",
            ]
        )

    lines.extend(
        [
            "litellm_settings:",
            f"  master_key: {yaml_scalar(master_key)}",
            "  drop_params: true",
        ]
    )
    return "\n".join(lines) + "\n"


def render_litellm_env(api_key: str) -> str:
    return f"export UPSTREAM_OPENAI_API_KEY={json.dumps(api_key, ensure_ascii=True)}\n"


def render_claude_env(*, port: int, master_key: str) -> str:
    lines = {
        "ANTHROPIC_BASE_URL": f"http://127.0.0.1:{port}",
        "ANTHROPIC_AUTH_TOKEN": master_key,
        "ANTHROPIC_MODEL": "gpt-5.4",
        "ANTHROPIC_DEFAULT_SONNET_MODEL": "gpt-5.4",
        "ANTHROPIC_DEFAULT_OPUS_MODEL": "gpt-5.4",
        "ANTHROPIC_DEFAULT_HAIKU_MODEL": "gpt-5.4-mini",
        "CLAUDE_CODE_SUBAGENT_MODEL": "gpt-5.4",
    }
    return "".join(
        f"export {key}={json.dumps(value, ensure_ascii=True)}\n"
        for key, value in lines.items()
    )


def render_claude_settings(*, port: int, master_key: str, default_model: str, mini_model: str) -> str:
    payload = {
        "env": {
            "ANTHROPIC_BASE_URL": f"http://127.0.0.1:{port}",
            "ANTHROPIC_AUTH_TOKEN": master_key,
            "ANTHROPIC_MODEL": default_model,
            "ANTHROPIC_DEFAULT_SONNET_MODEL": default_model,
            "ANTHROPIC_DEFAULT_OPUS_MODEL": default_model,
            "ANTHROPIC_DEFAULT_HAIKU_MODEL": mini_model,
            "CLAUDE_CODE_SUBAGENT_MODEL": default_model,
        },
        "model": default_model,
    }
    return json.dumps(payload, indent=2) + "\n"


def command_list(args: argparse.Namespace) -> int:
    roots = profile_search_roots(Path(args.profiles_root), args.profiles_local_root)
    for profile_dir in iter_profile_dirs(roots):
        profile = profile_dir.name
        try:
            _, _, provider = load_profile_config(roots, profile)
            base_url = provider.get("base_url", "")
            print(f"{profile}\tresponses\t{base_url}")
        except SystemExit as exc:
            print(f"{profile}\terror\t{exc}", file=sys.stderr)
    return 0


def command_render(args: argparse.Namespace) -> int:
    roots = profile_search_roots(Path(args.profiles_root), args.profiles_local_root)
    runtime_root = Path(args.runtime_root)
    profile_dir, _, provider = load_profile_config(roots, args.profile)
    api_key, key_source = resolve_upstream_api_key(
        profile_dir=profile_dir, profile=args.profile, provider=provider
    )

    state_path = runtime_root / f"{args.profile}.state.json"
    state = load_or_create_state(state_path, args.profile, provider.get("name", args.profile))

    yaml_path = runtime_root / f"{args.profile}.yaml"
    litellm_env_path = runtime_root / f"{args.profile}.litellm.env"
    claude_env_path = runtime_root / f"{args.profile}.claude.env"
    claude_settings_path = runtime_root / f"{args.profile}.claude.settings.json"

    write_secure(
        yaml_path,
        render_yaml(
            upstream_base_url=provider["base_url"],
            default_model=args.model,
            mini_model=args.mini_model,
            master_key=state["master_key"],
        ),
    )
    write_secure(litellm_env_path, render_litellm_env(api_key))
    write_secure(
        claude_env_path,
        render_claude_env(port=args.port, master_key=state["master_key"]),
    )
    write_secure(
        claude_settings_path,
        render_claude_settings(
            port=args.port,
            master_key=state["master_key"],
            default_model=args.model,
            mini_model=args.mini_model,
        ),
    )

    metadata = {
        "profile": args.profile,
        "provider_name": provider.get("name", args.profile),
        "upstream_base_url": provider["base_url"],
        "yaml_path": str(yaml_path),
        "litellm_env_path": str(litellm_env_path),
        "claude_env_path": str(claude_env_path),
        "claude_settings_path": str(claude_settings_path),
        "state_path": str(state_path),
        "port": args.port,
        "default_model": args.model,
        "mini_model": args.mini_model,
        "api_key_source": key_source,
    }
    print(json.dumps(metadata, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("--profiles-root", required=True)
    list_parser.add_argument("--profiles-local-root", default="")
    list_parser.set_defaults(func=command_list)

    render_parser = subparsers.add_parser("render")
    render_parser.add_argument("--profiles-root", required=True)
    render_parser.add_argument("--profiles-local-root", default="")
    render_parser.add_argument("--runtime-root", required=True)
    render_parser.add_argument("--profile", required=True)
    render_parser.add_argument("--model", default="gpt-5.4")
    render_parser.add_argument("--mini-model", default="gpt-5.4-mini")
    render_parser.add_argument("--port", type=int, default=4000)
    render_parser.set_defaults(func=command_render)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
