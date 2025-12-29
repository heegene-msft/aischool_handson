# 🎯 Microsoft Foundry Agent 핸즈온 워크샵

**Microsoft Agent Framework(MAF)를 활용한 AI Agent 개발 실습**

> ⏱️ 소요 시간: 약 3시간  
> 📊 난이도: L200-300 (중급)  
> 🎓 대상: Azure AI 서비스에 관심 있는 개발자

---

## 📋 워크샵 개요

이 워크샵에서는 **Microsoft Agent Framework(MAF)**를 사용하여 다양한 AI Agent를 직접 구축합니다.

### 학습 목표

| Lab | 내용 | 시간 |
|-----|------|------|
| **Lab 0** | Microsoft Foundry 프로젝트 생성 및 환경 설정 | 20분 |
| **Lab 1** | 기본 챗봇 구현 | 30분 |
| **Lab 2** | RAG(Retrieval Augmented Generation) 챗봇 - Azure AI Search 연동 | 40분 |
| **Lab 3** | Tool Calling - 사칙연산 함수 호출 | 40분 |
| **Lab 4** | (선택) Azure Container Apps 배포 | 30분 |

### 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React)                         │
│                    http://localhost:5173/#/labs                 │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Backend (Python/Quart)                      │
│                    http://localhost:50505                       │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                  Microsoft Agent Framework                  │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │ │
│  │  │ BaseAgent    │  │  RAGAgent    │  │  ToolAgent   │     │ │
│  │  │ (Lab 1)      │  │  (Lab 2)     │  │  (Lab 3)     │     │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘     │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                    │                       │
                    ▼                       ▼
    ┌───────────────────────────┐    ┌──────────────────────┐
    │   Microsoft Foundry       │    │  Azure AI Search     │
    │   (Agent Service)         │    │  (RAG용 벡터 인덱스)  │
    │   - gpt-4o-mini           │    └──────────────────────┘
    └───────────────────────────┘
```

---

## 🚀 사전 준비 사항

### 필수 소프트웨어

- **Python 3.10+** - [다운로드](https://www.python.org/downloads/)
- **Node.js 18+** - [다운로드](https://nodejs.org/)
- **Azure CLI** - [설치 가이드](https://learn.microsoft.com/ko-kr/cli/azure/install-azure-cli)
- **Git** - [다운로드](https://git-scm.com/)
- **VS Code** (권장) - [다운로드](https://code.visualstudio.com/)

### Azure 리소스

| 리소스 | 용도 | 필수 |
|--------|------|:----:|
| Microsoft Foundry 프로젝트 | Agent Service 호스팅 | ✅ |
| gpt-4o-mini 모델 배포 | LLM 추론 | ✅ |
| Azure AI Search | RAG용 벡터 검색 | Lab 2 |

---

## 📖 Lab 0: 환경 설정 (20분)

### Step 1: Microsoft Foundry 프로젝트 생성

1. **[Microsoft Foundry Portal](https://ai.azure.com)** 접속 및 로그인

2. **새 프로젝트 생성**:
   - 좌측 메뉴에서 **"프로젝트"** 선택
   - **"+ 새 프로젝트"** 클릭
   - 프로젝트 이름: `maf-handson-{이니셜}`
   - 리전: `Korea Central` 또는 `East US 2`
   - **"만들기"** 클릭

3. **Endpoint 확인**:
   - 프로젝트 > **설정** > **프로젝트 속성**
   - `프로젝트 엔드포인트` 복사 (나중에 사용)
   - 형식: `https://<resource>.services.ai.azure.com/api/projects/<project-id>`

### Step 2: gpt-4o-mini 모델 배포

1. 프로젝트 > **모델 + 엔드포인트** 선택
2. **"+ 모델 배포"** > **"기본 모델"** 선택
3. `gpt-4o-mini` 검색 후 선택
4. 배포 이름: `gpt-4o-mini`
5. **"배포"** 클릭

### Step 3: Azure AI Search 생성 (Lab 2용)

