from typing import List, Callable
from pathlib import Path
import openmc
import numpy as np
import xarray as xr


class TMCManager:
    def __init__(self, base_model: openmc.Model, perturbations: List[Callable],
                  n_samples, rng:np.random._generator.Generator=None):
        self.base_model = base_model
        self.perturbations = perturbations
        self.n_samples = n_samples
        self.results = []

        # Example of setting rng for reproducibility
        if rng is None:
            self.rng = np.random.default_rng()
        else:
            self.rng = rng

    def run(self, cwd='.', *args, **kwargs):

        tmc_statepoint = Path(cwd) / "tmc_statepoint.h5"

        for i,p in enumerate(self.perturbations):
            for n in range(self.n_samples):
                perturbed_model = p(self.base_model, rng=self.rng)
                # build the cwd/tmc/perturbation/ path
                pert_cwd = Path(cwd) / "tmc" / f"perturbation_{i}" / f"sample_{n}"
                sp_path = perturbed_model.run(cwd=pert_cwd, *args, **kwargs)
                # store in the manager the sp_path info to build results path structure

                # Save results in tmc_statepoint
                sp = openmc.StatePoint(sp_path)
                # open tally and push to netcdf ofb style
                for t in sp.tallies:
                    tally = sp.get_tally(id=t)
                    df = tally.get_pandas_dataframe()

                    # df = df.drop(columns=['surface', 'cell', 'particle', 'nuclide',
                    #             'score', 'energyfunction'], errors='ignore')

                    # Convert to xarray and add dimensions
                    da = xr.DataArray(
                        df.values[np.newaxis, :, :],  # shape: (1, r, c)
                        dims=["realization", "row", "column"],
                        coords={
                            "realization": [realization_label],
                            "column": df.columns,
                            "row": np.arange(df.shape[0]),
                        },
                        name=tally.name
                    )

    def _extract_results(self):
        pass