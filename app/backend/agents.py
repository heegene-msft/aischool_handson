"""
Microsoft Agent Framework (MAF) 기반 Agent 정의
https://learn.microsoft.com/en-us/agent-framework/

Lab 1: 기본 챗봇 (BaseAgent)
Lab 2: RAG 챗봇 (RAGAgent)
Lab 3: Tool Calling (ToolAgent)
"""
import logging
from typing import Optional, Annotated

from azure.identity.aio import AzureCliCredential
from pydantic import Field

# Microsoft Agent Framework imports
from agent_framework import ChatAgent
from agent_framework.azure import AzureAIAgentClient

from config import AzureConfig
from search_helper import SearchHelper

logger = logging.getLogger(__name__)


# ============================================================
# Tool Functions (Lab 3)
# ============================================================

def add(
    a: Annotated[float, Field(description="첫 번째 숫자")],
    b: Annotated[float, Field(description="두 번째 숫자")]
) -> float:
    """두 숫자를 더합니다."""
    return a + b


def subtract(
    a: Annotated[float, Field(description="첫 번째 숫자")],
    b: Annotated[float, Field(description="두 번째 숫자")]
) -> float:
    """첫 번째 숫자에서 두 번째 숫자를 뺍니다."""
    return a - b


def multiply(
    a: Annotated[float, Field(description="첫 번째 숫자")],
    b: Annotated[float, Field(description="두 번째 숫자")]
) -> float:
    """두 숫자를 곱합니다."""
    return a * b


def divide(
    a: Annotated[float, Field(description="나눠질 숫자 (피제수)")],
    b: Annotated[float, Field(description="나눌 숫자 (제수)")]
) -> float:
    """첫 번째 숫자를 두 번째 숫자로 나눕니다. 0으로 나눌 수 없습니다."""
    if b == 0:
        raise ValueError("0으로 나눌 수 없습니다.")
    return a / b


# All calculator tools as a list of functions
CALCULATOR_TOOLS = [add, subtract, multiply, divide]


# ============================================================
# Base Agent Class (Lab 1)
# ============================================================

class BaseAgent:
    """
    기본 Agent 클래스 - Lab 1용
    """
    
    def __init__(self, config: AzureConfig):
        self.config = config
        self.credential = None
        self.client: Optional[AzureAIAgentClient] = None
        self.agent: Optional[ChatAgent] = None
    
    async def initialize(self):
        """Agent 초기화"""
        self.credential = AzureCliCredential()
        
        # AzureAIAgentClient 생성
        self.client = AzureAIAgentClient(
            project_endpoint=self.config.project_endpoint,
            model_deployment_name=self.config.model_deployment_name,
            credential=self.credential,
        )
        
        # ChatAgent 생성
        self.agent = self.client.create_agent(
            name="기본 챗봇",
            instructions="""당신은 친절한 AI 어시스턴트입니다. 사용자 질문에 정확하고 간결하게 답변하세요.
한국어로 답변하세요.""",
        )
        
        logger.info("Base Agent 초기화 완료 (Microsoft Agent Framework)")
    
    async def chat(self, message: str) -> str:
        """
        채팅 메시지 처리
        
        Args:
            message: 사용자 메시지
            
        Returns:
            Agent 응답
        """
        if not self.agent:
            await self.initialize()
        
        try:
            result = await self.agent.run(message)
            return result.text
        except Exception as e:
            logger.error(f"Chat error: {e}")
            # Agent가 닫힌 경우 재초기화
            self.agent = None
            return f"오류가 발생했습니다: {str(e)}"
    
    async def chat_stream(self, message: str):
        """
        스트리밍 채팅 메시지 처리
        
        Args:
            message: 사용자 메시지
            
        Yields:
            응답 청크
        """
        if not self.agent:
            await self.initialize()
        
        try:
            async with self.agent as agent:
                async for chunk in agent.run_stream(message):
                    if chunk.text:
                        yield chunk.text
        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"오류가 발생했습니다: {str(e)}"
    
    async def close(self):
        """리소스 정리"""
        if self.client:
            await self.client.close()
        if self.credential:
            await self.credential.close()


# ============================================================
# RAG Agent Class (Lab 2)
# ============================================================

class RAGAgent(BaseAgent):
    """
    RAG Agent - Lab 2용
    Azure AI Search를 사용하여 문서 검색 후 답변
    """
    
    def __init__(self, config: AzureConfig):
        super().__init__(config)
        self.search_helper: Optional[SearchHelper] = None
    
    async def initialize(self):
        """RAG Agent 초기화"""
        self.credential = AzureCliCredential()
        
        # Search Helper 초기화
        self.search_helper = SearchHelper(
            endpoint=self.config.search_endpoint,
            index_name=self.config.search_index_name,
            credential=self.credential,
            api_key=self.config.search_api_key,
        )
        
        # AzureAIAgentClient 생성
        self.client = AzureAIAgentClient(
            project_endpoint=self.config.project_endpoint,
            model_deployment_name=self.config.model_deployment_name,
            credential=self.credential,
        )
        
        # RAG용 ChatAgent 생성
        self.agent = self.client.create_agent(
            name="RAG 챗봇",
            instructions="""당신은 Zava 회사의 문서를 기반으로 질문에 답변하는 AI 어시스턴트입니다.
제공된 문서 내용을 기반으로 정확하게 답변하세요.
문서에서 답을 찾을 수 없으면 솔직하게 모른다고 답변하세요.
한국어로 답변하세요.""",
        )
        
        logger.info("RAG Agent 초기화 완료 (Microsoft Agent Framework)")
    
    async def chat(self, message: str) -> str:
        """
        RAG 기반 채팅 - 검색 후 답변
        
        Args:
            message: 사용자 질문
            
        Returns:
            검색 결과 기반 응답
        """
        if not self.agent:
            await self.initialize()
        
        try:
            # 1. 검색 수행
            search_results = await self.search_helper.search(message, top=3)
            context = self.search_helper.format_search_results(search_results)
            
            # 2. 컨텍스트와 함께 메시지 구성
            augmented_message = f"""## 사용자 질문:
{message}

## 검색된 관련 문서:
{context}

위 문서 내용을 참고하여 사용자 질문에 답변해주세요."""
            
            # 3. Agent에게 전달
            result = await self.agent.run(augmented_message)
            
            # 출처 정보 추가
            sources = [r.get("source", "") for r in search_results if r.get("source")]
            response = result.text
            if sources:
                response += f"\n\n📚 출처: {', '.join(set(sources))}"
            return response
                
        except Exception as e:
            logger.error(f"RAG chat error: {e}")
            return f"오류가 발생했습니다: {str(e)}"
    
    async def close(self):
        """리소스 정리"""
        if self.search_helper:
            await self.search_helper.close()
        await super().close()


