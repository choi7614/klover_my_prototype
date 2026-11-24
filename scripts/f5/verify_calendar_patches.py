"""최신 기준 소스를 별도 폴더에 펼치고 기능 파일·공통 패치를 적용한다. 브랜치는 바꾸지 않는다."""

import hashlib
import json
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATCHES = ROOT / "patches/F5/calendar"


def main():
    manifest = json.loads((PATCHES / "baseline.json").read_text())
    folder = Path(tempfile.mkdtemp(prefix="klover-f5-calendar-check-"))
    archive = folder / "base.tar"
    subprocess.run(["git", "archive", manifest["base"], "-o", str(archive)], cwd=ROOT, check=True)
    with tarfile.open(archive) as bundle:
        bundle.extractall(folder, filter="data")
    for path, expected in manifest["common_files"].items():
        file = folder / path
        actual = hashlib.sha256(file.read_bytes()).hexdigest() if file.exists() else None
        if actual != expected:
            raise RuntimeError("공통 파일 기준이 다릅니다: " + path)
    for path in manifest["feature_files"]:
        target = folder / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / path, target)
    for patch in sorted(PATCHES.glob("*.patch")):
        subprocess.run(["git", "apply", "--check", str(patch)], cwd=folder, check=True)
        subprocess.run(["git", "apply", str(patch)], cwd=folder, check=True)
    print("패치 적용 검사 통과. 별도 검사 폴더:", folder)
    print("실제 DB/계정 설정을 복사하지 않았습니다. 합성 테스트 DB 변수만 지정해 검사하세요.")


if __name__ == "__main__":
    main()
