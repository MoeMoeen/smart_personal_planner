# === goal_parser_chain.py ===
# This file contains the LangChain chain that parses natural language goal descriptions
# into structured plans following our AI-driven schema (goal → cycles → occurrences → tasks)


from langchain_openai import ChatOpenAI                     # ✅ Interface to OpenAI chat models
from langchain.prompts import ChatPromptTemplate            # ✅ Helps define reusable prompt structure
from langchain.output_parsers import PydanticOutputParser, OutputFixingParser   # ✅ Enforces Pydantic schema on LLM output
from app.ai.schemas import GeneratedPlan                    # ✅ Import your structured schema
import os                                                   # ✅ For environment variable access     
from pydantic import SecretStr
from decouple import config
from langchain.schema.runnable import RunnableMap
from datetime import date
from datetime import datetime, timezone  # For handling timestamps in feedback


#Create a reusable LangChain pipeline that:
# Accepts a natural language input (user’s goal description)
# Sends it to the LLM
# Returns a structured GeneratedPlan object parsed into your new schema


# ✅ Create an output parser that forces LLM to return `GeneratedPlan` schema
base_parser = PydanticOutputParser(pydantic_object=GeneratedPlan)

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

# ✅ Define the prompt template with placeholders for dynamic content, i.e, for the LLM (system + user)
# ✅ Create the system prompt that guides the LLM

today = date.today().isoformat()

prompt_template = ChatPromptTemplate.from_messages([
    ("system", 
     f"""
     You are a smart AI personal planner. Today’s date is {today}. 
     Use this as the base for all scheduling decisions.
     """
    ),
    ("user",
     """
     A user will describe a personal goal in natural language. 
     Given the user's natural language description of a goal, generate a structured goal planning breakdown.

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

     ⚠️ Temporal Logic Requirements:
     - All dates must be in the future — never in the past.
     - For project goals, include an end_date that is at least 2 weeks after the start_date.
     - For habit goals, end_date can be omitted if recurrence is indefinite.
     - Start_date must not be earlier than today.
     - Make date logic consistent with the goal type and frequency.

     Do NOT include motivational or extra explanation text. Only return valid structured data.

     User goal: {goal_description}

     Today's date: {today_date}
     """
    )
])

# app/ai/refinement_prompt.py (or you can inline it in goal_parser_chain.py if preferred)

refinement_prompt_template = ChatPromptTemplate.from_messages([
    ("system", 
     f"""
     You are a smart AI personal planner who revises structured goal plans based on user feedback.
     Today’s date is {today}. Make sure all output respects today’s date.
     """
    ),
    ("user",
     """
     A user previously generated a structured goal plan, but they provided feedback asking for improvements.

     Your task:
     - Review the original goal description
     - Consider the user's feedback
     - Improve the previously generated plan accordingly

     Strictly follow these output rules:
     - All dates must be in the future (not before today)
     - For project goals:
         - Start date must be today or later
         - End date must be at least 2 weeks after start date
     - For habit goals:
         - End date is optional (may be recurring forever)
     - Inside each cycle or plan:
         - Add 2–4 detailed tasks per occurrence
         - Include one main task and one supporting/preparation task
         - Provide realistic due dates and estimated times

     You MUST follow this output format:
     {format_instructions}

     Original goal description:
     {goal_description}

     User feedback:
     {prior_feedback}

     Previous structured plan to refine:
     {previous_plan}

     Return only a valid structured plan. Do not include extra explanation or chat text.
     """
    )
])


# ✅ Bind the format instructions
prompt = prompt_template.partial(format_instructions=parser.get_format_instructions())

refinement_prompt_template = refinement_prompt_template.partial(
    format_instructions=parser.get_format_instructions()
)


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

goal_parser_chain = RunnableMap({
    "plan" : prompt | llm | parser
})


# ✅ Create the refinement chain that uses the refinement prompt, LLM, and output parser
refine_plan_chain = RunnableMap({
    "plan" : refinement_prompt_template | llm | parser
})


