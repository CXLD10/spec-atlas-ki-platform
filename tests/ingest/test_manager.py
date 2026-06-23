"""Tests for ingest job manager and ETA calculation."""

from datetime import datetime, timedelta

import pytest

from spec_atlas.ingest.manager import calculate_eta, format_eta_display


class TestCalculateETA:
    """Test ETA calculation logic."""

    def test_eta_at_zero_progress(self):
        """At 0-10% progress, return default estimate."""
        result = calculate_eta(current_progress_pct=5)
        assert result["eta_seconds"] > 0
        assert isinstance(result["show_warning"], bool)
        assert result["warning_message"] is None or isinstance(result["warning_message"], str)

    def test_eta_at_completion(self):
        """At 100% progress, ETA should be 0."""
        result = calculate_eta(current_progress_pct=100)
        assert result["eta_seconds"] == 0
        assert result["show_warning"] is False
        assert result["warning_message"] is None

    def test_eta_with_phase_durations(self):
        """With actual phase durations, calculate time remaining."""
        # Simulate 30 seconds elapsed in 50% of work
        phase_durations = {
            "resolve": 10,
            "inventory": 20,
        }
        result = calculate_eta(
            current_progress_pct=50,
            phase_durations=phase_durations,
        )
        # If 50% done in 30 seconds, we estimate 60 seconds total
        # So ~30 seconds remaining
        assert result["eta_seconds"] > 0
        assert result["eta_seconds"] <= 60  # Sanity check

    def test_eta_with_long_job_shows_warning(self):
        """Jobs taking >120 seconds total should show a warning."""
        # Simulate a slow job
        phase_durations = {
            "resolve": 50,
            "inventory": 40,
        }
        result = calculate_eta(
            current_progress_pct=30,
            phase_durations=phase_durations,
        )
        # 90 seconds for 30% = 300 seconds total
        if result["eta_seconds"] > 0:
            # If we estimated a long job
            estimated_total = (90 / 0.30)
            if estimated_total > 120:
                assert result["show_warning"] is True
                assert result["warning_message"] is not None

    def test_eta_handles_none_durations(self):
        """ETA calculation handles None phase_durations gracefully."""
        result = calculate_eta(
            current_progress_pct=50,
            phase_durations=None,
        )
        assert result["eta_seconds"] >= 0
        assert isinstance(result["show_warning"], bool)

    def test_eta_handles_zero_progress(self):
        """ETA calculation handles 0% progress."""
        result = calculate_eta(current_progress_pct=0)
        assert result["eta_seconds"] > 0

    def test_eta_with_partial_phase_progress(self):
        """ETA calculation accounts for progress within current phase."""
        result = calculate_eta(
            current_progress_pct=42,  # Midway through inventory phase
            phase_durations={"resolve": 30},
        )
        assert result["eta_seconds"] >= 0


class TestFormatETADisplay:
    """Test ETA display formatting."""

    def test_format_zero_seconds(self):
        """Zero seconds formats as 'Almost done!'"""
        assert format_eta_display(0) == "Almost done!"

    def test_format_negative_seconds(self):
        """Negative seconds format as 'Almost done!'"""
        assert format_eta_display(-10) == "Almost done!"

    def test_format_only_seconds(self):
        """Less than a minute formats as 'X sec remaining'"""
        assert format_eta_display(45) == "45 sec remaining"

    def test_format_only_minutes(self):
        """Exact minutes format as 'X min remaining'"""
        assert format_eta_display(120) == "2 min remaining"

    def test_format_minutes_and_seconds(self):
        """Minutes + seconds format as 'X min Y sec remaining'"""
        assert format_eta_display(165) == "2 min 45 sec remaining"

    def test_format_one_minute(self):
        """One minute formats correctly."""
        assert format_eta_display(60) == "1 min remaining"

    def test_format_one_minute_and_one_second(self):
        """One minute + one second formats correctly."""
        assert format_eta_display(61) == "1 min 1 sec remaining"

    def test_format_none(self):
        """None formats as 'Almost done!'"""
        assert format_eta_display(None) == "Almost done!"


class TestETAIntegration:
    """Integration tests for ETA calculation with realistic data."""

    def test_small_repo_eta(self):
        """Small repo should estimate quickly."""
        # Simulate a 10-second repo indexing 25% done
        phase_durations = {
            "resolve": 2,
            "inventory": 3,
        }
        result = calculate_eta(
            current_progress_pct=25,
            phase_durations=phase_durations,
        )
        # 5 seconds for 25% = 20 seconds total, so ~15 seconds remaining
        assert result["eta_seconds"] <= 30

    def test_medium_repo_eta(self):
        """Medium repo should estimate longer."""
        # Simulate a 60-second repo 50% done
        phase_durations = {
            "resolve": 15,
            "inventory": 20,
        }
        result = calculate_eta(
            current_progress_pct=50,
            phase_durations=phase_durations,
        )
        # 35 seconds for 50% = 70 seconds total, so ~35 seconds remaining
        assert result["eta_seconds"] <= 100

    def test_large_repo_warning(self):
        """Large repo (>120 sec total) should show warning."""
        # Simulate a 200-second repo 40% done
        phase_durations = {
            "resolve": 50,
            "inventory": 30,
        }
        result = calculate_eta(
            current_progress_pct=40,
            phase_durations=phase_durations,
        )
        # 80 seconds for 40% = 200 seconds total
        if result["eta_seconds"] > 0:
            assert result["show_warning"] is True
