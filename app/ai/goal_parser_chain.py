# === goal_parser_chain.py ===
# This file contains the LangChain chain that parses natural language goal descriptions
# into structured plans following our AI-driven schema (goal → cycles → occurrences → tasks)


from langchain_openai import ChatOpenAI                     # ✅ Interface to OpenAI chat models
from langchain.prompts import ChatPromptTemplate            # ✅ Helps define reusable prompt structure
from langchain.output_parsers import PydanticOutputParser   # ✅ Enforces Pydantic schema on LLM output
from app.ai.schemas import GeneratedPlan                    # ✅ Import your structured schema
import os                                                   # ✅ For environment variable access     
from pydantic import SecretStr
from decouple import config

#Create a reusable LangChain pipeline that:
# Accepts a natural language input (user’s goal description)
# Sends it to the LLM
# Returns a structured GeneratedPlan object parsed into your new schema


# ✅ Create an output parser that forces LLM to return `GeneratedPlan` schema
parser = PydanticOutputParser(pydantic_object=GeneratedPlan)

# ✅ Define the prompt template with placeholders for dynamic content, i.e, for the LLM (system + user)
# ✅ Create the system prompt that guides the LLM
prompt_template = ChatPromptTemplate.from_template(
    """
    You are a smart personal planner.

    Given a user's natural language description of a goal, generate a structured goal planning breakdown.

    Your response MUST:
    - Follow the JSON structure defined by this format:
    {format_instructions}

    The plan must include:
    - Top-level goal details (title, type, start date, recurrence info, etc.)
    - Habit cycles if the goal is recurring (e.g. monthly)
    - Inside each cycle, define N goal occurrences based on goal_frequency_per_cycle
    - Inside each occurrence, generate 2–4 detailed tasks:
        - Include the main action (e.g. "Play football")
        - Include at least 1 preparation or support task (e.g. commute, packing)
        - Use realistic estimated_time and due_date fields

    Do NOT include motivational or extra explanation text. Only return structured data.

    User goal: {goal_description}
    """
)

# ✅ Bind the format instructions
prompt = prompt_template.partial(format_instructions=parser.get_format_instructions())


# ✅ Connect the LLM (OpenAI model — use GPT-4 or GPT-3.5)

openai_api_key = config("OPENAI_API_KEY")  # Raises error if missing

llm_kwargs = {
    "model": os.getenv("OPENAI_MODEL", "gpt-4"),
    "temperature": 0.2,
}
if isinstance(openai_api_key, str) and openai_api_key:
    llm_kwargs["api_key"] = SecretStr(openai_api_key)

llm = ChatOpenAI(**llm_kwargs)

# ✅ Create the goal parser chain that combines the prompt, LLM, and output parser
# ✅ Combine everything into a full chain: prompt → LLM → parser

goal_parser_chain = (
    prompt | llm | parser
)

