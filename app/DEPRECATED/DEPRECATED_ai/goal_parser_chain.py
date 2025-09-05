#app/ai/goal_parser_chain.py
# === goal_parser_chain.py ===
# This file contains the LangChain chain that parses natural language goal descriptions
# into structured plans following our AI-driven schema (goal → cycles → occurrences → tasks)


from langchain_openai import ChatOpenAI                     # ✅ Interface to OpenAI chat models
from langchain.prompts import ChatPromptTemplate            # ✅ Helps define reusable prompt structure
from langchain.output_parsers import PydanticOutputParser   # ✅ Enforces Pydantic schema on LLM output
from app.DEPRECATED.DEPRECATED_ai.schemas import GeneratedPlan                    # ✅ Import your structured schema
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

    🎯 **TIME ESTIMATION CALIBRATION (CRITICAL):**
    - AVOID identical time estimates - each task has different complexity
    - Simple tasks: 180-300 minutes (basic concepts, setup)
    - Medium tasks: 300-420 minutes (moderate complexity, practice)
    - Complex tasks: 420-600 minutes (advanced concepts, integration)
    - Consider prerequisite knowledge and task difficulty differences
    - Vary estimates based on actual task complexity, not arbitrary patterns

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
        from app.DEPRECATED.DEPRECATED_ai.robust_parser import RobustParser
        
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
        logger.error(f"❌ ROBUST REFINE: Robust parsing failed, falling back to original chain: {e}")
        
        # Log the failed LLM output for debugging
        logger.error("💬 ROBUST REFINE: Last LLM output that failed parsing:")
        logger.error("=" * 50)
        output_str = str(llm_output)
        logger.error(output_str[:1000] + "..." if len(output_str) > 1000 else output_str)
        logger.error("=" * 50)
        
        # Use original chain as fallback
        result = refine_plan_chain.invoke({
            "goal_description": goal_description,
            "previous_plan": previous_plan_content, 
            "prior_feedback": prior_feedback
        })
        
        return result["plan"]


# ✅ NEW: Validate plan completeness function
def validate_plan_completeness(plan: GeneratedPlan) -> tuple[bool, list[str]]:
    """
    Validate that a generated plan has all required fields and structure completeness.
    
    This function performs comprehensive validation beyond basic semantic validation,
    checking for missing fields, proper structure, and logical consistency.
    
    Args:
        plan: The GeneratedPlan object to validate
        
    Returns:
        tuple: (is_valid: bool, issues: list[str])
            - is_valid: True if plan passes all validation checks
            - issues: List of validation issues found (empty if valid)
    """
    issues = []
    
    try:
        goal_data = plan.goal
        plan_data = plan.plan
        
        # Basic structure validation
        if not goal_data:
            issues.append("Missing goal data")
            return False, issues
            
        if not plan_data:
            issues.append("Missing plan data")
            return False, issues
            
        # Goal metadata validation
        if not goal_data.title or goal_data.title.strip() == "":
            issues.append("Goal title is missing or empty")
            
        if not goal_data.description or goal_data.description.strip() == "":
            issues.append("Goal description is missing or empty")
            
        # Plan structure validation
        if not plan_data.goal_type:
            issues.append("Goal type is missing")
            return False, issues
            
        if not plan_data.start_date:
            issues.append("Start date is missing")
            
        # Goal type specific validation
        goal_type = plan_data.goal_type
        
        if goal_type == "habit":
            # Habit-specific validation
            habit_issues = _validate_habit_plan_completeness(plan_data)
            issues.extend(habit_issues)
            
        elif goal_type == "project":
            # Project-specific validation
            project_issues = _validate_project_plan_completeness(plan_data)
            issues.extend(project_issues)
            
        elif goal_type == "hybrid":
            # Hybrid-specific validation (needs both habit and project elements)
            habit_issues = _validate_habit_plan_completeness(plan_data)
            project_issues = _validate_project_plan_completeness(plan_data, is_hybrid=True)
            issues.extend(habit_issues)
            issues.extend(project_issues)
            
        else:
            issues.append(f"Unknown goal type: {goal_type}")
            
        # Date validation
        date_issues = _validate_plan_dates(plan_data)
        issues.extend(date_issues)
        
        # Task validation
        task_issues = _validate_plan_tasks(plan_data)
        issues.extend(task_issues)
        
        is_valid = len(issues) == 0
        return is_valid, issues
        
    except Exception as e:
        issues.append(f"Validation error: {str(e)}")
        return False, issues


