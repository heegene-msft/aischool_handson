"""
Microsoft Agent Framework (MAF) 기반 Agent 정의
Microsoft Foundry Agent Service를 활용한 Lab 1, 2, 3 Agent 클래스들

참고 문서:
- Microsoft Agent Framework: https://learn.microsoft.com/en-us/agent-framework/
- Foundry Agent Service: https://learn.microsoft.com/en-us/azure/ai-foundry/agents/overview
"""
import json
import logging
from typing import Optional, AsyncGenerator

from azure.identity.aio import DefaultAzureCredential, AzureCliCredential
from azure.ai.agents.aio import AgentsClient
from azure.ai.agents.models import (
    MessageRole,
    MessageTextContent,
    ToolResources,
    RunStatus,
)

from config import AzureConfig
from tools.calculator import CALCULATOR_TOOLS, execute_calculator_function
from search_helper import SearchHelper, RAG_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class BaseAgent:
    """기본 Agent 클래스 - Lab 1용"""
    
    def __init__(self, config: AzureConfig):
        self.config = config
        self.credential = None
        self.client: Optional[AgentsClient] = None
        self.agent = None
        self.thread = None
    
    async def initialize(self):
        """Agent 초기화"""
        self.credential = DefaultAzureCredential()
        
        self.client = AgentsClient(
            endpoint=self.config.project_endpoint,
            credential=self.credential,
        )
        
        # 기본 Agent 생성
        self.agent = await self.client.create_agent(
            model=self.config.model_deployment_name,
            name="기본 챗봇",
            instructions="""당신은 친절하고 도움이 되는 AI 어시스턴트입니다.
            사용자의 질문에 정확하고 유용한 답변을 제공하세요.
            한국어로 답변하세요.""",
        )
        
        # 스레드 생성
        self.thread = await self.client.create_thread()
        
        logger.info(f"Agent 초기화 완료: {self.agent.id}")
    
    async def chat(self, message: str) -> str:
        """
        채팅 메시지 처리
        
        Args:
            message: 사용자 메시지
            
        Returns:
            Agent 응답
        """
        if not self.client or not self.agent or not self.thread:
            await self.initialize()
        
        # 메시지 추가
        await self.client.create_message(
            thread_id=self.thread.id,
            role=MessageRole.USER,
            content=message,
        )
        
        # Run 실행
        run = await self.client.create_run(
            thread_id=self.thread.id,
            agent_id=self.agent.id,
        )
        
        # 완료 대기
        while run.status in [RunStatus.QUEUED, RunStatus.IN_PROGRESS]:
            import asyncio
            await asyncio.sleep(0.5)
            run = await self.client.get_run(
                thread_id=self.thread.id,
                run_id=run.id,
            )
        
        if run.status != RunStatus.COMPLETED:
            logger.error(f"Run 실패: {run.status}")
            return f"오류가 발생했습니다: {run.status}"
        
        # 응답 가져오기
        messages = await self.client.list_messages(thread_id=self.thread.id)
        
        for msg in messages.data:
            if msg.role == MessageRole.ASSISTANT:
                for content in msg.content:
                    if isinstance(content, MessageTextContent):
                        return content.text.value
        
        return "응답을 생성할 수 없습니다."
    
    async def close(self):
        """리소스 정리"""
        if self.client:
            if self.agent:
                await self.client.delete_agent(self.agent.id)
            await self.client.close()
        if self.credential:
            await self.credential.close()


