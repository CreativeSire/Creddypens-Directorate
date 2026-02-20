from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _check_required(env_map: dict[str, str], keys: list[str]) -> list[str]:
    missing: list[str] = []
    for key in keys:
        value = env_map.get(key, "").strip()
        if not value:
            missing.append(key)
    return missing


def main() -> int:
    parser = argparse.ArgumentParser(description="Pre-deploy environment validation for CreddyPens.")
    parser.add_argument("--backend-env", default="backend/.env", help="Path to backend env file")
    parser.add_argument("--frontend-env", default="frontend/.env.local", help="Path to frontend env file")
    parser.add_argument(
        "--allow-missing-frontend",
        action="store_true",
        help="Do not fail when frontend env variables are missing",
    )
    args = parser.parse_args()

    backend_env = _parse_env_file(Path(args.backend_env))
    frontend_env = _parse_env_file(Path(args.frontend_env))

    backend_required = [
        "DATABASE_URL",
        "ALLOWED_ORIGINS",
        "LLM_MOCK",
    ]
    backend_provider_any = ["ANTHROPIC_API_KEY", "GEMINI_API_KEY", "OPENAI_API_KEY", "GROQ_API_KEY", "GOOGLE_API_KEY"]
    backend_optional_prod = [
        "SENTRY_DSN",
        "SERPER_API_KEY",
        "SUPABASE_URL",
        "SUPABASE_ANON_KEY",
        "SUPABASE_SERVICE_ROLE_KEY",
        "RATE_LIMIT_ENABLED",
        "EXECUTE_RATE_LIMIT_PER_MINUTE",
    ]

    frontend_required = ["NEXT_PUBLIC_SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_ANON_KEY"]
    frontend_optional = ["NEXT_PUBLIC_API_URL"]

    print("PREDEPLOY CHECK")
    print("=" * 64)
    print(f"Backend env file: {Path(args.backend_env).resolve()}")
    print(f"Frontend env file: {Path(args.frontend_env).resolve()}")
    print("-" * 64)

    backend_missing = _check_required(backend_env, backend_required)
    if backend_missing:
        print(f"FAIL backend required missing: {', '.join(backend_missing)}")
    else:
        print("PASS backend required keys present")

    if any((backend_env.get(k, "").strip() for k in backend_provider_any)):
        print("PASS backend provider key: at least one configured")
        provider_ok = True
    else:
        print(f"FAIL backend provider key missing: need one of {', '.join(backend_provider_any)}")
        provider_ok = False

    for key in backend_optional_prod:
        present = bool(backend_env.get(key, "").strip())
        print(f"{'PASS' if present else 'WARN'} optional backend {key}")

    frontend_missing = _check_required(frontend_env, frontend_required)
    if frontend_missing:
        level = "WARN" if args.allow_missing_frontend else "FAIL"
        print(f"{level} frontend required missing: {', '.join(frontend_missing)}")
    else:
        print("PASS frontend required keys present")

    for key in frontend_optional:
        present = bool(frontend_env.get(key, "").strip())
        print(f"{'PASS' if present else 'WARN'} optional frontend {key}")

    llm_mock_value = backend_env.get("LLM_MOCK", "").strip()
    if llm_mock_value == "0":
        print("PASS LLM_MOCK is production-safe (0)")
        llm_mock_ok = True
    else:
        print(f"WARN LLM_MOCK is '{llm_mock_value or '<missing>'}' (expected 0 for production)")
        llm_mock_ok = False

    print("-" * 64)
    failed = bool(backend_missing) or not provider_ok or (bool(frontend_missing) and not args.allow_missing_frontend)
    if failed:
        print("RESULT: FAIL")
        return 1

    if not llm_mock_ok:
        print("RESULT: PASS WITH WARNINGS")
        return 0

    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
