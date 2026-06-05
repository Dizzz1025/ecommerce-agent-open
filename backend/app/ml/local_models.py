from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np


class LocalModelManager:
    """Lazy loader for local Chinese embedding and reranking models.

    The backend should still work when a model file is missing or a dependency
    is unavailable, so every public method falls back to empty scores instead
    of raising into the agent pipeline.
    """

    def __init__(
        self,
        *,
        enable: bool,
        bge_embedding_path: Path | None,
        text2vec_path: Path | None,
        reranker_path: Path | None,
        device: str = "cpu",
    ) -> None:
        self.enable = enable
        self.bge_embedding_path = bge_embedding_path
        self.text2vec_path = text2vec_path
        self.reranker_path = reranker_path
        self.device = device
        self._embedding_models: dict[str, Any] = {}
        self._reranker: Any | None = None
        self._doc_embedding_cache: dict[str, dict[str, np.ndarray]] = {
            "bge": {},
            "text2vec": {},
        }
        self._load_errors: dict[str, str] = {}

    def status(self) -> dict[str, Any]:
        return {
            "enabled": self.enable,
            "device": self.device,
            "bge_embedding": self._model_status("bge", self.bge_embedding_path),
            "text2vec": self._model_status("text2vec", self.text2vec_path),
            "bge_reranker": self._reranker_status(),
            "load_errors": self._load_errors,
        }

    def best_text2vec_label(
        self,
        query: str,
        label_examples: dict[str, list[str]],
        *,
        threshold: float = 0.48,
    ) -> tuple[str | None, float]:
        """Classify a short text by semantic similarity to label examples."""

        if not query.strip() or not label_examples:
            return None, 0.0
        labels = list(label_examples)
        documents = ["；".join(label_examples[label]) for label in labels]
        scores = self._embedding_scores(
            model_key="text2vec",
            query=query,
            documents=documents,
            query_prefix="",
        )
        if not scores:
            return None, 0.0
        best_index = max(range(len(scores)), key=lambda index: scores[index])
        best_score = float(scores[best_index])
        if best_score < threshold:
            return None, best_score
        return labels[best_index], best_score

    def semantic_scores(self, query: str, documents: list[str]) -> dict[str, list[float]]:
        """Return BGE and text2vec cosine scores for the candidate documents."""

        if not documents:
            return {}
        scores: dict[str, list[float]] = {}
        bge_scores = self._embedding_scores(
            model_key="bge",
            query=query,
            documents=documents,
            query_prefix="为这个句子生成表示以用于检索相关文章：",
        )
        if bge_scores:
            scores["bge_embedding"] = bge_scores

        text2vec_scores = self._embedding_scores(
            model_key="text2vec",
            query=query,
            documents=documents,
            query_prefix="",
        )
        if text2vec_scores:
            scores["text2vec_embedding"] = text2vec_scores
        return scores

    def rerank_scores(self, query: str, documents: list[str]) -> list[float]:
        if not self.enable or not documents:
            return []
        model = self._load_reranker()
        if model is None:
            return []
        try:
            raw_scores = model.predict(
                [[query, document] for document in documents],
                show_progress_bar=False,
            )
            values = np.asarray(raw_scores, dtype=float).reshape(-1)
            return [_sigmoid(float(value)) for value in values]
        except Exception as exc:  # pragma: no cover - hardware/model specific
            self._load_errors["bge_reranker_predict"] = str(exc)
            return []

    def _embedding_scores(
        self,
        *,
        model_key: str,
        query: str,
        documents: list[str],
        query_prefix: str,
    ) -> list[float]:
        if not self.enable:
            return []
        model = self._load_embedding_model(model_key)
        if model is None:
            return []
        try:
            cache = self._doc_embedding_cache[model_key]
            missing = [document for document in documents if document not in cache]
            if missing:
                encoded_docs = model.encode(
                    missing,
                    normalize_embeddings=True,
                    convert_to_numpy=True,
                    show_progress_bar=False,
                )
                for document, vector in zip(missing, encoded_docs, strict=False):
                    cache[document] = np.asarray(vector, dtype=float)
            query_embedding = model.encode(
                [f"{query_prefix}{query}"],
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False,
            )[0]
            query_vector = np.asarray(query_embedding, dtype=float)
            doc_matrix = np.vstack([cache[document] for document in documents])
            raw_scores = doc_matrix @ query_vector
            return [float(max(0.0, min(1.0, (score + 1.0) / 2.0))) for score in raw_scores]
        except Exception as exc:  # pragma: no cover - hardware/model specific
            self._load_errors[f"{model_key}_predict"] = str(exc)
            return []

    def _load_embedding_model(self, model_key: str) -> Any | None:
        if model_key in self._embedding_models:
            return self._embedding_models[model_key]
        path = self.bge_embedding_path if model_key == "bge" else self.text2vec_path
        if not self._valid_model_path(path):
            self._load_errors[model_key] = f"model path not found: {path}"
            return None
        try:
            from sentence_transformers import SentenceTransformer

            model = SentenceTransformer(str(path), device=self.device)
            self._embedding_models[model_key] = model
            return model
        except Exception as exc:  # pragma: no cover - dependency/model specific
            self._load_errors[model_key] = str(exc)
            return None

    def _load_reranker(self) -> Any | None:
        if self._reranker is not None:
            return self._reranker
        if not self._valid_model_path(self.reranker_path):
            self._load_errors["bge_reranker"] = f"model path not found: {self.reranker_path}"
            return None
        try:
            from sentence_transformers import CrossEncoder

            self._reranker = CrossEncoder(str(self.reranker_path), device=self.device)
            return self._reranker
        except Exception as exc:  # pragma: no cover - dependency/model specific
            self._load_errors["bge_reranker"] = str(exc)
            return None

    def _model_status(self, model_key: str, path: Path | None) -> dict[str, Any]:
        return {
            "path": str(path) if path else None,
            "path_exists": self._valid_model_path(path),
            "loaded": model_key in self._embedding_models,
        }

    def _reranker_status(self) -> dict[str, Any]:
        return {
            "path": str(self.reranker_path) if self.reranker_path else None,
            "path_exists": self._valid_model_path(self.reranker_path),
            "loaded": self._reranker is not None,
        }

    @staticmethod
    def _valid_model_path(path: Path | None) -> bool:
        return bool(path and path.exists() and path.is_dir())


def _sigmoid(value: float) -> float:
    if value >= 0:
        z = math.exp(-value)
        return 1 / (1 + z)
    z = math.exp(value)
    return z / (1 + z)

