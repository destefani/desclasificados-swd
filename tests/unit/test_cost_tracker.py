"""Unit tests for cost_tracker module."""

import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from app.utils.cost_tracker import (
    CostTracker,
    PricingTier,
    PRICING,
    estimate_cost,
)


class TestPricingTier:
    """Tests for PricingTier dataclass."""

    def test_input_rate_calculation(self):
        """Test input rate is correctly calculated from per-million price."""
        tier = PricingTier(input_per_million=1.00, output_per_million=4.00)
        assert tier.input_rate == 1.00 / 1_000_000
        assert tier.input_rate == 0.000001

    def test_output_rate_calculation(self):
        """Test output rate is correctly calculated from per-million price."""
        tier = PricingTier(input_per_million=1.00, output_per_million=4.00)
        assert tier.output_rate == 4.00 / 1_000_000
        assert tier.output_rate == 0.000004

    def test_batch_rates_default_to_50_percent(self):
        """Test batch rates default to 50% of standard rates."""
        tier = PricingTier(input_per_million=2.00, output_per_million=8.00)
        assert tier.batch_input_rate == tier.input_rate * 0.5
        assert tier.batch_output_rate == tier.output_rate * 0.5

    def test_batch_rates_can_be_overridden(self):
        """Test batch rates can be explicitly set."""
        tier = PricingTier(
            input_per_million=2.00,
            output_per_million=8.00,
            batch_input_per_million=0.80,
            batch_output_per_million=3.20,
        )
        assert tier.batch_input_rate == 0.80 / 1_000_000
        assert tier.batch_output_rate == 3.20 / 1_000_000


