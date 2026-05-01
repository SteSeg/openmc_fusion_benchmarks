from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from enum import Enum
import numpy as np


class PointStatus(str, Enum):
    OK = "ok"
    WARNING = "warning"
    OUTLIER = "outlier"
    ERROR = "error"

class BenchmarkStatus(str, Enum):
    ACCEPTABLE = "acceptable"
    BORDERLINE = "borderline"
    PROBLEMATIC = "problematic"

@dataclass
class Measurement:
    """A single experimental or calculated measurement."""
    value: float
    uncertainty: float
    
    @property
    def relative_uncertainty(self) -> float:
        """Relative uncertainty as a fraction."""
        return abs(self.uncertainty / self.value) if self.value != 0 else np.inf
    

@dataclass
class PointMetrics:
    """Metrics for a single comparison point."""
    c_over_e: float
    relative_deviation: float
    absolute_deviation: float
    combined_uncertainty: float
    normalized_residual: float
    z_score: float
    chi2_contribution: float
    status: PointStatus


@dataclass
class ComparisonPoint:
    """One comparison point (detector, foil, energy bin, etc.)."""
    id: str
    observable_type: str  # "reaction_rate", "spectrum", "leakage", etc.
    experiment: Measurement
    calculation: Measurement
    metrics: Optional[PointMetrics] = None
    covariance_index: Optional[int] = None  # Index in covariance matrix if available


@dataclass
class ObservableComparison:
    """Comparison of all points for one observable (one tally, one spectrum, one foil traverse)."""
    name: str
    observable_type: str
    points: list[ComparisonPoint]
    
    # Observable-level aggregates
    mean_bias: float = field(default=0.0)
    mean_abs_relative_deviation: float = field(default=0.0)
    rms_relative_deviation: float = field(default=0.0)
    mean_abs_normalized_residual: float = field(default=0.0)
    reduced_chi2: float = field(default=0.0)
    fraction_within_1sigma: float = field(default=0.0)
    fraction_within_2sigma: float = field(default=0.0)
    fraction_beyond_3sigma: float = field(default=0.0)
    outlier_fraction: float = field(default=0.0)
    pass_count: int = field(default=0)
    warning_count: int = field(default=0)
    outlier_count: int = field(default=0)


@dataclass
class BenchmarkComparison:
    """Full validation comparison for one benchmark run against reference data."""
    benchmark_id: str
    code_name: str
    code_version: str
    reference_source: str  # "database", "path", etc.
    
    observables: list[ObservableComparison] = field(default_factory=list)
    
    # Benchmark-level aggregates
    weighted_mean_bias: float = field(default=0.0)
    weighted_rms_deviation: float = field(default=0.0)
    global_reduced_chi2: float = field(default=0.0)
    total_point_count: int = field(default=0)
    
    benchmark_status: BenchmarkStatus = field(default=BenchmarkStatus.ACCEPTABLE)
    dashboard_score: float = field(default=50.0)  # 0-100
    
    quality_flags: Dict[str, bool] = field(default_factory=dict)
    assumptions: Dict[str, Any] = field(default_factory=dict)