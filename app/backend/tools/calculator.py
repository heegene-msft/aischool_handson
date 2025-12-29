"""
사칙연산 Tool - Function Calling 예제
핸즈온 Lab 3에서 사용
"""
from typing import Annotated


def add(
    a: Annotated[float, "첫 번째 숫자"],
    b: Annotated[float, "두 번째 숫자"]
) -> float:
    """
    두 숫자를 더합니다.
    
    Args:
        a: 첫 번째 숫자
        b: 두 번째 숫자
        
    Returns:
        두 숫자의 합
    """
    return a + b


def subtract(
    a: Annotated[float, "첫 번째 숫자"],
    b: Annotated[float, "두 번째 숫자"]
) -> float:
    """
    첫 번째 숫자에서 두 번째 숫자를 뺍니다.
    
    Args:
        a: 첫 번째 숫자
        b: 두 번째 숫자
        
    Returns:
        빼기 결과
    """
    return a - b


def multiply(
    a: Annotated[float, "첫 번째 숫자"],
    b: Annotated[float, "두 번째 숫자"]
) -> float:
    """
    두 숫자를 곱합니다.
    
    Args:
        a: 첫 번째 숫자
        b: 두 번째 숫자
        
    Returns:
        두 숫자의 곱
    """
    return a * b


def divide(
    a: Annotated[float, "나눠질 숫자 (피제수)"],
    b: Annotated[float, "나눌 숫자 (제수)"]
) -> float:
    """
    첫 번째 숫자를 두 번째 숫자로 나눕니다.
    
    Args:
        a: 나눠질 숫자 (피제수)
        b: 나눌 숫자 (제수)
        
    Returns:
        나누기 결과
        
    Raises:
        ValueError: 0으로 나누려고 할 때
    """
    if b == 0:
        raise ValueError("0으로 나눌 수 없습니다.")
    return a / b


# Tool definitions for Azure AI Agent
CALCULATOR_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "add",
            "description": "두 숫자를 더합니다. 예: 3 + 5",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {
                        "type": "number",
                        "description": "첫 번째 숫자"
                    },
                    "b": {
                        "type": "number",
                        "description": "두 번째 숫자"
                    }
                },
                "required": ["a", "b"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "subtract",
            "description": "첫 번째 숫자에서 두 번째 숫자를 뺍니다. 예: 10 - 3",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {
                        "type": "number",
                        "description": "첫 번째 숫자"
                    },
                    "b": {
                        "type": "number",
                        "description": "두 번째 숫자"
                    }
                },
                "required": ["a", "b"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "multiply",
            "description": "두 숫자를 곱합니다. 예: 4 * 7",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {
                        "type": "number",
                        "description": "첫 번째 숫자"
                    },
                    "b": {
                        "type": "number",
                        "description": "두 번째 숫자"
                    }
                },
                "required": ["a", "b"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "divide",
            "description": "첫 번째 숫자를 두 번째 숫자로 나눕니다. 예: 20 / 4",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {
                        "type": "number",
                        "description": "나눠질 숫자 (피제수)"
                    },
                    "b": {
                        "type": "number",
                        "description": "나눌 숫자 (제수, 0이 아니어야 함)"
                    }
                },
                "required": ["a", "b"]
            }
        }
    }
]


def execute_calculator_function(function_name: str, arguments: dict) -> str:
    """
    Calculator 함수를 실행합니다.
    
    Args:
        function_name: 실행할 함수 이름
        arguments: 함수 인자
        
    Returns:
        실행 결과 문자열
    """
    functions = {
        "add": add,
        "subtract": subtract,
        "multiply": multiply,
        "divide": divide,
    }
    
    if function_name not in functions:
        return f"알 수 없는 함수: {function_name}"
    
    try:
        result = functions[function_name](**arguments)
        return str(result)
    except Exception as e:
        return f"오류 발생: {str(e)}"
