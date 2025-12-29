"""
Azure AI Search RAG Helper
AI Search를 활용한 검색 및 RAG 기능
"""
import json
import logging
from typing import Optional

from azure.identity.aio import DefaultAzureCredential
from azure.search.documents.aio import SearchClient
from azure.search.documents.models import VectorizedQuery

logger = logging.getLogger(__name__)


class SearchHelper:
    """Azure AI Search를 활용한 RAG 검색 헬퍼"""
    
    def __init__(
        self,
        endpoint: str,
        index_name: str,
        credential: Optional[DefaultAzureCredential] = None,
        api_key: Optional[str] = None,
    ):
        self.endpoint = endpoint
        self.index_name = index_name
        self.credential = credential
        self.api_key = api_key
        self._client: Optional[SearchClient] = None
    
    async def _get_client(self) -> SearchClient:
        """SearchClient 인스턴스 반환"""
        if self._client is None:
            if self.api_key:
                from azure.core.credentials import AzureKeyCredential
                self._client = SearchClient(
                    endpoint=self.endpoint,
                    index_name=self.index_name,
                    credential=AzureKeyCredential(self.api_key),
                )
            else:
                self._client = SearchClient(
                    endpoint=self.endpoint,
                    index_name=self.index_name,
                    credential=self.credential or DefaultAzureCredential(),
                )
        return self._client
    
    async def search(
        self,
        query: str,
        top: int = 5,
        filter_expression: Optional[str] = None,
    ) -> list[dict]:
        """
        하이브리드 검색 수행 (키워드 + 시멘틱)
        
        Args:
            query: 검색 쿼리
            top: 반환할 결과 수
            filter_expression: OData 필터 표현식
            
        Returns:
            검색 결과 리스트
        """
        client = await self._get_client()
        
        try:
            results = await client.search(
                search_text=query,
                top=top,
                filter=filter_expression,
                query_type="semantic",
                semantic_configuration_name="default",
                select=["id", "content", "title", "sourcefile"],
            )
            
            documents = []
            async for result in results:
                documents.append({
                    "id": result.get("id", ""),
                    "content": result.get("content", ""),
                    "title": result.get("title", ""),
                    "source": result.get("sourcefile", ""),
                    "score": result.get("@search.score", 0),
                })
            
            logger.info(f"검색 완료: {len(documents)}개 문서 발견")
            return documents
            
        except Exception as e:
            logger.error(f"검색 오류: {e}")
            # Fallback to simple search
            try:
                results = await client.search(
                    search_text=query,
                    top=top,
                    filter=filter_expression,
                )
                
                documents = []
                async for result in results:
                    documents.append({
                        "id": result.get("id", ""),
                        "content": result.get("content", ""),
                        "title": result.get("title", ""),
                        "source": result.get("sourcefile", ""),
                        "score": result.get("@search.score", 0),
                    })
                return documents
            except Exception as e2:
                logger.error(f"Fallback 검색도 실패: {e2}")
                return []
    
    def format_search_results(self, results: list[dict]) -> str:
        """
        검색 결과를 LLM 컨텍스트용 문자열로 변환
        
        Args:
            results: 검색 결과 리스트
            
        Returns:
            포맷된 문자열
        """
        if not results:
            return "관련 문서를 찾을 수 없습니다."
        
        formatted = []
        for i, doc in enumerate(results, 1):
            formatted.append(f"[문서 {i}] (출처: {doc.get('source', 'Unknown')})")
            formatted.append(doc.get("content", "")[:1000])
            formatted.append("")
        
        return "\n".join(formatted)
    
    async def close(self):
        """클라이언트 종료"""
        if self._client:
            await self._client.close()
            self._client = None


# RAG 시스템 프롬프트
RAG_SYSTEM_PROMPT = """당신은 Zava 회사의 문서를 기반으로 질문에 답변하는 도움이 되는 AI 어시스턴트입니다.

다음 지침을 따라주세요:
1. 제공된 문서 내용만을 기반으로 답변하세요.
2. 문서에서 답을 찾을 수 없는 경우, "제공된 문서에서 해당 정보를 찾을 수 없습니다."라고 답변하세요.
3. 답변할 때는 출처 문서를 언급해주세요.
4. 한국어로 답변하세요.

## 검색된 문서 내용:
{context}
"""
