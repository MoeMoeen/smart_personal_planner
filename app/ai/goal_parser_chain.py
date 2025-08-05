#app/ai/goal_parser_chain.py
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
from langchain.schema.runnable import RunnableMap
from datetime import date
from typing import Optional, Dict, Any                      # ✅ For type hints


#Create a reusable LangChain pipeline that:
# Accepts a natural language input (user’s goal description)
# Sends it to the LLM
# Returns a structured GeneratedPlan object parsed into your new schema


# ✅ Create an output parser that forces LLM to return `GeneratedPlan` schema
base_parser = PydanticOutputParser(pydantic_object=GeneratedPlan)

# ✅ Use the base parser directly instead of OutputFixingParser to avoid the chain issue
parser = base_parser

# ✅ If you want auto-fixing later, use this configuration:
# openai_api_key_str = str(config("OPENAI_API_KEY"))
# llm_for_fixing = ChatOpenAI(
#     model=os.getenv("OPENAI_MODEL", "gpt-4"),
#     temperature=0.2,
#     api_key=SecretStr(openai_api_key_str)
# )
# 
# # Create a simple fixing chain
# from langchain.prompts import ChatPromptTemplate
# fixing_prompt = ChatPromptTemplate.from_template(
#     "Fix the following JSON to be valid:\n{completion}\n\nFixed JSON:"
# )
# retry_chain = fixing_prompt | llm_for_fixing
# 
# parser = OutputFixingParser(
#     parser=base_parser,
#     retry_chain=retry_chain
# )

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
    - Follow the exact JSON structure defined by this format:
    {format_instructions}

    🏗️ **CRITICAL ARCHITECTURE**: The output has TWO separate sections:
    1. **goal**: Lightweight metadata container (title, description only)
    2. **plan**: Central orchestrator with ALL execution details

    ✅ **Goal Section** (lightweight metadata):
    - title: Clear, concise goal name
    - description: Detailed explanation of what the user wants to achieve
    - user_id: (optional, will be set by system)

    ✅ **Plan Section** (all execution details):
    - goal_type: "habit", "project", or "hybrid"
    - start_date: Must be today or later
    - end_date: Required for projects, optional for habits
    - progress: 0 (new plan)
    - All habit-specific fields (if applicable)
    - Structure: habit_cycles and/or tasks

    🎯 **Goal Type Classification Rules:**
    - **"project"**: Use for one-time achievements with a clear end date
      Examples: "read 12 books this year", "learn a skill", "complete a course", "organize my home"
    - **"habit"**: Use for ongoing, repetitive behaviors without a clear end
      Examples: "exercise 3 times per week", "meditate daily", "call mom weekly"
    - **"hybrid"**: Use for goals that benefit from both structured tasks AND recurring habits
      Examples: "learn Python" (daily coding habit + standalone non-repeating tasks), "get fit" (workout routine + race training)

    🔁 If goal_type is **"habit"**, the PLAN must include ALL of these fields:
    - goal_frequency_per_cycle (REQUIRED: e.g., 2 times per month, 3 times per week)
    - goal_recurrence_count (REQUIRED: e.g., 6 months, 12 weeks - NEVER leave this null)
    - recurrence_cycle (REQUIRED: e.g., "daily", "weekly", "monthly")
    - default_estimated_time_per_cycle (REQUIRED: e.g., 60 minutes per session)
    - habit_cycles: Array of cycles with occurrences and tasks
    
    📦 If goal_type is **"project"**, the PLAN must include:
    - end_date (at least 2 weeks after start_date)  
    - tasks: Array of tasks directly in the plan
    
    🔄 If goal_type is **"hybrid"**, the PLAN must include:
    - All habit fields (recurrence_cycle, goal_frequency_per_cycle, etc.)
    - Both habit_cycles AND tasks arrays
    - This allows for daily habits + milestone and/or standalone non-repeating tasks

     **Habit Parsing Examples:**
    - "every other day" → goal_frequency_per_cycle: 15, recurrence_cycle: "monthly", goal_recurrence_count: 6
    - "3 times per week" → goal_frequency_per_cycle: 3, recurrence_cycle: "weekly", goal_recurrence_count: 12
    - "daily" → goal_frequency_per_cycle: 1, recurrence_cycle: "daily", goal_recurrence_count: 90
    - habit_cycles → each with:
        - cycle_label
        - start_date / end_date
        - occurrences → each with:
            - occurrence_order
            - estimated_effort
            - 2–4 tasks with:
                - title
                - due_date
                - estimated_time

    ⚠️ Temporal Constraints:
    - All dates must be in the future
    - Habit end_date is optional if ongoing
    - Project end_date is required and ≥ 2 weeks after start_date

    🎨 **Example Output Structure:**
    ```json
    {
      "goal": {
        "title": "Learn Python Programming",
        "description": "Master Python fundamentals and build real projects"
      },
      "plan": {
        "goal_type": "hybrid",
        "start_date": "2025-08-06",
        "end_date": "2025-12-31",
        "progress": 0,
        "recurrence_cycle": "daily",
        "goal_frequency_per_cycle": 1,
        "goal_recurrence_count": 147,
        "habit_cycles": [...],
        "tasks": [...]
      }
    }
    ```

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
     Today's date is {today}. Make sure all output respects today's date.
     
     🏗️ **CRITICAL ARCHITECTURE**: The output has TWO separate sections:
     1. **goal**: Lightweight metadata (title, description only)
     2. **plan**: All execution details (goal_type, dates, tasks, cycles, etc.)
     
     CRITICAL: When generating refined plans, you MUST include ALL required fields:
     - For habit plans: goal_recurrence_count (NEVER NULL), goal_frequency_per_cycle, recurrence_cycle, default_estimated_time_per_cycle
     - For project plans: end_date, tasks with due_date and estimated_time
     - For hybrid plans: both habit_cycles AND tasks arrays
     - Always include complete habit_cycles with occurrences and tasks
     - Never leave required fields as null or missing
     
     ⚠️  VALIDATION RULE: If goal_type is "habit" or "hybrid", then goal_recurrence_count MUST be a positive integer (e.g., 6, 12, 24)
     """
    ),
    ("user",
     """
     A user previously generated a structured goal plan, but they provided feedback asking for improvements.

     Your task:
     - Review the original goal description
     - Consider the user's feedback
     - Improve the previously generated plan accordingly
     - ENSURE ALL REQUIRED FIELDS ARE INCLUDED (especially goal_recurrence_count for habits)

     🏗️ **REMEMBER**: Output has TWO sections:
     1. **goal**: Only title and description (keep these unless feedback asks to change them)
     2. **plan**: All execution details (this is where most changes will go)

     Strictly follow these output rules:
     - All dates must be in the future (not before today)
     - For project plans:
         - Start date must be today or later
         - End date must be at least 2 weeks after start date
     - For habit plans:
         - MUST include goal_recurrence_count (number of cycles to repeat)
         - MUST include goal_frequency_per_cycle (how many times per cycle)
         - MUST include recurrence_cycle (daily/weekly/monthly)
         - MUST include default_estimated_time_per_cycle
         - End date is optional (may be recurring forever)
     - For hybrid plans:
         - Include all habit fields AND project tasks
         - Both habit_cycles and tasks arrays should be populated
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

     Return only a valid structured plan with ALL required fields included. Do not include extra explanation or chat text.
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

