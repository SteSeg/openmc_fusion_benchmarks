import pytest
import jsonschema
import yaml
from unittest.mock import patch, mock_open, MagicMock
from pathlib import Path
from openmc_fusion_benchmarks import validate_benchmark


@pytest.fixture
def mock_schema():
    """Returns a mock schema for validation."""
    return {
        "$id": "benchmark_schema",
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "materials": {"type": "array"},
        },
        "required": ["name", "materials"]
    }


@pytest.fixture
def valid_yaml():
    """Returns a valid benchmark YAML content."""
    return """
    name: "Benchmark A"
    materials:
      - material_id: 1
        name: "Steel"
    """


@pytest.fixture
def invalid_yaml():
    """Returns an invalid YAML (missing required field 'materials')."""
    return """
    name: "Benchmark A"
    """


@pytest.fixture
def invalid_format_yaml():
    """Returns a YAML with incorrect syntax."""
    return """
    name: "Benchmark A"
    materials:
      - material_id: 1
        name: "Steel"
      - material_id: 2  # Missing 'name' key, which makes it invalid
    """


def test_validate_benchmark_valid(mock_schema, valid_yaml):
    """Test validation succeeds with a correct benchmark YAML file."""
    with patch("builtins.open", mock_open(read_data=valid_yaml)) as mock_file, \
            patch.object(Path, "is_file", return_value=True), \
            patch("yaml.safe_load", side_effect=[mock_schema, yaml.safe_load(valid_yaml)]), \
            patch("jsonschema.Draft7Validator") as mock_validator:

        mock_validator.return_value.iter_errors.return_value = []  # No validation errors

        validate_benchmark("valid_benchmark")  # Should not raise any exception
        mock_file.assert_called()


def test_validate_benchmark_missing_file():
    """Test validation fails when the benchmark file is missing."""
    with patch.object(Path, "is_file", return_value=False):
        with pytest.raises(FileNotFoundError, match="Benchmark file .* not found."):
            validate_benchmark("missing_benchmark")


def test_validate_benchmark_schema_validation_error(mock_schema, invalid_yaml):
    """Test validation fails when YAML does not conform to the schema."""
    with patch("builtins.open", mock_open(read_data=invalid_yaml)), \
            patch.object(Path, "is_file", return_value=True), \
            patch("yaml.safe_load", side_effect=[mock_schema, yaml.safe_load(invalid_yaml)]), \
            patch("jsonschema.Draft7Validator") as mock_validator:

        mock_validator.return_value.iter_errors.return_value = [
            MagicMock(message="Missing required field 'materials'",
                      path=["materials"])
        ]

        with pytest.raises(jsonschema.exceptions.ValidationError, match="YAML validation failed."):
            validate_benchmark("invalid_schema")
