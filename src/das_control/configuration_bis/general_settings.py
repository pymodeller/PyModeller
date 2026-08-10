"""AUTO-GENERATED ROOT SETTINGS."""

from pydantic import AliasChoices, Field
from pydantic_settings import SettingsConfigDict

from .base_settings import BaseTraceableSettings
from .zone import ZoneModel


class GeneralSettings(BaseTraceableSettings):
    """Root application settings.

    Composes all section settings into a single tree.
    """

    model_config = SettingsConfigDict(
        from_attributes=True,
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        env_prefix="APP_",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
        env_prefix_target="all",
    )

    # --- Flat variables (General Section) ---

    env: str = Field(
        default="local",
        alias="env",
        validation_alias=AliasChoices("ENV", "env"),
        description="Enable local development mode (disables some production guards)",
    )

    host: str = Field(
        default="localhost", alias="host", validation_alias=AliasChoices("HOST", "host"), description="Host"
    )

    port: int = Field(default=8000, alias="port", validation_alias=AliasChoices("PORT", "port"), description="App port")

    minutes_refresh_conf: int = Field(
        default=5,
        alias="minutesRefreshConf",
        validation_alias=AliasChoices("MINUTES_REFRESH_CONF", "minutesRefreshConf", "minutes_refresh_conf"),
        description="Minutes to refresh config",
    )

    server_url: str = Field(
        default="server_url_local",
        alias="serverUrl",
        validation_alias=AliasChoices("SERVER_URL", "serverUrl", "server_url"),
        description="Host",
    )

    server_ws: str = Field(
        default="server_ws_local",
        alias="serverWs",
        validation_alias=AliasChoices("SERVER_WS", "serverWs", "server_ws"),
        description="Host",
    )

    url_event: str = Field(
        default="url_event_local",
        alias="urlEvent",
        validation_alias=AliasChoices("URL_EVENT", "urlEvent", "url_event"),
        description="Host",
    )

    waterfall: str = Field(
        default="waterfall_name",
        alias="waterfall",
        validation_alias=AliasChoices("WATERFALL", "waterfall"),
        description="Host",
    )

    # --- Nested Sections (Composition) ---

    zone: ZoneModel = Field(default_factory=ZoneModel)
