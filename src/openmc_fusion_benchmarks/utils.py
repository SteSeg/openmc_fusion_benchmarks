import numpy as np
import openmc
from pathlib import Path
import xarray as xr
import pydagmc


def _openmc_to_ofb(spec_tallies: str, statepoint: str = 'statepoint.100.h5',
                   mesh: str = 'mesh.h5m', realization_label: str = 'baseline'):

    # Read openmc statepoint file
    sp = openmc.StatePoint(statepoint)
    # Read mesh file
    mesh = pydagmc.DAGModel(mesh)

    # Cycle tallies in specifications
    for spec_t in spec_tallies:
        # Get corresponding tally from statepoint
        df = sp.get_tally(name=spec_t['name']).get_pandas_dataframe()

        # Preparing tally dataframe
        df = df.drop(columns=['surface', 'cell', 'particle', 'nuclide',
                              'score', 'energyfunction'], errors='ignore')
        # Cycle tally filters
        norm = 1
        for f in spec_t['filters']:
            if f['type'] == 'cell':
                # Get cell volumes for normalization
                norm = [mesh.volumes_by_id[v].area for v in f['values']]
            elif f['type'] == 'surface':
                # Get surface areas for normalization
                norm = [mesh.surfaces_by_id[v].area for v in f['values']]
            elif f['type'] == 'material':
                raise NotImplementedError(
                    'Material filter not implemented in postprocess yet.')

            # Normalize the tally data
            df['mean'] = df['mean'] / norm
            df['std. dev.'] = df['std. dev.'] / norm

        # Convert to xarray and add dimensions
        t = xr.DataArray(
            df.values[np.newaxis, :, :],  # shape: (1, r, c)
            dims=["realization", "row", "column"],
            coords={
                "realization": [realization_label],
                "column": df.columns,
                "row": np.arange(df.shape[0]),
            },
            name=spec_t['name']
        )

        # # Save the tally data to a netCDF file
        _save_result(new_result=t, filename="benchmark_results.h5",
                     group=spec_t['name'], realization_label=realization_label)


def _save_result(new_result: xr.DataArray, filename: str, group: str, realization_label: str):
    """Append or initialize a 3D DataArray with 'realization' dimension in a NetCDF HDF5 file."""
    path = Path(filename)

    # Ensure the realization dimension exists
    if "realization" not in new_result.dims:
        new_result = new_result.expand_dims(
            {"realization": [realization_label]})
    else:
        new_result = new_result.assign_coords(realization=[realization_label])

    if not path.exists():
        # File doesn't exist: write initial result
        new_result.to_dataset(name=new_result.name).to_netcdf(
            path, mode='w', group=group)
        print(f"Saved new result to group '{group}' in '{filename}'")
    else:
        try:
            existing = xr.open_dataset(path, group=group)
            existing_da = existing.to_array().squeeze("variable", drop=True)

            # Concatenate along realization dimension
            combined = xr.concat([existing_da, new_result], dim="realization")

            # Save the combined array back
            combined.to_dataset(name=new_result.name).to_netcdf(
                path, mode='a', group=group)
            print(
                f"Appended realization '{realization_label}' to group '{group}' in '{filename}'")

        except KeyError:
            # Group does not exist yet
            new_result.to_dataset(name=new_result.name).to_netcdf(
                path, mode='a', group=group)
            print(f"Saved new result to new group '{group}' in '{filename}'")