def _validate_habit_plan_completeness(plan_data) -> list[str]:
    """Validate habit-specific plan completeness."""
    issues = []
    
    # Required habit fields
    required_fields = {
        'goal_frequency_per_cycle': 'Goal frequency per cycle',
        'goal_recurrence_count': 'Goal recurrence count',
        'recurrence_cycle': 'Recurrence cycle',
        'default_estimated_time_per_cycle': 'Default estimated time per cycle'
    }
    
    for field, label in required_fields.items():
        value = getattr(plan_data, field, None)
        if value is None:
            issues.append(f"{label} is missing")
        elif field in ['goal_frequency_per_cycle', 'goal_recurrence_count', 'default_estimated_time_per_cycle']:
            if not isinstance(value, (int, float)) or value <= 0:
                issues.append(f"{label} must be a positive number")
    
    # Validate habit cycles
    if not hasattr(plan_data, 'habit_cycles') or not plan_data.habit_cycles:
        issues.append("No habit cycles defined")
    else:
        for i, cycle in enumerate(plan_data.habit_cycles):
            cycle_issues = _validate_habit_cycle(cycle, i + 1)
            issues.extend(cycle_issues)
    
    return issues


def _validate_project_plan_completeness(plan_data, is_hybrid: bool = False) -> list[str]:
    """Validate project-specific plan completeness."""
    issues = []
    
    # Project plans require an end date
    if not is_hybrid and not plan_data.end_date:
        issues.append("Project plan is missing end date")
    
    # Project plans need tasks
    if not hasattr(plan_data, 'tasks') or not plan_data.tasks:
        issues.append("No project tasks defined")
    else:
        # Validate that tasks have proper structure
        for i, task in enumerate(plan_data.tasks):
            task_issues = _validate_task_structure(task, f"Project task {i + 1}")
            issues.extend(task_issues)
    
    return issues


def _validate_habit_cycle(cycle, cycle_num: int) -> list[str]:
    """Validate a habit cycle structure."""
    issues = []
    
    if not hasattr(cycle, 'cycle_label') or not cycle.cycle_label:
        issues.append(f"Cycle {cycle_num} is missing cycle_label")
    
    if not hasattr(cycle, 'start_date') or not cycle.start_date:
        issues.append(f"Cycle {cycle_num} is missing start_date")
    
    if not hasattr(cycle, 'end_date') or not cycle.end_date:
        issues.append(f"Cycle {cycle_num} is missing end_date")
    
    if not hasattr(cycle, 'occurrences') or not cycle.occurrences:
        issues.append(f"Cycle {cycle_num} has no occurrences")
    else:
        for j, occurrence in enumerate(cycle.occurrences):
            occ_issues = _validate_occurrence_structure(occurrence, cycle_num, j + 1)
            issues.extend(occ_issues)
    
    return issues


def _validate_occurrence_structure(occurrence, cycle_num: int, occ_num: int) -> list[str]:
    """Validate an occurrence structure."""
    issues = []
    
    if not hasattr(occurrence, 'occurrence_order') or occurrence.occurrence_order is None:
        issues.append(f"Cycle {cycle_num}, occurrence {occ_num} is missing occurrence_order")
    
    if not hasattr(occurrence, 'estimated_effort') or occurrence.estimated_effort is None:
        issues.append(f"Cycle {cycle_num}, occurrence {occ_num} is missing estimated_effort")
    
    if not hasattr(occurrence, 'tasks') or not occurrence.tasks:
        issues.append(f"Cycle {cycle_num}, occurrence {occ_num} has no tasks")
    else:
        for k, task in enumerate(occurrence.tasks):
            task_issues = _validate_task_structure(task, f"Cycle {cycle_num}, occurrence {occ_num}, task {k + 1}")
            issues.extend(task_issues)
    
    return issues


