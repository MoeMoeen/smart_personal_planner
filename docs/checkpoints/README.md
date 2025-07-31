# Smart Personal Planner

An AI-powered personal goal planner that helps you:
- Create and track project goals or habits
- Break goals into tasks based on time estimates and availability
- Generate personalized daily plans using LLMs (via LangChain)
- View progress and adjust intelligently

### Tech Stack:
- 🐍 FastAPI (backend API)
- 🧠 LangChain + OpenAI (AI engine)
- 🐘 PostgreSQL + SQLAlchemy (database)
- 🎨 HTML + CSS + JS (frontend)

### Project Phases:
- ✅ Phase 1: Create goals, tasks, AI plans
- 🔜 Phase 2: Track progress, send reminders
- 🔮 Phase 3: Learn from behavior, personalize further


### Short Term Todo
- Save plan feedback to db
- Add general logging via logger
- Add smart logging from comments to auto-update later project todos or project roadmap
- Once plan is approved, we'll use the ai-generated code to automatically save it to the db.



---------------
Issues:

1. why goal --> plan not plans? in models. it's a one to many relationship, so each goal has many plans, not a single plan.
2. ask chatgpt: i want the main ui/ux be conversational as if our planner has an assistant/chatbot that talks with the user and the assistant calls various functions to manipulate the db and give back responses to the user and also manipulate the ui ultimately.
3. source plan id is not working properly, also refinement round.