class RAGAgent(BaseAgent):
    """RAG Agent - Lab 2용"""
    
    def __init__(self, config: AzureConfig):
        super().__init__(config)
        self.search_helper: Optional[SearchHelper] = None
    
    async def initialize(self):
        """RAG Agent 초기화"""
        self.credential = DefaultAzureCredential()
        
        # Search Helper 초기화
        self.search_helper = SearchHelper(
            endpoint=self.config.search_endpoint,
            index_name=self.config.search_index_name,
            credential=self.credential,
            api_key=self.config.search_api_key,
        )
        
        self.client = AgentsClient(
            endpoint=self.config.project_endpoint,
            credential=self.credential,
        )
        
        # RAG Agent 생성 (기본 instructions, 실제 context는 메시지에서 추가)
        self.agent = await self.client.create_agent(
            model=self.config.model_deployment_name,
            name="RAG 챗봇",
            instructions="""당신은 Zava 회사의 문서를 기반으로 질문에 답변하는 AI 어시스턴트입니다.
            제공된 문서 내용을 기반으로 정확하게 답변하세요.
            문서에서 답을 찾을 수 없으면 솔직히 모른다고 답변하세요.
            한국어로 답변하세요.""",
        )
        
        self.thread = await self.client.create_thread()
        
        logger.info(f"RAG Agent 초기화 완료: {self.agent.id}")
    
    async def chat(self, message: str) -> str:
        """
        RAG 기반 채팅 - 검색 후 답변
        
        Args:
            message: 사용자 질문
            
        Returns:
            검색 결과 기반 응답
        """
        if not self.client or not self.agent or not self.thread:
            await self.initialize()
        
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
        await self.client.create_message(
            thread_id=self.thread.id,
            role=MessageRole.USER,
            content=augmented_message,
        )
        
        run = await self.client.create_run(
            thread_id=self.thread.id,
            agent_id=self.agent.id,
        )
        
        while run.status in [RunStatus.QUEUED, RunStatus.IN_PROGRESS]:
            import asyncio
            await asyncio.sleep(0.5)
            run = await self.client.get_run(
                thread_id=self.thread.id,
                run_id=run.id,
            )
        
        if run.status != RunStatus.COMPLETED:
            return f"오류가 발생했습니다: {run.status}"
        
        messages = await self.client.list_messages(thread_id=self.thread.id)
        
        for msg in messages.data:
            if msg.role == MessageRole.ASSISTANT:
                for content in msg.content:
                    if isinstance(content, MessageTextContent):
                        # 출처 정보 추가
                        sources = [r.get("source", "") for r in search_results if r.get("source")]
                        response = content.text.value
                        if sources:
                            response += f"\n\n📚 출처: {', '.join(set(sources))}"
                        return response
        
        return "응답을 생성할 수 없습니다."
    
    async def close(self):
        """리소스 정리"""
        if self.search_helper:
            await self.search_helper.close()
        await super().close()


class ToolAgent(BaseAgent):
    """Tool Calling Agent - Lab 3용 (사칙연산)"""
    
    async def initialize(self):
        """Tool Agent 초기화"""
        self.credential = DefaultAzureCredential()
        
        self.client = AgentsClient(
            endpoint=self.config.project_endpoint,
            credential=self.credential,
        )
        
        # Tool이 포함된 Agent 생성
        self.agent = await self.client.create_agent(
            model=self.config.model_deployment_name,
            name="계산기 Agent",
            instructions="""당신은 사칙연산을 수행할 수 있는 AI 어시스턴트입니다.
            사용자가 계산을 요청하면 제공된 도구(add, subtract, multiply, divide)를 사용하세요.
            계산 결과와 함께 계산 과정을 설명해주세요.
            한국어로 답변하세요.""",
            tools=CALCULATOR_TOOLS,
        )
        
        self.thread = await self.client.create_thread()
        
        logger.info(f"Tool Agent 초기화 완료: {self.agent.id}")
    
    async def chat(self, message: str) -> str:
        """
        Tool Calling 기반 채팅
        
        Args:
            message: 사용자 메시지
            
        Returns:
            Agent 응답 (Tool 실행 결과 포함)
        """
        if not self.client or not self.agent or not self.thread:
            await self.initialize()
        
        await self.client.create_message(
            thread_id=self.thread.id,
            role=MessageRole.USER,
            content=message,
        )
        
        run = await self.client.create_run(
            thread_id=self.thread.id,
            agent_id=self.agent.id,
        )
        
        # Tool calling 처리 루프
        while True:
            import asyncio
            await asyncio.sleep(0.5)
            run = await self.client.get_run(
                thread_id=self.thread.id,
                run_id=run.id,
            )
            
            if run.status == RunStatus.COMPLETED:
                break
            elif run.status == RunStatus.REQUIRES_ACTION:
                # Tool 실행 필요
                tool_outputs = []
                
                for tool_call in run.required_action.submit_tool_outputs.tool_calls:
                    function_name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)
                    
                    logger.info(f"Tool 호출: {function_name}({arguments})")
                    
                    result = execute_calculator_function(function_name, arguments)
                    
                    tool_outputs.append({
                        "tool_call_id": tool_call.id,
                        "output": result,
                    })
                
                # Tool 결과 제출
                run = await self.client.submit_tool_outputs(
                    thread_id=self.thread.id,
                    run_id=run.id,
                    tool_outputs=tool_outputs,
                )
            elif run.status in [RunStatus.FAILED, RunStatus.CANCELLED, RunStatus.EXPIRED]:
                return f"오류가 발생했습니다: {run.status}"
        
        # 응답 가져오기
        messages = await self.client.list_messages(thread_id=self.thread.id)
        
        for msg in messages.data:
            if msg.role == MessageRole.ASSISTANT:
                for content in msg.content:
                    if isinstance(content, MessageTextContent):
                        return content.text.value
        
        return "응답을 생성할 수 없습니다."


