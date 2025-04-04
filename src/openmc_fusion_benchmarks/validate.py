import yaml
import jsonschema
from referencing import Registry
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

    # Load the YAML file to validate
    with open(benchmark_path, "r") as yaml_file:
        yaml_data = yaml.safe_load(yaml_file)

    # Validate the YAML file
    validator = jsonschema.Draft7Validator(schema, registry=registry)
    errors = sorted(validator.iter_errors(yaml_data), key=lambda e: e.path)

    if errors:
        for error in errors:
            print(f"Validation Error: {error.message} at {list(error.path)}")
        raise jsonschema.exceptions.ValidationError("YAML validation failed.")

    # Print errors
    if errors:
        print(f"❌ {len(errors)} errors found in {benchmark_name}:")
        for error in errors:
            print(f"   - {error.message} (at {list(error.path)})")
    else:
        print(f"✅ {benchmark_name} is valid!")
