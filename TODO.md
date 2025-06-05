# To do
### Manage CAD geometry


## Benchmarks API
- Add capability of merging multiple surface results for oktavian (should happen only with surface tallies)
- Add expected tally results shape in `schema` and `specifications` to deal with the point here above
- Try to manage results as numpy arrays instead of pandas dataframes in `OpenmcBenchmark.postprocess()`
- Should we use `h5netcdf` engine for saving/opening datasets in `h5` files or stick with the default `netcdf4`?
- Do we wanna use `makefun` decorator for wrapped methods (e.g. `OpenmcBenchmark.run()`)?

## Tests
- Add tests to everything

## Notebooks
- Use `specifications` validation against `schema`  function and script
- Open and inspect a `specifications` file (just `metadata`)
- Instantiate an `OpenmcBenchmark` object, build model, run simulation
- Postprocessing and visualization

## Documentation
- introduction and motivation
- V&V explanation
- Definition of benchmark `specifications`
- Benchmarks
    - Oktavian description
    - Oktavian results

## Miscellanea

## Questions