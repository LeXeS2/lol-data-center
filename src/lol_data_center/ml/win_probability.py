"""Win probability prediction service using trained ML models."""

import pickle
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from lol_data_center.database.models import MatchParticipant
from lol_data_center.logging_config import get_logger

logger = get_logger(__name__)


class WinProbabilityPredictor:
    """Predict win probability for a given match participant."""

    def __init__(
        self,
        model_path: Path | None = None,
        scaler_path: Path | None = None,
        pca_path: Path | None = None,
    ) -> None:
        """Initialize the predictor.

        Args:
            model_path: Path to the trained model file
            scaler_path: Path to the fitted scaler
            pca_path: Path to the fitted PCA transformer
        """
        self.model_path = model_path
        self.scaler_path = scaler_path
        self.pca_path = pca_path

        self.model: RandomForestClassifier | LogisticRegression | None = None
        self.scaler: StandardScaler | None = None
        self.pca: PCA | None = None
        self.feature_names: list[str] = []

        if model_path and model_path.exists():
            self.load_model()

    def load_model(self) -> None:
        """Load trained model, scaler, and PCA from files."""
        if self.model_path and self.model_path.exists():
            logger.info("Loading model", path=str(self.model_path))
            with open(self.model_path, "rb") as f:
                model_data = pickle.load(f)
                self.model = model_data["model"]
                self.feature_names = model_data.get("feature_names", [])

        if self.scaler_path and self.scaler_path.exists():
            logger.info("Loading scaler", path=str(self.scaler_path))
            with open(self.scaler_path, "rb") as f:
                self.scaler = pickle.load(f)

        if self.pca_path and self.pca_path.exists():
            logger.info("Loading PCA", path=str(self.pca_path))
            with open(self.pca_path, "rb") as f:
                self.pca = pickle.load(f)

        logger.info("Model loaded successfully")

    def save_model(self) -> None:
        """Save trained model, scaler, and PCA to files."""
        if self.model_path and self.model:
            logger.info("Saving model", path=str(self.model_path))
            self.model_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.model_path, "wb") as f:
                pickle.dump({"model": self.model, "feature_names": self.feature_names}, f)

        if self.scaler_path and self.scaler:
            logger.info("Saving scaler", path=str(self.scaler_path))
            self.scaler_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.scaler_path, "wb") as f:
                pickle.dump(self.scaler, f)

        if self.pca_path and self.pca:
            logger.info("Saving PCA", path=str(self.pca_path))
            self.pca_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.pca_path, "wb") as f:
                pickle.dump(self.pca, f)

        logger.info("Model saved successfully")

    def prepare_features(self, participant_data: dict[str, Any]) -> pd.DataFrame:
        """Prepare features from participant data.

        Args:
            participant_data: Dictionary of participant features

        Returns:
            DataFrame with features ready for prediction
        """
        # Use the same feature extraction logic as training
        df = pd.DataFrame([participant_data])

        # Ensure all expected features are present
        for feature in self.feature_names:
            if feature not in df.columns:
                df[feature] = 0

        # Select only the features used in training
        df = df[self.feature_names]

        return df

    def predict_win_probability(
        self,
        participant_data: dict[str, Any],
        role: str | None = None,
        champion: str | None = None,
    ) -> dict[str, Any]:
        """Predict win probability for a participant.

        Args:
            participant_data: Dictionary of participant features
            role: Optional role for role-specific prediction
            champion: Optional champion for champion-specific prediction

        Returns:
            Dictionary with prediction results
        """
        if not self.model:
            raise ValueError("Model not loaded. Call load_model() first.")

        # Prepare features
        features_df = self.prepare_features(participant_data)

        # Scale features
        features_scaled = self.scaler.transform(features_df) if self.scaler else features_df.values

        # Apply PCA if available
        features_transformed = self.pca.transform(features_scaled) if self.pca else features_scaled

        # Predict
        win_probability = self.model.predict_proba(features_transformed)[0][1]
        prediction = self.model.predict(features_transformed)[0]

        result = {
            "win_probability": float(win_probability),
            "predicted_win": bool(prediction),
            "role": role,
            "champion": champion,
        }

        logger.debug(
            "Prediction made",
            probability=win_probability,
            prediction=prediction,
            role=role,
            champion=champion,
        )

        return result

    def identify_outliers(
        self,
        predictions: pd.DataFrame,
        threshold: float = 0.3,
    ) -> pd.DataFrame:
        """Identify matches where prediction significantly differs from reality.

        An outlier is defined as a match where:
        - Player won but had low win probability (unexpected win)
        - Player lost but had high win probability (unexpected loss)

        Args:
            predictions: DataFrame with columns 'win', 'win_probability'
            threshold: Probability threshold for outlier detection

        Returns:
            DataFrame containing only outlier matches
        """
        if "win" not in predictions.columns or "win_probability" not in predictions.columns:
            raise ValueError("predictions must contain 'win' and 'win_probability' columns")

        # Unexpected wins: won but predicted to lose (low probability)
        unexpected_wins = (predictions["win"] == True) & (  # noqa: E712
            predictions["win_probability"] < (1 - threshold)
        )

        # Unexpected losses: lost but predicted to win (high probability)
        unexpected_losses = (predictions["win"] == False) & (  # noqa: E712
            predictions["win_probability"] > threshold
        )

        outliers = predictions[unexpected_wins | unexpected_losses].copy()

        # Add outlier type
        outliers["outlier_type"] = np.where(
            outliers["win"],
            "unexpected_win",
            "unexpected_loss",
        )

        # Add surprise score (how far from expected)
        outliers["surprise_score"] = np.where(
            outliers["win"],
            1 - outliers["win_probability"],  # For wins, lower probability = higher surprise
            outliers["win_probability"],  # For losses, higher probability = higher surprise
        )

        # Sort by surprise score
        outliers = outliers.sort_values("surprise_score", ascending=False)

        logger.info(
            "Identified outliers",
            total=len(outliers),
            unexpected_wins=unexpected_wins.sum(),
            unexpected_losses=unexpected_losses.sum(),
        )

        return outliers


