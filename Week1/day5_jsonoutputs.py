# Exercise: Extract strcutured data (name, ingredients, time) from 5 messy recipe-text
# blobs, validate with pydantic, catch and log validation errors.

import os
from pydantic import BaseModel, ValidationError
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()
client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

# Define a Pydantic model for recipe data (Used for validation)
class Recipe(BaseModel):
    name: str
    ingredients: list[str]
    minutes: int

# Trick: Use a tools schema as a forced-output mechanism
tools = [{"name": "extract_recipe",
          "description": "Extract structured recipe data (name, ingredients, time) from messy text",
          "input_schema": Recipe.model_json_schema()}]

# Messy recipe-text blobs
messy_recipes = [
    "My mango shake is super easy! Grab a mango, some milk, and a bit of sugar. Done in like 10 mins.",
    "Oreo cream delight: crush some oreos, mix with cream, sugar, condensed milk, vanilla, and cake rusks. Takes about 20 min.",
    "Quick pasta - boil pasta, add tomato sauce and cheese. Ready in 20 minutes.",
    "Chicken sandwich: chicken, bread, lettuce, tomato, mayo. 10 mins.",
    "INVALID RECIPE - just vibes and good energy, no ingredients, no time"
]

# Validate with Pydantic and catch errors
def extract_recipe(messy_text: str) -> Recipe:
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=300,
        tools=tools,
        messages=[{"role": "user", "content": messy_text}]
    )

    for block in response.content:
        # parse tool_use.input directly into Recipe(**input)
        if block.type == "tool_use":
            try:
                return Recipe(**block.input)
            except ValidationError as e:
                print(f"Validation error: {e}")
                return None
            
# Output structured recipes
for text in messy_recipes:
    recipe = extract_recipe(text)
    print(recipe if recipe else "FAILED")