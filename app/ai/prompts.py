from datetime import date

def get_plan_generation_prompt(format_instructions: str) -> list:
    today = date.today().isoformat()
    return [
        (
            "system",
            f"""
            You are a smart AI personal planner. Today’s date is {today}. 
            Use this as the base for all scheduling decisions.
            """
        ),
        (
            "user",
            f"""
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

            User goal: {{goal_description}}

            Today's date: {today}
            """
        )
    ]