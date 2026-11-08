from typing import Any

from pydantic import BaseModel, Field


class IngestPathRequest(BaseModel): # what type of data should go database
    path: str = Field(min_length=5)


class IngestPathResponse(BaseModel): # what type of data should come from database
    ingested: int
    skipped: int


class SourceItem(BaseModel): # what data should we get from db
    id: str
    text: str
    score: float
    metadata: dict[str, Any] | None = None


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceItem]


class QueryRequest(BaseModel):
    question: str = Field(min_length=10)