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
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "You are a helpful AI assistant that generates structured plans based on user input."),
        ("user", "Here is a user's goal description:\n\n{goal_description}\n\n"
        "Respond with a structured plan that matches this format:\n{format_instructions}"),
    ]
)

# ✅ Initialize the OpenAI model — use GPT-4 or GPT-3.5

try:
    openai_api_key = config("OPENAI_API_KEY")  # Raises error if missing
except Exception:
    openai_api_key = None

llm_kwargs = {
    "model": os.getenv("OPENAI_MODEL", "gpt-4"),
    "temperature": 0.2,
}

if openai_api_key:
    llm_kwargs["api_key"] = SecretStr(openai_api_key)
else:
    # Fallback for testing - use a mock or raise a more informative error
    print("⚠️  OpenAI API key not configured. AI features will not work.")

try:
    llm = ChatOpenAI(**llm_kwargs)
except Exception as e:
    print(f"❌ Failed to initialize OpenAI client: {e}")
    llm = None

# ✅ Create the goal parser chain that combines the prompt, LLM, and output parser
# ✅ Combine everything into a full chain: prompt → LLM → parser

if llm is not None:
    goal_parser_chain = (
        prompt | llm | parser
    )
else:
    goal_parser_chain = None

