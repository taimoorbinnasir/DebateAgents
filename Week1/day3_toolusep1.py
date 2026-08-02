# tools = [{
#     "name": "get_weather",
#     "description": "Get current weather for a city",
#     "input_schema": {
#         "type": "object",
#         "properties": {"city": {"type": "string"}},
#         "required": ["city"]
#     }
# }]

# msg = client.messages.create(model="claude-haiku-4-5",
# max_tokens=300, tools=tools,
# messages=[{"role": "user", "content": "Weather in Lahore?"}])

# Note: msg.content will contain a tool_use block - inspect msg.stop_reason

# Exercise: Write a mock get_weather() function, print the tool_use input the model
# generates, manually fake the result

import os
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()
client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

tools = [{
    "name": "get_weather",
    "description": "Get current weather for a city",
    "input_schema": {
        "type": "object",
        "properties": {"city": {"type": "string"}},
        "required": ["city"]
    }
}]

# Setting up model
def get_weather(prompt, system="", max_tokens=300):
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=max_tokens,
        tools=tools,
        system=system or "",
        messages=[{"role": "user", "content": prompt}]
    )
    
    return response.content, response.stop_reason


response_content, stop_reason = get_weather("What is the weather in Karachi?")
print(response_content)
print(stop_reason)