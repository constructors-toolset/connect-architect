#!/usr/bin/env bash
# 목적: 허브의 서브모듈 포인터(repo/<이름>)를 서브 프로젝트의 푸시된 커밋에 맞추고 허브에 커밋한다.
# 사용법 (허브 저장소 루트에서):
#   tools/scripts/sync-subproject.sh <이름> [ref]
#   ref 생략 시: 서브 프로젝트 원격에 허브와 같은 이름의 브랜치가 있으면 그 브랜치, 없으면 원격 기본 브랜치.
# 푸시는 하지 않는다. 결과를 확인한 뒤 허브에서 직접 푸시한다.
set -euo pipefail

name="${1:?사용법: $0 <이름> [ref]}"
path="repo/$name"
root="$(git rev-parse --show-toplevel)"
cd "$root"

[ -n "$(git config -f .gitmodules --get "submodule.$path.url" || true)" ] \
  || { echo "서브모듈이 아님: $path" >&2; exit 1; }

git submodule update --init "$path" >/dev/null
git -C "$path" fetch --quiet origin

ref="${2:-}"
if [ -z "$ref" ]; then
  hub_branch="$(git branch --show-current)"
  if git -C "$path" rev-parse --verify --quiet "origin/$hub_branch" >/dev/null; then
    ref="origin/$hub_branch"
  else
    ref="$(git -C "$path" symbolic-ref --quiet --short refs/remotes/origin/HEAD || echo origin/main)"
  fi
fi

sha="$(git -C "$path" rev-parse --verify "$ref^{commit}")"
# 원격에 없는 커밋을 가리키면 다른 사람이 서브모듈을 받을 수 없다.
[ -n "$(git -C "$path" branch -r --contains "$sha")" ] \
  || { echo "원격에 푸시되지 않은 커밋: $sha" >&2; exit 1; }

git -C "$path" checkout --quiet "$sha"
git add "$path"
if git diff --cached --quiet -- "$path"; then
  echo "$path 는 이미 $ref (${sha:0:7}) 을 가리킨다."
  exit 0
fi

subject="$(git -C "$path" log -1 --format=%s "$sha")"
git commit --quiet -m "$path 포인터 갱신 — $subject" -m "$name ${sha:0:7} ($ref)" -- "$path"
echo "$path → ${sha:0:7} ($ref) 커밋 완료. 확인 후 git push 하세요."
