from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from shared.tools import llm, tools

prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful research agent. Reference previous questions if necessary."),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad")
    ])

# Test: Ask 5 follow-up questions that reference previous answers
# Then switch to summary_memory, repeat - compare token counts
questions = [
    "Who was the first person to walk on the moon, and what mission was it?",
    "How long did that mission take from launch to splashdown?",
    "What did he say when he first stepped on the surface?",
    "Were there other crew members on that mission? What were their roles?",
    "Of everything you've told me about this mission, what do you think was the most technically impressive achievement?"
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
        print(f"A: {result['output'][0]['text']}")
        print(f"-- Memory size: {mem_size} chars")

    return executer, chat_history


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
            f"Update this running summary with the new exchange. Keep all important facts.\n"
            f"Current summary: {summary}\n"
            f"New exchange:\nHuman: {q}\nAI: {result['output']}"
        )
        summary = summary_response.content

        print(f"\nQ: {q}")
        print(f"A: {result['output']}")
        print(f"-- Current summary: {summary}")
        print(f"-- Summary size: {len(summary)} chars")

    final_history = [AIMessage(content=f"Previous conversation summary: {summary}")]
    return executer, final_history



# Runnning each method independently to compare memory usage
executer_buffer, buffer_history = run_with_buffer_memory()
executer_summary, summary_history = run_with_summary_memory()


# Verification of memory usage
verification = "List every specific fact you remember from our conversation."
result_buffer = executer_buffer.invoke({"input": verification, "chat_history": buffer_history})
result_summary = executer_summary.invoke({"input": verification, "chat_history": summary_history})


print("\n" + "="*100)
print("BUFFER:\n", result_buffer["output"])
print("\nSUMMARY:\n", result_summary["output"])
