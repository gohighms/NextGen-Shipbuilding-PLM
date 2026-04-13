# Spec Search Architecture

## 1. Goal

Given a new shipbuilding specification, find similar past documents and compare major fields.

## 2. Suggested steps

### Step 1. Normalize source documents

- Extract text and tables from PDF, Excel, Word, and CSV
- Map field labels into standard keys
- Normalize units and value formats

Examples:

- `Length overall`, `LOA` -> `principal_dimensions.loa`
- `Main Engine` -> `machinery.main_engine`

### Step 2. Search similar specifications

- Filter by project metadata and major dimensions
- Rank candidates by text similarity or embeddings
- Re-rank by weighted business fields

### Step 3. Compare the selected baseline

- Check matching fields
- Calculate value differences
- Detect missing or extra fields
- Summarize high-impact design changes

## 3. Draft data model

```json
{
  "spec_id": "LNGC-250K-001",
  "ship_type": "LNGC",
  "principal_dimensions": {
    "loa": 299.0,
    "breadth": 46.4,
    "depth": 26.5
  },
  "machinery": {
    "main_engine": "ME-GI",
    "generator": "DFDE"
  },
  "performance": {
    "service_speed": 19.5
  }
}
```

## 4. Module roles

- `repository`: load saved spec data
- `similarity`: score text similarity
- `compare`: compare field values
- `service`: connect search and comparison logic
- `ui`: render the Streamlit page

## 5. Implementation order

1. Lock down the sample data shape
2. Add more sample project files
3. Replace raw text matching with field-based matching
4. Add embeddings when the baseline flow is stable
