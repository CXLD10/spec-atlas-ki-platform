"""Tests for spec schema validation."""

from __future__ import annotations

import pytest

from spec_atlas.specify.schema import InputSpec, OutputSpec, Spec, spec_json_schema, validate_spec


class TestInputSpec:
    """Tests for InputSpec validation."""

    def test_valid_input(self) -> None:
        """Create a valid input spec."""
        inp = InputSpec(name="user_id", type="int", description="User identifier")
        assert inp.name == "user_id"
        assert inp.type == "int"

    def test_empty_name_rejected(self) -> None:
        """Empty name is rejected."""
        with pytest.raises(ValueError):
            InputSpec(name="", type="int", description="test")

    def test_empty_type_rejected(self) -> None:
        """Empty type is rejected."""
        with pytest.raises(ValueError):
            InputSpec(name="x", type="", description="test")

    def test_whitespace_stripped(self) -> None:
        """Whitespace is stripped from fields."""
        inp = InputSpec(name="  x  ", type="  int  ", description="  desc  ")
        assert inp.name == "x"
        assert inp.type == "int"
        assert inp.description == "desc"


class TestOutputSpec:
    """Tests for OutputSpec validation."""

    def test_valid_output(self) -> None:
        """Create a valid output spec."""
        out = OutputSpec(name="result", type="str", description="Result string")
        assert out.name == "result"
        assert out.type == "str"

    def test_missing_required_field(self) -> None:
        """Missing required field raises ValueError."""
        with pytest.raises(ValueError):
            OutputSpec(name="result", type="str")  # missing description


class TestSpec:
    """Tests for complete Spec validation."""

    def test_minimal_valid_spec(self) -> None:
        """Create a minimal valid spec (only purpose required)."""
        spec = Spec(purpose="Authenticate users")
        assert spec.purpose == "Authenticate users"
        assert spec.inputs == []
        assert spec.outputs == []
        assert spec.dependencies == []
        assert spec.invariants == []
        assert spec.side_effects == []
        assert spec.failure_modes == []

    def test_full_valid_spec(self) -> None:
        """Create a spec with all fields."""
        spec = Spec(
            purpose="Validate password",
            inputs=[InputSpec(name="password", type="str", description="User password")],
            outputs=[OutputSpec(name="is_valid", type="bool", description="Validity")],
            dependencies=["auth.crypto"],
            invariants=["Password is hashed before comparison"],
            side_effects=["Logs failed attempts"],
            failure_modes=["Invalid hash format", "Database unavailable"],
        )
        assert spec.purpose == "Validate password"
        assert len(spec.inputs) == 1
        assert len(spec.outputs) == 1
        assert len(spec.dependencies) == 1
        assert len(spec.invariants) == 1

    def test_empty_purpose_rejected(self) -> None:
        """Empty purpose is rejected."""
        with pytest.raises(ValueError):
            Spec(purpose="")

    def test_empty_string_in_invariants_filtered(self) -> None:
        """Empty strings in invariants are filtered out."""
        spec = Spec(
            purpose="Test",
            invariants=["Must be positive", "", "  ", "Always true"],
        )
        assert len(spec.invariants) == 2
        assert "Must be positive" in spec.invariants
        assert "Always true" in spec.invariants

    def test_empty_dependencies_filtered(self) -> None:
        """Empty strings in dependencies are filtered."""
        spec = Spec(
            purpose="Test",
            dependencies=["auth.utils", "", "  ", "crypto.lib"],
        )
        assert len(spec.dependencies) == 2
        assert "auth.utils" in spec.dependencies
        assert "crypto.lib" in spec.dependencies

    def test_spec_serialization(self) -> None:
        """Spec can be serialized to JSON."""
        spec = Spec(
            purpose="Test function",
            inputs=[InputSpec(name="x", type="int", description="Input")],
            outputs=[OutputSpec(name="y", type="int", description="Output")],
        )
        data = spec.model_dump(mode="json")
        assert data["purpose"] == "Test function"
        assert len(data["inputs"]) == 1
        assert data["inputs"][0]["name"] == "x"


class TestValidateSpec:
    """Tests for the validate_spec function."""

    def test_valid_spec_passes(self) -> None:
        """Valid spec dict passes validation."""
        spec_dict = {
            "purpose": "Test function",
            "inputs": [{"name": "x", "type": "int", "description": "Input"}],
            "outputs": [],
            "dependencies": [],
            "invariants": [],
            "side_effects": [],
            "failure_modes": [],
        }
        result = validate_spec(spec_dict)
        assert result["purpose"] == "Test function"

    def test_minimal_spec_passes(self) -> None:
        """Minimal spec with only purpose passes."""
        spec_dict = {"purpose": "Test function"}
        result = validate_spec(spec_dict)
        assert result["purpose"] == "Test function"
        assert result["inputs"] == []

    def test_invalid_spec_raises_error(self) -> None:
        """Invalid spec raises ValueError."""
        spec_dict = {"purpose": ""}  # Empty purpose
        with pytest.raises(ValueError):
            validate_spec(spec_dict)

    def test_missing_required_field_raises_error(self) -> None:
        """Missing purpose raises ValueError."""
        spec_dict = {"inputs": []}
        with pytest.raises(ValueError):
            validate_spec(spec_dict)

    def test_invalid_inputs_type_raises_error(self) -> None:
        """Invalid input spec structure raises ValueError."""
        spec_dict = {
            "purpose": "Test",
            "inputs": [{"name": "x"}],  # Missing type and description
        }
        with pytest.raises(ValueError):
            validate_spec(spec_dict)

    def test_empty_strings_filtered_on_validation(self) -> None:
        """Empty strings are filtered during validation."""
        spec_dict = {
            "purpose": "Test",
            "invariants": ["Valid claim", "", "  ", "Another claim"],
        }
        result = validate_spec(spec_dict)
        assert len(result["invariants"]) == 2
        assert "Valid claim" in result["invariants"]
        assert "Another claim" in result["invariants"]


class TestSpecJsonSchema:
    """Tests for the JSON schema generation."""

    def test_schema_is_dict(self) -> None:
        """spec_json_schema returns a dict."""
        schema = spec_json_schema()
        assert isinstance(schema, dict)

    def test_schema_has_required_fields(self) -> None:
        """Schema includes all top-level fields."""
        schema = spec_json_schema()
        properties = schema.get("properties", {})
        assert "purpose" in properties
        assert "inputs" in properties
        assert "outputs" in properties
        assert "dependencies" in properties
        assert "invariants" in properties
        assert "side_effects" in properties
        assert "failure_modes" in properties

    def test_purpose_is_required(self) -> None:
        """Purpose is in the required fields."""
        schema = spec_json_schema()
        required = schema.get("required", [])
        assert "purpose" in required

    def test_schema_has_input_spec_definition(self) -> None:
        """Schema includes definition for InputSpec."""
        schema = spec_json_schema()
        # Pydantic generates $defs for nested models
        assert "$defs" in schema or "definitions" in schema

    def test_schema_is_valid_json_schema(self) -> None:
        """Schema structure is valid JSON Schema format."""
        schema = spec_json_schema()
        assert "type" in schema
        assert schema["type"] == "object"
        assert "properties" in schema
