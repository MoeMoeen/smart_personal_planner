# app/ai/robust_parser.py

from typing import Any, Dict, Optional, Type, TypeVar
from pydantic import BaseModel, ValidationError
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import json
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)

class RobustParser:
    """
    A robust parser that handles incomplete LLM outputs by iteratively fixing missing fields.
    """
    
    def __init__(self, llm: ChatOpenAI, max_retries: int = 3):
        self.llm = llm
        self.max_retries = max_retries
    
    def parse_with_retry(self, 
                        llm_output: str, 
                        target_model: Type[T], 
                        original_prompt_context: Optional[str] = None,
                        source_plan_data: Optional[Dict[str, Any]] = None) -> T:
        """
        Parse LLM output with automatic retry for missing fields.
        
        Args:
            llm_output: The raw output from the LLM
            target_model: The Pydantic model to parse into
            original_prompt_context: Original context for retry prompts
            previous_plan_data: Previous plan data to fill missing fields from
            
        Returns:
            Validated Pydantic model instance
            
        Raises:
            ValidationError: If parsing fails after all retries
        """
        
        for attempt in range(self.max_retries + 1):
            try:
                logger.info(f"🔧 ROBUST PARSER: Attempt {attempt + 1}/{self.max_retries + 1}")
                
                # Try to parse the current output
                parsed_data = self._safe_json_parse(llm_output)
                if parsed_data is None:
                    raise ValueError("Invalid JSON format")
                
                # Validate against the target model
                result = target_model(**parsed_data)
                logger.info("✅ ROBUST PARSER: Parsing successful")
                return result
                
            except ValidationError as e:
                logger.warning(f"⚠️ ROBUST PARSER: Validation failed - {e}")
                
                if attempt < self.max_retries:
                    # Generate a fix prompt for missing fields
                    llm_output = self._fix_missing_fields(
                        llm_output=llm_output,
                        validation_error=e,
                        target_model=target_model,
                        original_context=original_prompt_context,
                        source_plan=source_plan_data
                    )
                else:
                    logger.error("❌ ROBUST PARSER: All retries exhausted")
                    raise e
            except Exception as e:
                logger.error(f"❌ ROBUST PARSER: Unexpected error - {e}")
                if attempt >= self.max_retries:
                    raise e
                    
        raise ValidationError("Parsing failed after all retries")
    
    def _safe_json_parse(self, text: str) -> Optional[Dict[str, Any]]:
        """Safely parse JSON from LLM output, handling common issues."""
        try:
            # Try direct parsing first
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            import re
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass
            
            # Try to find JSON-like content
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    pass
                    
            return None
    
    def _fix_missing_fields(self, 
                           llm_output: str,
                           validation_error: ValidationError,
                           target_model: Type[T],
                           original_context: Optional[str] = None,
                           source_plan: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate a fix for missing fields by prompting the LLM.
        """
        
        # Extract missing field information
        missing_fields = []
        for error in validation_error.errors():
            if error['type'] == 'missing':
                field_name = error['loc'][0] if error['loc'] else 'unknown'
                missing_fields.append(field_name)
        
        logger.info(f"🔧 ROBUST PARSER: Missing fields detected: {missing_fields}")
        
        # Create a fix prompt
        fix_prompt = self._create_fix_prompt(
            original_output=llm_output,
            missing_fields=missing_fields,
            target_model=target_model,
            original_context=original_context,
            source_plan=source_plan
        )
        
        # Get the fixed output from LLM
        messages = [
            SystemMessage(content="You are a data completion assistant. Fix the provided JSON to include all required fields."),
            HumanMessage(content=fix_prompt)
        ]
        
        response = self.llm.invoke(messages)
        fixed_output = response.content if hasattr(response, 'content') else str(response)
        
        # Ensure we return a string
        if isinstance(fixed_output, list):
            fixed_output = str(fixed_output)
        elif not isinstance(fixed_output, str):
            fixed_output = str(fixed_output)
        
        logger.info("🔄 ROBUST PARSER: Generated fix attempt")
        return fixed_output
    
    def _create_fix_prompt(self, 
                          original_output: str,
                          missing_fields: list,
                          target_model: Type[T],
                          original_context: Optional[str] = None,
                          source_plan: Optional[Dict[str, Any]] = None) -> str:
        """Create a prompt to fix missing fields."""
        
        prompt_parts = [
            "The following JSON output is missing required fields:",
            f"Original JSON: {original_output}",
            f"Missing fields: {', '.join(missing_fields)}",
            "",
            "Your task:",
            "1. Keep all existing fields exactly as they are",
            "2. Add the missing required fields with appropriate values",
            "3. Return only the complete, valid JSON"
        ]
        
        # Add context if available
        if original_context:
            prompt_parts.extend([
                "",
                "Original context for reference:",
                original_context
            ])
        
        # Add previous plan data for reference
        if source_plan:
            prompt_parts.extend([
                "",
                "Previous plan data for reference:",
                json.dumps(source_plan, indent=2, default=str)
            ])
        
        # Add specific instructions for common missing fields
        if 'goal_recurrence_count' in missing_fields:
            prompt_parts.extend([
                "",
                "For goal_recurrence_count: Use a reasonable number like 12 for monthly habits, 52 for weekly habits"
            ])
        
        if 'default_estimated_time_per_cycle' in missing_fields:
            prompt_parts.extend([
                "",
                "For default_estimated_time_per_cycle: Use the total estimated time per cycle in minutes"
            ])
        
        # Add instructions for Plan-centric structure
        if any(field in missing_fields for field in ['goal', 'plan']):
            prompt_parts.extend([
                "",
                "CRITICAL ARCHITECTURE: The JSON must have TWO top-level sections:",
                "- 'goal': Contains only title, description, user_id",
                "- 'plan': Contains all execution details (goal_type, dates, tasks, habit_cycles, etc.)"
            ])
        
        if 'goal_type' in missing_fields:
            prompt_parts.extend([
                "",
                "For goal_type: Use 'habit', 'project', or 'hybrid' based on the goal's nature"
            ])
        
        if any(field in missing_fields for field in ['habit_cycles', 'tasks']):
            prompt_parts.extend([
                "",
                "For structure: habit goals need habit_cycles, project goals need tasks, hybrid goals need both"
            ])
        
        prompt_parts.extend([
            "",
            "Return only the corrected JSON, no explanation."
        ])
        
        return "\n".join(prompt_parts)
