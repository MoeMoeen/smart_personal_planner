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
prompt_template = ChatPromptTemplate.from_messages([
    ("system", "You are a smart AI personal planner."),
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

    Do NOT include motivational or extra explanation text. Only return structured data.

    User goal: {goal_description}
    """
    )
])

# app/ai/refinement_prompt.py (or you can inline it in goal_parser_chain.py if preferred)


refinement_prompt_template = ChatPromptTemplate.from_messages([
    ("system", 
     "You are a smart AI personal planner who improves goal planning based on user feedback."),
    ("user",
     """
    The user previously generated a structured goal plan, but they provided feedback that it needs refinement.

    Your task is to take the existing plan and the user's feedback, and generate a new, improved structured plan. 
    
    Here is the user's original goal description:

    {goal_description}

    Below is the feedback and suggestions provided by the user:

    {prior_feedback}

    Use this feedback to revise and improve the original structured plan.

    Here is the last generated plan that needs refinement:

    {previous_plan}

    Please use the feedback and improve the previous plan. Ensure that the new plan addresses the concerns and avoids repeating previous mistakes.

    Requirements:
    - Your output must strictly follow the structured plan schema.
    - ONLY return a valid JSON object.
    - Do NOT include any explanation or commentary.

    Your response MUST:
    - Follow the JSON structure defined by this format:
    {format_instructions}

        """)
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


