import { useState, useRef, useEffect } from "react";
import styles from "./Labs.module.css";

type AgentType = "basic" | "rag" | "tools" | "combined" | "websearch" | "orchestrator";

interface Message {
    role: "user" | "assistant";
    content: string;
}

const Labs = () => {
    const [selectedLab, setSelectedLab] = useState<AgentType>("basic");
    const [messages, setMessages] = useState<Message[]>([]);
    const [inputValue, setInputValue] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const [sessionId] = useState(() => `session_${Date.now()}`);

    const labInfo = {
        basic: {
            title: "Lab 1: 기본 챗봇",
            description: "Microsoft Foundry Agent를 활용한 기본 대화형 챗봇",
            icon: "🤖",
            placeholder: "안녕하세요! 무엇이든 물어보세요..."
        },
        rag: {
            title: "Lab 2: RAG 챗봇",
            description: "Azure AI Search를 활용한 문서 기반 질의응답",
            icon: "📚",
            placeholder: "Zava 회사에 대해 질문해보세요..."
        },
        tools: {
            title: "Lab 3: Tool Calling",
            description: "사칙연산 함수를 호출하는 Agent",
            icon: "🔧",
            placeholder: "계산을 요청해보세요. 예: 123 + 456은?"
        },
        combined: {
            title: "Lab 4: 통합 Agent",
            description: "RAG + Tool Calling 통합 Agent",
            icon: "🔗",
            placeholder: "회사 정보나 계산을 요청해보세요..."
        },
        websearch: {
            title: "Lab 5: 웹 검색",
            description: "Bing Search Grounding을 활용한 인터넷 검색",
            icon: "🌐",
            placeholder: "최신 정보나 날씨 등을 물어보세요..."
        },
        orchestrator: {
            title: "Lab 6: 오케스트레이터",
            description: "질문 유형에 따라 적절한 에이전트로 자동 라우팅",
            icon: "🎯",
            placeholder: "무엇이든 물어보세요! (RAG/계산/웹검색/일반 자동 분류)"
        }
    };

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const handleLabChange = (lab: AgentType) => {
        setSelectedLab(lab);
        setMessages([]);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!inputValue.trim() || isLoading) return;

        const userMessage = inputValue.trim();
        setInputValue("");
        setMessages(prev => [...prev, { role: "user", content: userMessage }]);
        setIsLoading(true);

        try {
            const endpoint = `/api/${selectedLab}`;
            const response = await fetch(endpoint, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    message: userMessage,
                    session_id: sessionId
                })
            });

            const data = await response.json();

            if (data.error) {
                setMessages(prev => [...prev, { 
                    role: "assistant", 
                    content: `오류: ${data.error}` 
                }]);
            } else {
                setMessages(prev => [...prev, { 
                    role: "assistant", 
                    content: data.response 
                }]);
            }
        } catch (error) {
            setMessages(prev => [...prev, { 
                role: "assistant", 
                content: `오류가 발생했습니다: ${error}` 
            }]);
        } finally {
            setIsLoading(false);
        }
    };

    const handleClear = async () => {
        try {
            await fetch("/api/reset", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ 
                    session_id: sessionId,
                    agent_type: selectedLab  // 현재 선택된 Lab의 agent 리셋
                })
            });
            setMessages([]);
        } catch (error) {
            console.error("Reset failed:", error);
        }
    };

    const handleExampleClick = (example: string) => {
        setInputValue(example);
    };

    return (
        <div className={styles.container}>
            {/* 사이드바 - Lab 선택 */}
            <aside className={styles.sidebar}>
                <h2 className={styles.sidebarTitle}>🎯 MAF 기반 Agent HoL Chat</h2>
                <nav className={styles.labNav}>
                    {(Object.keys(labInfo) as AgentType[]).map((lab) => (
                        <button
                            key={lab}
                            className={`${styles.labButton} ${selectedLab === lab ? styles.active : ""}`}
                            onClick={() => handleLabChange(lab)}
                        >
                            <span className={styles.labIcon}>{labInfo[lab].icon}</span>
                            <span className={styles.labTitle}>{labInfo[lab].title}</span>
                        </button>
                    ))}
                </nav>
            </aside>

            {/* 메인 채팅 영역 */}
            <main className={styles.main}>
                {/* 헤더 */}
                <header className={styles.header}>
                    <div>
                        <h1>
                            {labInfo[selectedLab].icon} {labInfo[selectedLab].title}
                        </h1>
                        <p className={styles.description}>{labInfo[selectedLab].description}</p>
                    </div>
                    <button className={styles.clearButton} onClick={handleClear}>
                        🗑️ 대화 초기화
                    </button>
                </header>

                {/* 메시지 목록 */}
                <div className={styles.messagesContainer}>
                    {messages.length === 0 ? (
                        <div className={styles.emptyState}>
                            <span className={styles.emptyIcon}>{labInfo[selectedLab].icon}</span>
                            <h3>{labInfo[selectedLab].title}</h3>
                            <p>{labInfo[selectedLab].description}</p>
                            <div className={styles.examples}>
                                <p>예시 질문:</p>
                                {selectedLab === "basic" && (
                                    <ul>
                                        <li onClick={() => handleExampleClick("자기소개를 해주세요")}>자기소개를 해주세요</li>
                                        <li onClick={() => handleExampleClick("오늘 날씨가 어떨까요?")}>오늘 날씨가 어떨까요?</li>
                                    </ul>
                                )}
                                {selectedLab === "rag" && (
                                    <ul>
                                        <li onClick={() => handleExampleClick("Zava 회사는 언제 설립되었나요?")}>Zava 회사는 언제 설립되었나요?</li>
                                        <li onClick={() => handleExampleClick("회사의 휴가 정책은 어떻게 되나요?")}>회사의 휴가 정책은 어떻게 되나요?</li>
                                        <li onClick={() => handleExampleClick("핵심 가치(Core Values)에 대해 알려주세요")}>핵심 가치(Core Values)에 대해 알려주세요</li>
                                    </ul>
                                )}
                                {selectedLab === "tools" && (
                                    <ul>
                                        <li onClick={() => handleExampleClick("123 더하기 456은?")}>123 더하기 456은?</li>
                                        <li onClick={() => handleExampleClick("1000에서 350을 빼면?")}>1000에서 350을 빼면?</li>
                                        <li onClick={() => handleExampleClick("25 곱하기 4는 얼마인가요?")}>25 곱하기 4는 얼마인가요?</li>
                                        <li onClick={() => handleExampleClick("100 나누기 8을 계산해주세요")}>100 나누기 8을 계산해주세요</li>
                                    </ul>
                                )}
                                {selectedLab === "combined" && (
                                    <ul>
                                        <li onClick={() => handleExampleClick("Zava 회사의 직원 수는 몇 명인가요?")}>Zava 회사의 직원 수는 몇 명인가요?</li>
                                        <li onClick={() => handleExampleClick("150 더하기 250은?")}>150 더하기 250은?</li>
                                        <li onClick={() => handleExampleClick("회사의 핵심 가치를 알려주세요")}>회사의 핵심 가치를 알려주세요</li>
                                    </ul>
                                )}
                                {selectedLab === "websearch" && (
                                    <ul>
                                        <li onClick={() => handleExampleClick("오늘 서울 날씨는 어때요?")}>오늘 서울 날씨는 어때요?</li>
                                        <li onClick={() => handleExampleClick("최근 AI 기술 동향을 알려주세요")}>최근 AI 기술 동향을 알려주세요</li>
                                        <li onClick={() => handleExampleClick("마이크로소프트의 최신 뉴스는?")}>마이크로소프트의 최신 뉴스는?</li>
                                    </ul>
                                )}
                                {selectedLab === "orchestrator" && (
                                    <ul>
                                        <li onClick={() => handleExampleClick("Zava 회사의 휴가 정책은?")}>Zava 회사의 휴가 정책은? (→ RAG)</li>
                                        <li onClick={() => handleExampleClick("123 곱하기 456은?")}>123 곱하기 456은? (→ Calculator)</li>
                                        <li onClick={() => handleExampleClick("오늘 뉴욕 날씨 어때?")}>오늘 뉴욕 날씨 어때? (→ Web Search)</li>
                                        <li onClick={() => handleExampleClick("안녕하세요, 반갑습니다!")}>안녕하세요, 반갑습니다! (→ Basic)</li>
                                    </ul>
                                )}
                            </div>
                        </div>
                    ) : (
                        <div className={styles.messages}>
                            {messages.map((msg, idx) => (
                                <div
                                    key={idx}
                                    className={`${styles.message} ${
                                        msg.role === "user" ? styles.userMessage : styles.assistantMessage
                                    }`}
                                >
                                    <div className={styles.messageIcon}>
                                        {msg.role === "user" ? "👤" : labInfo[selectedLab].icon}
                                    </div>
                                    <div className={styles.messageContent}>
                                        <div className={styles.messageRole}>
                                            {msg.role === "user" ? "You" : "Agent"}
                                        </div>
                                        <div className={styles.messageText}>{msg.content}</div>
                                    </div>
                                </div>
                            ))}
                            {isLoading && (
                                <div className={`${styles.message} ${styles.assistantMessage}`}>
                                    <div className={styles.messageIcon}>{labInfo[selectedLab].icon}</div>
                                    <div className={styles.messageContent}>
                                        <div className={styles.messageRole}>Agent</div>
                                        <div className={styles.loading}>
                                            <span>●</span><span>●</span><span>●</span>
                                        </div>
                                    </div>
                                </div>
                            )}
                            <div ref={messagesEndRef} />
                        </div>
                    )}
                </div>

                {/* 입력 폼 */}
                <form className={styles.inputForm} onSubmit={handleSubmit}>
                    <input
                        type="text"
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        placeholder={labInfo[selectedLab].placeholder}
                        disabled={isLoading}
                        className={styles.input}
                    />
                    <button 
                        type="submit" 
                        disabled={isLoading || !inputValue.trim()}
                        className={styles.submitButton}
                    >
                        {isLoading ? "⏳" : "전송 ➤"}
                    </button>
                </form>
            </main>
        </div>
    );
};

export default Labs;
