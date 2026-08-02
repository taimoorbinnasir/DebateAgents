from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from ..Week2.day5_raagent import llm, tools

prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful research agent. Reference previous questions if necessary."),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad")
    ])

# Test: Ask 5 follow-up questions that reference previous answers
# Then switch to summary_memory, repeat - compare token counts
questions = [
    "What medicine should I take for dust allergies?",
    "At what dose should I take it, and how often?",
    "Does it have any side effects I should watch out for?",
    "Are there any foods or other medicines I should avoid while taking it?",
    "Given everything you've told me, would you recommend I see a doctor first or just buy it over the counter?",
]

def run_with_buffer_memory():
    agent = create_tool_calling_agent(llm, tools, prompt)
    executer = AgentExecutor(agent=agent, tools=tools, verbose=False)
    chat_history = []  # manual buffer

    print("\n" + "="*50)
    print("  Manual Buffer Memory")
    print("="*50)

    for q in questions:
        result = executer.invoke({"input": q, "chat_history": chat_history})
        chat_history.append(HumanMessage(content=q))
        chat_history.append(AIMessage(content=result["output"]))

        mem_size = len(str(chat_history))
        print(f"\nQ: {q}")
        print(f"A: {result['output']}")
        print(f"[memory size: {mem_size} chars]")


def run_with_summary_memory():
    agent = create_tool_calling_agent(llm, tools, prompt)
    executer = AgentExecutor(agent=agent, tools=tools, verbose=False)
    summary = ""

    print("\n" + "="*50)
    print("  Manual Summary Memory")
    print("="*50)

    for q in questions:
        # Inject summary as a single message instead of full history
        summary_history = [AIMessage(content=f"Summary so far: {summary}")] if summary else []
        result = executer.invoke({"input": q, "chat_history": summary_history})

        # Summarize after each turn
        summary_response = llm.invoke(
            f"Summarize this conversation in 2 sentences:\n{summary}\nHuman: {q}\nAI: {result['output']}"
        )
        summary = summary_response.content

        mem_size = len(summary)
        print(f"\nQ: {q}")
        print(f"A: {result['output']}")
        print(f"[summary size: {mem_size} chars]")

run_with_buffer_memory()
run_with_summary_memory()
