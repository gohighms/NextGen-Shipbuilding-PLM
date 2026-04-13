## NextGen Shipbuilding PLM

This repository is set up so multiple PLM features can be added over time.
The first feature in place is a shipbuilding specification search and comparison screen.

### Project layout

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

### Why this layout

- `apps/` keeps app entrypoints only.
- `src/common/` is for shared paths, settings, and helpers.
- `src/features/` is where feature-specific code lives.
- New PLM functions can be added as another feature folder.

Possible future feature folders:

- `src/features/spec_search/`
- `src/features/bom_review/`
- `src/features/change_impact/`
- `src/features/document_parser/`

### Current feature

- Read saved spec JSON files
- Calculate simple text similarity
- Compare major attributes
- Review results in Streamlit

### 실행

```bash
streamlit run apps/main_app.py
```

### Suggested next steps

1. Add at least three real sample specifications in the same format
2. Define the standard field list to compare
3. Move from raw text matching to field-based comparison
