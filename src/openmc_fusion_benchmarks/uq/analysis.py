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
        Calculate the first-order Sobol sensitivity indices.

        The estimator uses the centered covariance form of the Saltelli
        first-order estimator for the pick-freeze construction

            AB_i = (A_i, B_-i).

        The first-order index is estimated as

            S_i = Cov(Y_A, Y_AB_i) / Var(Y_A)

        where the covariance is evaluated using the paired A and
        AB_i realizations.
        It is centered and not the exact Saltelli estimator, for better
        numerical stability at low sample sizes.

        Returns
        -------
        numpy.ndarray
            First-order Sobol indices. The first dimension corresponds
            to perturbation, while the remaining dimensions correspond
            to the tally output dimensions.
        """
        A = self.tally.A
        AB = self.tally.AB

        if AB.ndim != A.ndim + 1:
            raise ValueError(
                "The AB ensemble must have one additional leading "
                "dimension for perturbations."
            )

        if AB.shape[1:] != A.shape:
            raise ValueError(
                "Each AB perturbation ensemble must have the same "
                "shape as the A ensemble."
            )

        variance = self.variance

        if np.any(variance == 0):
            raise ValueError(
                "First-order Sobol indices are undefined for "
                "output dimensions with zero variance."
            )

        # Mean over realizations.
        A_mean = np.mean(A, axis=0)
        AB_mean = np.mean(AB, axis=1)

        # Center A and AB_i independently.
        A_centered = A - A_mean
        AB_centered = AB - AB_mean[:, None, ...]

        # Paired sample covariance:
        #
        # A_centered:
        #     (N, ...)
        #
        # AB_centered:
        #     (P, N, ...)
        #
        # Broadcasting gives:
        #     (P, N, ...)
        covariance = np.mean(
            A_centered[None, ...] * AB_centered,
            axis=1,
        )

        return covariance / variance


    # def first_order_saltelli(self):
    #     """
    #     Calculate the first-order Sobol sensitivity indices.

    #     The estimator uses the covariance form of the Saltelli
    #     first-order estimator for the pick-freeze construction

    #         AB_i = (A_i, B_-i).

    #     The first-order index is estimated as

    #         S_i = Cov(Y_A, Y_AB_i) / Var(Y_A).

    #     The covariance is evaluated using the paired A and AB_i
    #     realizations.

    #     Returns
    #     -------
    #     numpy.ndarray
    #         First-order Sobol indices. The first dimension corresponds
    #         to perturbation, while the remaining dimensions correspond
    #         to the tally output dimensions.
    #     """
    #     A = self.tally.A
    #     AB = self.tally.AB

    #     if AB.ndim != A.ndim + 1:
    #         raise ValueError(
    #             "The AB ensemble must have one additional leading "
    #             "dimension for perturbations."
    #         )

    #     if AB.shape[1:] != A.shape:
    #         raise ValueError(
    #             "Each AB perturbation ensemble must have the same "
    #             "shape as the A ensemble."
    #         )

    #     variance = self.variance

    #     if np.any(variance == 0):
    #         raise ValueError(
    #             "First-order Sobol indices are undefined for "
    #             "output dimensions with zero variance."
    #         )

    #     # Mean of the primary A ensemble.
    #     mean = np.mean(A, axis=0)

    #     # ------------------------------------------------------------------
    #     # Exact Saltelli first-order estimator
    #     #
    #     #     S_i = [E(Y_A * Y_AB_i) - mu^2] / Var(Y)
    #     #
    #     # where mu = E(Y).
    #     #
    #     # For the finite sample, mu is estimated from the A ensemble.
    #     # ------------------------------------------------------------------
    #     covariance = (
    #         np.mean(
    #             A[None, ...] * AB,
    #             axis=1,
    #         )
    #         - mean**2
    #     )

    #     return covariance / variance

    def total_order_contribution(self):
        """
        Return the total-order contribution of each input to output variance.

        C_Ti = S_Ti * Var(Y)
        """
        return self.total_order() * self.variance

    def total_order_contribution(self):
        """
        Return the total-order contribution of each input to output variance.

        C_Ti = S_Ti * Var(Y)
        """
        return self.total_order() * self.variance