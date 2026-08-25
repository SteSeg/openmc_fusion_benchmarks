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


    def _compute_total_order(self, A, AB):
        """
        Compute total-order Sobol indices from pick-freeze ensembles.

        The estimator is the Jansen total-order estimator for the
        pick-freeze construction

            AB_i = (A_i, B_-i):

            S_Ti = E[(Y_A - Y_AB_i)^2] / (2 Var(Y_A)).

        Parameters
        ----------
        A : numpy.ndarray
            Primary A ensemble. Shape:

                (n_realizations, ...)

        AB : numpy.ndarray
            Pick-freeze AB ensembles. Shape:

                (n_inputs, n_realizations, ...)

        Returns
        -------
        numpy.ndarray
            Total-order Sobol indices with shape:

                (n_inputs, ...)

        Raises
        ------
        ValueError
            If the A and AB arrays have incompatible shapes or if the
            variance is zero for any output element.
        """
        A = np.asarray(A)
        AB = np.asarray(AB)

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

        # Output variance from the A ensemble.
        variance = np.var(A, axis=0)

        if np.any(variance == 0):
            raise ValueError(
                "Total-order Sobol indices are undefined for "
                "output dimensions with zero variance."
            )

        # Jansen total-order numerator:
        #
        #     1/2 E[(Y_A - Y_AB_i)^2]
        numerator = 0.5 * np.mean(
            (A[None, ...] - AB) ** 2,
            axis=1,
        )

        return numerator / variance


    def _compute_first_order(self, A, AB):
        """
        Compute first-order Sobol indices from pick-freeze ensembles.

        The pick-freeze construction is assumed to be

            AB_i = (A_i, B_-i).

        The estimator is the covariance-form first-order estimator:

            S_i = Cov(Y_A, Y_AB_i) / Var(Y_A).

        Parameters
        ----------
        A : numpy.ndarray
            Primary A ensemble. Shape:

                (n_realizations, ...)

        AB : numpy.ndarray
            Pick-freeze AB ensembles. Shape:

                (n_inputs, n_realizations, ...)

        Returns
        -------
        numpy.ndarray
            First-order Sobol indices with shape:

                (n_inputs, ...)

        Raises
        ------
        ValueError
            If the A and AB arrays have incompatible shapes or if the
            variance is zero for any output element.
        """
        A = np.asarray(A)
        AB = np.asarray(AB)

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

        # Mean over realizations.
        A_mean = np.mean(A, axis=0)
        AB_mean = np.mean(AB, axis=1)

        # Center each ensemble.
        A_centered = A - A_mean
        AB_centered = AB - AB_mean[:, None, ...]

        # Paired covariance between A and each AB_i.
        covariance = np.mean(
            A_centered[None, ...] * AB_centered,
            axis=1,
        )

        # Output variance from the A ensemble.
        variance = np.var(A, axis=0)

        if np.any(variance == 0):
            raise ValueError(
                "First-order Sobol indices are undefined for "
                "output dimensions with zero variance."
            )

        return covariance / variance

    def total_order(self):
        """
        Calculate the Jansen total-order Sobol sensitivity indices.
        """
        return self._compute_total_order(
            self.tally.A,
            self.tally.AB,
        )

    def first_order(self):
        """
        Calculate the first-order Sobol sensitivity indices.
        """
        return self._compute_first_order(
            self.tally.A,
            self.tally.AB,
        )

    # def total_order(self):
    #     """
    #     Calculate the Jansen total-order Sobol sensitivity indices.

    #     The Jansen estimator is

    #         S_Ti = [1 / (2N)] * sum_r
    #             (Y_A[r] - Y_AB_i[r])**2 / V_Y

    #     where Y_A is the A ensemble, Y_AB_i is the pick-freeze
    #     ensemble associated with perturbation i, N is the number
    #     of realizations, and V_Y is the variance of the primary
    #     output ensemble.

    #     Returns
    #     -------
    #     numpy.ndarray
    #         Total-order Sobol indices. The first dimension corresponds
    #         to perturbation, while all remaining dimensions correspond
    #         to the output dimensions of the tally.

    #     Raises
    #     ------
    #     ValueError
    #         If the A and B ensembles have different shapes, if the
    #         AB ensemble does not have the expected dimensions, or if
    #         the number of realizations in AB does not match A.
    #     """
    #     A = self.tally.A
    #     B = self.tally.B
    #     AB = self.tally.AB

    #     # Validate A and B.
    #     if A.shape != B.shape:
    #         raise ValueError(
    #             "Pick-freeze A and B ensembles must have the same shape."
    #         )

    #     # Expected structure:
    #     # A  -> (realization, ...)
    #     # AB -> (perturbation, realization, ...)
    #     if AB.ndim != A.ndim + 1:
    #         raise ValueError(
    #             "The AB ensemble must have one additional leading "
    #             "dimension for perturbations."
    #         )

    #     if AB.shape[1] != A.shape[0]:
    #         raise ValueError(
    #             "The AB ensemble must have the same number of "
    #             "realizations as the A ensemble."
    #         )

    #     variance = self.variance

    #     if np.any(variance == 0):
    #         raise ValueError(
    #             "Jansen total-order Sobol indices are undefined "
    #             "for output dimensions with zero variance."
    #         )

    #     # A:  (N, ...)
    #     # AB: (P, N, ...)
    #     #     ↓ broadcasting
    #     #     (P, N, ...)
    #     squared_difference = (A[None, ...] - AB) ** 2

    #     # Average over the realization dimension.
    #     # Result: (P, ...)
    #     numerator = 0.5 * np.mean(
    #         squared_difference,
    #         axis=1,
    #     )

    #     return numerator / variance

    # def first_order(self):
    #     """
    #     Calculate the first-order Sobol sensitivity indices.

    #     The estimator uses the centered covariance form of the Saltelli
    #     first-order estimator for the pick-freeze construction

    #         AB_i = (A_i, B_-i).

    #     The first-order index is estimated as

    #         S_i = Cov(Y_A, Y_AB_i) / Var(Y_A)

    #     where the covariance is evaluated using the paired A and
    #     AB_i realizations.
    #     It is centered and not the exact Saltelli estimator, for better
    #     numerical stability at low sample sizes.

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

    #     # Mean over realizations.
    #     A_mean = np.mean(A, axis=0)
    #     AB_mean = np.mean(AB, axis=1)

    #     # Center A and AB_i independently.
    #     A_centered = A - A_mean
    #     AB_centered = AB - AB_mean[:, None, ...]

    #     # Paired sample covariance:
    #     #
    #     # A_centered:
    #     #     (N, ...)
    #     #
    #     # AB_centered:
    #     #     (P, N, ...)
    #     #
    #     # Broadcasting gives:
    #     #     (P, N, ...)
    #     covariance = np.mean(
    #         A_centered[None, ...] * AB_centered,
    #         axis=1,
    #     )

    #     return covariance / variance


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


    def bootstrap(
        self,
        n_resamples=1000,
        confidence_level=0.95,
        random_seed=None,
    ):
        """
        Estimate bootstrap uncertainty of the Sobol sensitivity indices.

        Bootstrap resampling is performed over the realization dimension.
        The same resampled realization indices are applied to the A ensemble
        and to every AB_i ensemble, preserving the pick-freeze pairing.

        The bootstrap uses the same first-order and total-order estimators
        implemented by :meth:`_compute_first_order` and
        :meth:`_compute_total_order`.

        Parameters
        ----------
        n_resamples : int, default=1000
            Number of bootstrap resamples.

        confidence_level : float, default=0.95
            Confidence level for the percentile confidence intervals.

        random_seed : int or None, default=None
            Seed for the bootstrap random-number generator.

        Returns
        -------
        dict
            Dictionary containing:

            ``first_order``
                Bootstrap first-order Sobol indices with shape
                ``(n_resamples, n_inputs, ...)``.

            ``total_order``
                Bootstrap total-order Sobol indices with shape
                ``(n_resamples, n_inputs, ...)``.

            ``first_order_estimate``
                First-order Sobol indices calculated from the original
                TMC ensemble.

            ``total_order_estimate``
                Total-order Sobol indices calculated from the original
                TMC ensemble.

            ``first_order_ci``
                Percentile confidence interval for the first-order indices.
                Shape ``(2, n_inputs, ...)``.

            ``total_order_ci``
                Percentile confidence interval for the total-order indices.
                Shape ``(2, n_inputs, ...)``.
        """
        if n_resamples < 1:
            raise ValueError(
                "n_resamples must be a positive integer."
            )

        if not 0.0 < confidence_level < 1.0:
            raise ValueError(
                "confidence_level must be between 0 and 1."
            )

        A = np.asarray(self.tally.A)
        AB = np.asarray(self.tally.AB)

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

        n_realizations = A.shape[0]

        if n_realizations < 2:
            raise ValueError(
                "At least two realizations are required for bootstrap analysis."
            )

        rng = np.random.default_rng(random_seed)

        first_order_samples = []
        total_order_samples = []

        # ------------------------------------------------------------------
        # Bootstrap resampling
        # ------------------------------------------------------------------
        for _ in range(n_resamples):

            # Resample realization indices with replacement.
            #
            # The same indices are applied to A and AB so that the
            # pick-freeze pairing is preserved.
            indices = rng.integers(
                0,
                n_realizations,
                size=n_realizations,
            )

            A_boot = A[indices, ...]
            AB_boot = AB[:, indices, ...]

            # Compute Sobol indices using the same estimators as the
            # corresponding public analysis methods.
            first_order = self._compute_first_order(
                A_boot,
                AB_boot,
            )

            total_order = self._compute_total_order(
                A_boot,
                AB_boot,
            )

            first_order_samples.append(first_order)
            total_order_samples.append(total_order)

        # ------------------------------------------------------------------
        # Convert bootstrap samples to arrays.
        #
        # Shape:
        #     (n_resamples, n_inputs, ...)
        # ------------------------------------------------------------------
        first_order_samples = np.stack(
            first_order_samples,
            axis=0,
        )

        total_order_samples = np.stack(
            total_order_samples,
            axis=0,
        )

        # ------------------------------------------------------------------
        # Percentile confidence intervals
        # ------------------------------------------------------------------
        alpha = 1.0 - confidence_level

        lower = 100.0 * alpha / 2.0
        upper = 100.0 * (1.0 - alpha / 2.0)

        first_order_ci = np.nanpercentile(
            first_order_samples,
            [lower, upper],
            axis=0,
        )

        total_order_ci = np.nanpercentile(
            total_order_samples,
            [lower, upper],
            axis=0,
        )

        # ------------------------------------------------------------------
        # Point estimates from the original TMC ensemble
        # ------------------------------------------------------------------
        first_order_estimate = self.first_order()
        total_order_estimate = self.total_order()

        return {
            "first_order": first_order_samples,
            "total_order": total_order_samples,
            "first_order_estimate": first_order_estimate,
            "total_order_estimate": total_order_estimate,
            "first_order_ci": first_order_ci,
            "total_order_ci": total_order_ci,
        }

    def convergence(self, sample_sizes=None):
        """
        Evaluate convergence of the Sobol sensitivity indices with
        increasing numbers of TMC realizations.

        The analysis uses the first ``n`` realizations of the A and AB
        ensembles for each requested sample size. No additional OpenMC
        simulations are performed.

        Parameters
        ----------
        sample_sizes : array-like or None, optional
            Numbers of realizations to use for each convergence estimate.
            If None, automatically generate a sequence of sample sizes
            between 2 and the total number of available realizations.

        Returns
        -------
        dict
            Dictionary containing:

            ``sample_sizes``
                Array of realization counts.

            ``first_order``
                First-order Sobol indices for each sample size. Shape:

                    (n_sample_sizes, n_inputs, ...)

            ``total_order``
                Total-order Sobol indices for each sample size. Shape:

                    (n_sample_sizes, n_inputs, ...)
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

        n_realizations = A.shape[0]

        if n_realizations < 2:
            raise ValueError(
                "At least two realizations are required for convergence analysis."
            )

        # --------------------------------------------------------------
        # Determine sample sizes.
        # --------------------------------------------------------------
        if sample_sizes is None:
            sample_sizes = np.unique(
                np.linspace(
                    2,
                    n_realizations,
                    min(10, n_realizations - 1),
                    dtype=int,
                )
            )
        else:
            sample_sizes = np.asarray(sample_sizes, dtype=int)

            if sample_sizes.ndim != 1:
                raise ValueError(
                    "sample_sizes must be a one-dimensional sequence."
                )

            if np.any(sample_sizes < 2):
                raise ValueError(
                    "All sample sizes must be at least 2."
                )

            if np.any(sample_sizes > n_realizations):
                raise ValueError(
                    "sample_sizes cannot exceed the number of available "
                    "TMC realizations."
                )

            sample_sizes = np.unique(sample_sizes)

        first_order_results = []
        total_order_results = []

        # --------------------------------------------------------------
        # Evaluate the Sobol estimators for each sample size.
        #
        # We use the first n realizations consistently across A and AB
        # so that the pick-freeze pairing is preserved.
        # --------------------------------------------------------------
        for n in sample_sizes:

            A_n = A[:n, ...]
            AB_n = AB[:, :n, ...]

            first_order_results.append(
                self._compute_first_order(
                    A_n,
                    AB_n,
                )
            )

            total_order_results.append(
                self._compute_total_order(
                    A_n,
                    AB_n,
                )
            )

        return {
            "sample_sizes": sample_sizes,
            "first_order": np.stack(
                first_order_results,
                axis=0,
            ),
            "total_order": np.stack(
                total_order_results,
                axis=0,
            ),
        }

    def interaction_contribution(self):
        """
        Calculate the variance contribution associated with interactions
        involving each input.

        This is defined as

            (S_Ti - S_i) * Var(Y).

        Returns
        -------
        numpy.ndarray
            Interaction contribution for each input and output dimension.
        """
        return (
            self.total_order() - self.first_order()
        ) * self.variance

    def interaction_fraction(self):
        """
        Calculate the fraction of output variance associated with
        interactions involving each input.

        This is defined as

            S_Ti - S_i.
        """
        return self.total_order() - self.first_order()

    def higher_order_variance(self):
        """
        Calculate the fraction of output variance not represented by
        first-order Sobol effects.

        This is

            1 - sum(S_i).

        It represents variance associated with interactions and should
        not be interpreted as model or numerical error.
        """
        return 1.0 - np.sum(
            self.first_order(),
            axis=0,
        )