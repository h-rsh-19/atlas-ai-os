from fastapi import APIRouter

from atlas_api.schemas import UserProfile, UserProfileUpdate
from atlas_api.services.store import store

router = APIRouter()


@router.get("", response_model=UserProfile)
def get_profile() -> UserProfile:
    return store.get_profile()


@router.put("", response_model=UserProfile)
def update_profile(payload: UserProfileUpdate) -> UserProfile:
    return store.update_profile(payload)
