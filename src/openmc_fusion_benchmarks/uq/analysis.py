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

    def _compute_global_variance(self, A, B):
        """Pooled A+B sample variance (ddof=1) along the realization axis."""
        pooled = np.concatenate((np.asarray(A), np.asarray(B)), axis=0)
        return np.var(pooled, axis=0, ddof=1)

    def _compute_global_mean(self, A, B):
        """Pooled A+B sample mean along the realization axis."""
        pooled = np.concatenate((np.asarray(A), np.asarray(B)), axis=0)
        return np.mean(pooled, axis=0)

    @property
    def global_mean(self):
        """Global response mean estimated from the pooled A and B ensembles."""
        return self._compute_global_mean(self.tally.A, self.tally.B)

    @property
    def global_variance(self):
        """
        Global response variance estimated from the pooled A and B ensembles.

        Uses ddof=1, i.e. the unbiased sample-variance estimator.
        """
        return self._compute_global_variance(self.tally.A, self.tally.B)

    @property
    def global_std_dev(self):
        """
        Global response standard deviation estimated from pooled A and B.
        """
        return np.sqrt(self.global_variance)

    @property
    def n_realizations(self):
        return self.tally.A.shape[0]

    @property
    def n_perturbations(self):
        return self.tally.AB.shape[0]


    def _compute_total_order(self, A, AB, B=None, variance=None):
        """
        Compute total-order Sobol indices from pick-freeze ensembles.

        The pick-freeze construction is assumed to be

            AB_i = (B_i, A_-i),

        where AB[i] corresponds to perturbation i.

        The estimator is the Jansen total-order estimator:

            S_T_i = E[(Y_A - Y_AB_i)^2] / (2 Var(Y)),

        where Var(Y) is the global output variance estimated from the
        pooled A and B ensembles (ddof=1).

        Parameters
        ----------
        A : numpy.ndarray
            Primary A ensemble. Shape:

                (n_realizations, ...)

        AB : numpy.ndarray
            Pick-freeze AB ensembles. Shape:

                (n_inputs, n_realizations, ...)

        B : numpy.ndarray, optional
            Independent B ensemble, shape (n_realizations, ...). Used to
            compute the pooled global variance if ``variance`` is not given.

        variance : numpy.ndarray, optional
            Precomputed global output variance, shape ``A.shape[1:]``.
            If given, it is used directly.

        Returns
        -------
        numpy.ndarray
            Total-order Sobol indices with shape:

                (n_inputs, ...)

        Raises
        ------
        ValueError
            If array shapes are incompatible, if neither ``B`` nor
            ``variance`` is provided, or if the variance is non-positive
            for any output element.
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

        # Global output variance from the pooled A+B ensembles.
        if variance is None:
            if B is None:
                raise ValueError(
                    "Either the B ensemble or a precomputed global "
                    "variance must be provided."
                )
            variance = self._compute_global_variance(A, B)
        else:
            variance = np.asarray(variance)
            if variance.shape != A.shape[1:]:
                raise ValueError(
                    "The variance must have the same shape as a single "
                    "A realization."
                )

        if np.any(variance <= 0):
            raise ValueError(
                "Total-order Sobol indices are undefined for "
                "output dimensions with non-positive variance."
            )

        # Jansen total-order numerator (unbiased, no mean estimate needed):
        #
        #     1/2 E[(Y_A - Y_AB_i)^2]
        numerator = 0.5 * np.mean(
            (A[None, ...] - AB) ** 2,
            axis=1,
        )

        return numerator / variance


    def _compute_first_order(self, A, B, AB, variance=None):
        """
        Compute covariance-form first-order Sobol indices from pick-freeze ensembles.

        The pick-freeze construction is assumed to be

            AB_i = (B_i, A_-i).

        The estimator is the covariance-form first-order estimator:

            S_i = Cov(Y_B, Y_AB_i) / Var(Y),

        where the covariance uses the unbiased 1/(n-1) normalization and
        Var(Y) is the global output variance estimated from the pooled
        A and B ensembles (ddof=1).

        Parameters
        ----------
        A : numpy.ndarray
            Primary A ensemble. Shape:

                (n_realizations, ...)

        B : numpy.ndarray
            Independent B ensemble. Shape:

                (n_realizations, ...)

        AB : numpy.ndarray
            Pick-freeze AB ensembles. Shape:

                (n_inputs, n_realizations, ...)

            AB[i] corresponds to perturbation i and is constructed as
            (B_i, A_-i).

        variance : numpy.ndarray, optional
            Precomputed global output variance, shape ``A.shape[1:]``.
            If None, it is computed from the pooled A and B ensembles.

        Returns
        -------
        numpy.ndarray
            First-order Sobol indices with shape:

                (n_inputs, ...)

        Raises
        ------
        ValueError
            If the A, B, and AB arrays have incompatible shapes, if fewer
            than two realizations are available, or if the variance is
            non-positive for any output element.
        """
        A = np.asarray(A)
        B = np.asarray(B)
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

        if B.shape != A.shape:
            raise ValueError(
                "The B ensemble must have the same shape as the A ensemble."
            )

        n_realizations = B.shape[0]

        if n_realizations < 2:
            raise ValueError(
                "At least two realizations are required to estimate "
                "first-order Sobol indices."
            )

        # Means over realizations.
        B_mean = np.mean(B, axis=0)
        AB_mean = np.mean(AB, axis=1)

        # Center each ensemble.
        B_centered = B - B_mean
        AB_centered = AB - AB_mean[:, None, ...]

        # Paired covariance between B and each AB_i -> V_i.
        # Unbiased 1/(n-1) normalization, consistent with ddof=1 variance.
        covariance = np.sum(
            B_centered[None, ...] * AB_centered,
            axis=1,
        ) / (n_realizations - 1)

        # Global output variance from the pooled A+B ensembles
        # (same normalizer as total_order).
        if variance is None:
            variance = self._compute_global_variance(A, B)
        else:
            variance = np.asarray(variance)
            if variance.shape != A.shape[1:]:
                raise ValueError(
                    "The variance must have the same shape as a single "
                    "A realization."
                )

        if np.any(variance <= 0):
            raise ValueError(
                "First-order Sobol indices are undefined for "
                "output dimensions with non-positive variance."
            )

        return covariance / variance

    def total_order(self):
        """
        Calculate the Jansen total-order Sobol sensitivity indices.
        """
        return self._compute_total_order(
            self.tally.A,
            self.tally.AB,
            variance=self.global_variance,
        )

    def first_order(self):
        """
        Calculate the first-order Sobol sensitivity indices.
        """
        return self._compute_first_order(
            self.tally.A,
            self.tally.B,
            self.tally.AB,
            variance=self.global_variance,
        )

    def total_order_contribution(self):
        """
        Return the total-order contribution of each input to output variance.

        C_Ti = S_Ti * Var(Y)
        """
        return self.total_order() * self.global_variance

    def _get_vard_mc_std(self):
        """
        Return stored per-run OpenMC standard deviations for A and B.

        VarD requires actual OpenMC mc_std data. Do not silently use the
        zero arrays returned by TMCTally when these data are unavailable.
        """
        if getattr(self.tally, "_A_mc_std_da", None) is None:
            raise ValueError("VarD requires stored A mc_std data.")
        if getattr(self.tally, "_B_mc_std_da", None) is None:
            raise ValueError("VarD requires stored B mc_std data.")

        return (
            np.asarray(self.tally.A_mc_std, dtype=float),
            np.asarray(self.tally.B_mc_std, dtype=float),
        )

    def _compute_vard_variance_components(self, A, B, mc_std_A, mc_std_B):
        """
        Compute observed, transport-noise, and VarD-corrected variances.

        The observed variance uses pooled A+B responses. The transport-noise
        variance is the corresponding mean of the per-run mc_std**2 values.
        """
        A = np.asarray(A, dtype=float)
        B = np.asarray(B, dtype=float)
        mc_std_A = np.asarray(mc_std_A, dtype=float)
        mc_std_B = np.asarray(mc_std_B, dtype=float)

        if A.shape != B.shape:
            raise ValueError("A and B must have identical shapes.")
        if mc_std_A.shape != A.shape or mc_std_B.shape != B.shape:
            raise ValueError("A/B mc_std arrays must match their response arrays.")
        if A.shape[0] < 2:
            raise ValueError("At least two realizations are required.")

        observed_variance = self._compute_global_variance(A, B)

        # Mean transport variance over the pooled A+B runs.
        transport_noise_variance = 0.5 * (
            np.mean(mc_std_A**2, axis=0)
            + np.mean(mc_std_B**2, axis=0)
        )

        parametric_variance = observed_variance - transport_noise_variance

        return (
            observed_variance,
            transport_noise_variance,
            parametric_variance,
        )

    @property
    def global_transport_noise_variance(self):
        """Mean per-run transport variance over the pooled A and B ensembles."""
        mc_std_A, mc_std_B = self._get_vard_mc_std()
        _, transport_noise_variance, _ = self._compute_vard_variance_components(
            self.tally.A,
            self.tally.B,
            mc_std_A,
            mc_std_B,
        )
        return transport_noise_variance

    @property
    def global_parametric_variance(self):
        """VarD estimate of response variance after removing transport noise."""
        mc_std_A, mc_std_B = self._get_vard_mc_std()
        _, _, parametric_variance = self._compute_vard_variance_components(
            self.tally.A,
            self.tally.B,
            mc_std_A,
            mc_std_B,
        )
        return parametric_variance

    def _compute_first_order_vard(
        self, A, B, AB, observed_variance, parametric_variance
    ):
        """
        Compute the VarD first-order index for AB_i = (B_i, A_-i).

        The conditional-variance estimate uses paired B and AB_i responses;
        these share input group i.
        """
        A = np.asarray(A, dtype=float)
        B = np.asarray(B, dtype=float)
        AB = np.asarray(AB, dtype=float)

        if B.shape != A.shape:
            raise ValueError("A and B must have identical shapes.")
        if AB.ndim != A.ndim + 1 or AB.shape[1:] != A.shape:
            raise ValueError("AB must have shape (n_inputs, n_realizations, ...).")

        # For each i, this estimates the conditional variance over X_-i.
        conditional_variance = 0.5 * np.mean(
            (B[None, ...] - AB) ** 2,
            axis=1,
        )

        numerator = observed_variance[None, ...] - conditional_variance
        denominator = parametric_variance[None, ...]

        return np.divide(
            numerator,
            denominator,
            out=np.full_like(numerator, np.nan, dtype=float),
            where=denominator > 0,
        )

    def _compute_total_order_vard(
        self, A, AB, observed_variance, parametric_variance
    ):
        """
        Compute the VarD total-order index for AB_i = (B_i, A_-i).

        The conditional-variance estimate uses paired A and AB_i responses;
        these share all input groups except i.
        """
        A = np.asarray(A, dtype=float)
        AB = np.asarray(AB, dtype=float)

        if AB.ndim != A.ndim + 1 or AB.shape[1:] != A.shape:
            raise ValueError("AB must have shape (n_inputs, n_realizations, ...).")

        # For each i, this estimates the conditional variance over X_i.
        conditional_variance = 0.5 * np.mean(
            (A[None, ...] - AB) ** 2,
            axis=1,
        )

        numerator = observed_variance[None, ...] - conditional_variance
        denominator = parametric_variance[None, ...]

        complement = np.divide(
            numerator,
            denominator,
            out=np.full_like(numerator, np.nan, dtype=float),
            where=denominator > 0,
        )

        return 1.0 - complement

    def first_order_vard(self):
        """Calculate first-order Sobol' indices using variance deconvolution."""
        A = np.asarray(self.tally.A, dtype=float)
        B = np.asarray(self.tally.B, dtype=float)
        AB = np.asarray(self.tally.AB, dtype=float)
        mc_std_A, mc_std_B = self._get_vard_mc_std()

        observed_variance, _, parametric_variance = (
            self._compute_vard_variance_components(A, B, mc_std_A, mc_std_B)
        )

        return self._compute_first_order_vard(
            A, B, AB, observed_variance, parametric_variance
        )

    def total_order_vard(self):
        """Calculate total-order Sobol' indices using variance deconvolution."""
        A = np.asarray(self.tally.A, dtype=float)
        B = np.asarray(self.tally.B, dtype=float)
        AB = np.asarray(self.tally.AB, dtype=float)
        mc_std_A, mc_std_B = self._get_vard_mc_std()

        observed_variance, _, parametric_variance = (
            self._compute_vard_variance_components(A, B, mc_std_A, mc_std_B)
        )

        return self._compute_total_order_vard(
            A, AB, observed_variance, parametric_variance
        )

    def interaction_remainder_vard(self):
        """
        Return total-order minus first-order VarD indices for each input.

        For p > 2, each result is the aggregate of all interactions involving
        that input; it is not an individual pairwise interaction index.
        """
        return self.total_order_vard() - self.first_order_vard()


    def bootstrap(
        self,
        n_resamples=1000,
        confidence_level=0.95,
        random_seed=None,
    ):
        """
        Estimate bootstrap uncertainty of the global response moments and
        of the Sobol sensitivity indices.

        Bootstrap resampling is performed over the realization dimension.
        The same resampled realization indices are applied to the A and B
        ensembles and to every AB_i ensemble, preserving the pick-freeze
        pairing.

        Global moments are computed from the pooled A and B ensembles
        (ddof=1 for the variance). The same pooled variance is used as the
        normalizer of the first-order and total-order estimators in every
        resample, consistently with _compute_first_order and
        _compute_total_order.

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

            ``global_mean``, ``global_variance``, ``global_std_dev``
                Bootstrap global moments with shape ``(n_resamples, ...)``.

            ``global_mean_estimate``, ``global_variance_estimate``,
            ``global_std_dev_estimate``
                Global moments calculated from the original TMC ensemble.

            ``global_mean_ci``, ``global_variance_ci``, ``global_std_dev_ci``
                Percentile confidence intervals. Shape ``(2, ...)``.

            ``global_mean_se``, ``global_variance_se``, ``global_std_dev_se``
                Bootstrap standard errors. Shape ``(...)``.

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

            ``first_order_se``
                Standard error of the first-order indices from the bootstrap
                resamples. Shape ``(n_inputs, ...)``.

            ``total_order_se``
                Standard error of the total-order indices from the bootstrap
                resamples. Shape ``(n_inputs, ...)``.

            ``confidence_level``
                Confidence level used for the percentile confidence intervals.

            ``n_resamples``
                Number of bootstrap resamples used to estimate uncertainty.
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
        B = np.asarray(self.tally.B)
        AB = np.asarray(self.tally.AB)

        if B.shape != A.shape:
            raise ValueError(
                "The B ensemble must have the same shape as the A ensemble."
            )

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

        global_mean_samples = []
        global_variance_samples = []

        first_order_samples = []
        total_order_samples = []

        interaction_remainder_samples = []
        higher_order_contribution_samples = []

        # ------------------------------------------------------------------
        # Bootstrap resampling
        # ------------------------------------------------------------------
        for _ in range(n_resamples):

            # Resample realization indices with replacement.
            #
            # The same indices are applied to A, B and AB so that the
            # pick-freeze pairing is preserved.
            indices = rng.integers(
                0,
                n_realizations,
                size=n_realizations,
            )

            A_boot = A[indices, ...]
            B_boot = B[indices, ...]
            AB_boot = AB[:, indices, ...]

            # Global moments from the pooled resampled A+B ensembles.
            mean_boot = self._compute_global_mean(A_boot, B_boot)
            variance_boot = self._compute_global_variance(A_boot, B_boot)

            global_mean_samples.append(mean_boot)
            global_variance_samples.append(variance_boot)

            # Compute Sobol indices using the same estimators and the same
            # pooled variance normalizer as the public analysis methods.
            first_order = self._compute_first_order(
                A_boot,
                B_boot,
                AB_boot,
                variance=variance_boot,
            )

            total_order = self._compute_total_order(
                A_boot,
                AB_boot,
                variance=variance_boot,
            )

            first_order_samples.append(first_order)
            total_order_samples.append(total_order)

            interaction_remainder_samples.append(total_order - first_order)

            # Aggregate variance contribution from all orders >= 2.
            # Shape: (tally dimensions...)
            higher_order_contribution_samples.append(
                1.0 - np.sum(first_order, axis=0)
)

        # ------------------------------------------------------------------
        # Convert bootstrap samples to arrays.
        #
        # Shapes:
        #     global moments: (n_resamples, ...)
        #     Sobol indices:  (n_resamples, n_inputs, ...)
        # ------------------------------------------------------------------
        global_mean_samples = np.stack(global_mean_samples, axis=0)
        global_variance_samples = np.stack(global_variance_samples, axis=0)
        global_std_dev_samples = np.sqrt(global_variance_samples)

        first_order_samples = np.stack(
            first_order_samples,
            axis=0,
        )

        total_order_samples = np.stack(
            total_order_samples,
            axis=0,
        )

        interaction_remainder_samples = np.stack(
        interaction_remainder_samples, axis=0
        )
        higher_order_contribution_samples = np.stack(
        higher_order_contribution_samples, axis=0
        )

        # ------------------------------------------------------------------
        # Percentile confidence intervals
        # ------------------------------------------------------------------
        alpha = 1.0 - confidence_level

        lower = 100.0 * alpha / 2.0
        upper = 100.0 * (1.0 - alpha / 2.0)

        global_mean_ci = np.nanpercentile(
            global_mean_samples, [lower, upper], axis=0
        )
        global_variance_ci = np.nanpercentile(
            global_variance_samples, [lower, upper], axis=0
        )
        global_std_dev_ci = np.nanpercentile(
            global_std_dev_samples, [lower, upper], axis=0
        )

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

        global_mean_se = np.nanstd(global_mean_samples, axis=0, ddof=1)
        global_variance_se = np.nanstd(global_variance_samples, axis=0, ddof=1)
        global_std_dev_se = np.nanstd(global_std_dev_samples, axis=0, ddof=1)

        first_order_se = np.nanstd(first_order_samples, axis=0, ddof=1)
        total_order_se = np.nanstd(total_order_samples, axis=0, ddof=1)

        # ------------------------------------------------------------------
        # Point estimates from the original TMC ensemble
        # ------------------------------------------------------------------
        global_mean_estimate = self.global_mean
        global_variance_estimate = self.global_variance
        global_std_dev_estimate = self.global_std_dev
        
        first_order_estimate = self.first_order()
        total_order_estimate = self.total_order()

        interaction_remainder_estimate = total_order_estimate - first_order_estimate
        higher_order_contribution_estimate = (
            1.0 - np.sum(first_order_estimate, axis=0)
        )

        interaction_remainder_ci = np.nanpercentile(
            interaction_remainder_samples, [lower, upper], axis=0
        )
        higher_order_contribution_ci = np.nanpercentile(
            higher_order_contribution_samples, [lower, upper], axis=0
        )

        interaction_remainder_se = np.nanstd(
            interaction_remainder_samples, axis=0, ddof=1
        )
        higher_order_contribution_se = np.nanstd(
            higher_order_contribution_samples, axis=0, ddof=1
        )

        return {
            "global_mean": global_mean_samples,
            "global_variance": global_variance_samples,
            "global_std_dev": global_std_dev_samples,
            "global_mean_estimate": global_mean_estimate,
            "global_variance_estimate": global_variance_estimate,
            "global_std_dev_estimate": global_std_dev_estimate,
            "global_mean_ci": global_mean_ci,
            "global_variance_ci": global_variance_ci,
            "global_std_dev_ci": global_std_dev_ci,
            "global_mean_se": global_mean_se,
            "global_variance_se": global_variance_se,
            "global_std_dev_se": global_std_dev_se,
            "first_order": first_order_samples,
            "total_order": total_order_samples,
            "first_order_estimate": first_order_estimate,
            "total_order_estimate": total_order_estimate,
            "first_order_ci": first_order_ci,
            "total_order_ci": total_order_ci,
            "first_order_se": first_order_se,
            "total_order_se": total_order_se,
            "interaction_remainder": interaction_remainder_samples,
            "interaction_remainder_estimate": interaction_remainder_estimate,
            "interaction_remainder_ci": interaction_remainder_ci,
            "interaction_remainder_se": interaction_remainder_se,
            "higher_order_contribution": higher_order_contribution_samples,
            "higher_order_contribution_estimate": higher_order_contribution_estimate,
            "higher_order_contribution_ci": higher_order_contribution_ci,
            "higher_order_contribution_se": higher_order_contribution_se,
            "confidence_level": confidence_level,
            "n_resamples": n_resamples,
        }

    def convergence(self, sample_sizes=None):
        """
        Evaluate convergence of the global response moments and of the
        Sobol sensitivity indices with increasing numbers of TMC
        realizations.

        The analysis uses the first ``n`` realizations of the A, B and AB
        ensembles for each requested sample size. No additional OpenMC
        simulations are performed. For each sample size, global moments
        are computed from the pooled first ``n`` realizations of A and B
        (ddof=1 for the variance), and the same pooled variance is used
        as the normalizer of the first-order and total-order estimators.

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

            ``global_mean``, ``global_variance``, ``global_std_dev``
                Global moments for each sample size. Shape:

                    (n_sample_sizes, ...)

            ``first_order``
                First-order Sobol indices for each sample size. Shape:

                    (n_sample_sizes, n_inputs, ...)

            ``total_order``
                Total-order Sobol indices for each sample size. Shape:

                    (n_sample_sizes, n_inputs, ...)
        """
        A = np.asarray(self.tally.A)
        B = np.asarray(self.tally.B)
        AB = np.asarray(self.tally.AB)

        if B.shape != A.shape:
            raise ValueError(
                "The B ensemble must have the same shape as the A ensemble."
            )

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

        global_mean_results = []
        global_variance_results = []

        first_order_results = []
        total_order_results = []

        # --------------------------------------------------------------
        # Evaluate global moments and Sobol estimators for each sample
        # size.
        #
        # We use the first n realizations consistently across A, B and
        # AB so that the pick-freeze pairing is preserved.
        # --------------------------------------------------------------
        for n in sample_sizes:

            A_n = A[:n, ...]
            B_n = B[:n, ...]
            AB_n = AB[:, :n, ...]

            # Pooled A+B global moments for this sample size.
            mean_n = self._compute_global_mean(A_n, B_n)
            variance_n = self._compute_global_variance(A_n, B_n)

            global_mean_results.append(mean_n)
            global_variance_results.append(variance_n)

            first_order_results.append(
                self._compute_first_order(
                    A_n,
                    B_n,
                    AB_n,
                    variance=variance_n,
                )
            )

            total_order_results.append(
                self._compute_total_order(
                    A_n,
                    AB_n,
                    variance=variance_n,
                )
            )

        global_variance_results = np.stack(global_variance_results, axis=0)

        return {
            "sample_sizes": sample_sizes,
            "global_mean": np.stack(global_mean_results, axis=0),
            "global_variance": global_variance_results,
            "global_std_dev": np.sqrt(global_variance_results),
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
        ) * self.global_variance

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


    @property
    def sampling_method(self):
        """Sampling method used by this analysis."""
        return "pick-freeze"


    @property
    def primary_ensemble(self):
        """Primary ensemble used to define the output distribution."""
        return "A"


    @property
    def first_order_estimator(self):
        """
        First-order Sobol estimator used by this analysis.

        The estimator is the covariance-form Saltelli estimator,
        using A as the primary ensemble and AB_i = (B_i, A_-i).
        """
        return "Saltelli"


    @property
    def total_order_estimator(self):
        """
        Total-order Sobol estimator used by this analysis.

        The estimator is the Jansen total-order estimator, using
        A as the primary ensemble and AB_i = (B_i, A_-i).
        """
        return "Jansen"


    def sampling_summary(self):
        """
        Summary on checks the consistency of the pick-freeze sampling ensembles.

        The analysis assumes each AB_i ensemble is constructed according to

            AB_i = (B_i, A_-i).

        Returns
        -------
        dict
            Dictionary containing the sampling dimensions and validation
            results.

        Raises
        ------
        ValueError
            If the A, B, and AB ensembles have incompatible shapes.
        """
        A = np.asarray(self.tally.A)
        B = np.asarray(self.tally.B)
        AB = np.asarray(self.tally.AB)

        if A.ndim < 1:
            raise ValueError(
                "The A ensemble must have at least one dimension."
            )

        if B.ndim != A.ndim:
            raise ValueError(
                "A and B ensembles must have the same number of dimensions."
            )

        if B.shape != A.shape:
            raise ValueError(
                "A and B ensembles must have identical shapes."
            )

        if AB.ndim != A.ndim + 1:
            raise ValueError(
                "The AB ensemble must have one additional leading "
                "dimension for perturbations."
            )

        if AB.shape[1:] != A.shape:
            raise ValueError(
                "Each AB perturbation ensemble must have the same shape "
                "as the A ensemble."
            )

        n_realizations = A.shape[0]
        n_perturbations = AB.shape[0]

        if n_realizations < 2:
            raise ValueError(
                "At least two realizations are required for variance "
                "and Sobol estimates."
            )

        return {
            "valid": True,
            "sampling_method": self.sampling_method,
            "primary_ensemble": self.primary_ensemble,
            "n_realizations": n_realizations,
            "n_perturbations": n_perturbations,
            "A_shape": A.shape,
            "B_shape": B.shape,
            "AB_shape": AB.shape,
        }

    def transport_noise_diagnostic(self):
        """
        Compare average per-run OpenMC tally variance with observed
        pick-freeze response variance.

        The per-run OpenMC variance is estimated as ``mc_std**2``. The
        pooled transport variance averages this quantity over all A, B,
        and AB calculations. The denominator is the observed response
        variance estimated from pooled A and B response ensembles.

        Returns
        -------
        dict
            Arrays with the tally dimensions retained:

            ``A_mc_variance``, ``B_mc_variance``, ``AB_mc_variance``
                Mean per-run transport variance within each ensemble.

            ``mean_mc_variance``
                Mean per-run transport variance pooled over A, B, and all
                AB ensembles.

            ``global_variance``
                Observed response variance from pooled A and B ensembles.

            ``noise_ratio``
                ``mean_mc_variance / global_variance`` as a fraction.

            ``noise_ratio_percent``
                The same ratio expressed as a percentage.

        Notes
        -----
        This is a screening diagnostic, not a correction to the Sobol'
        indices. The observed A+B variance includes transport noise.
        """
        A_mc_std = self.tally.A_mc_std
        B_mc_std = self.tally.B_mc_std
        AB_mc_std = self.tally.AB_mc_std

        if A_mc_std is None or B_mc_std is None or AB_mc_std is None:
            raise ValueError(
                "Transport-noise diagnostic requires mc_std data for "
                "the A, B, and AB ensembles."
            )

        A_mc_std = np.asarray(A_mc_std, dtype=float)
        B_mc_std = np.asarray(B_mc_std, dtype=float)
        AB_mc_std = np.asarray(AB_mc_std, dtype=float)

        if A_mc_std.ndim < 1:
            raise ValueError("A mc_std data must have a realization dimension.")

        if B_mc_std.shape != A_mc_std.shape:
            raise ValueError(
                "A and B mc_std ensembles must have the same shape."
            )

        if AB_mc_std.ndim != A_mc_std.ndim + 1:
            raise ValueError(
                "AB mc_std must have one additional leading dimension "
                "for perturbations."
            )

        if AB_mc_std.shape[1:] != A_mc_std.shape:
            raise ValueError(
                "Each AB mc_std ensemble must match the A/B ensemble shape."
            )

        # Average squared per-run transport uncertainty, retaining tally dims.
        A_mc_variance = np.mean(A_mc_std**2, axis=0)
        B_mc_variance = np.mean(B_mc_std**2, axis=0)
        AB_mc_variance = np.mean(AB_mc_std**2, axis=(0, 1))

        n_inputs = AB_mc_std.shape[0]

        # All ensembles contain the same number of runs, so each contributes
        # equally to the pooled mean over (p + 2) * r calculations.
        mean_mc_variance = (
            A_mc_variance + B_mc_variance + n_inputs * AB_mc_variance
        ) / (n_inputs + 2)

        global_variance = np.asarray(self.global_variance, dtype=float)

        noise_ratio = np.divide(
            mean_mc_variance,
            global_variance,
            out=np.full_like(global_variance, np.nan, dtype=float),
            where=global_variance > 0,
        )

        return {
            "A_mc_variance": A_mc_variance,
            "B_mc_variance": B_mc_variance,
            "AB_mc_variance": AB_mc_variance,
            "mean_mc_variance": mean_mc_variance,
            "global_variance": global_variance,
            "noise_ratio": noise_ratio,
            "noise_ratio_percent": 100.0 * noise_ratio,
        }