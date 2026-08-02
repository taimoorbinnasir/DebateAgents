"""
Day 1 deliverable: a 20-line multi-turn chatbot that prints token cost per turn.
Run: python3 chat.py
Requires: export ANTHROPIC_API_KEY=sk-ant-...
"""

import os
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
messages = []

# Haiku 4.5 pricing per million tokens — update if prices change
INPUT_COST_PER_M = 0.25
OUTPUT_COST_PER_M = 1.25

print("Chat with Claude. Type 'exit' to quit.\n")

while True:
    user_input = input("You: ").strip()
    if user_input.lower() in ("exit", "quit"):
        break

    messages.append({"role": "user", "content": user_input})

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=300,
        system="You are a terse, helpful CS tutor. Max 3 sentences per answer.",
        messages=messages,
    )

    reply = response.content[0].text
    messages.append({"role": "assistant", "content": reply})

    in_tok = response.usage.input_tokens
    out_tok = response.usage.output_tokens
    cost = (in_tok / 1e6) * INPUT_COST_PER_M + (out_tok / 1e6) * OUTPUT_COST_PER_M

    print(f"\nClaude: {reply}")
    print(f"[tokens: {in_tok} in / {out_tok} out | cost: ${cost:.5f}]\n")
