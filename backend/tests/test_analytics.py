"""Tests for the analytics engine."""

import numpy as np
import pandas as pd
import pytest

from app.analytics.composite import (
    normalize_metric,
    calculate_financial_health,
    assign_peer_group,
)
from app.analytics.forecast import detect_trend, forecast_linear, detect_anomalies


class TestNormalization:
    def test_normalize_higher_is_better(self):
        s = pd.Series([10, 20, 30, 40, 50])
        result = normalize_metric(s, higher_is_better=True)
        assert result.iloc[0] == 0.0
        assert result.iloc[-1] == 100.0

    def test_normalize_lower_is_better(self):
        s = pd.Series([10, 20, 30, 40, 50])
        result = normalize_metric(s, higher_is_better=False)
        assert result.iloc[0] == 100.0
        assert result.iloc[-1] == 0.0

    def test_normalize_all_same(self):
        s = pd.Series([50, 50, 50])
        result = normalize_metric(s)
        assert all(result == 50.0)

    def test_normalize_with_nan(self):
        s = pd.Series([np.nan, np.nan, np.nan])
        result = normalize_metric(s)
        assert result.isna().all()


class TestPeerGroups:
    def test_city_large(self):
        assert assign_peer_group(400000) == "city_large"

    def test_city_medium(self):
        assert assign_peer_group(25000) == "city_medium"

    def test_urban(self):
        assert assign_peer_group(12000) == "urban"

    def test_suburban(self):
        assert assign_peer_group(7000) == "suburban"

    def test_rural_large(self):
        assert assign_peer_group(3000) == "rural_large"

    def test_rural_small(self):
        assert assign_peer_group(500) == "rural_small"

    def test_none(self):
        assert assign_peer_group(None) == "unknown"


class TestTrendDetection:
    def test_improving_trend(self):
        values = [10, 12, 14, 16, 18, 20, 22]
        result = detect_trend(values)
        assert result["direction"] == "improving"
        assert result["confidence"] > 90

    def test_declining_trend(self):
        values = [100, 90, 80, 70, 60, 50]
        result = detect_trend(values)
        assert result["direction"] == "declining"

    def test_stable(self):
        values = [50, 51, 49, 50, 51, 49, 50]
        result = detect_trend(values)
        assert result["direction"] == "stable"

    def test_insufficient_data(self):
        values = [10, 20]
        result = detect_trend(values)
        assert result["direction"] == "insufficient_data"


class TestForecast:
    def test_linear_forecast(self):
        years = [2018, 2019, 2020, 2021, 2022]
        values = [100, 110, 120, 130, 140]
        result = forecast_linear(years, values, forecast_years=2)
        assert len(result) == 2
        assert result[0]["year"] == 2023
        assert result[0]["predicted_value"] == pytest.approx(150, abs=1)


class TestAnomalyDetection:
    def test_detect_outlier(self):
        values = [100, 102, 98, 101, 99, 500, 100, 101]
        anomalies = detect_anomalies(values)
        assert 5 in anomalies  # The 500 spike

    def test_no_anomalies(self):
        values = [100, 101, 99, 100, 101, 99, 100]
        anomalies = detect_anomalies(values)
        assert len(anomalies) == 0
