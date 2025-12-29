"""
Azure AI Search RAG Helper
AI Search를 활용한 검색 및 RAG 기능
"""
import base64
import json
import logging
from typing import Optional
from urllib.parse import unquote

from azure.identity.aio import DefaultAzureCredential
from azure.search.documents.aio import SearchClient
from azure.search.documents.models import VectorizedQuery

logger = logging.getLogger(__name__)


def decode_parent_id(parent_id: str) -> str:
    """
    Portal에서 생성된 parent_id (Base64 인코딩된 URL)를 디코딩하여 파일명 추출
    예: aHR0cHM6Ly8uLi4vWmF2YV9Db21wYW55X092ZXJ2aWV3Lm1kOzc1 
        -> Zava_Company_Overview.md
    """
    try:
        # Base64 디코딩
        decoded = base64.b64decode(parent_id).decode('utf-8')
        # URL에서 파일명만 추출 (예: https://.../data/Zava_Company_Overview.md;75)
        # 세미콜론 이전까지 자르고 마지막 / 이후 부분 추출
        path = decoded.split(';')[0] if ';' in decoded else decoded
        filename = path.split('/')[-1]
        return unquote(filename)  # URL 인코딩 해제
    except Exception:
        # 디코딩 실패시 원본 반환
        return parent_id


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
        
        # Portal "Import and vectorize data"로 생성된 인덱스 필드명:
        # chunk_id, parent_id, chunk, title, text_vector
        # Semantic configuration: {index_name}-semantic-configuration
        try:
            results = await client.search(
                search_text=query,
                top=top,
                filter=filter_expression,
                query_type="semantic",
                semantic_configuration_name=f"{self.index_name}-semantic-configuration",
                select=["chunk_id", "chunk", "title", "parent_id"],
            )
            
            documents = []
            async for result in results:
                # parent_id는 Base64 인코딩된 URL이므로 디코딩하여 파일명 추출
                parent_id = result.get("parent_id", "")
                source = decode_parent_id(parent_id) if parent_id else ""
                
                documents.append({
                    "id": result.get("chunk_id", ""),
                    "content": result.get("chunk", ""),
                    "title": result.get("title", ""),
                    "source": source,
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
                    parent_id = result.get("parent_id", "")
                    source = decode_parent_id(parent_id) if parent_id else ""
                    
                    documents.append({
                        "id": result.get("chunk_id", ""),
                        "content": result.get("chunk", ""),
                        "title": result.get("title", ""),
                        "source": source,
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
