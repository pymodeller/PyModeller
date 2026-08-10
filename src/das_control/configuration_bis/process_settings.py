"""Auto-generated settings from YAML spec."""

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import SettingsConfigDict

from .base_settings import BaseTraceableSettings


class ProcessSettings(BaseTraceableSettings):
    """Settings for the Process section."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        env_prefix="PROCESSING_",
        env_nested_delimiter="__",
        case_sensitive=False,
        env_prefix_target="all",
        from_attributes=True,
        extra="ignore",
        populate_by_name=True,
    )

    frames_energy: int = Field(
        default=10,
        alias="framesEnergy",
        validation_alias=AliasChoices("FRAMES_ENERGY", "framesEnergy", "frames_energy"),
        description="Number of frames used for energy computation.",
    )

    threads_energy: int = Field(
        default=10,
        alias="threadsEnergy",
        validation_alias=AliasChoices("THREADS_ENERGY", "threadsEnergy", "threads_energy"),
        description="Number of threads used for energy processing.",
    )

    token_value: SecretStr = Field(
        default=SecretStr("arn:aws:s3:my-bucket/Environment"),
        alias="tokenValue",
        validation_alias=AliasChoices("TOKEN_VALUE", "tokenValue", "token_value"),
        description="just a token value",
    )
