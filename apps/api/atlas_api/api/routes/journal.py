from fastapi import APIRouter, status

from atlas_api.schemas import JournalEntry, JournalEntryCreate, JournalSummary
from atlas_api.services.store import store

router = APIRouter()


@router.get("", response_model=list[JournalEntry])
def list_journal_entries() -> list[JournalEntry]:
    return store.list_journal_entries()


@router.post("", response_model=JournalEntry, status_code=status.HTTP_201_CREATED)
def create_journal_entry(payload: JournalEntryCreate) -> JournalEntry:
    return store.create_journal_entry(payload)


@router.get("/summary", response_model=JournalSummary)
def summarize_journal() -> JournalSummary:
    return store.summarize_journal()
