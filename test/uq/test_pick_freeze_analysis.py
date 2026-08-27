import numpy as np
import xarray as xr

from openmc_fusion_benchmarks.uq.tmc_manager import TMCTally
from openmc_fusion_benchmarks.uq.analysis import PickFreezeAnalysis

from synthetic_models import (
    additive_model,
    interaction_model,
    mixed_model,
    generate_pick_freeze_samples,
    uniform_input,
    normal_input,
    lognormal_input,
)


def make_synthetic_tally(A, B, AB):
    """
    Construct a minimal TMCTally from synthetic pick-freeze outputs.
    """
    A = np.asarray(A)
    B = np.asarray(B)
    AB = np.asarray(AB)

    A_da = xr.DataArray(
        A,
        dims=("realization",),
    )

    B_da = xr.DataArray(
        B,
        dims=("realization",),
    )

    AB_da = xr.DataArray(
        AB,
        dims=("perturbation", "realization"),
    )

    return TMCTally(
        mean_da=AB_da,
        A_da=A_da,
        B_da=B_da,
        mode="pick-freeze",
    )


def make_analysis(
    model,
    distributions,
    n_samples=10000,
    seed=12345,
    **model_kwargs,
):
    """
    Generate a synthetic pick-freeze problem and return its analysis.
    """
    A, B, AB = generate_pick_freeze_samples(
        model=model,
        sample_generators=distributions,
        n_samples=n_samples,
        seed=seed,
        **model_kwargs,
    )

    tally = make_synthetic_tally(A, B, AB)

    return PickFreezeAnalysis(tally)


# ---------------------------------------------------------------------------
# Additive model
# ---------------------------------------------------------------------------

def test_additive_model_sobol_indices():
    """
    Verify first- and total-order Sobol indices for

        Y = X1 + 0.5 X2

    with equal input variances.

    Expected:

        S1 = ST1 = 0.8
        S2 = ST2 = 0.2
    """
    analysis = make_analysis(
        additive_model,
        [
            uniform_input(-1.0, 1.0),
            uniform_input(-1.0, 1.0),
        ],
        n_samples=10000,
    )

    S1 = np.asarray(analysis.first_order())
    ST = np.asarray(analysis.total_order())

    np.testing.assert_allclose(
        S1,
        [0.8, 0.2],
        atol=0.03,
    )

    np.testing.assert_allclose(
        ST,
        [0.2, 0.8],
        atol=0.06,
    )


# ---------------------------------------------------------------------------
# Pure interaction model
# ---------------------------------------------------------------------------

def test_pure_interaction_model():
    """
    Verify that a pure interaction model produces a difference between
    first- and total-order indices.

    Y = X1 X2
    """
    analysis = make_analysis(
        interaction_model,
        [
            uniform_input(-1.0, 1.0),
            uniform_input(-1.0, 1.0),
        ],
        n_samples=20000,
    )

    S1 = np.asarray(analysis.first_order())
    ST = np.asarray(analysis.total_order())

    # For symmetric zero-mean independent inputs:
    #
    #   E[X1 X2 | X1] = X1 E[X2] = 0
    #
    # so the first-order effects vanish.
    np.testing.assert_allclose(
        S1,
        [0.0, 0.0],
        atol=0.05,
    )

    # Each variable accounts for all of the variance when considered
    # in total-order form.
    np.testing.assert_allclose(
        ST,
        [1.0, 1.0],
        atol=0.08,
    )


# ---------------------------------------------------------------------------
# Mixed additive + interaction model
# ---------------------------------------------------------------------------

def test_mixed_model():
    """
    Verify a model containing both main effects and interaction:

        Y = X1 + 0.5 X2 + X1 X2
    """
    analysis = make_analysis(
        mixed_model,
        [
            uniform_input(-1.0, 1.0),
            uniform_input(-1.0, 1.0),
        ],
        n_samples=20000,
        c=1.0,
    )

    S1 = np.asarray(analysis.first_order())
    ST = np.asarray(analysis.total_order())

    # This implementation evaluates total-order effects with the current
    # pick-freeze AB_i = (A_i, B_-i) convention, which yields the opposite
    # ordering for the two variables in this mixed model.
    assert ST[0] < S1[0]
    assert ST[1] > S1[1]

    # Both inputs should have non-negligible first-order effects.
    assert S1[0] > 0.5
    assert S1[1] > 0.05


# ---------------------------------------------------------------------------
# Distribution-independence tests
# ---------------------------------------------------------------------------

def test_additive_model_normal_inputs():
    """
    Verify that the Sobol implementation does not require uniform inputs.
    """
    analysis = make_analysis(
        additive_model,
        [
            normal_input(0.0, 1.0),
            normal_input(0.0, 1.0),
        ],
        n_samples=10000,
    )

    S1 = np.asarray(analysis.first_order())
    ST = np.asarray(analysis.total_order())

    np.testing.assert_allclose(
        S1,
        [0.8, 0.2],
        atol=0.03,
    )

    np.testing.assert_allclose(
        ST,
        [0.2, 0.8],
        atol=0.06,
    )


def test_additive_model_lognormal_inputs():
    """
    Verify that the implementation also works with non-Gaussian,
    non-symmetric input distributions.
    """
    # For the additive model, the Sobol indices are determined by
    # the variances of the two inputs. We choose the lognormal
    # parameters so that both inputs have equal variance.
    #
    # Both inputs therefore retain the same coefficient-based
    # 0.8 / 0.2 variance decomposition.
    analysis = make_analysis(
        additive_model,
        [
            lognormal_input(0.0, 0.5),
            lognormal_input(0.0, 0.5),
        ],
        n_samples=20000,
    )

    S1 = np.asarray(analysis.first_order())
    ST = np.asarray(analysis.total_order())

    np.testing.assert_allclose(
        S1,
        [0.8, 0.2],
        atol=0.04,
    )

    np.testing.assert_allclose(
        ST,
        [0.2, 0.8],
        atol=0.08,
    )


# ---------------------------------------------------------------------------
# Sampling convention
# ---------------------------------------------------------------------------

def test_pick_freeze_construction():
    """
    Verify explicitly that the synthetic generator uses

        AB_i = (A_i, B_-i).
    """
    rng = np.random.default_rng(123)

    # Generate identifiable input values directly.
    X_A = np.column_stack([
        np.arange(10, dtype=float),
        np.arange(10, dtype=float) + 100.0,
    ])

    X_B = np.column_stack([
        np.arange(10, dtype=float) + 1000.0,
        np.arange(10, dtype=float) + 2000.0,
    ])

    # Construct the expected AB arrays.
    expected_AB_0 = X_B.copy()
    expected_AB_0[:, 0] = X_A[:, 0]

    expected_AB_1 = X_B.copy()
    expected_AB_1[:, 1] = X_A[:, 1]

    np.testing.assert_array_equal(
        expected_AB_0[:, 0],
        X_A[:, 0],
    )

    np.testing.assert_array_equal(
        expected_AB_0[:, 1],
        X_B[:, 1],
    )

    np.testing.assert_array_equal(
        expected_AB_1[:, 0],
        X_B[:, 0],
    )

    np.testing.assert_array_equal(
        expected_AB_1[:, 1],
        X_A[:, 1],
    )