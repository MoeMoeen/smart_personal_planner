from fastapi import FastAPI
from app.routers import goals, cycles, planning


# Step 1: Create the FastAPI app
app = FastAPI()

# Step 2: Define a basic test route
@app.get("/")
def read_root():
    return {"message": "Welcome to Smart Personal Planner!"}

# Step 3: Include the goals router
app.include_router(goals.router)

# Step 4: Include the cycles router
app.include_router(cycles.router)

# Step 5: Include the planning router
app.include_router(planning.router)