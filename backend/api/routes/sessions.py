"""Authenticated, user-owned investigations with durable turn replay."""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, field_validator

from api.deps import get_graph_repo, get_groq_service, get_rel_store
from api.security import get_current_principal, require_llm_rate_limit
from investigation.sessions import SessionService

router = APIRouter(prefix="/sessions", tags=["sessions"])


class CreateSession(BaseModel):
    asset_id: str | None = Field(default=None, max_length=36)
    title: str | None = Field(default=None, max_length=160)

    @field_validator('title')
    @classmethod
    def clean_title(cls, value):
        return value.strip() or None if value is not None else None


class SessionAnswer(BaseModel):
    attribute: str = Field(min_length=1, max_length=80)
    value: str = Field(min_length=1, max_length=200)


class TurnRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    answer: SessionAnswer | None = None

    @field_validator('message')
    @classmethod
    def nonblank_message(cls, value):
        if not value.strip():
            raise ValueError('message must not be blank')
        return value.strip()


class CloseSession(BaseModel):
    outcome_part: str | None = Field(default=None, max_length=200)
    outcome_jasc: str | None = Field(default=None, max_length=20)
    outcome_record_id: str | None = Field(default=None, max_length=120)
    outcome_note: str = Field(min_length=1, max_length=4000)

    @field_validator('outcome_part', 'outcome_jasc', 'outcome_record_id')
    @classmethod
    def clean_optional(cls, value):
        return value.strip() or None if value is not None else None

    @field_validator('outcome_note')
    @classmethod
    def nonblank_note(cls, value):
        if not value.strip():
            raise ValueError('outcome_note must not be blank')
        return value.strip()


def service(store=Depends(get_rel_store), principal=Depends(get_current_principal)):
    return SessionService(store, principal)


@router.get('/summary')
def summary(store=Depends(get_rel_store), principal=Depends(get_current_principal)):
    if principal.kind != 'user':
        # Preserve the prep route's empty widget for demo/service callers. No user data disclosed.
        return {'title': 'Investigation sessions', 'link': '/app/investigations', 'stats': []}
    return SessionService(store, principal).summary()


@router.post('', status_code=201)
def create_session(req: CreateSession, sessions=Depends(service), graph_repo=Depends(get_graph_repo)):
    asset_tail = None
    if req.asset_id:
        asset = next((a for a in graph_repo.list_assets_with_counts() if a['id'] == req.asset_id), None)
        if asset is None:
            raise HTTPException(404, 'Aircraft not found.')
        asset_tail = asset.get('tail_number')
    return sessions.create(asset_id=req.asset_id, asset_tail=asset_tail, title=req.title)


@router.get('')
def list_sessions(status: Literal['open', 'closed'] | None = None, mine: bool = False,
                  has_outcome: bool | None = None, cursor: str | None = Query(default=None, max_length=512),
                  limit: int = Query(default=20, ge=1, le=100), sessions=Depends(service)):
    return sessions.list(status=status, mine=mine, has_outcome=has_outcome, cursor=cursor, limit=limit)


@router.get('/{session_id}')
def get_session(session_id: str, sessions=Depends(service)):
    return sessions.get(session_id)


@router.post('/{session_id}/turns', dependencies=[Depends(require_llm_rate_limit)])
def add_turn(session_id: str, req: TurnRequest, sessions=Depends(service),
             graph_repo=Depends(get_graph_repo), groq_service=Depends(get_groq_service)):
    return sessions.turn(session_id, message=req.message,
                         answer=req.answer.model_dump() if req.answer else None,
                         graph_repo=graph_repo, groq_service=groq_service)


@router.post('/{session_id}/close')
def close_session(session_id: str, req: CloseSession, sessions=Depends(service),
                  graph_repo=Depends(get_graph_repo)):
    # Authorize before validating referenced graph IDs, avoiding an existence oracle.
    sessions.get(session_id)
    if req.outcome_record_id and graph_repo.get_service_record(req.outcome_record_id) is None:
        raise HTTPException(422, 'Outcome record was not found in the graph.')
    return sessions.close(session_id, **req.model_dump())


@router.get('/{session_id}/report', response_class=HTMLResponse)
def session_report(session_id: str, sessions=Depends(service)):
    from investigation.report import render_report
    investigation = sessions.get(session_id)
    if investigation['status'] != 'closed':
        raise HTTPException(409, 'Close the investigation before printing its outcome report.')
    return HTMLResponse(render_report(investigation), headers={'Cache-Control': 'no-store'})
