# Deliverable: react_scratch.py - prints thinking -> tool call <- result each iteration
# Build: ask_anything.py + react_scratch loop (includes <thinking> tags)
import math
import os, re
import requests
from pydantic import BaseModel
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()
client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

class Answer(BaseModel):
    text: str
    sources: list[str]

# - Tools: web_search (mock or real via requests), calculator (eval-safe)
tools = [{
    "name": "web_search",
    "description": "Search the web for information regarding the query. Query is an input string. Return a summary of the top results.",
    "input_schema": {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"]
}}, {
    "name": "calculator",
    "description": "Evaluate the mathematical expression in the input. Input must be a safe expression string.",
    "input_schema": {
        "type": "object",
        "properties": {"expression": {"type": "string"}},
        "required": ["expression"]
}
}]


# =========================== TOOL EXECUTION FUNCTIONS ===========================
# Make sure you pass actual article snippets and not just the title and link to the model
def web_search(query: str) -> str:
    SERP_API_KEY = os.environ.get("SERP_API_KEY")
    if SERP_API_KEY:
        url = "https://serpapi.com/search"
        params = {"q": query, "api_key": SERP_API_KEY}
        response = requests.get(url, params=params)
        data = response.json()
        results = [
            item.get("title", "") + ": " + item.get("snippet", "")
            for item in data.get("organic_results", [])
        ]
        return "\n".join(results[:3])
    else:
        return f"Actual results not found. Mocked web search result for query: {query}"

def calculator(expression: str) -> str:
    try:
        # safe eval: only allow math operations
        result = eval(expression, {"__builtins__": {}}, vars(math))
        return str(result)
    except Exception as e:
        return f"Error: {e}"

def execute_tool(name: str, inputs: dict) -> str:
    if name == "web_search":
        return web_search(**inputs)
    elif name == "calculator":
        return calculator(**inputs)
    return "Unknown tool"


# =========================== MAIN AGENT CELL ===========================
# - User asks a questions
def ask_anything(query: str, response=None) -> Answer:
    system = """
        You are a reaearch agent. Before each action, reason inside <thinking> tags.
        Think about: what do I know, what do I need, which tool helps me get it. Then
        call the appropriate tool.
    """
    messages = [{"role": "user", "content": query}]
    sources = []
    total_input, total_output = 0, 0

    while True:
        # - Model picks 0, 1, or 2 tools, executes, loops to final answer
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=500,
            system=system,
            messages=messages,
            tools=tools
        )

        total_input += response.usage.input_tokens
        total_output += response.usage.output_tokens
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            cost = (total_input / 1e6) * 0.8 + (total_output / 1e6) * 4.0  # haiku pricing
            print(f"[tokens: {total_input} in / {total_output} out | cost: ${cost:.5f}]")
            for block in response.content:
                if block.type == "text":
                    return Answer(text=block.text, sources=sources)
            
        # Upgrade it: extract and print thinking separately each iteration.
        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "text" and "<thinking>" in block.text:
                    thinking = re.search(r"<thinking>(.*?)</thinking>", block.text, re.DOTALL)
                    if thinking:
                        print(f"\t{thinking.group(1).strip()}")

                if block.type == "tool_use":
                    sources.append(block.name)
                    print(f"  → calling {block.name}({block.input})")
                    result = execute_tool(block.name, block.input)
                    print(f"  ← result: {result}")

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })
                    
            # - Log total tokens + cost for the whole run
            messages.append({"role": "user", "content": tool_results})
            print(f"\tTotal tokens so far: {total_input} in / {total_output} out")
        
    # - Final answer extracted as structured Pydantic Answer(text, sources)
        else:
            return Answer(text=f"Stopped: {response.stop_reason}", sources=sources)


# =========================== VALIDATION ===========================
questions = [
    "What is the capital of France?",
    "What is 2847 * 3921?",
    "Who won the 2024 Pakistani presidential election?",
    "Search for the current price of gold per ounce, then calculate how much 3.5 ounces would cost.",
    "What is 15% of Pakistan's 2023 GDP?"
]

print("\n\n========== Ask Anything Agent ==========")
for q in questions:
    print(f"Q: {q}")
    answer = ask_anything(q)
    print(f"A: {answer.text}\nSources:\n{answer.sources}\n\n")