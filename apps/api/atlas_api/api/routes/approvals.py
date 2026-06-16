from fastapi import APIRouter

from atlas_api.schemas import ApprovalAction
from atlas_api.services.store import store

router = APIRouter()


@router.get("", response_model=list[ApprovalAction])
def list_approvals() -> list[ApprovalAction]:
    return [action for action in store.list_actions() if action.status == "pending"]
