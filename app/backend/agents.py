"""
Microsoft Agent Framework (MAF) 기반 Agent 정의
https://learn.microsoft.com/en-us/agent-framework/

Lab 1: 기본 챗봇 (BaseAgent)
Lab 2: RAG 챗봇 (RAGAgent)
Lab 3: Tool Calling (ToolAgent)
Lab 4: 통합 Agent (CombinedAgent) - RAG + Tool Calling
Lab 5: Web Search (WebSearchAgent) - Bing Search Grounding
Lab 6: 오케스트레이터 (OrchestratorAgent) - 멀티에이전트 라우팅
"""
import logging
from typing import Optional, Annotated
from enum import Enum

from azure.identity.aio import AzureCliCredential
from pydantic import Field

# Microsoft Agent Framework imports
from agent_framework import ChatAgent, HostedWebSearchTool
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
                response += f"\n\n[출처: {', '.join(set(sources))}]"
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


# ============================================================
# Web Search Agent Class (Lab 4) - Bing Search Grounding
# ============================================================

class WebSearchAgent(BaseAgent):
    """
    Web Search Agent - Lab 4용
    Bing Search Grounding을 사용하여 인터넷 검색 기반 답변
    
    Connection ID 우선순위:
    1. BING_CONNECTION_ID 환경변수에 전체 ID가 있으면 사용
    2. BING_CONNECTION_ID에 이름만 있으면 SDK로 조회하여 ID 획득
    3. 환경변수 없으면 프로젝트에서 Bing connection 자동 검색
    """
    
    async def _get_bing_connection_id(self) -> str:
        """
        Bing Connection ID를 SDK를 사용하여 자동으로 가져옴
        
        우선순위:
        1. BING_CONNECTION_ID가 전체 경로면 그대로 사용
        2. BING_CONNECTION_ID가 이름이면 SDK로 조회
        3. 없으면 프로젝트에서 Bing 타입 connection 자동 검색
        """
        import os
        
        connection_id = os.getenv("BING_CONNECTION_ID", "").strip()
        
        # 1. 전체 connection_id가 이미 있는 경우
        if connection_id.startswith("/subscriptions/"):
            logger.info(f"환경변수에서 Bing Connection ID 사용")
            return connection_id
        
        # 2 & 3. SDK를 사용하여 connection 조회
        try:
            from azure.ai.projects import AIProjectClient
            from azure.identity import DefaultAzureCredential
            
            # sync SDK 사용 (connections API가 sync만 지원하는 경우가 많음)
            project_client = AIProjectClient(
                endpoint=self.config.project_endpoint,
                credential=DefaultAzureCredential(),
            )
            
            with project_client:
                # 이름이 있으면 해당 이름으로 조회
                if connection_id:
                    logger.info(f"Connection 이름 '{connection_id}'로 조회 중...")
                    connection = project_client.connections.get(connection_id)
                    if connection and hasattr(connection, 'id'):
                        logger.info(f"Bing Connection ID 찾음: {connection.id[:80]}...")
                        return connection.id
                
                # 3. 이름이 없으면 전체 목록에서 Bing 관련 connection 검색
                logger.info("프로젝트에서 Bing connection 자동 검색 중...")
                for connection in project_client.connections.list():
                    conn_name = getattr(connection, 'name', '').lower()
                    conn_type = str(getattr(connection, 'connection_type', '')).lower()
                    
                    # Bing 관련 connection 찾기
                    if 'bing' in conn_name or 'bing' in conn_type:
                        if hasattr(connection, 'id'):
                            logger.info(f"Bing Connection 자동 발견: {connection.name}")
                            return connection.id
                
                logger.warning("프로젝트에서 Bing connection을 찾을 수 없습니다.")
                
        except ImportError:
            logger.warning("azure-ai-projects SDK가 설치되지 않았습니다. pip install azure-ai-projects")
        except Exception as e:
            logger.warning(f"SDK로 Connection 조회 실패: {e}")
        
        # 찾지 못한 경우 빈 문자열 반환
        return ""
    
    async def initialize(self):
        """Web Search Agent 초기화 - HostedWebSearchTool 사용"""
        self.credential = AzureCliCredential()
        
        # Bing Connection ID 가져오기 (자동 생성 시도)
        bing_connection_id = await self._get_bing_connection_id()
        
        # HostedWebSearchTool 생성 - Bing Grounding 사용
        bing_search_tool = HostedWebSearchTool(
            name="Bing Grounding Search",
            description="Search the web for current information using Bing",
            additional_properties={
                "connection_id": bing_connection_id,
            } if bing_connection_id else None,
        )
        
        # AzureAIAgentClient 생성
        self.client = AzureAIAgentClient(
            project_endpoint=self.config.project_endpoint,
            model_deployment_name=self.config.model_deployment_name,
            credential=self.credential,
        )
        
        # Bing Search Grounding이 포함된 Agent 생성
        self.agent = self.client.create_agent(
            name="웹 검색 Agent",
            instructions="""당신은 인터넷 검색을 통해 최신 정보를 제공하는 AI 어시스턴트입니다.

다음 지침을 따라주세요:
1. 사용자의 질문에 대해 Bing 검색을 통해 최신 정보를 찾아 답변하세요.
2. 날씨, 뉴스, 최신 이벤트, 실시간 정보 등을 제공할 수 있습니다.
3. 검색 결과를 바탕으로 정확하고 유용한 답변을 제공하세요.
4. 정보의 출처를 가능하면 언급해주세요.
5. 한국어로 답변하세요.""",
            tools=[bing_search_tool],
        )
        
        logger.info("Web Search Agent 초기화 완료 (Bing Search Grounding with HostedWebSearchTool)")
    
    async def chat(self, message: str) -> str:
        """
        웹 검색 기반 채팅
        
        Args:
            message: 사용자 질문
            
        Returns:
            웹 검색 결과 기반 응답
        """
        if not self.agent:
            await self.initialize()
        
        try:
            result = await self.agent.run(message)
            return result.text
                
        except Exception as e:
            logger.error(f"Web Search chat error: {e}")
            self.agent = None
            return f"오류가 발생했습니다: {str(e)}"


