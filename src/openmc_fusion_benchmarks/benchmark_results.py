import h5py
import xarray as xr
import numpy as np


class BenchmarkResults:
    def __init__(self, filepath: str):
        self.filepath = filepath

    @property
    def tallies(self):
        with h5py.File(self.filepath, 'r') as f:
            tallies = list(f.keys())
        return tallies

    def get_tally(self, name: str) -> xr.DataArray:
        return xr.load_dataarray(self.filepath, group=name)
    

# # Some utilities for data analysis
# def get_means(tally: xr.DataArray) -> xr.DataArray:
#     """Extract tally means from the tally DataArray."""
#     return tally.sel(column='mean').squeeze()

# def get_stds(tally: xr.DataArray) -> xr.DataArray:
#     """Extract tally standard deviations from the tally DataArray."""
#     return tally.sel(column='std. dev.').squeeze()

# def get_rstds(tally: xr.DataArray) -> xr.DataArray:
#     """Compute tally relative standard deviations from the tally DataArray."""
#     mean_vals = get_means(tally)
#     std_vals = get_stds(tally)
#     return std_vals / mean_vals


# # UQ-TMC base analysis functions - Move in uq/ ?
# def mean_of_means(tally: xr.DataArray) -> xr.DataArray:
#     """Compute the mean of the means across realizations."""
#     means = get_means(tally)
#     return means.mean(dim='realization')

# def std_of_means(tally: xr.DataArray) -> xr.DataArray:
#     """Compute the standard deviation of the means across realizations."""
#     means = get_means(tally)
#     return means.std(dim='realization')

# def rstd_of_means(tally: xr.DataArray) -> xr.DataArray:
#     """Compute the relative standard deviation of the means across realizations."""
#     mean_vals = mean_of_means(tally)
#     std_vals = std_of_means(tally)
#     return std_vals / mean_vals

# # UQ-TMC dynamic realization analysis functions - Move in uq/ ?
# def dynamic_mean_of_means(tally: xr.DataArray) -> np.ndarray:
#     """Compute the dynamic mean of the means across realizations."""
#     means = get_means(tally)
#     return np.array([means[:i].mean(dim='realization') for i in range(2, len(means.realization) + 1)])

# def dynamic_std_of_means(tally: xr.DataArray) -> np.ndarray:
#     """Compute the dynamic standard deviation of the means across realizations."""
#     means = get_means(tally)
#     return np.array([
#         means[:i].std(dim='realization') for i in range(2, len(means.realization) + 1)
#     ])

# def dynamic_rstd_of_means(tally: xr.DataArray) -> np.ndarray:
#     """Compute the dynamic relative standard deviation of the means across realizations."""
#     means = get_means(tally)
#     return np.array([
#         means[:i].std(dim='realization') / means[:i].mean(dim='realization')
#         for i in range(2, len(means.realization) + 1)
#     ])

# def dynamic_rstd_of_rstds(tally: xr.DataArray) -> np.ndarray:
#     """Compute the dynamic relative standard deviation of the relative standard deviations across realizations."""
#     rstds = dynamic_rstd_of_means(tally)
#     return np.array([
#         rstds[:i].std() / rstds[:i].mean() for i in range(2, len(rstds) + 1)
#     ])

# def derivative_of_dynamic_rstds(tally: xr.DataArray) -> np.ndarray:
#     """Compute the derivative of the dynamic relative standard deviations."""
#     dynamic_rstds = dynamic_rstd_of_means(tally)
#     return np.gradient(dynamic_rstds, axis=0)