class CombinedAgent(BaseAgent):
    """RAG + Tool Calling 통합 Agent"""
    
    def __init__(self, config: AzureConfig):
        super().__init__(config)
        self.search_helper: Optional[SearchHelper] = None
    
    async def initialize(self):
        """통합 Agent 초기화"""
        self.credential = DefaultAzureCredential()
        
        self.search_helper = SearchHelper(
            endpoint=self.config.search_endpoint,
            index_name=self.config.search_index_name,
            credential=self.credential,
            api_key=self.config.search_api_key,
        )
        
        self.client = AgentsClient(
            endpoint=self.config.project_endpoint,
            credential=self.credential,
        )
        
        self.agent = await self.client.create_agent(
            model=self.config.model_deployment_name,
            name="통합 Agent",
            instructions="""당신은 다음 기능을 갖춘 AI 어시스턴트입니다:
            1. Zava 회사 문서 기반 질문 답변 (RAG)
            2. 사칙연산 계산 (Tool Calling)
            
            사용자의 질문 유형에 따라 적절히 답변하세요.
            계산이 필요하면 제공된 도구를 사용하세요.
            한국어로 답변하세요.""",
            tools=CALCULATOR_TOOLS,
        )
        
        self.thread = await self.client.create_thread()
        
        logger.info(f"통합 Agent 초기화 완료: {self.agent.id}")
    
    async def chat(self, message: str) -> str:
        """통합 채팅 처리"""
        if not self.client or not self.agent or not self.thread:
            await self.initialize()
        
        # 검색이 필요한지 휴리스틱 판단 (간단한 방법)
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
        
        await self.client.create_message(
            thread_id=self.thread.id,
            role=MessageRole.USER,
            content=augmented_message,
        )
        
        run = await self.client.create_run(
            thread_id=self.thread.id,
            agent_id=self.agent.id,
        )
        
        while True:
            import asyncio
            await asyncio.sleep(0.5)
            run = await self.client.get_run(
                thread_id=self.thread.id,
                run_id=run.id,
            )
            
            if run.status == RunStatus.COMPLETED:
                break
            elif run.status == RunStatus.REQUIRES_ACTION:
                tool_outputs = []
                
                for tool_call in run.required_action.submit_tool_outputs.tool_calls:
                    function_name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)
                    result = execute_calculator_function(function_name, arguments)
                    
                    tool_outputs.append({
                        "tool_call_id": tool_call.id,
                        "output": result,
                    })
                
                run = await self.client.submit_tool_outputs(
                    thread_id=self.thread.id,
                    run_id=run.id,
                    tool_outputs=tool_outputs,
                )
            elif run.status in [RunStatus.FAILED, RunStatus.CANCELLED, RunStatus.EXPIRED]:
                return f"오류가 발생했습니다: {run.status}"
        
        messages = await self.client.list_messages(thread_id=self.thread.id)
        
        for msg in messages.data:
            if msg.role == MessageRole.ASSISTANT:
                for content in msg.content:
                    if isinstance(content, MessageTextContent):
                        return content.text.value
        
        return "응답을 생성할 수 없습니다."
    
    async def close(self):
        if self.search_helper:
            await self.search_helper.close()
        await super().close()
