"""
MAF 기반 챗봇 백엔드 애플리케이션
Microsoft Agent Framework를 활용한 핸즈온 워크샵용
"""
import logging
import os
from typing import Optional

from dotenv import load_dotenv
from quart import Quart, jsonify, request, send_from_directory
from quart_cors import cors

from config import load_config, AzureConfig
from agents import BaseAgent, RAGAgent, ToolAgent, CombinedAgent, WebSearchAgent, OrchestratorAgent

# 환경변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Quart 앱 생성
app = Quart(__name__, static_folder="../frontend/dist", static_url_path="")
app = cors(app, allow_origin="*")

# 전역 Agent 인스턴스
agents: dict = {}
config: Optional[AzureConfig] = None


@app.before_serving
async def startup():
    """앱 시작시 초기화"""
    global config
    azure_config, app_config = load_config()
    config = azure_config
    logger.info("Configuration loaded successfully")
    if config.project_endpoint:
        logger.info(f"Project Endpoint: {config.project_endpoint[:50]}...")


@app.after_serving
async def shutdown():
    """앱 종료시 정리"""
    for agent in agents.values():
        await agent.close()
    logger.info("All agents closed")


# ============================================================
# API 엔드포인트
# ============================================================

@app.route("/")
async def index():
    """프론트엔드 서빙"""
    return await send_from_directory(app.static_folder, "index.html")


@app.route("/config")
async def get_config():
    """클라이언트 설정 반환"""
    return jsonify({
        "showDeveloperSettings": True,
        "streaming": False,  # 핸즈온에서는 간단히 비스트리밍
        "features": {
            "chat": True,
            "rag": True,
            "tools": True,
        },
        "labs": {
            "lab1_basic": True,
            "lab2_rag": True,
            "lab3_tools": True,
        }
    })


@app.route("/api/chat", methods=["POST"])
@app.route("/api/basic", methods=["POST"])
async def chat():
    """
    Lab 1: 기본 채팅
    """
    global agents, config
    
    data = await request.get_json()
    message = data.get("message", "")
    session_id = data.get("session_id", "default")
    
    if not message:
        return jsonify({"error": "메시지가 비어있습니다."}), 400
    
    # Agent 인스턴스 가져오기 또는 생성
    agent_key = f"basic_{session_id}"
    if agent_key not in agents:
        agents[agent_key] = BaseAgent(config)
    
    try:
        response = await agents[agent_key].chat(message)
        return jsonify({
            "response": response,
            "agent_type": "basic",
        })
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/rag", methods=["POST"])
async def rag_chat():
    """
    Lab 2: RAG 채팅 (AI Search 기반)
    """
    global agents, config
    
    data = await request.get_json()
    message = data.get("message", "")
    session_id = data.get("session_id", "default")
    
    if not message:
        return jsonify({"error": "메시지가 비어있습니다."}), 400
    
    agent_key = f"rag_{session_id}"
    if agent_key not in agents:
        agents[agent_key] = RAGAgent(config)
    
    try:
        response = await agents[agent_key].chat(message)
        return jsonify({
            "response": response,
            "agent_type": "rag",
        })
    except Exception as e:
        logger.error(f"RAG chat error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/tools", methods=["POST"])
async def tools_chat():
    """
    Lab 3: Tool Calling 채팅 (사칙연산)
    """
    global agents, config
    
    data = await request.get_json()
    message = data.get("message", "")
    session_id = data.get("session_id", "default")
    
    if not message:
        return jsonify({"error": "메시지가 비어있습니다."}), 400
    
    agent_key = f"tool_{session_id}"
    if agent_key not in agents:
        agents[agent_key] = ToolAgent(config)
    
    try:
        response = await agents[agent_key].chat(message)
        return jsonify({
            "response": response,
            "agent_type": "tools",
        })
    except Exception as e:
        logger.error(f"Tools chat error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/combined", methods=["POST"])
async def combined_chat():
    """
    통합 채팅 (RAG + Tools)
    """
    global agents, config
    
    data = await request.get_json()
    message = data.get("message", "")
    session_id = data.get("session_id", "default")
    
    if not message:
        return jsonify({"error": "메시지가 비어있습니다."}), 400
    
    agent_key = f"combined_{session_id}"
    if agent_key not in agents:
        agents[agent_key] = CombinedAgent(config)
    
    try:
        response = await agents[agent_key].chat(message)
        return jsonify({
            "response": response,
            "agent_type": "combined",
        })
    except Exception as e:
        logger.error(f"Combined chat error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/websearch", methods=["POST"])
