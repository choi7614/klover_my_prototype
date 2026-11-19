"""서버 실행이나 외부 연결 없이 실제 앱의 OpenAPI 문서를 내보낸다."""

import argparse
import json
from pathlib import Path

from app.main import app


def main() -> None:
    parser = argparse.ArgumentParser(description="Klover OpenAPI 문서를 내보냅니다")
    parser.add_argument("--output", required=True, type=Path, help="저장할 JSON 파일 경로")
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(app.openapi(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
