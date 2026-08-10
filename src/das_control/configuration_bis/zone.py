"""Auto-generated settings from YAML spec."""

from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class ZoneModel(BaseModel):
    """Settings for the Zone section."""

    model_config = ConfigDict(
        from_attributes=True,
        extra="ignore",
        populate_by_name=True,
    )

    type: Literal["Zone"] = Field(default="Zone", exclude=True)

    start: int = Field(
        default=0, alias="start", validation_alias=AliasChoices("START", "start"), description="Start point to process"
    )

    end: int = Field(
        default=50, alias="end", validation_alias=AliasChoices("END", "end"), description="End point to process"
    )

    threshold: float | None = Field(
        default=None,
        alias="threshold",
        validation_alias=AliasChoices("THRESHOLD", "threshold"),
        description="Specific threshold for the zone waterfall",
    )
