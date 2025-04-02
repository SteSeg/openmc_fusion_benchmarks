
import os
import yaml
from jsonschema import Draft7Validator, RefResolver
from jsonschema.exceptions import ValidationError
from openapi_schema_validator import OAS30Validator

# Path to the OpenAPI file
openapi_path = "src/openmc_fusion_benchmarks/benchmarks/benchmark_schema.yaml"

# Load the full OpenAPI schema
with open(openapi_path, "r") as f:
    openapi_schema = yaml.safe_load(f)

# Validate OpenAPI schema itself
OAS30Validator(openapi_schema).validate(openapi_schema)

# Create a resolver to allow $ref to work with internal references
resolver = RefResolver.from_schema(openapi_schema)

# Get schema components for validation
benchmark_schema = openapi_schema["components"]["schemas"]["Benchmark"]
metadata_schema = openapi_schema["components"]["schemas"]["Metadata"]
materials_schema = openapi_schema["components"]["schemas"]["Materials"]

# Create validators
benchmark_validator = Draft7Validator(benchmark_schema, resolver=resolver)
metadata_validator = Draft7Validator(metadata_schema, resolver=resolver)
materials_validator = Draft7Validator(materials_schema, resolver=resolver)

# Path to the benchmarks
benchmarks_dir = "src/openmc_fusion_benchmarks/benchmarks"

# Loop through each benchmark file
for folder in os.listdir(benchmarks_dir):
    path = os.path.join(benchmarks_dir, folder, "specifications.yaml")
    if not os.path.isfile(path):
        continue

    print(f"\n🔍 Validating benchmark file: {folder}")

    with open(path, "r") as f:
        benchmark_data = yaml.safe_load(f)

    # Validate the full benchmark
    errors = sorted(benchmark_validator.iter_errors(
        benchmark_data), key=lambda e: e.path)

    # Validate individual submodules
    if "metadata" in benchmark_data:
        metadata_errors = sorted(metadata_validator.iter_errors(
            benchmark_data["metadata"]), key=lambda e: e.path)
        errors.extend(metadata_errors)

    if "materials" in benchmark_data:
        # Ensure materials is a list
        if not isinstance(benchmark_data["materials"], list):
            errors.append(ValidationError(
                "Materials should be an array, but got a different type."))

        # Validate materials one by one
        for i, material in enumerate(benchmark_data["materials"]):
            material_errors = sorted(materials_validator.iter_errors(
                material), key=lambda e: e.path)
            errors.extend(material_errors)

    # Print errors
    if errors:
        print(f"❌ {len(errors)} errors found in {folder}:")
        for error in errors:
            print(f"   - {error.message} (at {list(error.path)})")
    else:
        print(f"✅ {folder} is valid!")