1. **[Azure Portal](https://portal.azure.com)** 접속
2. **"리소스 만들기"** > `Azure AI Search` 검색
3. 설정:
   - 서비스 이름: `search-maf-{이니셜}`
   - 가격 계층: **Basic** (핸즈온용)
4. **"검토 + 만들기"** → **"만들기"**

### Step 4: 로컬 환경 설정

```bash
# 1. 저장소 클론
git clone <repository-url>
cd azure-search-openai-demo

# 2. Python 가상환경 생성 및 활성화
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. 백엔드 패키지 설치
pip install -r app/backend/requirements.txt

# 4. 프론트엔드 패키지 설치
cd app/frontend
npm install
cd ../..
```

### Step 5: 환경 변수 설정

```bash
# .env 파일 생성
cp app/backend/.env.sample app/backend/.env
```

`app/backend/.env` 파일 편집:

```env
# Microsoft Foundry Project (Foundry Portal > 프로젝트 > 설정에서 확인)
AZURE_AI_PROJECT_ENDPOINT=https://your-resource.services.ai.azure.com/api/projects/your-project-id
AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4o-mini

# Azure AI Search (Azure Portal > AI Search > 개요에서 확인)
AZURE_SEARCH_SERVICE_ENDPOINT=https://your-search.search.windows.net
AZURE_SEARCH_INDEX_NAME=gptkbindex
```

### Step 6: Azure 로그인

```bash
az login
```

---

## 🤖 Lab 1: 기본 챗봇 (30분)

### 목표
Microsoft Agent Framework의 `AgentsClient`를 사용하여 기본 대화형 챗봇을 구현합니다.

### 핵심 코드: `app/backend/agents.py`

```python
from azure.ai.agents.aio import AgentsClient
from azure.identity.aio import DefaultAzureCredential

class BaseAgent:
    """기본 Agent 클래스 - Lab 1용"""
    
    async def initialize(self):
        # Azure 인증
        self.credential = DefaultAzureCredential()
        
        # Agent Service 클라이언트 생성
        self.client = AgentsClient(
            endpoint=self.config.project_endpoint,
            credential=self.credential,
        )
        
        # Agent 생성
        self.agent = await self.client.create_agent(
            model=self.config.model_deployment_name,
            name="기본 챗봇",
            instructions="당신은 친절하고 도움이 되는 AI 어시스턴트입니다.",
        )
        
        # 대화 스레드 생성
        self.thread = await self.client.create_thread()
    
    async def chat(self, message: str) -> str:
        # 메시지 추가
        await self.client.create_message(
            thread_id=self.thread.id,
            role=MessageRole.USER,
            content=message,
        )
        
        # Agent 실행 및 응답 대기
        run = await self.client.create_run(
            thread_id=self.thread.id,
            agent_id=self.agent.id,
        )
        # ... 응답 처리
```

### 실습

**터미널 1 - 백엔드 실행:**
```bash
cd app/backend
python -m quart --app app:app run --port 50505 --reload
```

**터미널 2 - CLI 테스트:**
```bash
cd app/backend
python test_agents.py basic
```

**예상 출력:**
```
🤖 Lab 1: 기본 챗봇 테스트
==================================================

✅ 응답:
안녕하세요! 저는 AI 어시스턴트입니다. 무엇을 도와드릴까요?
```

### 📝 실습 과제

`agents.py`의 `BaseAgent.initialize()` 메서드에서 `instructions`를 수정하여:
1. 특정 페르소나(예: 요리사, 여행 가이드)를 가진 챗봇 만들기
2. 특정 언어로만 응답하도록 설정하기

---

## 📚 Lab 2: RAG 챗봇 (40분)

### 목표
Azure AI Search를 연동하여 문서 기반 질의응답(RAG) 시스템을 구현합니다.

### Step 1: 데이터 인덱싱

샘플 데이터 `data/Zava_Company_Overview.md`를 Azure AI Search에 인덱싱:

```bash
# prepdocs 스크립트 실행
./scripts/prepdocs.sh
```

또는 Azure Portal에서 수동 설정:
1. AI Search > **데이터 가져오기**
2. 데이터 원본: Blob Storage 또는 직접 업로드
3. 인덱스 이름: `gptkbindex`

### 핵심 코드: RAGAgent

```python
class RAGAgent(BaseAgent):
    """RAG Agent - Lab 2용"""
    
    async def chat(self, message: str) -> str:
        # 1. Azure AI Search에서 관련 문서 검색
        search_results = await self.search_helper.search(message, top=3)
        context = self.search_helper.format_search_results(search_results)
        
        # 2. 검색 결과를 컨텍스트로 포함
        augmented_message = f"""
## 사용자 질문:
{message}

## 검색된 관련 문서:
{context}

위 문서를 참고하여 답변해주세요.
"""
        
        # 3. Agent에게 전달하여 응답 생성
        # ...
```

### 실습

```bash
python test_agents.py rag
```

**예상 출력:**
```
📚 Lab 2: RAG 챗봇 테스트
==================================================

✅ 응답:
Zava는 1985년에 설립된 기술 회사입니다...

📚 출처: Zava_Company_Overview.md
```

### 📝 실습 과제

다양한 질문 시도:
- "Zava의 핵심 가치는?"
- "휴가 정책에 대해 알려주세요"
- "직원 복지 프로그램이 있나요?"

---

## 🔧 Lab 3: Tool Calling (40분)

### 목표
Function Calling을 사용하여 사칙연산 기능을 가진 Agent를 구현합니다.

### Tool 정의: `app/backend/tools/calculator.py`

```python
# 함수 구현
def add(a: float, b: float) -> float:
    """두 숫자를 더합니다."""
    return a + b

def multiply(a: float, b: float) -> float:
    """두 숫자를 곱합니다."""
    return a * b

# Tool 스키마 정의 (OpenAI Function Calling 형식)
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
    # ... subtract, multiply, divide
]
```

### ToolAgent 동작 흐름

```
1. 사용자: "123 + 456은?"
2. Agent → LLM: 질문 분석
3. LLM: "add 함수 호출 필요" (name: "add", args: {a: 123, b: 456})
4. Agent: add(123, 456) 실행 → 579
5. Agent → LLM: 결과 전달
6. LLM → 사용자: "123 + 456 = 579입니다"
```

### 핵심 코드: ToolAgent

```python
class ToolAgent(BaseAgent):
    async def initialize(self):
        self.agent = await self.client.create_agent(
            model=self.config.model_deployment_name,
            name="계산기 Agent",
            instructions="사칙연산을 수행하는 AI입니다.",
            tools=CALCULATOR_TOOLS,  # 🔑 Tool 등록
        )
    
    async def chat(self, message: str) -> str:
        # ... Run 생성 후
        
        if run.status == RunStatus.REQUIRES_ACTION:
            # Tool 호출 처리
            for tool_call in run.required_action.submit_tool_outputs.tool_calls:
                result = execute_calculator_function(
                    tool_call.function.name,
                    json.loads(tool_call.function.arguments)
                )
                # 결과를 Agent에게 반환
```

### 실습

```bash
python test_agents.py tools
```

**예상 출력:**
```
🔧 Lab 3: Tool Calling 테스트
==================================================

📝 질문: 123 더하기 456은?
✅ 응답: 123 + 456 = 579입니다.

📝 질문: 25 곱하기 4는?
✅ 응답: 25 × 4 = 100입니다.
```

### 📝 실습 과제

`tools/calculator.py`에 새로운 Tool 추가:
- `power(base, exponent)` - 거듭제곱
- `sqrt(n)` - 제곱근
- `modulo(a, b)` - 나머지

---

## 🖥️ Frontend에서 테스트

### 실행

**터미널 1:**
```bash
cd app/backend
python -m quart --app app:app run --port 50505 --reload
```

**터미널 2:**
```bash
cd app/frontend
npm run dev
```

### Labs 페이지 접속

브라우저에서 **http://localhost:5173/#/labs** 접속

- **기본 챗봇** 탭: Lab 1 테스트
- **RAG 검색** 탭: Lab 2 테스트  
- **Tool Calling** 탭: Lab 3 테스트
- **통합 Agent** 탭: RAG + Tool Calling

---

## 🚀 Lab 4: Azure Container Apps 배포 (선택)

### 사전 요구사항

```bash
# Azure Developer CLI 설치
# macOS
brew install azure-dev

# Windows
winget install Microsoft.Azd
```

### 배포

```bash
# 핸즈온용 azure.yaml 사용
cp azure.handson.yaml azure.yaml

# Azure 로그인
azd auth login

# 환경 초기화 및 배포
azd up
```

---

## 📚 참고 자료

### 공식 문서
- [Microsoft Agent Framework](https://learn.microsoft.com/en-us/agent-framework/)
- [Microsoft Foundry Agent Service](https://learn.microsoft.com/en-us/azure/ai-foundry/agents/overview)
- [Azure AI Search](https://learn.microsoft.com/en-us/azure/search/)
- [Function Calling](https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/function-calling)

### GitHub
- [Agent Framework Repository](https://github.com/microsoft/agent-framework)
- [Azure AI Samples](https://github.com/Azure-Samples)

---

## ❓ 문제 해결

### "Unauthorized" 오류
```bash
# Azure CLI 재로그인
az login

# 권한 확인 (Cognitive Services User 역할 필요)
az role assignment list --assignee <your-email>
```

### 검색 결과가 없음
- Azure Portal에서 인덱스 생성 확인
- 인덱스 이름이 `.env`의 `AZURE_SEARCH_INDEX_NAME`과 일치하는지 확인

### Tool이 호출되지 않음
- "계산해줘", "더해줘" 등 명시적인 요청 사용
- Tool 스키마의 `description`이 명확한지 확인

---

## 🎉 워크샵 완료!

축하합니다! Microsoft Agent Framework로 AI Agent를 구축해보셨습니다.

### 다음 단계
- 🔗 Multi-Agent 시스템 구축
- 🌐 외부 API 연동 Tool 추가
- 📊 Azure Monitor로 모니터링 설정
- 🔒 Production 배포 및 보안 설정

피드백이나 질문은 Issue로 등록해주세요! 🙏
