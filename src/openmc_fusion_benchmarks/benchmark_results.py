import h5py
import xarray as xr


class BenchmarkResults:
    def __init__(self, filepath: str):
        self.filepath = filepath

    @property
    def tallies(self):
        with h5py.File(self.filepath, 'r') as f:
            tallies = list(f['tallies'].keys())
        return tallies

    def get_tally(self, tally_name: str) -> xr.DataArray:
        return xr.load_dataarray(self.filepath, group=tally_name, engine="netcdf4")