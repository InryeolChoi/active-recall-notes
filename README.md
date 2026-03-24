# active-recall-notes

정처기 실기 대비를 위해 이론을 markdown으로 정리하는 저장소이다.

## 만든 이유

정처기 실기는 서술형 문제가 많아서, 단순히 눈으로만 읽어서는 답을 안정적으로 써내기 어렵다.
그렇다고 이론을 전부 손으로 정리하기에는 시간이 너무 오래 걸리고, 무작정 외우려고 하면 유지가 잘 되지 않는다.

그래서 먼저 markdown으로 개념을 구조화하고, 이후 이를 active recall 방식으로 반복 학습할 수 있도록 정리한다.

## 이 저장소의 역할

이 저장소는 `active-recall-quiz`에 콘텐츠를 공급하는 노트 저장소이다.

- 여기에서 작성한 markdown은 학습용 원문 데이터가 된다.
- 정리된 내용은 퀴즈 생성 및 복습 흐름의 기반이 된다.
- 저장소에 push된 내용은 `active-recall-quiz`의 DB로 자동 저장될 예정이다.

관련 저장소:

- [active-recall-quiz](https://github.com/InryeolChoi/active-recall-quiz)

## 노트 구조

현재 노트는 `unit_*/*.md` 패턴으로 관리한다.

예시:

- `unit_01_01/part01.md`
- `unit_01_01/part10.md`

`main` 브랜치에 이 노트 파일들을 직접 작성하고 수동으로 `git push` 하면, GitHub Actions가 실행되어 `active-recall-quiz`의 content sync 엔드포인트로 현재 노트 스냅샷을 전송한다.

동기화는 개별 파일 누적 전송이 아니라 markdown 전체를 하나의 JSON snapshot으로 변환해 전달하는 방식으로 동작한다.
이 과정의 Python 실행은 로컬 전역 패키지 설치 대신 `uv` 기준으로 맞춘다.

## 작성 원칙

- 서술형 답안을 바로 떠올릴 수 있도록 핵심 개념을 짧고 분명하게 정리한다.
- 암기만을 위한 문장보다, "왜 그런지"까지 함께 설명하는 구조를 우선한다.
- 한 번 읽고 끝나는 요약이 아니라, 나중에 문제로 다시 꺼내기 좋은 형태로 작성한다.
- 표현은 간결하게 유지하되, 시험 답안으로 옮겨 적을 수 있을 정도의 정확성을 확보한다.

## 목표

이 저장소의 목표는 단순한 이론 보관이 아니다.
정리한 내용을 바탕으로 반복 회상 학습이 가능하도록 만들어, 정처기 실기 서술형에 대응할 수 있는 답안 작성력을 기르는 데 있다.

## content sync 설정

GitHub Actions 기반 content sync 설정 방법은 [docs/content-sync.md](docs/content-sync.md)에 정리했다.
