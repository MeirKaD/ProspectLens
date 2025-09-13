from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import uvicorn
import os

# Import the agent
from agent import ImprovedPersonQualificationAgent

# Initialize the app
app = FastAPI(
    title="Person Qualification API",
    description="API for qualifying a person for an event using AI",
    version="1.0.0"
)

# Add CORS middleware to allow requests from the Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the agent
agent = ImprovedPersonQualificationAgent()

# Define request models
class EventRequirement(BaseModel):
    requirement: str

class EventDetails(BaseModel):
    name: str
    type: str
    requirements: List[str]
    audience: str
    format: str

class QualificationRequest(BaseModel):
    person_name: str
    event_details: EventDetails

class QualificationFromUrlRequest(BaseModel):
    person_name: str
    event_url: str

class QualificationResponse(BaseModel):
    person_name: str
    qualification_score: int
    qualification_reasoning: str
    searches_performed: int
    information_sources: List[Dict[str, Any]]
    timestamp: str
    error: Optional[str] = None

@app.get("/")
async def root():
    return {"message": "Person Qualification API is running"}

@app.post("/qualify", response_model=QualificationResponse)
async def qualify_person(request: QualificationRequest):
    try:
        # Call the agent to qualify the person
        result = agent.qualify_person(
            person_name=request.person_name,
            event_details=request.event_details.dict()
        )

        # Return the result
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/qualify-from-url", response_model=QualificationResponse)
async def qualify_person_from_url(request: QualificationFromUrlRequest):
    try:
        # Call the agent to qualify the person using URL
        result = agent.qualify_person_from_url(
            person_name=request.person_name,
            event_url=request.event_url
        )

        # Return the result
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Run the app
if __name__ == "__main__":
    # Get port from environment variable or use default
    port = int(os.environ.get("PORT", 8000))
    
    # Run the server
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)