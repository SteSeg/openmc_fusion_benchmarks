from __future__ import annotations

from pathlib import Path
from typing import Callable, Iterable
import json

import h5py
import numpy as np
import openmc
import xarray as xr


class BaseTally:
	"""Common wrapper for structured tally datasets."""

	def __init__(self, mean_da: xr.DataArray, mc_std_da: xr.DataArray | None = None, parent_ds: xr.Dataset | None = None):
		self._da = mean_da
		self._da_mc_std = mc_std_da
		self._parent_ds = parent_ds

	@property
	def id(self):
		"""Tally ID."""
		return self._da.attrs.get("tally_id")

	@property
	def name(self):
		"""Tally name."""
		return self._da.attrs.get("tally_name")

	@property
	def data(self):
		"""Underlying mean data array values."""
		return self._da.values

	@property
	def scores(self):
		"""List of score names."""
		if "score" in self._da.coords:
			return [str(s) for s in self._da.coords["score"].values]

		if self._parent_ds is not None:
			scores_json = self._parent_ds.attrs.get("scores")
			if scores_json:
				return json.loads(scores_json)

		scores_json = self._da.attrs.get("scores")
		if scores_json:
			return json.loads(scores_json)
		return []

	@property
	def nuclides(self):
		"""List of nuclide names."""
		if "nuclide" in self._da.coords:
			return [str(n) for n in self._da.coords["nuclide"].values]

		if self._parent_ds is not None:
			nuclides_json = self._parent_ds.attrs.get("nuclides")
			if nuclides_json:
				return json.loads(nuclides_json)

		nuclides_json = self._da.attrs.get("nuclides")
		if nuclides_json:
			return json.loads(nuclides_json)
		return []

	@property
	def filters(self):
		"""List of filter metadata entries."""
		if self._parent_ds is not None:
			filt_json = self._parent_ds.attrs.get("filter_axes")
			if filt_json:
				return json.loads(filt_json)

		filt_json = self._da.attrs.get("filter_axes")
		if filt_json:
			return json.loads(filt_json)
		return []

	@property
	def shape(self):
		"""Shape of the underlying mean data array."""
		return self._da.shape

	@property
	def dims(self):
		"""Dimension names of the underlying mean data array."""
		return self._da.dims

	@property
	def mean(self):
		"""Mean array for non-TMC tallies (already the final mean)."""
		return self._da.values

	@property
	def std_dev(self):
		"""MC standard deviation array for non-TMC tallies."""
		if self._da_mc_std is not None:
			return self._da_mc_std.values
		return np.zeros_like(self._da.values)

	def get_slice(self, scores=None, nuclides=None, **filter_kwargs):
		"""Get a filtered xarray view of the mean tally data."""
		da = self._da

		if filter_kwargs:
			da = da.sel(**filter_kwargs)

		if scores is not None and "score" in da.dims:
			all_scores = self.scores
			score_indices = [all_scores.index(s) for s in scores]
			da = da.isel(score=score_indices)

		if nuclides is not None and "nuclide" in da.dims:
			all_nuclides = self.nuclides
			nuclide_indices = [all_nuclides.index(n) for n in nuclides]
			da = da.isel(nuclide=nuclide_indices)

		return da


class BenchmarkTally(BaseTally):
	"""Wrapper for benchmark/non-TMC tally groups."""

	def __repr__(self):
		return f"<BenchmarkTally {self.id}: '{self.name}', shape={self.shape}>"


def _unique_filter_dims(filters: list[openmc.Filter]) -> list[str]:
	"""Build stable, unique filter dimension names."""
	counts: dict[str, int] = {}
	dims: list[str] = []
	for flt in filters:
		base = type(flt).__name__.replace("Filter", "").lower() or "filter"
		idx = counts.get(base, 0)
		counts[base] = idx + 1
		dims.append(base if idx == 0 else f"{base}_{idx}")
	return dims


def _to_1d_coord(values) -> np.ndarray:
	"""Normalize scalar/list-like coordinate input into a 1D numpy array."""
	arr = np.asarray(values)
	if arr.ndim == 0:
		arr = arr.reshape(1)
	return arr


