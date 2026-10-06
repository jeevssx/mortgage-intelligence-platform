"""Export the OpenAPI spec to docs/api/analytics-openapi.yaml (no DB or AWS needed).

Run from the service folder:  python -m scripts.export_openapi
"""

from __future__ import annotations

from pathlib import Path

import yaml

from src.api.main import create_app
from src.config import Settings

OUTPUT = Path(__file__).resolve().parents[3] / "docs" / "api" / "analytics-openapi.yaml"


class _Unused:
    def __getattr__(self, name: str):
        raise RuntimeError("not used during export")


def main() -> None:
    app = create_app(Settings(db_check_on_startup=False), repository=_Unused(), s3_client=_Unused())
    spec = app.openapi()
    spec["servers"] = [{"url": "http://localhost:8000", "description": "Local"}]
    OUTPUT.write_text(yaml.safe_dump(spec, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
