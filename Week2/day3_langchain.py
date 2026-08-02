import os, requests, math
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

@tool
def web_search(query: str) -> str:
    """Search the web for current information about a query."""
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

@tool
def calculator(expression: str) -> str:
    """Evaluate a mathematical expression safely."""
    try:
        # safe eval: only allow math operations
        result = eval(expression, {"__builtins__": {}}, vars(math))
        return str(result)
    except Exception as e:
        return f"Error: {e}"



llm = ChatAnthropic(
    model="claude-haiku-4-5",
    api_key=os.environ["ANTHROPIC_API_KEY"]
)
tools = [web_search, calculator]
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful research agent."),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}")
])
agent = create_tool_calling_agent(llm, tools, prompt)
executer = AgentExecutor(agent=agent, tools=tools, verbose=True)



questions = [
    "Is 17 a prime number?",
    "Who won the 2024 Pakistani presidential election?",
    "Search for the current price of gold per ounce, then calculate how much 3.5 ounces would cost.",
    "What is 15% of Pakistan's 2023 GDP?"
]

for q in questions:
    result = executer.invoke({"input": q})
    print(result["output"])

