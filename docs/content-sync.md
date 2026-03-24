# content sync 설정

이 저장소는 `main` 브랜치에 노트를 직접 작성하고 직접 `git push` 하는 운영을 전제로 한다.
`main`에 note markdown이 push되면 GitHub Actions가 실행되고, markdown 파일들을 하나의 JSON snapshot으로 변환한 뒤 `active-recall-quiz`의 content sync 엔드포인트로 POST 한다.

## 전체 흐름

- `main`에서 markdown 작성
- 사용자가 수동으로 `git push`
- GitHub Actions 실행
- markdown 파일을 JSON snapshot으로 변환
- `active-recall-quiz` content sync API로 POST
- `active-recall-quiz`가 SQLite에 idempotent upsert

## workflow 트리거

- 이벤트: `push`
- 브랜치: `main`
- 대상 파일:
- `unit_*/*.md`
- `unit_*/**/*.md`
- `.github/workflows/notes-sync.yml`
- `scripts/build_content_sync_payload.py`

즉, 사용자가 `main`에서 노트 markdown을 수정한 뒤 수동으로 `git push` 하면 해당 push가 그대로 sync 트리거가 된다.

## 필요한 GitHub 설정

Repository Settings에서 아래 값을 설정한다.

### Secrets

- `ACTIVE_RECALL_QUIZ_SYNC_URL`
- `ACTIVE_RECALL_QUIZ_SYNC_TOKEN`

예시 URL:

- `https://your-active-recall-quiz.example.com/api/content/sync`

토큰은 GitHub Actions에서 `Authorization: Bearer <token>` 헤더로 전송된다.

### Variables

- `ACTIVE_RECALL_SYNC_SOURCE`
- `ACTIVE_RECALL_SYNC_TIMEOUT_SECONDS`

권장값:

- `ACTIVE_RECALL_SYNC_SOURCE=active-recall-notes`
- `ACTIVE_RECALL_SYNC_TIMEOUT_SECONDS=30`

## 요청 형태

workflow는 현재 저장소의 note markdown 전체 스냅샷을 JSON으로 만들어 전송한다.
요청에는 아래 정보가 함께 포함된다.

- source
- 저장소명
- git ref
- 현재 commit SHA
- 이전 SHA
- snapshotVersion
- generatedAt
- 변경된 note 파일 목록
- 전체 markdown 문서 목록과 각 파일 내용
- unitId / partId / title
- Actions run id / attempt
- 전체 note 스냅샷 기준 `snapshotKey`

예시 필드:

- `source`
- `ref`
- `commitSha`
- `snapshotVersion`
- `generatedAt`
- `documents`

각 document는 최소한 아래 필드를 포함한다.

- `path`
- `unitId`
- `partId`
- `title`
- `content`

## 실패 확인

실패 원인은 GitHub 저장소의 Actions 탭에서 확인한다.
설정 누락이나 API 비정상 응답이 있으면 job 자체가 실패 상태가 되며, `curl --fail-with-body`를 사용하므로 응답 본문도 로그에서 확인할 수 있다.

## idempotent 재실행

같은 commit SHA 기준 snapshot은 다시 보내도 안전하도록 설계했다.

- `snapshotVersion`은 기본적으로 `commitSha`와 동일하다.
- 전체 snapshot을 보내므로 부분 patch 누적으로 꼬이지 않는다.
- 같은 push를 rerun 하더라도 quiz 쪽에서 `commitSha`, `snapshotVersion`, `snapshotKey` 기준으로 upsert 또는 동일 snapshot 무시를 적용할 수 있다.
- workflow는 `X-Content-Snapshot-Version` 헤더에도 현재 commit SHA를 함께 보낸다.

## 실패 처리

아래 경우 workflow는 즉시 실패한다.

- sync URL secret 누락
- sync token secret 누락
- endpoint가 2xx 이외 응답을 반환
