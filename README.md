## NextGen Shipbuilding PLM

이 저장소는 여러 PLM 기능을 단계적으로 붙여갈 수 있도록 기본 구조를 먼저 정리한 상태입니다.
현재 첫 기능으로 건조사양서 유사 검색 및 비교 화면이 들어가 있습니다.

### 프로젝트 구조

```text
.
|-- apps/
|   `-- main_app.py
|-- data/
|   |-- embeddings/
|   |   `-- .gitkeep
|   |-- processed/
|   |   `-- sample_lngc_spec.json
|   `-- raw/
|       `-- .gitkeep
|-- docs/
|   `-- spec-comparison-architecture.md
|-- src/
|   |-- common/
|   |   `-- paths.py
|   `-- features/
|       `-- spec_search/
|           |-- compare.py
|           |-- models.py
|           |-- repository.py
|           |-- service.py
|           |-- similarity.py
|           `-- ui.py
|-- tests/
|   `-- test_spec_search.py
`-- requirements.txt
```

### 구조를 이렇게 잡은 이유

- `apps/`는 실행 진입점만 둡니다.
- `src/common/`에는 여러 기능이 같이 쓰는 경로, 설정, 공통 유틸을 둡니다.
- `src/features/` 아래에 기능별 코드를 나눕니다.
- 새 기능이 생기면 `src/features/기능명/`만 추가하면 됩니다.

예를 들면 앞으로 이런 식으로 늘릴 수 있습니다.

- `src/features/spec_search/`
- `src/features/bom_review/`
- `src/features/change_impact/`
- `src/features/document_parser/`

### 현재 들어간 기능

- 저장된 사양서 JSON 조회
- 입력 텍스트 기반 유사도 계산
- 주요 속성 비교
- Streamlit 화면에서 결과 확인

### 실행

```bash
streamlit run apps/main_app.py
```

### 다음 작업 추천

1. 실제 건조사양서 샘플을 더 추가해 비교 정확도를 높입니다.
2. 비교 기준이 되는 공통 항목 체계를 정의합니다.
3. 텍스트 유사도에서 항목 기반 비교로 점진적으로 옮겨갑니다.