# ✅ NEW: Robust refinement function that handles incomplete outputs gracefully
def robust_refine_plan(goal_description: str, previous_plan_content: str, prior_feedback: str, 
                      source_plan_data: Optional[Dict[str, Any]] = None) -> GeneratedPlan:
    """
    Enhanced refinement function with robust parsing that handles incomplete LLM outputs.
    
    Args:
        goal_description: Original goal description
        previous_plan: Formatted previous plan content  
        prior_feedback: Combined feedback from all previous iterations
        source_plan_data: Original plan data for field completion

    Returns:
        GeneratedPlan: Validated and complete plan
    """
    try:
        # Import here to avoid circular imports
        from app.ai.robust_parser import RobustParser
        
        # Generate initial LLM output using the refinement prompt
        messages = refinement_prompt_template.format_messages(
            goal_description=goal_description,
            previous_plan=previous_plan_content,
            prior_feedback=prior_feedback
        )
        
        response = llm.invoke(messages)
        llm_output = response.content if hasattr(response, 'content') else str(response)
        
        # Ensure we have a string output
        if isinstance(llm_output, list):
            llm_output = str(llm_output)
        elif not isinstance(llm_output, str):
            llm_output = str(llm_output)
        
        # Initialize robust parser
        robust_parser = RobustParser(llm=llm, max_retries=3)

        # Use robust parser to handle any missing fields
        original_context = f"Goal: {goal_description}\nFeedback: {prior_feedback}"
        
        result = robust_parser.parse_with_retry(
            llm_output=llm_output,
            target_model=GeneratedPlan,
            original_prompt_context=original_context,
            source_plan_data=source_plan_data
        )
        
        return result
        
    except Exception as e:
        # Fallback to original chain if robust parsing fails
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Robust parsing failed, falling back to original chain: {e}")
        
        # Use original chain as fallback
        result = refine_plan_chain.invoke({
            "goal_description": goal_description,
            "previous_plan": previous_plan_content, 
            "prior_feedback": prior_feedback
        })
        
        return result["plan"]


