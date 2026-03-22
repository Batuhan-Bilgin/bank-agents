
import os
from typing import Optional
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

app = FastAPI(
    title="BankAI Agent API",
    description="100 Specialised Banking AI Agents powered by Claude Opus 4.6",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_factory = None
def get_factory():
    global _factory
    if _factory is None:
        from core.agent_factory import get_factory as _get_factory
        _factory = _get_factory()
    return _factory


class ChatRequest(BaseModel):
    message: str
    reset_session: bool = False

class ChatResponse(BaseModel):
    agent_id: str
    agent_role: str
    department: str
    response: str

class AutoRequest(BaseModel):
    task: str

class AutoResponse(BaseModel):
    selected_agent_id: str
    selected_agent_role: str
    department: str
    response: str

class PipelineRequest(BaseModel):
    agent_ids: list[str]
    task: str

class PipelineResponse(BaseModel):
    results: dict[str, str]
    agents_used: int

class AgentSummary(BaseModel):
    id: str
    role: str
    department: str
    authority_level: int
    tool_count: int


@app.get("/health")
def health():
    return {"status": "ok", "agents_loaded": get_factory().total}


@app.get("/departments")
def list_departments():
    return {"departments": get_factory().list_departments()}


@app.get("/agents", response_model=list[AgentSummary])
def list_agents(department: Optional[str] = None):
    return get_factory().list_agents(department=department)


@app.get("/agents/{agent_id}", response_model=AgentSummary)
def get_agent(agent_id: str):
    try:
        agent = get_factory().get(agent_id)
        return {
            "id": agent.id,
            "role": agent.role,
            "department": agent.department,
            "authority_level": agent.authority_level,
            "tool_count": len(agent.tool_names),
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/agents/{agent_id}/chat", response_model=ChatResponse)
def chat_with_agent(agent_id: str, req: ChatRequest):
    try:
        agent = get_factory().get(agent_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if req.reset_session:
        agent.reset()

    if not os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY") == "your_api_key_here":
        raise HTTPException(
            status_code=503,
            detail="ANTHROPIC_API_KEY not configured. Add it to .env file."
        )

    try:
        response_text = agent.chat(req.message, verbose=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return ChatResponse(
        agent_id=agent.id,
        agent_role=agent.role,
        department=agent.department,
        response=response_text,
    )


@app.post("/auto", response_model=AutoResponse)
def auto_route(req: AutoRequest):
    if not os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY") == "your_api_key_here":
        raise HTTPException(
            status_code=503,
            detail="ANTHROPIC_API_KEY not configured. Add it to .env file."
        )

    factory = get_factory()
    agent = factory.best_agent_for(req.task)
    try:
        response_text = agent.chat(req.task, verbose=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return AutoResponse(
        selected_agent_id=agent.id,
        selected_agent_role=agent.role,
        department=agent.department,
        response=response_text,
    )


@app.post("/pipeline", response_model=PipelineResponse)
def run_pipeline(req: PipelineRequest):
    if not os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY") == "your_api_key_here":
        raise HTTPException(
            status_code=503,
            detail="ANTHROPIC_API_KEY not configured. Add it to .env file."
        )

    from core.orchestrator import Orchestrator
    orch = Orchestrator()
    try:
        results = orch.pipeline(req.agent_ids, req.task, verbose=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return PipelineResponse(results=results, agents_used=len(results))


@app.get("/stats")
def get_stats():
    return get_factory().stats()