async def websearch_chat():
    """
    Lab 4: Web Search 채팅 (Bing Search Grounding)
    """
    global agents, config
    
    data = await request.get_json()
    message = data.get("message", "")
    session_id = data.get("session_id", "default")
    
    if not message:
        return jsonify({"error": "메시지가 비어있습니다."}), 400
    
    agent_key = f"websearch_{session_id}"
    if agent_key not in agents:
        agents[agent_key] = WebSearchAgent(config)
    
    try:
        response = await agents[agent_key].chat(message)
        return jsonify({
            "response": response,
            "agent_type": "websearch",
        })
    except Exception as e:
        logger.error(f"Web Search chat error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/orchestrator", methods=["POST"])
async def orchestrator_chat():
    """
    Lab 5: 오케스트레이터 채팅 (멀티에이전트 라우팅)
    """
    global agents, config
    
    data = await request.get_json()
    message = data.get("message", "")
    session_id = data.get("session_id", "default")
    
    if not message:
        return jsonify({"error": "메시지가 비어있습니다."}), 400
    
    agent_key = f"orchestrator_{session_id}"
    if agent_key not in agents:
        agents[agent_key] = OrchestratorAgent(config)
    
    try:
        response = await agents[agent_key].chat(message)
        return jsonify({
            "response": response,
            "agent_type": "orchestrator",
        })
    except Exception as e:
        logger.error(f"Orchestrator chat error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/reset", methods=["POST"])
async def reset_session():
    """세션 리셋 - 새로운 대화 시작 및 에이전트 삭제"""
    global agents
    
    data = await request.get_json()
    session_id = data.get("session_id", "default")
    agent_type = data.get("agent_type")  # 특정 타입만 리셋 (optional)
    
    removed_count = 0
    
    # 해당 세션의 Agent 정리
    if agent_type:
        # 특정 타입만 리셋
        key = f"{agent_type}_{session_id}"
        if key in agents:
            try:
                await agents[key].close()
            except Exception as e:
                logger.warning(f"Agent close warning: {e}")
            del agents[key]
            removed_count = 1
            logger.info(f"Agent {key} 삭제됨")
    else:
        # 해당 세션의 모든 Agent 정리
        keys_to_remove = [k for k in agents.keys() if k.endswith(f"_{session_id}")]
        for key in keys_to_remove:
            try:
                await agents[key].close()
            except Exception as e:
                logger.warning(f"Agent close warning for {key}: {e}")
            del agents[key]
            logger.info(f"Agent {key} 삭제됨")
        removed_count = len(keys_to_remove)
    
    return jsonify({
        "message": "세션이 리셋되었습니다.",
        "session_id": session_id,
        "removed_count": removed_count
    })


@app.route("/health")
async def health():
    """헬스체크"""
    return jsonify({"status": "healthy"})


@app.route("/auth_setup")
async def auth_setup():
    """인증 설정 - 핸즈온에서는 인증 비활성화"""
    return jsonify({
        "useLogin": False,
        "requireAccessControl": False,
        "enableLogout": False,
    })


# ============================================================
# 기존 API 호환성 (프론트엔드와 호환)
# ============================================================

@app.route("/chat", methods=["POST"])
async def legacy_chat():
    """기존 chat API 호환"""
    data = await request.get_json()
    messages = data.get("messages", [])
    
    if not messages:
        return jsonify({"error": "messages required"}), 400
    
    # 마지막 사용자 메시지 추출
    last_message = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            last_message = msg.get("content", "")
            break
    
    # RAG Agent 사용
    global agents, config
    agent_key = "rag_legacy"
    if agent_key not in agents:
        agents[agent_key] = RAGAgent(config)
    
    try:
        response = await agents[agent_key].chat(last_message)
        return jsonify({
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": response
                }
            }]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/ask", methods=["POST"])
async def legacy_ask():
    """기존 ask API 호환"""
    return await legacy_chat()


# ============================================================
# 메인
# ============================================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=50505, debug=True)
