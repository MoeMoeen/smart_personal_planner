from fastapi import FastAPI
from app.routers import goals, cycles, occurrences, planning, telegram
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)

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

# Step 5: Include the occurrences router
app.include_router(occurrences.router)

# Step 6: Include the planning router
app.include_router(planning.router)

# Step 7: Include the Telegram router
app.include_router(telegram.router)
