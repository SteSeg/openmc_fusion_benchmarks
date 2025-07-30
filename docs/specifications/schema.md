# Benchmark Schema

The OpenMC Fusion Benchmarks (OFB) project uses a modular, schema-driven format to ensure that all benchmark `specifications` follow a consistent, machine-validated structure.

## Validation

Validation can be performed anually using the OFB Python API:

```python
import openmc_fusion_benchmarks as ofb

ofb.validate_benchmark('benchmark_name')
```

Alternatively, you can run the `validate_all_benchmarks.py` script located in the repository’s `scripts/` folder. This script iterates through all benchmark `specifications.yaml` files and validates them against the repository’s `benchmark_schema`.

Validation output looks like:

```shell
🔍 Validating benchmark file: benchmark_name
✅ benchmark_name is valid!
```

Or in case of validation errors:

```shell
🔍 Validating benchmark file: oktavian_al
❌ 1 errors found in oktavian_al:
   - None is not of type 'object' (at ['materials', 1, 'composition', 'data'])
```

In the example above, the material with `id` 1 is missing a defined composition.

Validation is also automatically triggered when instantiating a `benchmark` object:

```python
import openmc_fusion_benchmarks as ofb

benchmark = ofb.OpenmcBenchmark(name='benchmark_name')
```
```shell
🔍 Validating benchmark file: benchmark_name
✅ benchmark_name is valid!
```

## Purpose of the Schema

To guarantee interoperability and automation, each `specifications.yaml` file must conform to a predefined [JSON Schema](https://json-schema.org/). This enables:

- **Automatic validation** of input files
- **Improved error reporting** for malformed benchmarks
- **Robust tooling** for model generation and testing
- **Future extensibility** of the specification format

## Schema-to-Specifications Mapping

The `benchmark_schema` defines _sections_ of the `specifications`:

```yaml
$ref: "#/components/schemas/Benchmark"
components:
  schemas:
    Benchmark:
      type: object
      required: 
        - metadata
        - materials
        - geometry
        - sources
        - settings
        - tallies
      properties:
        metadata:
          $ref: '#/components/schemas/Metadata'
        materials:
          type: array
          items:
            $ref: '#/components/schemas/Material'
        ...
```

Some of them can be optional:

```yaml
        ...
        irradiation_schedule:
          $ref: '#/components/schemas/IrradiationSchedule'
        uncertainty_quantification:
          $ref: '#/components/schemas/UncertaintyQuantification'
```

The `schema` defines also object _structure_ and _type_ in a hierarchical fashion:

```yaml
Tally:
  type: object
  required: [name, particle, filters, scores]
  properties:
    name: 
      type: string
      ...
    particle:
      type: string
      enum: [neutron, photon, electron, positron]
    filters:
      type: array
      items:
        type: object
        required: [type, values]
    ...
```

Each section in a benchmark’s `specifications.yaml` file is validated against the corresponding part of the unified `benchmark_schema.yaml`. 


For example, for a material `density` object that in the `specifications` looks like this:
```yaml
density:
    value: 0.997
    units: g/cm3
```

The corresponding `schema` is defined like this:

```yaml
density:
  type: object
  properties:
    value:
      type: number
    units:
      type: string
      enum: [g/cm3]
  required: [value, units]
```

And for a whole `material` object in the list of `materials` in the `specifications`:

```yaml
- id: 1
  name: Water
  composition:
      composition_type: element
      fraction_type: atomic
      data:
      H: 0.67
      O: 0.33
  density:
      value: 0.997
      units: g/cm3
```

The corresponding definition in the `schema` looks like this:

```yaml
Material:
  type: object
  required: [id, name, composition, density]
  properties:
    id:
      type: integer
    name:
      type: string
    composition:
      type: object
      properties:
        composition_type:
          type: string
        fraction_type:
          type: string
          enum: [atomic, weight]
        data:
          type: object
          additionalProperties:
            type: number
      required: [composition_type, fraction_type, data]
    density:
      ...
```

## Unified Schema Format

The OFB schema is a **single, unified JSON Schema file** that defines the complete structure of a valid `specifications.yaml` file. It includes all top-level sections—such as `metadata`, `geometry`, `materials`, `source`, `tallies`, and others—and their corresponding nested fields.

Although the schema is written modularly (with subschemas for each section), it is maintained as **one file** for simplicity, validation consistency, and ease of distribution.