from fastapi import FastAPI

# Step 1: Create the FastAPI app
app = FastAPI()

# Step 2: Define a basic test route
@app.get("/")
def read_root():
    return {"message": "Welcome to Smart Personal Planner!"}
