"""Tests for win probability prediction service."""

import pandas as pd
import pytest

from lol_data_center.ml.win_probability import WinProbabilityPredictor


def test_predictor_initialization():
    """Test that predictor can be initialized without models."""
    predictor = WinProbabilityPredictor()

    assert predictor.model is None
    assert predictor.scaler is None
    assert predictor.pca is None


def test_identify_outliers():
    """Test outlier detection logic."""
    predictor = WinProbabilityPredictor()

    # Create test data
    predictions = pd.DataFrame(
        {
            "win": [True, True, False, False, True, False],
            "win_probability": [0.9, 0.2, 0.1, 0.8, 0.5, 0.5],
        }
    )

    # Identify outliers with 0.7 threshold
    outliers = predictor.identify_outliers(predictions, threshold=0.7)

    # Should identify:
    # - Row 1: win=True, prob=0.2 (unexpected win)
    # - Row 3: win=False, prob=0.8 (unexpected loss)
    assert len(outliers) == 2

    # Check outlier types
    outlier_types = set(outliers["outlier_type"])
    assert "unexpected_win" in outlier_types
    assert "unexpected_loss" in outlier_types

    # Check surprise scores are calculated
    assert "surprise_score" in outliers.columns
    assert (outliers["surprise_score"] > 0).all()


def test_identify_outliers_no_outliers():
    """Test outlier detection when no outliers exist."""
    predictor = WinProbabilityPredictor()

    # Create test data with no outliers
    predictions = pd.DataFrame(
        {
            "win": [True, True, False, False],
            "win_probability": [0.9, 0.8, 0.1, 0.2],
        }
    )

    outliers = predictor.identify_outliers(predictions, threshold=0.7)

    # Should identify no outliers
    assert len(outliers) == 0


def test_identify_outliers_invalid_input():
    """Test outlier detection with invalid input."""
    predictor = WinProbabilityPredictor()

    # Missing columns
    predictions = pd.DataFrame({"some_col": [1, 2, 3]})

    with pytest.raises(ValueError, match="must contain"):
        predictor.identify_outliers(predictions)


def test_prepare_features():
    """Test feature preparation."""
    predictor = WinProbabilityPredictor()
    predictor.feature_names = ["kills", "deaths", "assists", "damage_per_min"]

    # Create test data
    participant_data = {
        "kills": 10,
        "deaths": 5,
        "assists": 8,
        "damage_per_min": 500,
        "extra_field": 999,  # Should be ignored
    }

    df = predictor.prepare_features(participant_data)

    # Check shape
    assert df.shape == (1, 4)

    # Check values
    assert df.loc[0, "kills"] == 10
    assert df.loc[0, "deaths"] == 5

    # Extra field should not be present
    assert "extra_field" not in df.columns


def test_prepare_features_missing_fields():
    """Test feature preparation with missing fields."""
    predictor = WinProbabilityPredictor()
    predictor.feature_names = ["kills", "deaths", "assists"]

    # Missing 'assists' field
    participant_data = {"kills": 10, "deaths": 5}

    df = predictor.prepare_features(participant_data)

    # Should fill missing with 0
    assert df.loc[0, "assists"] == 0
