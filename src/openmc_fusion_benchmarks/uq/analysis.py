import numpy as np

class PickFreezeAnalysis:
    """Statistical analysis of a pick-freeze TMC tally."""

    def __init__(self, tally):
        if tally.mode != "pick-freeze":
            raise ValueError(
                "PickFreezeAnalysis requires a TMCTally in pick-freeze mode."
            )

        self.tally = tally
        self._validate()

    def _validate(self):
        A = self.tally.A
        B = self.tally.B
        AB = self.tally.AB

        if A.shape != B.shape:
            raise ValueError(
                "Pick-freeze A and B ensembles must have the same shape."
            )

        if AB.shape[1] != A.shape[0]:
            raise ValueError(
                "Pick-freeze AB ensemble must have the same number "
                "of realizations as A and B."
            )

    @property
    def mean(self):
        """Mean of the primary pick-freeze output ensemble."""
        return self.tally.mean


    @property
    def variance(self):
        """Variance of the primary pick-freeze output ensemble."""
        return self.tally.variance


    @property
    def std_dev(self):
        """Standard deviation of the primary pick-freeze output ensemble."""
        return self.tally.std_dev

    @property
    def n_realizations(self):
        return self.tally.A.shape[0]

    @property
    def n_perturbations(self):
        return self.tally.AB.shape[0]

    def total_order(self):
        """
        Calculate the Jansen total-order Sobol sensitivity indices.

        The Jansen estimator is

            S_Ti = [1 / (2N)] * sum_r
                (Y_A[r] - Y_AB_i[r])**2 / V_Y

        where Y_A is the A ensemble, Y_AB_i is the pick-freeze
        ensemble associated with perturbation i, N is the number
        of realizations, and V_Y is the variance of the primary
        output ensemble.

        Returns
        -------
        numpy.ndarray
            Total-order Sobol indices. The first dimension corresponds
            to perturbation, while all remaining dimensions correspond
            to the output dimensions of the tally.

        Raises
        ------
        ValueError
            If the A and B ensembles have different shapes, if the
            AB ensemble does not have the expected dimensions, or if
            the number of realizations in AB does not match A.
        """
        A = self.tally.A
        B = self.tally.B
        AB = self.tally.AB

        # Validate A and B.
        if A.shape != B.shape:
            raise ValueError(
                "Pick-freeze A and B ensembles must have the same shape."
            )

        # Expected structure:
        # A  -> (realization, ...)
        # AB -> (perturbation, realization, ...)
        if AB.ndim != A.ndim + 1:
            raise ValueError(
                "The AB ensemble must have one additional leading "
                "dimension for perturbations."
            )

        if AB.shape[1] != A.shape[0]:
            raise ValueError(
                "The AB ensemble must have the same number of "
                "realizations as the A ensemble."
            )

        variance = self.variance

        if np.any(variance == 0):
            raise ValueError(
                "Jansen total-order Sobol indices are undefined "
                "for output dimensions with zero variance."
            )

        # A:  (N, ...)
        # AB: (P, N, ...)
        #     ↓ broadcasting
        #     (P, N, ...)
        squared_difference = (A[None, ...] - AB) ** 2

        # Average over the realization dimension.
        # Result: (P, ...)
        numerator = 0.5 * np.mean(
            squared_difference,
            axis=1,
        )

        return numerator / variance

    def first_order(self):
        """
        Calculate the Saltelli first-order Sobol sensitivity indices.

        The estimator used here is the covariance form of the
        Saltelli first-order Sobol estimator:

            S_i = [E(Y_A * Y_AB_i) - mu_Y**2] / V_Y

        where Y_A is the A ensemble, Y_AB_i is the pick-freeze
        ensemble associated with perturbation i, mu_Y is the mean
        of the primary output ensemble, and V_Y is its variance.

        The pick-freeze ensemble is constructed as

            AB_i = (A_i, B_-i),

        i.e. perturbation i is taken from the A ensemble while all
        other perturbations are taken from the B ensemble.

        Returns
        -------
        numpy.ndarray
            First-order Sobol indices. The first dimension corresponds
            to perturbation, while all remaining dimensions correspond
            to the output dimensions of the tally.

        Raises
        ------
        ValueError
            If the A and B ensembles have different shapes, if the
            AB ensemble does not have the expected dimensions, if
            the number of realizations in AB does not match A, or if
            the output variance is zero.
        """
        A = self.tally.A
        B = self.tally.B
        AB = self.tally.AB

        # Validate A and B.
        if A.shape != B.shape:
            raise ValueError(
                "Pick-freeze A and B ensembles must have the same shape."
            )

        # Expected structure:
        # A  -> (realization, ...)
        # AB -> (perturbation, realization, ...)
        if AB.ndim != A.ndim + 1:
            raise ValueError(
                "The AB ensemble must have one additional leading "
                "dimension for perturbations."
            )

        if AB.shape[1] != A.shape[0]:
            raise ValueError(
                "The AB ensemble must have the same number of "
                "realizations as the A ensemble."
            )

        variance = self.variance

        if np.any(variance == 0):
            raise ValueError(
                "First-order Sobol indices are undefined for "
                "output dimensions with zero variance."
            )

        mean = self.mean

        # A:       (N, ...)
        # AB:      (P, N, ...)
        # A[None]: (1, N, ...)
        #
        # Broadcasting gives:
        # A[None, ...] * AB -> (P, N, ...)
        product = A[None, ...] * AB

        # Average over realizations.
        # Result: (P, ...)
        covariance = np.mean(product, axis=1) - mean**2

        return covariance / variance