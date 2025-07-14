from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import goals, cycles, planning, tasks, daily_planner


# Step 1: Create the FastAPI app
app = FastAPI(
    title="Smart Personal Planner API",
    description="AI-powered personal goal planner API",
    version="1.0.0"
)

# Step 2: Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Step 3: Define a basic test route
@app.get("/")
def read_root():
    return {"message": "Welcome to Smart Personal Planner!"}

# Step 4: Include the goals router
app.include_router(goals.router)

# Step 5: Include the cycles router
app.include_router(cycles.router)

# Step 6: Include the planning router
app.include_router(planning.router)

# Step 7: Include the tasks router
app.include_router(tasks.router)

# Step 8: Include the daily planner router
app.include_router(daily_planner.router)