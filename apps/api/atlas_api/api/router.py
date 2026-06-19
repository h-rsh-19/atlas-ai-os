from fastapi import APIRouter

from atlas_api.api.routes import (
    actions,
    approvals,
    chat,
    code,
    dashboard,
    decisions,
    demo,
    evals,
    growth,
    health,
    journal,
    knowledge,
    labs,
    memory,
    plugins,
    privacy,
    profile,
    projects,
    providers,
    resume,
    retrieval,
    self_eval,
    simulator,
    traces,
    workflows,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(profile.router, prefix="/profile", tags=["profile"])
api_router.include_router(resume.router, prefix="/resume", tags=["resume"])
api_router.include_router(memory.router, prefix="/memory", tags=["memory"])
api_router.include_router(retrieval.router, prefix="/retrieval", tags=["retrieval"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(demo.router, prefix="/demo", tags=["demo"])
api_router.include_router(privacy.router, prefix="/privacy", tags=["privacy"])
api_router.include_router(journal.router, prefix="/journal", tags=["journal"])
api_router.include_router(decisions.router, prefix="/decisions", tags=["decisions"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(code.router, prefix="/code", tags=["code"])
api_router.include_router(labs.router, prefix="/labs", tags=["labs"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
api_router.include_router(growth.router, prefix="/growth", tags=["growth"])
api_router.include_router(workflows.router, prefix="/workflows", tags=["workflows"])
api_router.include_router(traces.router, prefix="/traces", tags=["traces"])
api_router.include_router(actions.router, prefix="/actions", tags=["actions"])
api_router.include_router(evals.router, prefix="/evals", tags=["evals"])
api_router.include_router(self_eval.router, prefix="/self-eval", tags=["self-eval"])
api_router.include_router(simulator.router, prefix="/simulator", tags=["simulator"])
api_router.include_router(plugins.router, prefix="/plugins", tags=["plugins"])
api_router.include_router(providers.router, prefix="/providers", tags=["providers"])
api_router.include_router(approvals.router, prefix="/approvals", tags=["approvals"])
