import os, requests, json, math
from datetime import datetime
from dotenv import load_dotenv
from anthropic import Anthropic
from langchain_anthropic import ChatAnthropic
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()
client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

# ===================================== T O O L S =====================================
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


# - Add a third tool: save_tool(title, content) - writes to a local notes.json file
@tool
def save_note(title: str, content: str) -> str:
    """Save a research note to notes.json."""
    notes = json.load(open("notes.json")) if os.path.exists("notes.json") else {}
    notes[title] = {"content": content, "saved_at": str(datetime.now())}
    json.dump(notes, open("notes.json", "w"), indent=2)
    return f"Saved note: '{title}'"


# - Add summarize_url(url) - fetches a URL with requests, sends content to Claude
#   for summarization
@tool
def summarize_url(url: str) -> str:
    """Fetch a URL and return a summary of its content."""
    response = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
    text = response.text[:3000]
    return llm.invoke(f"Summarize this article in 3 sentences:\n{text}").content
# =====================================================================================



llm = ChatAnthropic(
    model="claude-haiku-4-5",
    api_key=os.environ["ANTHROPIC_API_KEY"]
)
tools = [web_search, calculator, save_note, summarize_url]
prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a helpful research agent. 
        When asked to research and save a note:
        1. Search for the topic
        2. Summarize ONE article
        3. Save the note
        4. Stop and return your answer.
        Do not search for additional articles after saving the note."""),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}")
])
agent = create_tool_calling_agent(llm, tools, prompt)
executer = AgentExecutor(agent=agent, tools=tools, verbose=True)



# - Ask a multi-step research question - agent should research, fetch a result URL,
#   summarize it, save the note
# result = executer.invoke({"input": "Research the latest development in LLM agents, summarize one article, and save a note about it."})
# print(result["output"])