"""
간단한 CLI 테스트 스크립트
핸즈온에서 백엔드 테스트용
"""
import asyncio
import sys
import os

# 프로젝트 경로 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from config import load_config
from agents import BaseAgent, RAGAgent, ToolAgent, CombinedAgent


async def test_basic_agent():
    """Lab 1: 기본 Agent 테스트"""
    print("\n" + "="*50)
    print("Lab 1: 기본 챗봇 테스트")
    print("="*50)
    
    config, _ = load_config()
    agent = BaseAgent(config)
    
    try:
        response = await agent.chat("안녕하세요! 자기소개를 해주세요.")
        print(f"\n[응답]\n{response}")
    finally:
        await agent.close()


async def test_rag_agent():
    """Lab 2: RAG Agent 테스트"""
    print("\n" + "="*50)
    print("Lab 2: RAG 챗봇 테스트")
    print("="*50)
    
    config, _ = load_config()
    agent = RAGAgent(config)
    
    try:
        response = await agent.chat("Java 역사에 대해 알려주세요")
        print(f"\n[응답]\n{response}")
    finally:
        await agent.close()


async def test_tool_agent():
    """Lab 3: Tool Agent 테스트"""
    print("\n" + "="*50)
    print("Lab 3: Tool Calling 테스트")
    print("="*50)
    
    config, _ = load_config()
    agent = ToolAgent(config)
    
    try:
        # 사칙연산 테스트
        questions = [
            "123 더하기 456은 얼마인가요?",
            "1000에서 350을 빼면?",
            "25 곱하기 4는?",
            "100을 25로 나누면?",
        ]
        
        for q in questions:
            print(f"\n[질문] {q}")
            response = await agent.chat(q)
            print(f"[응답] {response}")
    finally:
        await agent.close()


async def test_combined_agent():
    """통합 Agent 테스트"""
    print("\n" + "="*50)
    print("통합 Agent 테스트")
    print("="*50)
    
    config, _ = load_config()
    agent = CombinedAgent(config)
    
    try:
        questions = [
            "Zava 회사의 휴가 정책에 대해 알려주세요.",
            "15 곱하기 8은?",
        ]
        
        for q in questions:
            print(f"\n[질문] {q}")
            response = await agent.chat(q)
            print(f"[응답] {response}")
    finally:
        await agent.close()


async def interactive_mode():
    """대화형 모드"""
    print("\n" + "="*50)
    print("💬 대화형 모드")
    print("="*50)
    print("Agent 타입 선택:")
    print("1. 기본 챗봇 (Lab 1)")
    print("2. RAG 챗봇 (Lab 2)")
    print("3. Tool Calling (Lab 3)")
    print("4. 통합 Agent")
    print("q. 종료")
    
    choice = input("\n선택: ").strip()
    
    if choice == 'q':
        return
    
    config, _ = load_config()
    
    agent_map = {
        '1': BaseAgent,
        '2': RAGAgent,
        '3': ToolAgent,
        '4': CombinedAgent,
    }
    
    if choice not in agent_map:
        print("잘못된 선택입니다.")
        return
    
    agent = agent_map[choice](config)
    
    print("\n대화를 시작합니다. 'quit' 입력시 종료.")
    
    try:
        while True:
            user_input = input("\nYou: ").strip()
            if user_input.lower() in ['quit', 'exit', 'q']:
                break
            if not user_input:
                continue
            
            response = await agent.chat(user_input)
            print(f"\nAgent: {response}")
    finally:
        await agent.close()


async def main():
    """메인 함수"""
    print("\n" + "="*60)
    print("Microsoft Agent Framework 핸즈온 테스트")
    print("="*60)
    
    if len(sys.argv) > 1:
        test = sys.argv[1]
        if test == "basic":
            await test_basic_agent()
        elif test == "rag":
            await test_rag_agent()
        elif test == "tools":
            await test_tool_agent()
        elif test == "combined":
            await test_combined_agent()
        elif test == "interactive":
            await interactive_mode()
        else:
            print(f"알 수 없는 테스트: {test}")
    else:
        print("\n사용법: python test_agents.py [basic|rag|tools|combined|interactive]")
        print("\n전체 테스트를 실행합니다...")
        
        await test_basic_agent()
        await test_rag_agent()
        await test_tool_agent()
        await test_combined_agent()


if __name__ == "__main__":
    asyncio.run(main())
