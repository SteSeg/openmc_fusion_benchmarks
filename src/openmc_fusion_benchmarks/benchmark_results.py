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
    

# ResultArray class maybe not necessary, leaving it as xarray.DataArray for now:
# 1 list the labels of any dimension (e.g. realization, column, row etc.): da.realization.values
# 2 select a slice of the data: slice2d = da.sel(realization='label1')
# 3 get a pandas dataframe from a slice (if the slice is 2D): df = slice2d.to_pandas()
# 4 Further slice down to 1d: slice1d = slice2d.sel(column='mean')


class ResultArray:
    def __init__(self, data: xr.DataArray):
        self.data = data

    @property
    def realizations(self):
        return self.data.realization.values

    @property
    def rows(self):
        return self.data.row.values

    @property
    def columns(self):
        return self.data.column.values

    def get_realization(self, label) -> xr.DataArray:
        return self.data.sel(realization=label)
    
    def get_row(self, index) -> xr.DataArray:
        return self.data.sel(row=index)
    
    def get_column(self, name) -> xr.DataArray:
        return self.data.sel(column=name)

    def mean_of_stds(self) -> np.ndarray:
        std_da = self.get_column('std. dev.')
        return std_da.values.mean(axis=0)
    
    def mean_of_rstds(self) -> np.ndarray:
        mean_da = self.get_column('mean')
        std_da = self.get_column('std. dev.')
        rstd = std_da.values / mean_da.values
        return rstd.mean(axis=0)

    def mean_of_means(self) -> np.ndarray:
        mean_da = self.get_column('mean')
        return mean_da.values.mean(axis=0)
    
    def std_of_means(self) -> np.ndarray:
        mean_da = self.get_column('mean')
        return mean_da.values.std(axis=0)
    
    def evolution_of_means(self) -> np.ndarray:
        mean_da = self.get_column('mean')
        return np.cumsum(mean_da.values, axis=0) / np.arange(1, len(mean_da.values)+1)[:, None]