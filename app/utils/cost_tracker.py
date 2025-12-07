"""
Thread-safe cost tracker for API usage.

Provides real-time cost tracking for OpenAI and Anthropic API calls
with support for multiple pricing models.
"""

import threading
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PricingTier:
    """Pricing configuration for a model."""

    input_per_million: float
    output_per_million: float
    batch_input_per_million: Optional[float] = None
    batch_output_per_million: Optional[float] = None

    @property
    def input_rate(self) -> float:
        """Cost per input token."""
        return self.input_per_million / 1_000_000

    @property
    def output_rate(self) -> float:
        """Cost per output token."""
        return self.output_per_million / 1_000_000

    @property
    def batch_input_rate(self) -> float:
        """Cost per input token in batch mode (50% discount if not specified)."""
        if self.batch_input_per_million is not None:
            return self.batch_input_per_million / 1_000_000
        return self.input_rate * 0.5

    @property
    def batch_output_rate(self) -> float:
        """Cost per output token in batch mode (50% discount if not specified)."""
        if self.batch_output_per_million is not None:
            return self.batch_output_per_million / 1_000_000
        return self.output_rate * 0.5


# Pricing configurations for supported models
PRICING = {
    # OpenAI GPT-4.1 family
    "gpt-4.1-nano": PricingTier(0.10, 0.40),
    "gpt-4.1-mini": PricingTier(0.40, 1.60),
    "gpt-4.1": PricingTier(2.00, 8.00),
    # OpenAI GPT-4o family
    "gpt-4o": PricingTier(2.50, 10.00),
    "gpt-4o-mini": PricingTier(0.15, 0.60),
    "gpt-4o-2024-11-20": PricingTier(2.50, 10.00),
    # Claude models
    "claude-sonnet-4-5-20250929": PricingTier(3.00, 15.00, 1.50, 7.50),
    "claude-sonnet-4-5": PricingTier(3.00, 15.00, 1.50, 7.50),
    "claude-3-5-haiku-20241022": PricingTier(0.80, 4.00, 0.40, 2.00),
    "claude-3-5-sonnet-20241022": PricingTier(3.00, 15.00, 1.50, 7.50),
    "claude-3-haiku-20240307": PricingTier(0.25, 1.25, 0.125, 0.625),
}

# Default pricing tier for unknown models
DEFAULT_PRICING = PricingTier(1.00, 4.00)


@dataclass
class CostTracker:
    """
    Thread-safe cost tracker for API usage.

    Tracks input and output tokens, calculates costs based on model pricing,
    and provides summary reporting.

    Example:
        tracker = CostTracker()
        tracker.add_usage(1000, 500)  # 1000 input, 500 output tokens
        print(f"Cost so far: ${tracker.get_cost('gpt-4.1-nano'):.4f}")
    """

    total_input_tokens: int = field(default=0, init=False)
    total_output_tokens: int = field(default=0, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)

    def add_usage(self, input_tokens: int, output_tokens: int) -> None:
        """
        Track token usage from an API call.

        Args:
            input_tokens: Number of input/prompt tokens used
            output_tokens: Number of output/completion tokens used
        """
        with self._lock:
            self.total_input_tokens += input_tokens
            self.total_output_tokens += output_tokens

    def get_cost(
        self,
        model: str,
        batch_mode: bool = False,
    ) -> float:
        """
        Calculate total cost based on model pricing.

        Args:
            model: Model name to use for pricing lookup
            batch_mode: If True, use batch API pricing (50% discount)

        Returns:
            Total cost in USD
        """
        pricing = PRICING.get(model, DEFAULT_PRICING)

        if batch_mode:
            input_rate = pricing.batch_input_rate
            output_rate = pricing.batch_output_rate
        else:
            input_rate = pricing.input_rate
            output_rate = pricing.output_rate

        with self._lock:
            return (
                self.total_input_tokens * input_rate
                + self.total_output_tokens * output_rate
            )

    def get_total_tokens(self) -> int:
        """Get total tokens used (input + output)."""
        with self._lock:
            return self.total_input_tokens + self.total_output_tokens

    def reset(self) -> None:
        """Reset all counters to zero."""
        with self._lock:
            self.total_input_tokens = 0
            self.total_output_tokens = 0

    def print_summary(
        self,
        model: str,
        batch_mode: bool = False,
    ) -> None:
        """
        Print a formatted cost summary.

        Args:
            model: Model name for pricing calculation
            batch_mode: If True, show batch API pricing
        """
        mode_str = "BATCH (50% off)" if batch_mode else "STANDARD"

        with self._lock:
            total = self.total_input_tokens + self.total_output_tokens
            cost = self.get_cost(model, batch_mode)

        print("\n" + "-" * 70)
        print("TOKEN USAGE & COST")
        print("-" * 70)
        print(f"Model:          {model}")
        print(f"Mode:           {mode_str}")
        print(f"Input tokens:   {self.total_input_tokens:,}")
        print(f"Output tokens:  {self.total_output_tokens:,}")
        print(f"Total tokens:   {total:,}")
        print(f"Estimated cost: ${cost:.4f}")
        print("-" * 70)


def estimate_cost(
    num_files: int,
    model: str,
    avg_input_tokens: int = 5600,
    avg_output_tokens: int = 2000,
    batch_mode: bool = False,
) -> float:
    """
    Estimate cost for processing a batch of files.

    Args:
        num_files: Number of files to process
        model: Model name for pricing lookup
        avg_input_tokens: Average input tokens per document (default ~3.5 pages)
        avg_output_tokens: Average output tokens per document
        batch_mode: If True, use batch API pricing

    Returns:
        Estimated cost in USD
    """
    pricing = PRICING.get(model, DEFAULT_PRICING)

    if batch_mode:
        input_rate = pricing.batch_input_rate
        output_rate = pricing.batch_output_rate
    else:
        input_rate = pricing.input_rate
        output_rate = pricing.output_rate

    per_doc = avg_input_tokens * input_rate + avg_output_tokens * output_rate
    return num_files * per_doc
