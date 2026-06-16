from fastapi import APIRouter

from atlas_api.schemas import SkillTreeResponse, TimelineEvent
from atlas_api.services.store import store

router = APIRouter()


@router.get("/timeline", response_model=list[TimelineEvent])
def get_timeline() -> list[TimelineEvent]:
    return store.timeline()


@router.get("/skills", response_model=SkillTreeResponse)
def get_skill_tree() -> SkillTreeResponse:
    return store.skill_tree()
