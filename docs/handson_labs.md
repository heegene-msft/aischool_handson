# 🧪 Microsoft Agent Framework 핸즈온 Labs

이 문서는 Microsoft Agent Framework (MAF)를 사용한 핸즈온 Labs의 상세 가이드입니다.

---

## 📋 Labs 개요

| Lab | 제목 | 난이도 | 예상 시간 |
|-----|------|--------|-----------|
| Lab 0 | 환경 설정 | ⭐ | 20분 |
| Lab 1 | 기본 챗봇 만들기 | ⭐ | 30분 |
| Lab 2 | RAG 검색 추가하기 | ⭐⭐ | 40분 |
| Lab 3 | Tool Calling 구현하기 | ⭐⭐ | 40분 |
| Lab 4 | 통합 에이전트 만들기 | ⭐⭐⭐ | 30분 |

총 예상 시간: **약 2.5~3시간**

---

## Lab 0: 환경 설정

### 0.1 사전 요구 사항

- Azure 구독 (무료 체험 가능)
- Python 3.10 이상
- Node.js 18 이상
- VS Code (권장)
- Azure CLI 설치

### 0.2 Azure 리소스 생성 (Portal)

#### Microsoft Foundry 프로젝트 생성

1. [Microsoft Foundry Portal](https://ai.azure.com) 접속
2. **+ 새 프로젝트** 클릭
3. 프로젝트 이름 입력: `maf-handson`
4. 리전 선택: `Korea Central` 또는 `East US 2`
5. **만들기** 클릭

#### gpt-4o-mini 모델 배포

1. 프로젝트 > **모델 + 엔드포인트** > **모델 배포**
2. **gpt-4o-mini** 선택
3. 배포 이름: `gpt-4o-mini`
4. TPM: 30K (기본값)
5. **배포** 클릭

#### Azure AI Search 생성

1. Azure Portal > **리소스 만들기** > **Azure AI Search**
2. 서비스 이름: `search-maf-handson`
3. 가격 책정 계층: **기본(Basic)**
4. **검토 + 만들기** 클릭

### 0.3 로컬 환경 설정

```bash
# 저장소 클론
git clone <repository-url>
cd azure-search-openai-demo

# Python 가상 환경 생성
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 패키지 설치
pip install -r app/backend/requirements.txt

# 환경 변수 설정
cp app/backend/.env.sample app/backend/.env
```

### 0.4 환경 변수 설정

`app/backend/.env` 파일을 열고 값을 입력합니다:

```env
# Microsoft Foundry (Foundry Portal > 프로젝트 > 설정에서 확인)
AZURE_AI_PROJECT_ENDPOINT=https://your-project.services.ai.azure.com/api/projects/your-project-name
AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4o-mini

# Azure AI Search (Azure Portal > Search 서비스 > 개요에서 확인)
AZURE_SEARCH_SERVICE_ENDPOINT=https://your-search.search.windows.net
AZURE_SEARCH_INDEX_NAME=gptkbindex
```

### 0.5 Azure 로그인

```bash
# Azure CLI 로그인
az login

# 구독 확인
az account show
```

---

## Lab 1: 기본 챗봇 만들기

### 1.1 학습 목표

- Microsoft Agent Framework의 기본 구조 이해
- Azure AI Agent Service와 연동하는 방법
- 간단한 대화형 챗봇 구현

### 1.2 핵심 코드 분석

`app/backend/agents.py`의 `BaseAgent` 클래스를 살펴봅니다:

```python
class BaseAgent:
    """Lab 1: 기본 챗봇 에이전트"""
    
    def __init__(self, config: AzureConfig):
        self.config = config
        self.client = None
        self.agent = None
        
    async def initialize(self):
        # Azure AI Agent Service 클라이언트 생성
        self.client = AgentsClient(
            endpoint=self.config.project_endpoint,
            credential=DefaultAzureCredential()
        )
        
        # 에이전트 생성
        self.agent = await self.client.create_agent(
            model=self.config.model_deployment_name,
            name="maf-basic-chatbot",
            instructions="당신은 친절한 AI 어시스턴트입니다..."
        )
```

### 1.3 실습

1. **백엔드 실행**:
   ```bash
   cd app/backend
   python -m quart --app main:app run --port 50505 --reload
   ```

2. **API 테스트**:
   ```bash
   curl -X POST http://localhost:50505/api/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "안녕하세요!"}'
   ```

3. **Labs 페이지 테스트**:
   - 브라우저에서 `http://localhost:50505/#/labs` 접속
   - "기본 챗봇" 탭 선택
   - 메시지 입력 후 응답 확인

### 1.4 연습 문제

1. `instructions` 프롬프트를 수정해서 다른 페르소나의 챗봇을 만들어보세요.
2. 한국어로만 응답하도록 프롬프트를 수정해보세요.

---

## Lab 2: RAG 검색 추가하기

### 2.1 학습 목표

- RAG (Retrieval-Augmented Generation) 패턴 이해
- Azure AI Search 연동 방법
- 검색 결과를 활용한 답변 생성

### 2.2 데이터 인덱싱

```bash
# 데이터 폴더의 문서를 Azure AI Search에 인덱싱
./scripts/prepdocs.sh
```

### 2.3 핵심 코드 분석

`app/backend/search_helper.py`의 검색 로직:

```python
class SearchHelper:
    async def search(self, query: str, top_k: int = 3) -> list:
        results = await self.client.search(
            search_text=query,
            select=["content", "title", "sourcepage"],
            top=top_k
        )
        return [doc async for doc in results]
    
    def format_search_results(self, results: list) -> str:
        formatted = []
        for r in results:
            formatted.append(f"## {r['title']}\n{r['content']}\n")
        return "\n".join(formatted)
```

`app/backend/agents.py`의 `RAGAgent` 클래스:

```python
class RAGAgent(BaseAgent):
    """Lab 2: RAG 에이전트"""
    
    async def chat(self, message: str, thread_id: str = None) -> dict:
        # 1. 검색 수행
        search_results = await self.search_helper.search(message)
        context = self.search_helper.format_search_results(search_results)
        
        # 2. 컨텍스트와 함께 질문 구성
        augmented_message = f"""
다음 참고 자료를 바탕으로 질문에 답변하세요:

{context}

질문: {message}
"""
        # 3. 에이전트에게 전달
        return await super().chat(augmented_message, thread_id)
```

### 2.4 실습

1. **RAG 테스트**:
   ```bash
   curl -X POST http://localhost:50505/api/rag \
     -H "Content-Type: application/json" \
     -d '{"message": "Zava 회사에 대해 알려줘"}'
   ```

2. **Labs 페이지에서 테스트**:
   - "RAG 검색" 탭 선택
   - "Zava의 주요 제품은 무엇인가요?" 입력

### 2.5 연습 문제

1. `top_k` 값을 변경해서 검색 결과 수가 답변에 미치는 영향을 확인하세요.
2. 검색 결과가 없을 때 다른 응답을 하도록 수정해보세요.

---

## Lab 3: Tool Calling 구현하기

### 3.1 학습 목표

- Function Calling (Tool Calling) 패턴 이해
- 사칙연산 도구 정의 및 구현
- LLM이 도구를 호출하는 과정 이해

### 3.2 핵심 코드 분석

`app/backend/tools/calculator.py`의 도구 정의:

```python
def add(a: float, b: float) -> float:
    """두 숫자를 더합니다."""
    return a + b

CALCULATOR_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "add",
            "description": "두 숫자를 더합니다",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "number", "description": "첫 번째 숫자"},
                    "b": {"type": "number", "description": "두 번째 숫자"}
                },
                "required": ["a", "b"]
            }
        }
    },
    # ... multiply, subtract, divide
]
```

`app/backend/agents.py`의 `ToolAgent` 클래스:

```python
class ToolAgent(BaseAgent):
    """Lab 3: Tool Calling 에이전트"""
    
    async def initialize(self):
        self.agent = await self.client.create_agent(
            model=self.config.model_deployment_name,
            name="maf-tool-agent",
            instructions="계산기 도구를 사용해서 수학 문제를 풀어주세요.",
            tools=CALCULATOR_TOOLS  # 도구 등록
        )
```

### 3.3 실습

1. **Tool Calling 테스트**:
   ```bash
   curl -X POST http://localhost:50505/api/tools \
     -H "Content-Type: application/json" \
     -d '{"message": "123 곱하기 456은?"}'
   ```

2. **복잡한 계산**:
   - "100에서 30을 빼고 5를 곱하면?"
   - "1234 나누기 7의 결과는?"

### 3.4 도구 추가 실습

`app/backend/tools/calculator.py`에 새로운 도구를 추가해보세요:

```python
def power(base: float, exponent: float) -> float:
    """거듭제곱을 계산합니다."""
    return base ** exponent

# CALCULATOR_TOOLS에 추가
{
    "type": "function",
    "function": {
        "name": "power",
        "description": "거듭제곱을 계산합니다 (base^exponent)",
        "parameters": {
            "type": "object",
            "properties": {
                "base": {"type": "number", "description": "밑"},
                "exponent": {"type": "number", "description": "지수"}
            },
            "required": ["base", "exponent"]
        }
    }
}
```

### 3.5 연습 문제

1. 제곱근(sqrt) 도구를 추가해보세요.
2. 퍼센트 계산(percent) 도구를 추가해보세요.

---

## Lab 4: 통합 에이전트 만들기

### 4.1 학습 목표

- RAG + Tool Calling 통합
- 복잡한 에이전트 워크플로우 설계
- 실제 비즈니스 시나리오 적용

### 4.2 핵심 코드 분석

`app/backend/agents.py`의 `CombinedAgent` 클래스:

```python
class CombinedAgent(BaseAgent):
    """Lab 4: RAG + Tool Calling 통합 에이전트"""
    
    async def initialize(self):
        # RAG를 위한 검색 헬퍼
        self.search_helper = SearchHelper(
            self.config.search_endpoint,
            self.config.search_index_name
        )
        
        # 도구 + 검색 결합
        self.agent = await self.client.create_agent(
            model=self.config.model_deployment_name,
            name="maf-combined-agent",
            instructions="""
당신은 Zava 회사의 AI 어시스턴트입니다.
- 회사 정보 질문: 제공된 참고 자료를 활용하세요
- 수학 계산 요청: 계산기 도구를 사용하세요
항상 정확하고 친절하게 답변하세요.
            """,
            tools=CALCULATOR_TOOLS
        )
```

### 4.3 실습

1. **통합 에이전트 테스트**:
   ```bash
   curl -X POST http://localhost:50505/api/combined \
     -H "Content-Type: application/json" \
     -d '{"message": "Zava 직원 수가 100명이고 연봉 평균이 5000만원이면 총 인건비는?"}'
   ```

2. **복합 질문 테스트**:
   - "Zava의 제품 가격이 10만원이고 20% 할인하면 얼마야?"
   - "회사 개요를 알려주고, 직원 1인당 매출이 1억이면 전체 매출은?"

### 4.4 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                    CombinedAgent                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    │
│   │   검색      │    │   LLM       │    │   도구      │    │
│   │ (AI Search) │◄──►│ (gpt-4o)   │◄──►│ (Calculator)│    │
│   └─────────────┘    └─────────────┘    └─────────────┘    │
│         ▲                   │                  │            │
│         │                   │                  │            │
│         └───────────────────┴──────────────────┘            │
│                             │                               │
└─────────────────────────────┼───────────────────────────────┘
                              │
                        ┌─────┴─────┐
                        │   사용자   │
                        └───────────┘
```

### 4.5 연습 문제

1. 날씨 API를 연동하는 도구를 추가해보세요.
2. 데이터베이스 조회 도구를 추가해보세요.

---

## 🎯 핸즈온 완료 체크리스트

- [ ] Microsoft Foundry 프로젝트 생성
- [ ] gpt-4o-mini 모델 배포
- [ ] Azure AI Search 서비스 생성
- [ ] 로컬 환경 설정 완료
- [ ] Lab 1: 기본 챗봇 테스트
- [ ] Lab 2: RAG 검색 테스트
- [ ] Lab 3: Tool Calling 테스트
- [ ] Lab 4: 통합 에이전트 테스트
- [ ] (선택) 새로운 도구 추가

---

## 📚 추가 학습 자료

- [Microsoft Agent Framework 공식 문서](https://learn.microsoft.com/azure/ai-services/agents)
- [Azure AI Search 문서](https://learn.microsoft.com/azure/search)
- [Microsoft Foundry 포털](https://ai.azure.com)
- [RAG 패턴 가이드](https://learn.microsoft.com/azure/search/retrieval-augmented-generation-overview)
