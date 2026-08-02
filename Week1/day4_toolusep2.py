import os, math
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()
client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

tools = [
    {
        "name": "get_weather",
        "description": "Get current temperature in Celsius for a city",
        "input_schema": {
            "type": "object",
            "properties": {"city": {"type": "string"}},
            "required": ["city"]
        }
    },
    {
        "name": "calculator",
        "description": "Evaluate a mathematical expression. Input must be a safe expression string.",
        "input_schema": {
            "type": "object",
            "properties": {"expression": {"type": "string"}},
            "required": ["expression"]
        }
    }
]

# Mock implementations — replace with real APIs later
def get_weather(city: str) -> str:
    mock_data = {"karachi": 34, "lahore": 38, "london": 12, "tokyo": 22}
    temp = mock_data.get(city.lower(), 25)
    return f"{temp}C"


def calculator(expression: str) -> str:
    try:
        # safe eval: only allow math operations
        result = eval(expression, {"__builtins__": {}}, vars(math))
        return str(result)
    except Exception as e:
        return f"Error: {e}"


def execute_tool(name: str, inputs: dict) -> str:
    if name == "get_weather":
        return get_weather(**inputs)
    elif name == "calculator":
        return calculator(**inputs)
    return "Unknown tool"


# Main agent loop: keep calling model until it returns a final answer
def run_agent(user_question: str) -> str:
    messages = [{"role": "user", "content": user_question}]

    while True:
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=500,
            tools=tools,
            messages=messages
        )

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            # Extract final text answer
            for block in response.content:
                if block.type == "text":
                    return block.text
            return "No text response"

        if response.stop_reason == "tool_use":
            # Execute every tool the model requested (can be multiple in one turn)
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"  → calling {block.name}({block.input})")
                    result = execute_tool(block.name, block.input)
                    print(f"  ← result: {result}")
                    
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,   # must match exactly
                        "content": result
                    })

            messages.append({"role": "user", "content": tool_results})
            # Loop continues → model sees results → decides to call more tools or end

        else:
            return f"Stopped unexpectedly: {response.stop_reason}"

# Sample questions to test the agent
questions = [
    "What's the weather in Lahore?",
    "What is 1234 * 5678?",
    "What is the weather in Karachi? Convert that temperature to Fahrenheit using (C * 9/5) + 32.",
]

for q in questions:
    print(f"\nQ: {q}")
    answer = run_agent(q)
    print(f"A: {answer}")