from fileinput import filename
import numpy as np
import openmc
from pathlib import Path
import xarray as xr
import pydagmc
import h5py


def _openmc_to_ofb(spec_tallies: str, statepoint: openmc.StatePoint,
                   mesh: str = 'mesh.h5m', realization_label: str = 'baseline'):

    # Read openmc statepoint file
    # sp = openmc.StatePoint(statepoint)
    # Read mesh file
    msh = pydagmc.Model(mesh)

    # Cycle tallies in specifications
    for spec_t in spec_tallies:
        # Get corresponding tally from statepoint
        df = statepoint.get_tally(name=spec_t['name']).get_pandas_dataframe()

        # Preparing tally dataframe
        df = df.drop(columns=['surface', 'cell', 'particle', 'nuclide',
                              'score', 'energyfunction'], errors='ignore')
        # Cycle tally filters
        for f in spec_t['filters']:
            if f['type'] == 'cell':
                # Get cell volumes for normalization
                norm = [msh.volumes_by_id[v].volume for v in f['values']]
            elif f['type'] == 'surface':
                # Get surface areas for normalization
                norm = [msh.surfaces_by_id[v].area for v in f['values']]
            elif f['type'] == 'material':
                raise NotImplementedError(
                    'Material filter not implemented in postprocess yet.')
            else:
                norm = 1

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

        # Save the tally data to a netCDF file
        _save_result(new_result=t, filename="benchmark_results.h5",
                     group=spec_t['name'], realization_label=realization_label)


def _save_result(new_result: xr.DataArray, filename: str, group: str, realization_label: str):
    """Save or append a DataArray to a NetCDF file under a given group,
    extending along the 'realization' dimension if present."""

    # Path to filename
    path = Path(filename)

    if not path.exists():
        # First time -> create file with this group
        new_result.to_netcdf(
            path, mode="w", engine="netcdf4", group=group)
        new_result = new_result.assign_coords(
            realization=new_result.realization.astype(object))
        print(f"Created file '{filename}' with group '{group}'")
        return

    # File exists -> try to read & merge
    try:
        with xr.open_dataset(path, group=group, engine="netcdf4") as existing:
            existing_da = xr.load_dataarray(path, group=group)
            existing_da = existing_da.assign_coords(
                realization=existing_da.realization.astype(object))

            # Align coords explicitly so realization labels don’t clash
            combined = xr.concat([existing_da, new_result], dim="realization")
    except (OSError, ValueError):
        # Group missing or bad -> just use new_result
        combined = new_result

    # Save back (overwrite only this group)
    with h5py.File(path, "a") as f:
        if group in f:
            del f[group]
    combined.to_netcdf(
        path, mode="a", engine="netcdf4", group=group)
    print(
        f"Updated group '{group}' in '{filename}' with realization '{realization_label}'")
    return