# ============================================================
# Agent Type Enum for Orchestrator
# ============================================================

class AgentType(Enum):
    """에이전트 유형 정의"""
    BASIC = "basic"
    RAG = "rag"
    CALCULATOR = "calculator"
    WEB_SEARCH = "web_search"


# ============================================================
# Orchestrator Agent Class (Lab 5) - Multi-Agent Router
# ============================================================

class OrchestratorAgent(BaseAgent):
    """
    오케스트레이터 Agent - Lab 5용
    질문 유형을 분석하여 적절한 전문 에이전트로 라우팅
    
    라우팅 규칙:
    - Zava 회사 관련 → RAG Agent
    - 사칙연산/계산 → Calculator Agent (Tool Agent)
    - 날씨/뉴스/최신정보 → Web Search Agent
    - 일반 질문 → Basic Agent
    """
    
    def __init__(self, config: AzureConfig):
        super().__init__(config)
        # 전문 에이전트들
        self.basic_agent: Optional[BaseAgent] = None
        self.rag_agent: Optional[RAGAgent] = None
        self.tool_agent: Optional[ToolAgent] = None
        self.web_search_agent: Optional[WebSearchAgent] = None
        # 라우팅 판단용 에이전트
        self.router_agent: Optional[ChatAgent] = None
    
    async def initialize(self):
        """오케스트레이터 및 전문 에이전트들 초기화"""
        self.credential = AzureCliCredential()
        
        # 라우팅 판단용 에이전트 생성
        self.client = AzureAIAgentClient(
            project_endpoint=self.config.project_endpoint,
            model_deployment_name=self.config.model_deployment_name,
            credential=self.credential,
        )
        
        self.router_agent = self.client.create_agent(
            name="라우터",
            instructions="""당신은 사용자 질문을 분석하여 적절한 전문가에게 라우팅하는 역할입니다.

질문을 분석하고 다음 중 하나의 카테고리로 분류하세요:
- "rag": Zava 회사, 직원, 휴가, 복지, 정책, 회사 역사, 핵심 가치 등 회사 내부 문서 관련 질문
- "calculator": 사칙연산, 계산, 더하기, 빼기, 곱하기, 나누기 등 수학 계산 질문
- "web_search": 날씨, 뉴스, 최신 정보, 실시간 데이터, 인터넷 검색이 필요한 질문
- "basic": 일반적인 대화, 인사, 자기소개, 기타 질문

반드시 다음 형식으로만 응답하세요 (다른 텍스트 없이):
ROUTE: [카테고리]

예시:
- "Zava 회사의 휴가 정책은?" → ROUTE: rag
- "123 더하기 456은?" → ROUTE: calculator
- "오늘 서울 날씨 어때?" → ROUTE: web_search
- "안녕하세요" → ROUTE: basic""",
        )
        
        # 전문 에이전트들 초기화
        self.basic_agent = BaseAgent(self.config)
        self.rag_agent = RAGAgent(self.config)
        self.tool_agent = ToolAgent(self.config)
        self.web_search_agent = WebSearchAgent(self.config)
        
        logger.info("Orchestrator Agent 초기화 완료 (멀티에이전트 라우팅)")
    
    async def _determine_route(self, message: str) -> AgentType:
        """
        질문을 분석하여 적절한 에이전트 유형 결정
        
        Args:
            message: 사용자 질문
            
        Returns:
            라우팅할 AgentType
        """
        try:
            result = await self.router_agent.run(message)
            response = result.text.strip().upper()
            
            if "ROUTE: RAG" in response:
                return AgentType.RAG
            elif "ROUTE: CALCULATOR" in response:
                return AgentType.CALCULATOR
            elif "ROUTE: WEB_SEARCH" in response:
                return AgentType.WEB_SEARCH
            else:
                return AgentType.BASIC
                
        except Exception as e:
            logger.warning(f"라우팅 판단 실패, 기본 에이전트 사용: {e}")
            return AgentType.BASIC
    
    async def chat(self, message: str) -> str:
        """
        오케스트레이터 채팅 - 질문 분석 후 적절한 에이전트로 라우팅
        
        Args:
            message: 사용자 질문
            
        Returns:
            전문 에이전트의 응답
        """
        if not self.router_agent:
            await self.initialize()
        
        try:
            # 1. 라우팅 결정
            agent_type = await self._determine_route(message)
            logger.info(f"라우팅 결정: {agent_type.value}")
            
            # 2. 적절한 에이전트로 전달
            if agent_type == AgentType.RAG:
                response = await self.rag_agent.chat(message)
                prefix = "[RAG Agent]\n"
            elif agent_type == AgentType.CALCULATOR:
                response = await self.tool_agent.chat(message)
                prefix = "🔢 [Calculator Agent]\n"
            elif agent_type == AgentType.WEB_SEARCH:
                response = await self.web_search_agent.chat(message)
                prefix = "[Web Search Agent]\n"
            else:
                response = await self.basic_agent.chat(message)
                prefix = "[Basic Agent]\n"
            
            return f"{prefix}{response}"
                
        except Exception as e:
            logger.error(f"Orchestrator chat error: {e}")
            return f"오류가 발생했습니다: {str(e)}"
    
    async def close(self):
        """모든 에이전트 리소스 정리"""
        if self.basic_agent:
            await self.basic_agent.close()
        if self.rag_agent:
            await self.rag_agent.close()
        if self.tool_agent:
            await self.tool_agent.close()
        if self.web_search_agent:
            await self.web_search_agent.close()
        await super().close()
