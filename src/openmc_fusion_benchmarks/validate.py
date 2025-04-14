# import yaml
# from jsonschema import Draft202012Validator
# from referencing import Registry
# from pathlib import Path


# def validate_benchmark(benchmark_name: str):
#     print(f"\n🔍 Validating benchmark file: {benchmark_name}")

#     base_path = Path("src/openmc_fusion_benchmarks/benchmarks")
#     schema_path = base_path / "benchmark_schema.yaml"
#     benchmark_path = base_path / benchmark_name / "specifications.yaml"

#     if not benchmark_path.is_file():
#         raise FileNotFoundError(f"Benchmark file {benchmark_path} not found.")

#     # Load the schema
#     with schema_path.open("r") as schema_file:
#         schema = yaml.safe_load(schema_file)

#     # Ensure the schema has an $id
#     schema_id = schema.get(
#         "$id", "https://openmc-fusion/schemas/benchmark_schema")

#     # Create a registry and register the schema
#     registry = Registry().with_resource(schema_id, schema)

#     # Load the benchmark YAML
#     with benchmark_path.open("r") as yaml_file:
#         yaml_data = yaml.safe_load(yaml_file)

#     # Create validator with the schema and registry
#     validator = Draft202012Validator(schema, registry=registry)

#     # Perform validation
#     errors = sorted(validator.iter_errors(yaml_data), key=lambda e: e.path)
#     if errors:
#         print(f"❌ {len(errors)} validation error(s) in {benchmark_name}:")
#         for error in errors:
#             print(f"   - {error.message} (at {list(error.path)})")
#         raise ValueError("Validation failed.")
#     else:
#         print(f"✅ {benchmark_name} is valid!")


import yaml
import jsonschema
from referencing import Registry, Resource
from pathlib import Path


def validate_benchmark(benchmark_name: str):

    print(f"\n🔍 Validating benchmark file: {benchmark_name}")

    base_path = Path("src/openmc_fusion_benchmarks/benchmarks")
    schema_path = base_path / "benchmark_schema.yaml"
    benchmark_path = base_path / benchmark_name / "specifications.yaml"

    if not benchmark_path.is_file():
        raise FileNotFoundError(f"Benchmark file {benchmark_path} not found.")

    # Load the schema
    with schema_path.open("r") as schema_file:
        schema = yaml.safe_load(schema_file)

    # Create a registry and register the schema
    registry = Registry().with_resources(
        [(schema.get("$id", "benchmark_schema"), schema)])

    # CHANGED: Wrap the schema in a Resource and use the referencing registry
    schema_id = schema.get(
        "$id", "https://openmc-fusion/schemas/benchmark_schema")  # <-- CHANGED
    registry = Registry().with_resources(
        [(schema_id, Resource.from_contents(schema))])  # <-- CHANGED

    # Load the YAML file to validate
    with open(benchmark_path, "r") as yaml_file:
        yaml_data = yaml.safe_load(yaml_file)

    # CHANGED: Use jsonschema 2020-12 validator with registry
    validator_cls = jsonschema.validators.validator_for(schema)  # <-- ADDED
    validator_cls.check_schema(schema)                           # <-- ADDED
    validator = validator_cls(schema, registry=registry)         # <-- CHANGED

    # Validate the YAML file
    errors = sorted(validator.iter_errors(yaml_data), key=lambda e: e.path)

    # Print errors
    if errors:
        print(f"❌ {len(errors)} errors found in {benchmark_name}:")
        for error in errors:
            print(f"   - {error.message} (at {list(error.path)})")
    else:
        print(f"✅ {benchmark_name} is valid!")
