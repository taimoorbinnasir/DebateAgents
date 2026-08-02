# Exercise: Write a classifier 3 ways (zero-shot, few-shot, and CoT) on the same
# 10 examples. Log accuracy differences.

import os, re
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()
client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

# Setting up model
def ask(prompt, system="", max_tokens=300):
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=max_tokens,
        system=system or "",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text


# ====================== Zero-shot vs Few-shot ======================
# Test cases
test_cases = [
    ("The food was cold and the waiter was rude.", "negative"),
    ("Best meal I've had all year!", "positive"),
    ("It was fine, nothing special.", "neutral"),
    ("Loved the ambiance, but the soup was bland.", "mixed"),  # tricky on purpose
    ("Service was slow but the dessert made up for it.", "mixed"),
]

# Few-shot: Classify sentiment with 3 examples in prompt
zero_shot_prompt = "Classify the sentiment as positive, negative, neutral, or mixed: \"{}\""

# Zero-shot: Classify sentiment with no examples in prompt
few_shot_prompt = """Classify sentiment as positive, negative, neutral, or mixed.
Only respond with one of those four words. Here are some examples:

Text: "Great service, friendly staff!" -> positive
Text: "Never coming back." -> negative
Text: "It was okay, nothing memorable." -> neutral
Text: "Good food, bad parking." -> mixed

Text: "{}" -> "" """

# Compare zero-shot vs few-shot accuracy on 10 test cases
print("============ Zero-shot vs Few-shot sentiment classification ============")
for text, expected in test_cases:
    zero = ask(zero_shot_prompt.format(text), max_tokens=10)
    few = ask(few_shot_prompt.format(text), max_tokens=10)
    print(f"Expected: {expected:10} \nZero-shot: {zero.strip():10} \nFew-shot: {few.strip()}\n\n")


# ===================== Chain of Thought (CoT) reasoning ======================
# CoT: Think step-by-step in <thinking> tags, then <answer>
problem = """A train leaves Lahore at 2:00 PM going 60 km/h toward Multan, 300km away.
Another train leaves Multan at 2:30 PM going 90 km/h toward Lahore.
At what time do they meet?"""

direct = ask(f"{problem}\nAnswer with just the time.", max_tokens=20)

cot = ask(f"""{problem}

Think through this step by step inside <thinking> tags, then give the final answer inside <answer> tags.""", max_tokens=400)

print("\n============ Direct vs CoT reasoning ============")
print("Direct:", direct)
print("\nCoT:\n", cot)


# ===================== XML tags incorporation ======================
print("\n============ Code review ============")
prompt = """Review this code and respond using this exact format:

<issues>
<issue severity="high|medium|low">description</issue>
</issues>
<summary>one sentence overall verdict</summary>

Code:
def get_user(id):
    data = db.query("SELECT * FROM users WHERE id=" + id)
    return data[0]
"""

response = ask(prompt, max_tokens=400)
print(response)

issues = re.findall(r'<issue severity="(\w+)">(.*?)</issue>', response)
summary = re.search(r'<summary>(.*?)</summary>', response, re.DOTALL)

for severity, desc in issues:
    print(f"[{severity}] {desc}")
print("Summary:", summary.group(1).strip() if summary else "MISSING")