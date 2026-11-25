#!/bin/bash
# Finder에서도 설치 도구의 일반 경로를 찾는다.
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
KLOVER_ROOT="$(cd -- "$(dirname -- "$0")" && pwd)" || exit 1
KLOVER_PYTHON="$KLOVER_ROOT/apps/server/.venv/bin/python"
if [ ! -x "$KLOVER_PYTHON" ]; then
  echo '먼저 docs/dev/setup.md의 최초 설치를 완료하세요.'
  read -r -p 'Enter를 누르면 닫습니다. ' _
  exit 1
fi
"$KLOVER_PYTHON" "$KLOVER_ROOT/scripts/launcher/run.py" "$@"
KLOVER_RESULT=$?
read -r -p 'Enter를 누르면 실행 창을 닫습니다. ' _
exit "$KLOVER_RESULT"
