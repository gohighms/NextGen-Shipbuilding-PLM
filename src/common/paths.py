from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
EMBEDDINGS_DIR = DATA_DIR / "embeddings"
TAG_REGISTRY_DIR = DATA_DIR / "tag_registry"
POS_DATA_DIR = DATA_DIR / "pos"
POS_DRAFT_DIR = DATA_DIR / "pos_drafts"
MODEL_DATA_DIR = DATA_DIR / "models"
MODEL_DRAFT_DIR = DATA_DIR / "model_drafts"
DESIGN_CHANGE_DIR = DATA_DIR / "design_changes"
BLOCK_DIVISION_DIR = DATA_DIR / "block_division"
MBOM_DIR = DATA_DIR / "mbom"
WBOM_DIR = DATA_DIR / "wbom"
WORK_INSTRUCTION_DIR = DATA_DIR / "work_instructions"
