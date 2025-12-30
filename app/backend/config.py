"""
Configuration settings for the MAF-based chatbot application.
환경변수 및 설정값 관리
"""
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class AzureConfig:
    """Microsoft Foundry 및 관련 서비스 설정"""
    
    # Microsoft Foundry Project
    project_endpoint: str
    model_deployment_name: str
    
    # Azure AI Search
    search_endpoint: str
    search_index_name: str
    search_api_key: Optional[str] = None  # Managed Identity 사용시 불필요
    
    # Bing Search Grounding (Lab 4)
    bing_connection_id: Optional[str] = None
    
    # Optional: Azure OpenAI (별도 사용시)
    openai_endpoint: Optional[str] = None
    openai_api_key: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> "AzureConfig":
        """환경변수에서 설정값 로드"""
        return cls(
            project_endpoint=os.environ.get(
                "AZURE_AI_PROJECT_ENDPOINT",
                ""
            ),
            model_deployment_name=os.environ.get(
                "AZURE_AI_MODEL_DEPLOYMENT_NAME",
                "gpt-4.1"
            ),
            search_endpoint=os.environ.get(
                "AZURE_SEARCH_SERVICE_ENDPOINT",
                ""
            ),
            search_index_name=os.environ.get(
                "AZURE_SEARCH_INDEX_NAME",
                "gptkbindex"
            ),
            search_api_key=os.environ.get("AZURE_SEARCH_API_KEY"),
            bing_connection_id=os.environ.get("BING_CONNECTION_ID"),
            openai_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),
            openai_api_key=os.environ.get("AZURE_OPENAI_API_KEY"),
        )


@dataclass
class AppConfig:
    """애플리케이션 설정"""
    
    debug: bool = False
    cors_origins: list[str] = None
    
    def __post_init__(self):
        if self.cors_origins is None:
            self.cors_origins = ["*"]
    
    @classmethod
    def from_env(cls) -> "AppConfig":
        return cls(
            debug=os.environ.get("DEBUG", "false").lower() == "true",
            cors_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
        )


# Global config instances
azure_config: Optional[AzureConfig] = None
app_config: Optional[AppConfig] = None


def load_config():
    """설정 로드 및 초기화"""
    global azure_config, app_config
    azure_config = AzureConfig.from_env()
    app_config = AppConfig.from_env()
    return azure_config, app_config
