"""공통 앱을 수정하지 않고 F2 등록 이후의 계약만 내보낸다. 외부 연결은 없다."""

import argparse
import json
from pathlib import Path

from app.api.profile_draft import register_profile_draft
from app.main import create_app


def main():
    parser = argparse.ArgumentParser(description="F2 적용 검토용 OpenAPI 생성")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    application = create_app()
    register_profile_draft(application)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(application.openapi(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