class TestCostTracker:
    """Tests for CostTracker class."""

    def test_initial_state(self):
        """Test tracker starts with zero usage."""
        tracker = CostTracker()
        assert tracker.total_input_tokens == 0
        assert tracker.total_output_tokens == 0
        assert tracker.get_total_tokens() == 0

    def test_add_usage(self):
        """Test adding token usage."""
        tracker = CostTracker()
        tracker.add_usage(1000, 500)
        assert tracker.total_input_tokens == 1000
        assert tracker.total_output_tokens == 500
        assert tracker.get_total_tokens() == 1500

    def test_add_usage_cumulative(self):
        """Test multiple add_usage calls accumulate."""
        tracker = CostTracker()
        tracker.add_usage(1000, 500)
        tracker.add_usage(2000, 1000)
        assert tracker.total_input_tokens == 3000
        assert tracker.total_output_tokens == 1500

    def test_get_cost_gpt41_nano(self):
        """Test cost calculation for gpt-4.1-nano."""
        tracker = CostTracker()
        tracker.add_usage(1_000_000, 1_000_000)  # 1M tokens each

        # gpt-4.1-nano: $0.10 input, $0.40 output per million
        cost = tracker.get_cost("gpt-4.1-nano")
        expected = 0.10 + 0.40  # $0.50 total
        assert abs(cost - expected) < 0.001

    def test_get_cost_gpt41_mini(self):
        """Test cost calculation for gpt-4.1-mini."""
        tracker = CostTracker()
        tracker.add_usage(1_000_000, 1_000_000)

        # gpt-4.1-mini: $0.40 input, $1.60 output per million
        cost = tracker.get_cost("gpt-4.1-mini")
        expected = 0.40 + 1.60  # $2.00 total
        assert abs(cost - expected) < 0.001

    def test_get_cost_batch_mode(self):
        """Test batch mode applies 50% discount."""
        tracker = CostTracker()
        tracker.add_usage(1_000_000, 1_000_000)

        standard_cost = tracker.get_cost("gpt-4.1-nano", batch_mode=False)
        batch_cost = tracker.get_cost("gpt-4.1-nano", batch_mode=True)

        assert abs(batch_cost - standard_cost * 0.5) < 0.001

    def test_get_cost_unknown_model_uses_default(self):
        """Test unknown model falls back to default pricing."""
        tracker = CostTracker()
        tracker.add_usage(1_000_000, 1_000_000)

        # Should not raise, uses default pricing
        cost = tracker.get_cost("unknown-model-xyz")
        assert cost > 0

    def test_reset(self):
        """Test reset clears all counters."""
        tracker = CostTracker()
        tracker.add_usage(1000, 500)
        tracker.reset()
        assert tracker.total_input_tokens == 0
        assert tracker.total_output_tokens == 0

    def test_thread_safety(self):
        """Test concurrent add_usage calls are thread-safe."""
        tracker = CostTracker()

        def add_tokens():
            for _ in range(100):
                tracker.add_usage(10, 5)

        threads = [threading.Thread(target=add_tokens) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 10 threads * 100 iterations * (10 input + 5 output)
        assert tracker.total_input_tokens == 10 * 100 * 10
        assert tracker.total_output_tokens == 10 * 100 * 5

    def test_thread_safety_with_executor(self):
        """Test thread safety with ThreadPoolExecutor."""
        tracker = CostTracker()

        def add_tokens(n: int):
            tracker.add_usage(100, 50)
            return n

        with ThreadPoolExecutor(max_workers=10) as executor:
            list(executor.map(add_tokens, range(1000)))

        assert tracker.total_input_tokens == 1000 * 100
        assert tracker.total_output_tokens == 1000 * 50


class TestEstimateCost:
    """Tests for estimate_cost function."""

    def test_basic_estimation(self):
        """Test basic cost estimation."""
        # 100 files with default token estimates
        cost = estimate_cost(100, "gpt-4.1-nano")
        assert cost > 0

    def test_zero_files(self):
        """Test zero files returns zero cost."""
        cost = estimate_cost(0, "gpt-4.1-nano")
        assert cost == 0

    def test_custom_token_estimates(self):
        """Test custom token estimates."""
        cost = estimate_cost(
            1,
            "gpt-4.1-nano",
            avg_input_tokens=1_000_000,  # 1M input
            avg_output_tokens=1_000_000,  # 1M output
        )
        # gpt-4.1-nano: $0.10 + $0.40 = $0.50 for 1M each
        assert abs(cost - 0.50) < 0.01

    def test_batch_mode_discount(self):
        """Test batch mode applies 50% discount."""
        standard = estimate_cost(100, "gpt-4.1-nano", batch_mode=False)
        batch = estimate_cost(100, "gpt-4.1-nano", batch_mode=True)
        assert abs(batch - standard * 0.5) < 0.001

    def test_different_models(self):
        """Test different models have different costs."""
        nano_cost = estimate_cost(100, "gpt-4.1-nano")
        mini_cost = estimate_cost(100, "gpt-4.1-mini")
        gpt4o_cost = estimate_cost(100, "gpt-4o")

        # Costs should be in order: nano < mini < gpt-4o
        assert nano_cost < mini_cost < gpt4o_cost


class TestPricingConfig:
    """Tests for PRICING configuration."""

    def test_all_models_have_required_fields(self):
        """Test all configured models have required pricing fields."""
        for model, pricing in PRICING.items():
            assert hasattr(pricing, "input_per_million"), f"{model} missing input"
            assert hasattr(pricing, "output_per_million"), f"{model} missing output"
            assert pricing.input_per_million > 0, f"{model} has zero input price"
            assert pricing.output_per_million > 0, f"{model} has zero output price"

    def test_openai_models_present(self):
        """Test OpenAI models are configured."""
        openai_models = ["gpt-4.1-nano", "gpt-4.1-mini", "gpt-4o", "gpt-4o-mini"]
        for model in openai_models:
            assert model in PRICING, f"Missing OpenAI model: {model}"

    def test_claude_models_present(self):
        """Test Claude models are configured."""
        claude_models = ["claude-3-5-haiku-20241022", "claude-sonnet-4-5-20250929"]
        for model in claude_models:
            assert model in PRICING, f"Missing Claude model: {model}"
