import numpy as np


def additive_model(x):
    """
    Additive two-input model.

    Y = X1 + 0.5 X2
    """
    x = np.asarray(x)

    if x.shape[-1] != 2:
        raise ValueError("additive_model requires exactly two inputs.")

    return x[..., 0] + 0.5 * x[..., 1]


def interaction_model(x):
    """
    Pure interaction two-input model.

    Y = X1 X2
    """
    x = np.asarray(x)

    if x.shape[-1] != 2:
        raise ValueError("interaction_model requires exactly two inputs.")

    return x[..., 0] * x[..., 1]


def mixed_model(x, c=1.0):
    """
    Mixed additive/interaction two-input model.

    Y = X1 + 0.5 X2 + c X1 X2
    """
    x = np.asarray(x)

    if x.shape[-1] != 2:
        raise ValueError("mixed_model requires exactly two inputs.")

    x1 = x[..., 0]
    x2 = x[..., 1]

    return x1 + 0.5 * x2 + c * x1 * x2


def generate_pick_freeze_samples(
    model,
    sample_generators,
    n_samples,
    seed=None,
    **model_kwargs,
):
    """
    Generate synthetic A, B, and AB pick-freeze model outputs.

    The input samples are constructed as independent A and B matrices:

        X_A : (N, P)
        X_B : (N, P)

    where N is the number of realizations and P is the number of
    uncertain inputs.

    The corresponding model outputs are:

        A  = Y(X_A)
        B  = Y(X_B)

    with shapes:

        A  : (N, ...)
        B  : (N, ...)

    For input i, the pick-freeze ensemble is constructed as:

        X_AB_i = (X_B[:, 0], ..., X_A[:, i], ..., X_B[:, P-1])

    and therefore:

        AB : (P, N, ...)

    where ... denotes the model-output dimensions.

    Parameters
    ----------
    model : callable
        Model accepting an array of shape ``(n_samples, n_inputs)``.
    sample_generators : sequence of callable
        One callable per input. Each callable must accept
        ``(rng, n_samples)`` and return ``n_samples`` samples.
    n_samples : int
        Number of Monte Carlo realizations.
    seed : int or None
        Random seed.
    **model_kwargs
        Additional keyword arguments passed to ``model``.

    Returns
    -------
    A : numpy.ndarray
        Model outputs from the A ensemble.
    B : numpy.ndarray
        Model outputs from the B ensemble.
    AB : numpy.ndarray
        Pick-freeze model outputs with shape
        ``(n_inputs, n_samples, ...)``.
    """
    rng = np.random.default_rng(seed)

    n_inputs = len(sample_generators)

    if n_inputs == 0:
        raise ValueError("At least one input distribution is required.")

    # Generate independent A and B input matrices.
    X_A = np.empty((n_samples, n_inputs), dtype=float)
    X_B = np.empty((n_samples, n_inputs), dtype=float)

    for i, generator in enumerate(sample_generators):
        X_A[:, i] = generator(rng, n_samples)
        X_B[:, i] = generator(rng, n_samples)

    # Primary ensembles.
    A = np.asarray(model(X_A, **model_kwargs))
    B = np.asarray(model(X_B, **model_kwargs))

    # Pick-freeze ensembles:
    #
    # AB_i = (A_i, B_-i)
    AB = np.empty(
        (n_inputs,) + A.shape,
        dtype=float,
    )

    for i in range(n_inputs):
        X_AB = X_B.copy()
        X_AB[:, i] = X_A[:, i]

        AB[i] = model(X_AB, **model_kwargs)

    return A, B, AB


# ---------------------------------------------------------------------------
# Common independent input distributions
# ---------------------------------------------------------------------------

def uniform_input(low=0.0, high=1.0):
    """Return a generator for U(low, high)."""

    def generator(rng, n_samples):
        return rng.uniform(low, high, size=n_samples)

    return generator


def normal_input(mean=0.0, std=1.0):
    """Return a generator for N(mean, std)."""

    def generator(rng, n_samples):
        return rng.normal(mean, std, size=n_samples)

    return generator


def lognormal_input(mean=0.0, sigma=1.0):
    """Return a generator for a lognormal distribution."""

    def generator(rng, n_samples):
        return rng.lognormal(mean, sigma, size=n_samples)

    return generator