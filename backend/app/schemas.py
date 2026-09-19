from uuid import UUID

from pydantic import BaseModel, Field

class CreateWorkspaceRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)

class JoinWorkspaceRequest(BaseModel):
    invite_code: str = Field(min_length=4, max_length=50)

class CreateSessionRequest(BaseModel):
    title: str | None = Field(default=None, max_length=255)

class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=2000)  #capped at 2000 to prevent someone using up token quota in one request 

class GenerateRoadmapRequest(BaseModel):
    document_id: UUID

class ProgramRequest(BaseModel):
    completed: bool