# ============================================================
# Tool Agent Class (Lab 3)
# ============================================================

class ToolAgent(BaseAgent):
    """
    Tool Calling Agent - Lab 3용 (사칙연산)
    Microsoft Agent Framework의 function tools 기능 사용
    """
    
    async def initialize(self):
        """Tool Agent 초기화"""
        self.credential = AzureCliCredential()
        
        # AzureAIAgentClient 생성
        self.client = AzureAIAgentClient(
            project_endpoint=self.config.project_endpoint,
            model_deployment_name=self.config.model_deployment_name,
            credential=self.credential,
        )
        
        # Tool이 포함된 ChatAgent 생성
        # Microsoft Agent Framework에서는 함수를 직접 tools 파라미터로 전달
        self.agent = self.client.create_agent(
            name="계산기 Agent",
            instructions="""당신은 사칙연산을 수행할 수 있는 AI 어시스턴트입니다.
사용자가 계산을 요청하면 제공된 도구(add, subtract, multiply, divide)를 사용하세요.
계산 결과와 함께 계산 과정을 설명해주세요.
한국어로 답변하세요.""",
            tools=CALCULATOR_TOOLS,  # 함수 리스트 직접 전달
        )
        
        logger.info("Tool Agent 초기화 완료 (Microsoft Agent Framework)")
    
    async def chat(self, message: str) -> str:
        """
        Tool Calling 기반 채팅
        
        Args:
            message: 사용자 메시지
            
        Returns:
            Agent 응답 (Tool 실행 결과 포함)
        """
        if not self.agent:
            await self.initialize()
        
        try:
            # Microsoft Agent Framework가 자동으로 tool calling 처리
            result = await self.agent.run(message)
            return result.text
        except Exception as e:
            logger.error(f"Tool chat error: {e}")
            self.agent = None
            return f"오류가 발생했습니다: {str(e)}"


# ============================================================
# Combined Agent Class (RAG + Tools)
# ============================================================

class CombinedAgent(BaseAgent):
    """
    RAG + Tool Calling 통합 Agent
    문서 검색과 사칙연산 도구를 모두 사용
    """
    
    def __init__(self, config: AzureConfig):
        super().__init__(config)
        self.search_helper: Optional[SearchHelper] = None
    
    async def initialize(self):
        """통합 Agent 초기화"""
        self.credential = AzureCliCredential()
        
        # Search Helper 초기화
        self.search_helper = SearchHelper(
            endpoint=self.config.search_endpoint,
            index_name=self.config.search_index_name,
            credential=self.credential,
            api_key=self.config.search_api_key,
        )
        
        # AzureAIAgentClient 생성
        self.client = AzureAIAgentClient(
            project_endpoint=self.config.project_endpoint,
            model_deployment_name=self.config.model_deployment_name,
            credential=self.credential,
        )
        
        # RAG + Tools Agent 생성
        self.agent = self.client.create_agent(
            name="통합 Agent",
            instructions="""당신은 다음 기능을 갖춘 AI 어시스턴트입니다:
1. Zava 회사 문서 기반 질문 답변 (RAG)
2. 사칙연산 계산 (Tool Calling)

사용자의 질문 유형에 따라 적절히 답변하세요.
계산이 필요하면 제공된 도구를 사용하세요.
한국어로 답변하세요.""",
            tools=CALCULATOR_TOOLS,
        )
        
        logger.info("통합 Agent 초기화 완료 (Microsoft Agent Framework)")
    
    async def chat(self, message: str) -> str:
        """통합 채팅 처리"""
        if not self.agent:
            await self.initialize()
        
        try:
            # 검색이 필요한지 휴리스틱 판단
            search_keywords = ["회사", "zava", "직원", "휴가", "복지", "역사", "가치", "정책"]
            needs_search = any(kw in message.lower() for kw in search_keywords)
            
            if needs_search:
                search_results = await self.search_helper.search(message, top=3)
                context = self.search_helper.format_search_results(search_results)
                augmented_message = f"""## 사용자 질문:
{message}

## 참고 문서:
{context}"""
            else:
                augmented_message = message
            
            result = await self.agent.run(augmented_message)
            return result.text
                
        except Exception as e:
            logger.error(f"Combined chat error: {e}")
            self.agent = None
            return f"오류가 발생했습니다: {str(e)}"
    
    async def close(self):
        """리소스 정리"""
        if self.search_helper:
            await self.search_helper.close()
        await super().close()
