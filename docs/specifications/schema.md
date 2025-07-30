# Benchmark Schema

The OpenMC Fusion Benchmarks (OFB) project uses a modular, schema-driven format to ensure that all benchmark specifications follow a consistent, machine-validated structure.

## Purpose of the Schema

To guarantee interoperability and automation, each `specifications.yaml` file must conform to a predefined [JSON Schema](https://json-schema.org/). This enables:

- **Automatic validation** of input files
- **Improved error reporting** for malformed benchmarks
- **Robust tooling** for model generation and testing
- **Future extensibility** of the specification format

## Unified Schema Format

The OFB schema is a **single, unified JSON Schema file** that defines the complete structure of a valid `specifications.yaml` file. It includes all top-level sections—such as `metadata`, `geometry`, `materials`, `source`, `tallies`, and others—and their corresponding nested fields.

Although the schema is written modularly (with subschemas for each section), it is maintained as **one file** for simplicity, validation consistency, and ease of distribution.

## Validation

Validation can be performed using the OFB Python API:

```python
from ofb.schema import validate_specifications

validate_specifications("my_benchmark/specifications.yaml")