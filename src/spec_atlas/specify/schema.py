"""JSON Schema and validation for generated specs."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class InputSpec(BaseModel):
    """Input parameter specification."""

    name: str = Field(..., min_length=1, description="Parameter name")
    type: str = Field(..., min_length=1, description="Parameter type")
    description: str = Field(..., min_length=1, description="Parameter description")

    model_config = ConfigDict(str_strip_whitespace=True)


class OutputSpec(BaseModel):
    """Output value specification."""

    name: str = Field(..., min_length=1, description="Output name")
    type: str = Field(..., min_length=1, description="Output type")
    description: str = Field(..., min_length=1, description="Output description")

    model_config = ConfigDict(str_strip_whitespace=True)


class Spec(BaseModel):
    """Complete specification for a code component."""

    purpose: str = Field(..., min_length=1, description="What this component does")
    inputs: list[InputSpec] = Field(default_factory=list, description="Input parameters")
    outputs: list[OutputSpec] = Field(default_factory=list, description="Output values")
    dependencies: list[str] = Field(
        default_factory=list, description="Component references this depends on"
    )
    invariants: list[str] = Field(
        default_factory=list,
        description="Properties that must always be true",
    )
    side_effects: list[str] = Field(
        default_factory=list, description="Effects beyond the main purpose"
    )
    failure_modes: list[str] = Field(default_factory=list, description="Possible failure scenarios")

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("invariants", "side_effects", "failure_modes", mode="before")
    @classmethod
    def validate_non_empty_strings(cls, v: list[str]) -> list[str]:
        """Ensure all strings in the list are non-empty."""
        if not isinstance(v, list):
            return v
        return [s.strip() for s in v if isinstance(s, str) and s.strip()]

    @field_validator("dependencies", mode="before")
    @classmethod
    def validate_dependencies_format(cls, v: list[str]) -> list[str]:
        """Ensure dependencies are non-empty component references."""
        if not isinstance(v, list):
            return v
        return [s.strip() for s in v if isinstance(s, str) and s.strip()]


def validate_spec(spec_obj: dict) -> dict:
    """Validate a spec object against the schema.

    Args:
        spec_obj: Dictionary to validate.

    Returns:
        The validated spec as a dict.

    Raises:
        ValueError: If validation fails.
    """
    try:
        spec = Spec(**spec_obj)
        return spec.model_dump(mode="json")
    except Exception as e:
        raise ValueError(f"Spec validation failed: {e}") from e


def spec_json_schema() -> dict:
    """Get the JSON schema for specs.

    Returns:
        A JSON schema dict compatible with OpenAPI/JSON Schema validators.
    """
    return Spec.model_json_schema()
