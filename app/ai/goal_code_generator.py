# We'll now update your prompt template to instruct the LLM to output two structured blocks:
# 1. A JSON plan
# 2. A code snippet (Python) for how to persist the plan to DB
from pydantic import BaseModel, Field
from typing import Optional
from app.ai.schemas import GeneratedPlan
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI
from langchain.output_parsers import OutputFixingParser

import os
from decouple import config
from pydantic import SecretStr


# ------------------------------------------------
# ✅ Create an output schema that includes both the structured goal plan and a code snippet for saving it
# This is a Pydantic model that defines the structure of the generated plan with code snippet
# 👇 This is what the LLM returns

class GeneratedPlanWithCode(BaseModel):
    plan: GeneratedPlan = Field(..., description="The main goal being planned")
    code_snippet: str = Field(..., description="Multiline Python code string (escaped) to save this plan to the database")
    # examples=["import os\\nprint('Hello')"]
    """
    This schema includes both the structured goal plan and a code snippet for saving it.
    The LLM should return a valid JSON object that matches this schema.
    """

# ------------------------------------------------
# ✅ Create an output parser that forces LLM to return `GeneratedPlanWithCode` schema
base_parser = PydanticOutputParser(pydantic_object=GeneratedPlanWithCode)

openai_api_key_str = str(config("OPENAI_API_KEY"))
llm_for_fixing = ChatOpenAI(
    model=os.getenv("OPENAI_MODEL", "gpt-4"),
    temperature=0.2,
    api_key=SecretStr(openai_api_key_str)
)

parser = OutputFixingParser(
    parser=base_parser,
    retry_chain=llm_for_fixing,
    # This will ensure the LLM outputs valid JSON that matches the GeneratedPlanWithCode schema
)

# Get format instructions
format_instructions = parser.get_format_instructions()

# ------------------------------------------------
# ✅ Create a reusable prompt template that includes both the structured plan and code snippet

prompt_template = ChatPromptTemplate.from_messages([
    ("system", "You are a smart AI personal planner and experienced Python developer."),
    ("user", 
     """
    A user will describe a personal goal in natural language.

    Your task is to:
    1. Analyze the user's intent and infer structure.
    2. Generate a structured goal plan JSON following the correct schema.
    3. Then generate Python SQLAlchemy code that saves this plan into a PostgreSQL database.

    ⚠️ You must return ONLY a valid JSON object in the following format:
    
    {{
    "plan": {{ <insert full structured goal plan here> }},
    "code_snippet": "<insert full Python SQLAlchemy code here as a single-line string>"
    }}

    Requirements:
    - The "plan" field must strictly follow the format and field names defined in the schema.
    - The "code_snippet" must be valid Python code that saves the plan to the database using SQLAlchemy.
    - All double quotes and line breaks in the code must be escaped to ensure valid JSON.
    - Do NOT wrap the output in Markdown.
    - Do NOT use triple backticks.
    - Do NOT include any explanation, commentary, or extra text — only the raw JSON object.
    - The Python code MUST be returned as a JSON-safe string:
        - Escape double quotes as \\"
        - Escape newlines as \\n
        - Escape backslashes as \\\\
        - Example: "code_snippet": "import os\\nprint(\\"Hello, World!\\")"

    - If the user goal is invalid or unclear, return a plan with empty fields and set "code_snippet" to an empty string.
    

    {format_instructions}

    User goal:
    {goal_description}
    """
    )
])

# ------------------------------------------------

# prompt_template = ChatPromptTemplate.from_template(
#     """
#     You are a smart AI personal planner and Python developer.

#     A user will describe a personal goal in natural language.

#     Given the user's natural language description of a goal, 
#     generate a structured goal planning breakdown 
#     and a Python function that saves this plan into a database using SQLAlchemy.

#     The final output must be a JSON object with the following fields:
#         - `plan`: a structured goal plan with nested cycles, occurrences, and tasks (like a planner)
#         - `code_block`: a valid Python function (as a string) that shows how to save this plan using SQLAlchemy ORM
    
#     Your `plan` MUST:
#     - Follow the JSON structure defined by this format:
#     {format_instructions}

#     The `plan` must include:
#     - Top-level goal details (title, type, start date, recurrence info, etc.)
#     - Habit cycles if the goal is recurring (e.g. monthly)
#     - Inside each cycle, define N goal occurrences based on goal_frequency_per_cycle
#     - Inside each occurrence, generate 2–4 detailed tasks:
#         - Include the main action (e.g. "Play football")
#         - Include at least 1 preparation or support task (e.g. commute, packing)
#         - Use realistic estimated_time and due_date fields

#     Do NOT include motivational or extra explanation text. Only return structured data.

#     Now process this goal:

#     User goal: "{goal_description}"

#     The Python `code_block` snippet that can be used to save this plan to the database.
#     The `code_block` should:
#     - Use SQLAlchemy ORM to create the necessary models
#     - Handle both HabitGoal and ProjectGoal types
#     - Include all relevant fields from the GeneratedPlan schema
#     """
# )

# ✅ Bind the format instructions
prompt = prompt_template.partial(format_instructions=parser.get_format_instructions())

# ------------------------------------------------
# ✅ Connect the LLM (OpenAI model — use GPT-4 or GPT-3.5)
openai_api_key = config("OPENAI_API_KEY")  # Raises error if missing

llm_kwargs = {
    "model": os.getenv("OPENAI_MODEL", "gpt-4"),
    "temperature": 0.2,
}
if isinstance(openai_api_key, str) and openai_api_key:
    llm_kwargs["api_key"] = SecretStr(openai_api_key)

llm = ChatOpenAI(**llm_kwargs)

# ------------------------------------------------
# ✅ Create the goal parser chain that combines the prompt, LLM, and output parser
# ✅ Combine everything into a full chain: prompt → LLM → parser

goal_code_chain = (
    prompt | llm | parser
)
# This chain will now return a structured GeneratedPlanWithCode object
# that includes both the goal plan and the Python code snippet for saving it.
# You can use this chain in your FastAPI route to generate plans and code snippets dynamically.