"""Compatibility module for validation APIs.

New code should import from:
- `openmc_fusion_benchmarks.validate_spec`
- `openmc_fusion_benchmarks.validate_results`
"""

from .validate_spec import validate_benchmark
from .validate_results import validate_tally_consistency, normalize_filter_type

__all__ = [
    "validate_benchmark",
    "validate_tally_consistency",
    "normalize_filter_type",
]