def tally_to_dataset(
	tally: openmc.Tally,
	tmc_coords: dict[str, Iterable] | None = None,
	normalizer: Callable[[openmc.Tally, np.ndarray, np.ndarray], tuple[np.ndarray, np.ndarray]] | None = None,
) -> xr.Dataset:
	"""
	Convert one OpenMC tally into an xarray Dataset with variables `mean` and `mc_std`.

	The output schema mirrors the one used in `uq/tmc_manager.py`:
	dimensions are `(tmc dims..., filter dims..., nuclide, score)` and metadata
	is stored in dataset attrs (`filter_axes`, `nuclides`, `scores`).
	"""
	tmc_coords = tmc_coords or {}

	filters = list(tally.filters)
	filter_bins = [f.num_bins for f in filters]
	n_nuclides = max(len(tally.nuclides), 1)
	n_scores = len(tally.scores)
	nd_shape = tuple(filter_bins) + (n_nuclides, n_scores)

	mean_nd = tally.mean.reshape(nd_shape)
	std_nd = tally.std_dev.reshape(nd_shape)

	if normalizer is not None:
		mean_nd, std_nd = normalizer(tally, mean_nd, std_nd)

	tmc_dims = tuple(tmc_coords.keys())
	tmc_coord_arrays = {k: _to_1d_coord(v) for k, v in tmc_coords.items()}
	tmc_shape = tuple(len(v) for v in tmc_coord_arrays.values())

	full_shape = tmc_shape + nd_shape
	mean_full = mean_nd.reshape((1,) * len(tmc_shape) + nd_shape)
	std_full = std_nd.reshape((1,) * len(tmc_shape) + nd_shape)

	# Broadcast to provided TMC coordinate lengths (usually all 1 for a single write).
	mean_full = np.broadcast_to(mean_full, full_shape)
	std_full = np.broadcast_to(std_full, full_shape)

	filter_dims = _unique_filter_dims(filters)
	dims = tmc_dims + tuple(filter_dims) + ("nuclide", "score")

	coords: dict[str, tuple[str, np.ndarray] | np.ndarray] = {}
	for d, c in tmc_coord_arrays.items():
		coords[d] = (d, c)
	for f, d in zip(filters, filter_dims):
		coords[d] = (d, np.arange(f.num_bins))

	nuclides = [str(n) for n in tally.nuclides] if tally.nuclides else ["total"]
	scores = [str(s) for s in tally.scores]
	coords["nuclide"] = ("nuclide", np.asarray(nuclides, dtype="U"))
	coords["score"] = ("score", np.asarray(scores, dtype="U"))

	ds = xr.Dataset(
		{
			"mean": xr.DataArray(mean_full, dims=dims, coords=coords),
			"mc_std": xr.DataArray(std_full, dims=dims, coords=coords),
		}
	)

	tally_name = tally.name or f"tally_{tally.id}"
	ds["mean"].attrs["tally_id"] = int(tally.id)
	ds["mean"].attrs["tally_name"] = tally_name
	ds["mc_std"].attrs["tally_id"] = int(tally.id)
	ds["mc_std"].attrs["tally_name"] = tally_name

	ds.attrs["filter_axes"] = json.dumps(
		[{"name": type(f).__name__, "num_bins": int(f.num_bins)} for f in filters]
	)
	ds.attrs["nuclides"] = json.dumps(nuclides)
	ds.attrs["scores"] = json.dumps(scores)

	return ds


def save_statepoint_tallies(
	statepoint: openmc.StatePoint,
	filename: str | Path,
	tally_names: Iterable[str] | None = None,
	tmc_coords: dict[str, Iterable] | None = None,
	append_dim: str | None = None,
	normalizer: Callable[[openmc.Tally, np.ndarray, np.ndarray], tuple[np.ndarray, np.ndarray]] | None = None,
	engine: str = "h5netcdf",
) -> Path:
	"""
	Minimal universal writer for OpenMC tallies.

	Parameters
	----------
	statepoint:
		OpenMC statepoint object already loaded by caller.
	filename:
		Output HDF5/NetCDF file.
	tally_names:
		Optional tally-name filter. If omitted, all tallies are written.
	tmc_coords:
		Optional leading dimensions (for example `{"realization": ["baseline"]}` or
		matrix dims such as `{"perturbation_0": [0], "perturbation_1": [2]}`).
	append_dim:
		Optional dimension name used to append when group already exists.
	normalizer:
		Optional callback to transform `(mean_nd, std_nd)` before save.
	engine:
		Xarray engine to use (`h5netcdf` by default).
	"""
	filename = Path(filename)
	if tally_names is None:
		selected = list(statepoint.tallies.values())
	else:
		selected = [statepoint.get_tally(name=name) for name in tally_names]

	for tally in selected:
		ds_new = tally_to_dataset(
			tally=tally,
			tmc_coords=tmc_coords,
			normalizer=normalizer,
		)
		group = f"tally_{int(tally.id)}"

		if not filename.exists():
			ds_new.to_netcdf(filename, mode="w", group=group, engine=engine)
			continue

		try:
			ds_old = xr.open_dataset(filename, group=group, engine=engine)
			if append_dim is not None and append_dim in ds_old.dims and append_dim in ds_new.dims:
				ds_combined = xr.concat([ds_old, ds_new], dim=append_dim)
			else:
				ds_combined = ds_new
			ds_old.close()
		except (OSError, ValueError, KeyError):
			ds_combined = ds_new

		with h5py.File(filename, "a") as h5f:
			if group in h5f:
				del h5f[group]
		ds_combined.to_netcdf(filename, mode="a", group=group, engine=engine)

	return filename.resolve()

