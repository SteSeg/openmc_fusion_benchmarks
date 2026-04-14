from __future__ import annotations

import json

import numpy as np
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

class Tally(BaseTally):
	"""Generic OFB tally wrapper for non-TMC result groups."""

	def __repr__(self):
		return f"<Tally {self.id}: '{self.name}', shape={self.shape}>"

def tally_to_dataset(*args, **kwargs):
	"""Backward-compatible alias to the OpenMC backend serializer."""
	from .backends.openmc.tallies import openmc_tally_to_dataset

	return openmc_tally_to_dataset(*args, **kwargs)


def save_statepoint_tallies(*args, **kwargs):
	"""Backward-compatible alias to the OpenMC backend statepoint writer."""
	from .backends.openmc.tallies import save_openmc_statepoint_tallies

	return save_openmc_statepoint_tallies(*args, **kwargs)
