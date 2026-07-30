"""Interpretable multi-label text classifier for the eight CHẮN signals."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable, Sequence

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.multiclass import OneVsRestClassifier
from sklearn.pipeline import FeatureUnion

from .context_boosts import apply_context_boosts
from .constants import (
    ENGINE_VERSION,
    SIGNAL_CODES,
    SIGNAL_DECISION_THRESHOLD,
)
from .normalize import normalize_for_model
from .policy import aggregate_risk
from .protective_context import apply_protective_context

_EXPLANATIONS = {
    "mao_danh_tham_quyen": "Tin nhắn tự nhận là cơ quan hoặc tổ chức có thẩm quyền.",
    "yeu_cau_bi_mat": "Người gửi yêu cầu giữ bí mật với gia đình.",
    "ap_luc_thoi_gian": "Người gửi thúc ép phải làm ngay.",
    "tk_ca_nhan": "Tin nhắn yêu cầu chuyển tiền vào tài khoản cá nhân.",
    "cai_app_ngoai": "Tin nhắn yêu cầu cài ứng dụng ngoài cửa hàng chính thức.",
    "loi_ich_bat_thuong": "Tin nhắn hứa một khoản lợi ích bất thường.",
    "chuyen_kenh": "Người gửi muốn chuyển sang một kênh liên lạc riêng.",
    "yeu_cau_otp": "Người gửi yêu cầu cung cấp mã xác nhận.",
}

_QUESTIONS = {
    "mao_danh_tham_quyen": "Tôi có thể tự gọi số chính thức của cơ quan để kiểm tra không?",
    "yeu_cau_bi_mat": "Tại sao việc này lại không được nói với người thân?",
    "ap_luc_thoi_gian": "Tại sao tôi phải làm ngay mà không có thời gian kiểm tra?",
    "tk_ca_nhan": "Tại sao tiền lại chuyển vào tài khoản cá nhân?",
    "cai_app_ngoai": "Ứng dụng này có trên cửa hàng chính thức không?",
    "loi_ich_bat_thuong": "Tại sao tôi nhận được lợi ích này khi chưa đăng ký?",
    "chuyen_kenh": "Tại sao không trao đổi qua kênh chính thức?",
    "yeu_cau_otp": "Tại sao anh/chị cần mã xác nhận chỉ mình tôi được biết?",
}

_SIGNAL_PRIORITY = {
    "yeu_cau_otp": 8,
    "yeu_cau_bi_mat": 7,
    "cai_app_ngoai": 6,
    "tk_ca_nhan": 5,
    "mao_danh_tham_quyen": 4,
    "ap_luc_thoi_gian": 3,
    "loi_ich_bat_thuong": 2,
    "chuyen_kenh": 1,
}


@dataclass(frozen=True)
class ModelConfig:
    word_features: int = 40_000
    char_features: int = 80_000
    min_df: int = 2
    regularization_c: float = 4.0
    max_iter: int = 500
    random_state: int = 20260730
    probability_temperature: float = 0.35
    scam_prior_weight: float = 0.405
    scam_word_features: int = 60_000
    scam_regularization_c: float = 1.0


class PhishingSignalModel:
    """Predict signals; delegate the final risk decision to deterministic L4."""

    def __init__(self, config: ModelConfig | None = None) -> None:
        self.config = config or ModelConfig()
        self.vectorizer = FeatureUnion(
            [
                (
                    "word",
                    TfidfVectorizer(
                        preprocessor=normalize_for_model,
                        analyzer="word",
                        ngram_range=(1, 2),
                        min_df=self.config.min_df,
                        max_features=self.config.word_features,
                        sublinear_tf=True,
                    ),
                ),
                (
                    "char",
                    TfidfVectorizer(
                        preprocessor=normalize_for_model,
                        analyzer="char_wb",
                        ngram_range=(3, 5),
                        min_df=self.config.min_df,
                        max_features=self.config.char_features,
                        sublinear_tf=True,
                    ),
                ),
            ]
        )
        self.classifier = OneVsRestClassifier(
            LogisticRegression(
                C=self.config.regularization_c,
                class_weight="balanced",
                max_iter=self.config.max_iter,
                random_state=self.config.random_state,
                solver="liblinear",
            ),
            # A single process avoids sparse-matrix writeability issues in
            # joblib's macOS process backend and is predictable in containers.
            n_jobs=1,
        )
        self.scam_classifier = LogisticRegression(
            C=self.config.scam_regularization_c,
            class_weight="balanced",
            max_iter=self.config.max_iter,
            random_state=self.config.random_state,
            solver="liblinear",
        )
        self.scam_vectorizer = TfidfVectorizer(
            preprocessor=normalize_for_model,
            analyzer="word",
            ngram_range=(1, 3),
            min_df=self.config.min_df,
            max_features=self.config.scam_word_features,
            sublinear_tf=True,
        )
        self.metadata: dict[str, object] = {
            "engine_version": ENGINE_VERSION,
            "signal_codes": list(SIGNAL_CODES),
        }
        self._feature_names: np.ndarray | None = None
        self._is_fitted = False

    def fit(
        self,
        texts: Sequence[str],
        labels: Sequence[dict[str, float]],
        *,
        is_phishing: Sequence[bool] | None = None,
        metadata: dict[str, object] | None = None,
    ) -> "PhishingSignalModel":
        if len(texts) != len(labels) or not texts:
            raise ValueError("texts and labels must be non-empty and have equal length")
        unknown = set().union(*(set(item) for item in labels)) - set(SIGNAL_CODES)
        if unknown:
            raise ValueError(f"unknown signal codes: {sorted(unknown)}")
        y = np.asarray(
            [
                [int(float(item.get(code, 0.0)) >= 0.5) for code in SIGNAL_CODES]
                for item in labels
            ],
            dtype=np.int8,
        )
        for index, code in enumerate(SIGNAL_CODES):
            if len(np.unique(y[:, index])) < 2:
                raise ValueError(
                    f"training data needs positive and negative examples for {code}"
                )
        if is_phishing is None:
            scam_y = np.asarray([bool(item) for item in labels], dtype=np.int8)
        else:
            if len(is_phishing) != len(texts):
                raise ValueError("is_phishing must match texts")
            scam_y = np.asarray(is_phishing, dtype=np.int8)
        if len(np.unique(scam_y)) < 2:
            raise ValueError("training data needs phishing and legitimate examples")
        matrix = self.vectorizer.fit_transform(texts)
        self.classifier.fit(matrix, y)
        scam_matrix = self.scam_vectorizer.fit_transform(texts)
        self.scam_classifier.fit(scam_matrix, scam_y)
        self._feature_names = self.vectorizer.get_feature_names_out()
        if metadata:
            self.metadata.update(metadata)
        self.metadata["training_examples"] = len(texts)
        self._is_fitted = True
        return self

    def predict_probabilities(self, texts: Sequence[str]) -> np.ndarray:
        probabilities, _ = self.predict_components(texts)
        return probabilities

    def predict_scam_probabilities(self, texts: Sequence[str]) -> np.ndarray:
        _, scam_probabilities = self.predict_components(texts)
        return scam_probabilities

    def predict_components(self, texts: Sequence[str]) -> tuple[np.ndarray, np.ndarray]:
        self._check_fitted()
        segments: list[str] = []
        owners: list[int] = []
        for owner, text in enumerate(texts):
            parts = [
                sentence.strip()
                for sentence in re.split(r"(?<=[.!?…])\s+|\n+", text)
                if sentence.strip()
            ]
            candidates = [text]
            if len(parts) > 1:
                candidates.extend(parts)
            segments.extend(candidates)
            owners.extend([owner] * len(candidates))
        matrix = self.vectorizer.transform(segments)
        segment_probabilities = np.asarray(self.classifier.predict_proba(matrix))
        raw = np.zeros((len(texts), len(SIGNAL_CODES)), dtype=float)
        np.maximum.at(raw, np.asarray(owners), segment_probabilities)
        scam_matrix = self.scam_vectorizer.transform(texts)
        raw_scam = np.asarray(self.scam_classifier.predict_proba(scam_matrix))[:, 1]
        # L4 weights expect confident semantic signal strengths. Independent
        # logistic models are conservative when a held-out phrase is present,
        # so sharpen probabilities with a validation-selected temperature.
        clipped = np.clip(raw, 1e-6, 1.0 - 1e-6)
        logits = np.log(clipped / (1.0 - clipped))
        probabilities = 1.0 / (
            1.0 + np.exp(-logits / self.config.probability_temperature)
        )
        for index, text in enumerate(texts):
            probabilities[index], raw_scam[index] = apply_context_boosts(
                text,
                probabilities[index],
                float(raw_scam[index]),
            )
            probabilities[index], raw_scam[index] = apply_protective_context(
                text,
                probabilities[index],
                float(raw_scam[index]),
            )
        return probabilities, raw_scam

    def predict_many(
        self,
        texts: Sequence[str],
        *,
        similarity_scores: Sequence[float] | None = None,
        similarity_beta: float = 0.0,
        blocklist_matches: Sequence[bool] | None = None,
    ) -> list[dict[str, object]]:
        self._check_fitted()
        probabilities, scam_probabilities = self.predict_components(texts)
        if similarity_scores is None:
            similarity_scores = [0.0] * len(texts)
        if len(similarity_scores) != len(texts):
            raise ValueError("similarity_scores must match texts")
        if blocklist_matches is None:
            blocklist_matches = [False] * len(texts)
        if len(blocklist_matches) != len(texts):
            raise ValueError("blocklist_matches must match texts")
        return [
            self._format_prediction(
                text,
                probabilities[index],
                scam_probability=float(scam_probabilities[index]),
                similarity_max=float(similarity_scores[index]),
                similarity_beta=similarity_beta,
                blocklist_match=bool(blocklist_matches[index]),
            )
            for index, text in enumerate(texts)
        ]

    def predict(
        self,
        text: str,
        *,
        similarity_max: float = 0.0,
        similarity_beta: float = 0.0,
        blocklist_match: bool = False,
    ) -> dict[str, object]:
        """Score one text. ``blocklist_match`` is the §6 hard override for a
        recipient account already reported to the Lookup Service."""
        return self.predict_many(
            [text],
            similarity_scores=[similarity_max],
            similarity_beta=similarity_beta,
            blocklist_matches=[blocklist_match],
        )[0]

    def _format_prediction(
        self,
        text: str,
        probabilities: np.ndarray,
        *,
        scam_probability: float,
        similarity_max: float,
        similarity_beta: float,
        blocklist_match: bool = False,
    ) -> dict[str, object]:
        confidence_map = {
            code: float(probabilities[index]) for index, code in enumerate(SIGNAL_CODES)
        }
        policy = aggregate_risk(
            confidence_map,
            scam_probability=scam_probability,
            scam_beta=self.config.scam_prior_weight,
            similarity_max=similarity_max,
            similarity_beta=similarity_beta,
            blocklist_match=blocklist_match,
        )
        selected = [
            {
                "code": code,
                "confidence": round(confidence_map[code], 4),
                "evidence": self._evidence(text, code),
            }
            for code in SIGNAL_CODES
            if confidence_map[code] >= SIGNAL_DECISION_THRESHOLD
        ]
        selected.sort(
            key=lambda item: (
                _SIGNAL_PRIORITY[str(item["code"])],
                float(str(item["confidence"])),
            ),
            reverse=True,
        )
        if policy.risk == "unknown":
            explanation = "Chưa phát hiện dấu hiệu."
            selected = []
        else:
            explanation_items = (
                selected[:1]
                if selected and selected[0]["code"] == "yeu_cau_otp"
                else selected[:3]
            )
            sentences = [_EXPLANATIONS[str(item["code"])] for item in explanation_items]
            explanation = " ".join(sentences) or "Cần kiểm tra thêm trước khi làm theo."
        question_items = (
            selected[:1]
            if selected and selected[0]["code"] == "yeu_cau_otp"
            else selected[:2]
        )
        questions = [_QUESTIONS[str(item["code"])] for item in question_items]
        return {
            "risk": policy.risk,
            "score": policy.score,
            "scam_confidence": round(scam_probability, 4),
            "signals": selected,
            "explanation": explanation,
            "questions": questions,
            "engine_version": str(self.metadata.get("engine_version", ENGINE_VERSION)),
        }

    def _evidence(self, text: str, signal_code: str) -> str:
        """Return a model-supported word span, not a regex/rule match."""
        matrix = self.vectorizer.transform([text])
        names = self._feature_names
        if names is None:
            names = self.vectorizer.get_feature_names_out()
            self._feature_names = names
        signal_index = SIGNAL_CODES.index(signal_code)
        coefficients_by_signal = np.vstack(
            [estimator.coef_[0] for estimator in self.classifier.estimators_]
        )
        coefficients = coefficients_by_signal[signal_index]
        other_coefficients = np.delete(coefficients_by_signal, signal_index, axis=0)
        candidates: list[tuple[float, str]] = []
        for feature_index in matrix.indices:
            name = str(names[feature_index])
            if not name.startswith("word__"):
                continue
            feature = name.removeprefix("word__")
            contribution = float(coefficients[feature_index] * matrix[0, feature_index])
            competing = float(
                np.max(other_coefficients[:, feature_index]) * matrix[0, feature_index]
            )
            specificity = contribution - competing
            if contribution > 0:
                candidates.append((specificity, feature))
        if not candidates:
            return ""
        candidates.sort(reverse=True)
        normalized = normalize_for_model(text)
        for _, phrase in candidates:
            if " " in phrase and phrase in normalized:
                return self._source_sentence(text, phrase)
        return self._source_sentence(text, candidates[0][1])

    @staticmethod
    def _source_sentence(text: str, feature: str) -> str:
        """Return source text around an attribution; never invent a phrase."""
        sentences = [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?…])\s+|\n+", text)
            if sentence.strip()
        ]
        for sentence in sentences:
            if feature in normalize_for_model(sentence):
                return sentence[:240]
        return text.strip()[:240]

    def _check_fitted(self) -> None:
        if not self._is_fitted:
            raise RuntimeError("model is not fitted")

    def __getstate__(self) -> dict[str, object]:
        return self.__dict__

    def __setstate__(self, state: dict[str, object]) -> None:
        self.__dict__.update(state)
