"""Application settings, loaded from environment variables / .env.

When ``FOUNDRY_PROJECT_ENDPOINT`` is empty the service runs in deterministic
MOCK mode so the lab is runnable with zero Azure resources. Set the Foundry
variables (and `az login`) to switch to the real Foundry Agent Service backend.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    log_level: str = "INFO"

    # Microsoft Foundry project (Agent Service).
    # Endpoint form: https://<account>.services.ai.azure.com/api/projects/<project>
    foundry_project_endpoint: str = ""
    # Deployment name of a chat model in your Foundry project (e.g. "gpt-4o").
    foundry_model_name: str = "gpt-4o"
    # Name given to the hosted claims-intake agent (for traceability in the portal).
    foundry_agent_name: str = "claims-intake-agent"

    @property
    def use_foundry(self) -> bool:
        """True when the real Foundry Agent Service backend should be used."""
        return bool(self.foundry_project_endpoint)


@lru_cache
def get_settings() -> Settings:
    return Settings()
