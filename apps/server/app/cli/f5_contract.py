"""분리 F5 계약을 내보낸다. 운영 앱·계정·DB에 연결하지 않는다."""

import argparse
import json
from pathlib import Path

from fastapi import FastAPI

from app.api.f5 import register_f5_api
from app.schemas.f5 import ScanInput


def main():
    parser = argparse.ArgumentParser(description="F5 전용 계약 출력")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    application = FastAPI()
    register_f5_api(application)
    for filename, document in (
        ("openapi.json", application.openapi()),
        ("f1-input.schema.json", ScanInput.model_json_schema()),
    ):
        (args.output_dir / filename).write_text(
            json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    main()
