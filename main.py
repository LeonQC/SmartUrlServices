from fastapi import FastAPI
from app.api.routes import router
from app.database.db import init_db
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Create FastAPI application
app = FastAPI(title="Smart URL")

# Add our API routes
app.include_router(router)

# Initialize database when the app starts
@app.on_event("startup")
async def startup_event():
    init_db()

# Run the application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)