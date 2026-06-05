import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parent
DATA_DIR = REPO_ROOT / "data"
STORAGE_DIR = REPO_ROOT / "storage"
DEFAULT_EXTERNAL_DATASET_DIR = Path("/Users/grsxsa/2026 Spring/ecommerce_agent_dataset")
DEFAULT_REPO_DATASET_DIR = REPO_ROOT / "ecommerce_agent_dataset"
DEFAULT_MODELS_DIR = REPO_ROOT / "models"


class Settings(BaseModel):
    app_name: str = "Ecommerce Guider Backend"
    app_version: str = "0.1.0"
    api_prefix: str = "/api"
    app_env: str = "local"
    product_data_path: Path = DATA_DIR / "products.json"
    product_dataset_dir: Path | None = None
    user_history_dir: Path = STORAGE_DIR / "user_history"
    use_mock_llm: bool = False
    doubao_api_key: str | None = None
    doubao_base_url: str | None = None
    doubao_model: str = "ep-20260514111645-lmgt2"
    retrieval_top_k: int = 5
    enable_local_models: bool = True
    local_model_device: str = "cpu"
    bge_embedding_model_path: Path = DEFAULT_MODELS_DIR / "bge-small-zh-v1.5"
    text2vec_model_path: Path = DEFAULT_MODELS_DIR / "text2vex-base-chinese"
    bge_reranker_model_path: Path = DEFAULT_MODELS_DIR / "bge-reranker-base"
    enable_multimodal: bool = True
    vision_model: str | None = None
    upload_image_dir: Path = STORAGE_DIR / "uploads"


def _load_dotenv() -> None:
    dotenv_path = REPO_ROOT / ".env"
    if not dotenv_path.exists():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def _read_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _read_path(name: str, default: Path) -> Path:
    raw = os.getenv(name)
    path = Path(raw) if raw else default
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path


@lru_cache
def get_settings() -> Settings:
    _load_dotenv()
    product_data_raw = Path(os.getenv("PRODUCT_DATA_PATH", str(DATA_DIR / "products.json")))
    if not product_data_raw.is_absolute():
        product_data_raw = REPO_ROOT / product_data_raw
    dataset_env = os.getenv("PRODUCT_DATASET_DIR")
    if dataset_env:
        dataset_dir = Path(dataset_env)
    elif DEFAULT_REPO_DATASET_DIR.exists():
        dataset_dir = DEFAULT_REPO_DATASET_DIR
    else:
        dataset_dir = DEFAULT_EXTERNAL_DATASET_DIR
    if not dataset_dir.is_absolute():
        dataset_dir = REPO_ROOT / dataset_dir
    if not dataset_dir.exists():
        dataset_dir = DATA_DIR / "raw"
    explicit_use_mock_llm = os.getenv("USE_MOCK_LLM")
    doubao_api_key = os.getenv("DOUBAO_API_KEY")
    use_mock_llm = _read_bool("USE_MOCK_LLM", not bool(doubao_api_key)) if explicit_use_mock_llm is not None else not bool(doubao_api_key)
    return Settings(
        app_name=os.getenv("BACKEND_APP_NAME", "Ecommerce Guider Backend"),
        app_version=os.getenv("BACKEND_APP_VERSION", "0.1.0"),
        api_prefix=os.getenv("API_PREFIX", os.getenv("API_V1_PREFIX", "/api")),
        app_env=os.getenv("APP_ENV", "local"),
        product_data_path=product_data_raw,
        product_dataset_dir=dataset_dir,
        user_history_dir=_read_path("USER_HISTORY_DIR", STORAGE_DIR / "user_history"),
        use_mock_llm=use_mock_llm,
        doubao_api_key=doubao_api_key,
        doubao_base_url=os.getenv("DOUBAO_BASE_URL"),
        doubao_model=os.getenv("DOUBAO_MODEL", "ep-20260514111645-lmgt2"),
        retrieval_top_k=int(os.getenv("RETRIEVAL_TOP_K", "5")),
        enable_local_models=_read_bool("ENABLE_LOCAL_MODELS", True),
        local_model_device=os.getenv("LOCAL_MODEL_DEVICE", "cpu"),
        bge_embedding_model_path=_read_path("BGE_EMBEDDING_MODEL_PATH", DEFAULT_MODELS_DIR / "bge-small-zh-v1.5"),
        text2vec_model_path=_read_path("TEXT2VEC_MODEL_PATH", DEFAULT_MODELS_DIR / "text2vex-base-chinese"),
        bge_reranker_model_path=_read_path("BGE_RERANKER_MODEL_PATH", DEFAULT_MODELS_DIR / "bge-reranker-base"),
        enable_multimodal=_read_bool("ENABLE_MULTIMODAL", True),
        vision_model=os.getenv("VISION_MODEL") or os.getenv("DOUBAO_VISION_MODEL"),
        upload_image_dir=_read_path("UPLOAD_IMAGE_DIR", STORAGE_DIR / "uploads"),
    )


settings = get_settings()