def extract_participant_features_for_prediction(
    participant: MatchParticipant, game_duration: int
) -> dict[str, Any]:
    """Extract features from a MatchParticipant for prediction.

    Args:
        participant: MatchParticipant instance
        game_duration: Game duration in seconds

    Returns:
        Dictionary of features
    """
    game_duration_minutes = game_duration / 60.0

    features: dict[str, Any] = {
        # KDA features
        "kills": participant.kills,
        "deaths": participant.deaths,
        "assists": participant.assists,
        "kda": participant.kda,
        # Combat features (per minute)
        "damage_per_min": participant.total_damage_dealt_to_champions / game_duration_minutes,
        "damage_taken_per_min": participant.total_damage_taken / game_duration_minutes,
        "damage_mitigated_per_min": participant.damage_self_mitigated / game_duration_minutes,
        # Economy (per minute)
        "gold_per_min": participant.gold_earned / game_duration_minutes,
        "cs_per_min": (participant.total_minions_killed + participant.neutral_minions_killed)
        / game_duration_minutes,
        # Vision
        "vision_score": participant.vision_score,
        "vision_score_per_min": participant.vision_score / game_duration_minutes,
        "wards_placed": participant.wards_placed,
        "wards_killed": participant.wards_killed,
        # Objectives
        "turret_takedowns": participant.turret_takedowns,
        "inhibitor_takedowns": participant.inhibitor_takedowns,
        "baron_kills": participant.baron_kills,
        "dragon_kills": participant.dragon_kills,
        # Utility
        "heal_per_min": participant.total_heal / game_duration_minutes,
        "heals_on_teammates_per_min": participant.total_heals_on_teammates / game_duration_minutes,
        "shield_on_teammates_per_min": participant.total_damage_shielded_on_teammates
        / game_duration_minutes,
        "cc_time_dealt": participant.total_time_cc_dealt,
        # Multi-kills
        "double_kills": participant.double_kills,
        "triple_kills": participant.triple_kills,
        "quadra_kills": participant.quadra_kills,
        "penta_kills": participant.penta_kills,
        # Early game indicators
        "first_blood_kill": participant.first_blood_kill,
        "first_tower_kill": participant.first_tower_kill,
        # Game context
        "game_duration_minutes": game_duration_minutes,
        "champion_level": participant.champion_level,
    }

    return features
