"""Adaptive confidence estimation and feedback handling for BOM extraction."""
from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence

from typing import Protocol


DEFAULT_STORAGE_ENV = "BOM_EXTRACTOR_LEARNING_PATH"
DEFAULT_STORAGE_FILENAME = "learning_state.json"
BIAS_PRIOR_POSITIVE = 5.0
BIAS_PRIOR_NEGATIVE = 3.0
FEATURE_PRIOR_DEFAULT = (1.0, 1.0)
MAX_SUMMARY_FEATURES = 6


class SupportsFeatures(Protocol):
    """Protocol describing the subset of :class:`BOMItem` we use."""

    extras: MutableMapping[str, str]

    def __getattr__(self, name: str) -> object:  # pragma: no cover - protocol helper
        ...


@dataclass
class LearningState:
    """Serializable container with accumulated feedback statistics."""

    feature_stats: Dict[str, Dict[str, float]] = field(default_factory=dict)
    total_positive: float = 0.0
    total_negative: float = 0.0
    version: int = 1

    def to_dict(self) -> Dict[str, object]:
        return {
            "feature_stats": self.feature_stats,
            "total_positive": self.total_positive,
            "total_negative": self.total_negative,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "LearningState":
        feature_stats = {
            str(name): {
                "positive": float(values.get("positive", 0.0)),
                "negative": float(values.get("negative", 0.0)),
            }
            for name, values in (data.get("feature_stats") or {}).items()
        }
        return cls(
            feature_stats=feature_stats,
            total_positive=float(data.get("total_positive", 0.0)),
            total_negative=float(data.get("total_negative", 0.0)),
            version=int(data.get("version", 1)),
        )


_FEATURE_PRIORS: Dict[str, tuple[float, float]] = {
    "source::table": (6.0, 1.0),
    "source::text": (3.5, 2.0),
    "source::geometry": (2.5, 3.0),
    "source::fallback": (1.0, 4.0),
    "mode::table": (5.0, 1.5),
    "mode::interpreted": (2.5, 3.0),
    "heuristic::hoch": (5.5, 1.0),
    "heuristic::mittel": (3.0, 2.0),
    "heuristic::niedrig": (1.2, 3.5),
    "fields::1": (1.0, 2.5),
    "fields::2": (1.5, 2.0),
    "fields::3": (2.5, 1.5),
    "fields::4": (3.0, 1.2),
    "fields::5+": (3.5, 1.0),
    "has_quantity": (3.5, 1.0),
    "has_part_number": (3.0, 1.2),
    "has_material": (2.6, 1.4),
}


_FEATURE_LABELS: Dict[str, Dict[str, str]] = {
    "source": {
        "table": "Tabellenextraktion",
        "text": "Textinterpretation",
        "geometry": "Geometrie-Analyse",
        "fallback": "Fallback-Sammlung",
    },
    "mode": {
        "table": "Dokument enthielt Tabelle",
        "interpreted": "KI-Interpretation der Zeichnung",
    },
    "heuristic": {
        "hoch": "Heuristische Bewertung: hoch",
        "mittel": "Heuristische Bewertung: mittel",
        "niedrig": "Heuristische Bewertung: niedrig",
    },
    "fields": {
        "1": "1 Feld erkannt",
        "2": "2 Felder erkannt",
        "3": "3 Felder erkannt",
        "4": "4 Felder erkannt",
        "5+": "≥5 Felder erkannt",
    },
    "component": {
        "rohr": "Komponente: Rohr",
        "rohrbogen": "Komponente: Rohrbogen",
        "rohrende": "Komponente: Rohrende",
        "blech": "Komponente: Blech",
        "flansch": "Komponente: Flansch",
    },
}


class LearningEngine:
    """Small online learner that adapts confidence scores via user feedback."""

    def __init__(self, storage_path: Optional[Path] = None) -> None:
        self._storage_path = storage_path or self._default_storage_path()
        self._lock = Lock()
        self._state = self._load_state()

    # ------------------------------------------------------------------
    # public API
    def annotate_result(self, result: "BOMExtractionResult") -> "BOMExtractionResult":
        """Attach confidence scores and learning metadata to an extraction result."""

        context: Dict[str, str] = {}
        if result.metadata:
            mode = result.metadata.get("mode")
            if isinstance(mode, str):
                context["mode"] = mode

        for item in result.items:
            features = self._item_features(item, context)
            confidence = self._score_from_features(features)
            item.confidence = round(confidence, 4)
            source = item.extras.get("source")
            if not source and context.get("mode"):
                item.extras["source"] = context["mode"]
            item.extras.setdefault("confidence_estimate", f"{confidence * 100:.1f} %")

        summary = self.summary()
        if summary:
            result.metadata = dict(result.metadata)
            result.metadata["learning_feedback"] = summary.get("total_feedback", 0)
            result.metadata["learning_success_rate"] = round(
                float(summary.get("success_rate", 0.0)) * 100.0, 1
            )

        return result

    def record_feedback(
        self,
        ratings: Sequence[tuple[SupportsFeatures, bool]],
        metadata: Optional[Mapping[str, object]] = None,
    ) -> Dict[str, object]:
        """Update the learner with user-labelled ratings."""

        if not ratings:
            return self.summary()

        context: Dict[str, str] = {}
        if metadata and isinstance(metadata, Mapping):
            mode = metadata.get("mode")
            if isinstance(mode, str):
                context["mode"] = mode

        with self._lock:
            for item, correct in ratings:
                features = self._item_features(item, context)
                self._update_stats(features, correct)
            self._save_state()
        return self.summary()

    def summary(self) -> Dict[str, object]:
        """Return an aggregate summary of the learnt state."""

        total = self._state.total_positive + self._state.total_negative
        if total <= 0:
            return {
                "total_feedback": 0,
                "success_rate": 0.0,
                "top_features": [],
            }

        success_rate = self._state.total_positive / total

        features: List[Dict[str, object]] = []
        for name, stats in self._state.feature_stats.items():
            support = stats.get("positive", 0.0) + stats.get("negative", 0.0)
            if support <= 0:
                continue
            label = self._describe_feature(name)
            feature_success = stats.get("positive", 0.0) / support
            features.append(
                {
                    "feature": name,
                    "label": label,
                    "support": int(round(support)),
                    "success_rate": feature_success,
                }
            )

        features.sort(key=lambda entry: (entry["support"], entry["success_rate"]), reverse=True)
        return {
            "total_feedback": int(round(total)),
            "success_rate": success_rate,
            "top_features": features[:MAX_SUMMARY_FEATURES],
        }

    # ------------------------------------------------------------------
    # internal helpers
    def _default_storage_path(self) -> Path:
        env_path = os.environ.get(DEFAULT_STORAGE_ENV)
        if env_path:
            path = Path(env_path)
        else:
            path = Path(__file__).resolve().parent / DEFAULT_STORAGE_FILENAME
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _load_state(self) -> LearningState:
        if self._storage_path.exists():
            try:
                with self._storage_path.open("r", encoding="utf-8") as handle:
                    data = json.load(handle)
                return LearningState.from_dict(data)
            except (OSError, ValueError, TypeError):  # pragma: no cover - defensive
                pass
        return LearningState()

    def _save_state(self) -> None:
        try:
            with self._storage_path.open("w", encoding="utf-8") as handle:
                json.dump(self._state.to_dict(), handle, ensure_ascii=False, indent=2)
        except OSError:  # pragma: no cover - defensive
            pass

    def _item_features(self, item: SupportsFeatures, context: Mapping[str, str]) -> List[str]:
        features: List[str] = []
        extras = getattr(item, "extras", {}) or {}
        source = extras.get("source")
        if isinstance(source, str):
            features.append(f"source::{source.lower()}")
        mode = context.get("mode")
        if mode:
            features.append(f"mode::{mode.lower()}")

        confidence_label = extras.get("confidence")
        if isinstance(confidence_label, str) and confidence_label:
            features.append(f"heuristic::{confidence_label.strip().lower()}")

        component_code = extras.get("component_code")
        if isinstance(component_code, str) and component_code:
            features.append(f"component::{component_code.lower()}")

        field_names = ("position", "part_number", "description", "quantity", "unit", "material", "comment")
        field_count = 0
        for name in field_names:
            value = getattr(item, name, None)
            if value is not None and value != "":
                field_count += 1
        if field_count >= 5:
            features.append("fields::5+")
        else:
            features.append(f"fields::{field_count}")

        if getattr(item, "quantity", None) is not None:
            features.append("has_quantity")
        if getattr(item, "part_number", None):
            features.append("has_part_number")
        if getattr(item, "material", None):
            features.append("has_material")

        return features

    def _score_from_features(self, features: Iterable[str]) -> float:
        logit = math.log(
            (self._state.total_positive + BIAS_PRIOR_POSITIVE)
            / (self._state.total_negative + BIAS_PRIOR_NEGATIVE)
        )
        for name in features:
            stats = self._state.feature_stats.get(name)
            positive = stats.get("positive", 0.0) if stats else 0.0
            negative = stats.get("negative", 0.0) if stats else 0.0
            prior_pos, prior_neg = _FEATURE_PRIORS.get(name, FEATURE_PRIOR_DEFAULT)
            logit += math.log((positive + prior_pos) / (negative + prior_neg))
        return 1.0 / (1.0 + math.exp(-logit))

    def _update_stats(self, features: Iterable[str], correct: bool) -> None:
        if correct:
            self._state.total_positive += 1.0
        else:
            self._state.total_negative += 1.0
        for name in features:
            stats = self._state.feature_stats.setdefault(name, {"positive": 0.0, "negative": 0.0})
            key = "positive" if correct else "negative"
            stats[key] += 1.0

    def _describe_feature(self, name: str) -> str:
        if "::" not in name:
            return name
        prefix, value = name.split("::", 1)
        value = value.strip()
        if prefix in _FEATURE_LABELS:
            return _FEATURE_LABELS[prefix].get(value, f"{prefix}: {value}")
        if prefix == "has_quantity":
            return "Menge erkannt"
        if prefix == "has_part_number":
            return "Artikelnummer erkannt"
        if prefix == "has_material":
            return "Materialangabe vorhanden"
        return f"{prefix}: {value}"


_DEFAULT_ENGINE: Optional[LearningEngine] = None


def get_learning_engine() -> LearningEngine:
    """Return a process-wide singleton :class:`LearningEngine`."""

    global _DEFAULT_ENGINE
    if _DEFAULT_ENGINE is None:
        _DEFAULT_ENGINE = LearningEngine()
    return _DEFAULT_ENGINE


def apply_learning_to_result(result: "BOMExtractionResult") -> "BOMExtractionResult":
    """Convenience wrapper to attach learning metadata using the default engine."""

    engine = get_learning_engine()
    return engine.annotate_result(result)


__all__ = [
    "LearningEngine",
    "apply_learning_to_result",
    "get_learning_engine",
]
