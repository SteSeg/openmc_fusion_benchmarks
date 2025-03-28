import os
import yaml
from jsonschema import RefResolver, Draft7Validator
from openapi_schema_validator import OAS30Validator

# Path to the OpenAPI file
openapi_path = "src/openmc_fusion_benchmarks/benchmarks/openapi.yaml"

# Load the full OpenAPI schema
with open(openapi_path, "r") as f:
    openapi_schema = yaml.safe_load(f)

# Validate OpenAPI schema itself
OAS30Validator(openapi_schema).validate(openapi_schema)

# Get the Benchmark schema from components
benchmark_schema = openapi_schema["components"]["schemas"]["Benchmark"]

# Create a resolver to allow $ref to work with internal references
resolver = RefResolver.from_schema(openapi_schema)

# Create a validator for the benchmark schema with the resolver
validator = Draft7Validator(benchmark_schema, resolver=resolver)

# Path to the benchmarks
benchmarks_dir = "src/openmc_fusion_benchmarks/benchmarks"

# Loop through each benchmark
for folder in os.listdir(benchmarks_dir):
    path = os.path.join(benchmarks_dir, folder, "benchmark_specs.yaml")
    if not os.path.isfile(path):
        continue

    print(f"\n🔍 Validating benchmark file: {folder}")

    with open(path, "r") as f:
        benchmark_data = yaml.safe_load(f)

    # Validate
    errors = sorted(validator.iter_errors(
        benchmark_data), key=lambda e: e.path)

    if not errors:
        print("✅ Benchmark file is valid.")
    else:
        print("❌ Benchmark file is invalid.")
        for error in errors:
            loc = " -> ".join([str(p) for p in error.path])
            print(f" - {loc}: {error.message}")
