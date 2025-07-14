# Smart Personal Planner

An AI-powered personal goal planner that helps you:
- Create and track project goals or habits
- Break goals into tasks based on time estimates and availability
- Generate personalized daily plans using LLMs (via LangChain)
- View progress and adjust intelligently

## 🚀 Recent Bug Fixes and Improvements

### Critical Bugs Fixed:
- ✅ **Pydantic V2 Compatibility**: Fixed `orm_mode` → `from_attributes` for Pydantic V2
- ✅ **Environment Variables**: Added proper fallback handling for missing DATABASE_URL
- ✅ **Database Relationships**: Fixed cascade relationship bug in Task model
- ✅ **AI Configuration**: Added proper error handling for missing OpenAI API key
- ✅ **Empty Files**: Implemented missing config.py and daily_planner.py

### Anti-Patterns Resolved:
- ✅ **Input Validation**: Added comprehensive validation for business logic constraints
- ✅ **Error Handling**: Consistent error responses across all endpoints
- ✅ **Logging**: Added proper logging throughout the application
- ✅ **Database Transactions**: Added proper rollback handling
- ✅ **CORS Support**: Added for frontend integration

### New Features Added:
- ✅ **Task Management**: Full CRUD operations for tasks
- ✅ **Daily Planning**: AI-powered daily plan generation
- ✅ **Weekly Overview**: Plan generation for entire weeks
- ✅ **Frontend Interface**: Basic HTML/CSS/JS interface
- ✅ **API Documentation**: Comprehensive OpenAPI/Swagger docs

## 🏗️ Tech Stack:
- 🐍 **FastAPI** (backend API)
- 🧠 **LangChain + OpenAI** (AI engine)
- 🐘 **PostgreSQL/SQLite + SQLAlchemy** (database)
- 🎨 **HTML + CSS + JS** (frontend)

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set Up Environment Variables (Optional)
```bash
# Create .env file
DATABASE_URL=sqlite:///./smart_planner.db  # Default
OPENAI_API_KEY=your_openai_api_key_here    # For AI features
```

### 3. Create Database Tables
```bash
python create_db.py
```

### 4. Run the Application
```bash
python -m uvicorn app.main:app --reload
```

### 5. Access the Application
- **API Documentation**: http://localhost:8000/docs
- **Frontend**: Open `frontend/index.html` in your browser
- **API Base URL**: http://localhost:8000

## 📚 API Endpoints

### Goals
- `POST /goals/project/` - Create project goal
- `POST /goals/habit/` - Create habit goal
- `GET /goals/` - List all goals
- `GET /goals/{goal_id}` - Get specific goal
- `PUT /goals/project/{goal_id}` - Update project goal
- `PUT /goals/habit/{goal_id}` - Update habit goal
- `DELETE /goals/{goal_id}` - Delete goal

### Tasks
- `POST /tasks/` - Create task
- `GET /tasks/{task_id}` - Get specific task
- `GET /tasks/goal/{goal_id}` - Get tasks for goal
- `PUT /tasks/{task_id}` - Update task
- `DELETE /tasks/{task_id}` - Delete task
- `PATCH /tasks/{task_id}/complete` - Mark task complete

### Daily Planning
- `GET /daily-planner/today` - Get today's plan
- `POST /daily-planner/generate` - Generate custom daily plan
- `GET /daily-planner/week` - Get weekly overview

### AI Planning
- `POST /planning/ai-generate-plan` - Generate AI-powered plan

## 🔧 Configuration

The application uses environment variables for configuration:

- `DATABASE_URL`: Database connection string (defaults to SQLite)
- `OPENAI_API_KEY`: Required for AI features
- `OPENAI_MODEL`: AI model to use (default: gpt-4)
- `DEBUG`: Enable debug mode (default: false)

## 🧪 Testing

The application has been tested with:
- ✅ Goal creation (project and habit)
- ✅ Task management
- ✅ Daily planning
- ✅ Input validation
- ✅ Error handling
- ✅ API documentation

## 🎯 Project Phases:
- ✅ **Phase 1**: Create goals, tasks, AI plans
- 🔜 **Phase 2**: Track progress, send reminders
- 🔮 **Phase 3**: Learn from behavior, personalize further

## 🐛 Known Issues Resolved:
1. **Pydantic V2 warnings** - Fixed by updating config syntax
2. **Database crashes** - Added proper error handling and defaults
3. **AI service failures** - Added graceful fallbacks
4. **Missing validation** - Added comprehensive input validation
5. **Empty implementations** - Completed all missing modules
6. **Inconsistent errors** - Standardized error responses

## 💡 Development Notes:
- The application now handles missing environment variables gracefully
- SQLite is used as default database for development
- AI features are optional and degrade gracefully if not configured
- All endpoints include proper error handling and logging
- Frontend provides basic functionality for testing the API