def _validate_task_structure(task, task_label: str) -> list[str]:
    """Validate a task structure."""
    issues = []
    
    if not hasattr(task, 'title') or not task.title or task.title.strip() == "":
        issues.append(f"{task_label} is missing title")
    
    if not hasattr(task, 'due_date'):
        issues.append(f"{task_label} is missing due_date")
    
    if not hasattr(task, 'estimated_time') or task.estimated_time is None:
        issues.append(f"{task_label} is missing estimated_time")
    elif not isinstance(task.estimated_time, (int, float)) or task.estimated_time <= 0:
        issues.append(f"{task_label} estimated_time must be a positive number")
    
    return issues


def _validate_plan_dates(plan_data) -> list[str]:
    """Validate plan dates for logical consistency."""
    issues = []
    
    try:
        from datetime import datetime, date as date_type
        
        # Convert date strings to date objects for comparison
        start_date = None
        end_date = None
        
        if plan_data.start_date:
            if isinstance(plan_data.start_date, str):
                start_date = datetime.fromisoformat(plan_data.start_date).date()
            elif isinstance(plan_data.start_date, date_type):
                start_date = plan_data.start_date
        
        if plan_data.end_date:
            if isinstance(plan_data.end_date, str):
                end_date = datetime.fromisoformat(plan_data.end_date).date()
            elif isinstance(plan_data.end_date, date_type):
                end_date = plan_data.end_date
        
        # Validate date logic
        if start_date and end_date:
            if end_date <= start_date:
                issues.append("End date must be after start date")
        
        # Check if dates are in the future
        today = date_type.today()
        if start_date and start_date < today:
            issues.append("Start date should not be in the past")
    
    except Exception as e:
        issues.append(f"Date validation error: {str(e)}")
    
    return issues


def _validate_plan_tasks(plan_data) -> list[str]:
    """Validate overall task structure and consistency."""
    issues = []
    
    total_tasks = 0
    
    # Count tasks in habit cycles
    if hasattr(plan_data, 'habit_cycles') and plan_data.habit_cycles:
        for cycle in plan_data.habit_cycles:
            if hasattr(cycle, 'occurrences') and cycle.occurrences:
                for occurrence in cycle.occurrences:
                    if hasattr(occurrence, 'tasks') and occurrence.tasks:
                        total_tasks += len(occurrence.tasks)
    
    # Count project tasks
    if hasattr(plan_data, 'tasks') and plan_data.tasks:
        total_tasks += len(plan_data.tasks)
    
    if total_tasks == 0:
        issues.append("Plan has no tasks defined")
    
    return issues


# ✅ NEW: Generate plan with validation function
def generate_plan_with_validation(goal_description: str) -> GeneratedPlan:
    """
    Generate a structured plan from a natural language goal description with enhanced validation.
    
    This function uses the robust parser to handle incomplete LLM outputs and ensure
    all required fields are properly filled.
    
    Args:
        goal_description: Natural language description of the goal
        
    Returns:
        GeneratedPlan: Validated and complete plan
        
    Raises:
        Exception: If plan generation fails after all retries
    """
    try:
        # Import here to avoid circular imports
        from app.DEPRECATED.DEPRECATED_ai.robust_parser import RobustParser
        
        # Get today's date for prompt context
        today = date.today().isoformat()
        
        # Generate initial LLM output using the main prompt
        messages = prompt.format_messages(
            goal_description=goal_description,
            today_date=today
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
        original_context = f"Goal: {goal_description}\nToday: {today}"
        
        result = robust_parser.parse_with_retry(
            llm_output=llm_output,
            target_model=GeneratedPlan,
            original_prompt_context=original_context,
            source_plan_data=None
        )
        
        return result
        
    except Exception as e:
        # Fallback to original chain if robust parsing fails
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"❌ VALIDATION: Enhanced generation failed, falling back to original chain: {e}")
        
        # Use original chain as fallback
        today = date.today().isoformat()
        result = goal_parser_chain.invoke({
            "goal_description": goal_description,
            "format_instructions": parser.get_format_instructions(),
            "today_date": today
        })
        
        return result["plan"]


