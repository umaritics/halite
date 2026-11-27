"""User-scoped session lifecycle, atomic turns and exact response replay."""
from __future__ import annotations

import base64
import json
import time
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import and_, func, or_, select, update

from db.models import utc_now
from db.models.sessions import DiagnosticSession, SessionSnapshot, SessionTurn
from investigation.turns import run_turn


def _iso(value):
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _json(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False)


def _session_dict(row):
    names = ('id', 'organization_id', 'user_id', 'asset_id', 'asset_tail', 'title', 'status',
             'outcome_part', 'outcome_jasc', 'outcome_note', 'outcome_record_id', 'turn_count')
    return {**{name: getattr(row, name) for name in names},
            **{name: _iso(getattr(row, name)) for name in ('created_at', 'updated_at', 'closed_at')}}


class SessionService:
    def __init__(self, store, principal, *, settings=None):
        if store is None or not store.is_available:
            raise HTTPException(503, 'Session database is unavailable.')
        if principal.kind != 'user' or not principal.user_id or not principal.organization_id:
            raise HTTPException(403, 'Sign in with a user account to access investigations.')
        self.store = store
        self.principal = principal
        self.settings = settings

    def _scope(self, mine=False):
        p = self.principal
        clauses = [DiagnosticSession.organization_id == p.organization_id]
        if mine or p.role not in ('admin', 'supervisor'):
            clauses.append(DiagnosticSession.user_id == p.user_id)
        return clauses

    def _find(self, db, session_id, write=False):
        row = db.scalar(select(DiagnosticSession).where(DiagnosticSession.id == session_id, *self._scope()))
        if row is None:
            raise HTTPException(404, 'Investigation not found.')
        if write and row.user_id != self.principal.user_id:
            raise HTTPException(403, 'Only the investigation owner can change it.')
        return row

    def create(self, *, asset_id=None, asset_tail=None, title=None):
        with self.store.session_scope() as db:
            row = DiagnosticSession(user_id=self.principal.user_id,
                                    organization_id=self.principal.organization_id,
                                    asset_id=asset_id, asset_tail=asset_tail,
                                    title=title or 'Investigation')
            db.add(row)
            db.flush()
            return _session_dict(row)

    def list(self, *, status=None, mine=False, has_outcome=None, cursor=None, limit=20):
        if not 1 <= limit <= 100:
            raise HTTPException(422, 'limit must be between 1 and 100.')
        if status not in (None, 'open', 'closed'):
            raise HTTPException(422, 'status must be open or closed.')
        clauses = self._scope(mine)
        if status:
            clauses.append(DiagnosticSession.status == status)
        if has_outcome is not None:
            outcome = and_(DiagnosticSession.status == 'closed',
                           DiagnosticSession.outcome_part.is_not(None), DiagnosticSession.outcome_part != '')
            clauses.append(outcome if has_outcome else ~outcome)
        if cursor:
            try:
                if len(cursor) > 512:
                    raise ValueError()
                decoded = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
                stamp = datetime.fromisoformat(decoded['created_at'])
                row_id = str(uuid.UUID(decoded['id']))
            except (ValueError, KeyError, TypeError, UnicodeError) as exc:
                raise HTTPException(422, 'Invalid session cursor.') from exc
            clauses.append(or_(DiagnosticSession.created_at < stamp,
                               and_(DiagnosticSession.created_at == stamp, DiagnosticSession.id < row_id)))
        with self.store.session_scope() as db:
            rows = db.scalars(select(DiagnosticSession).where(*clauses).order_by(
                DiagnosticSession.created_at.desc(), DiagnosticSession.id.desc()).limit(limit + 1)).all()
            items = [_session_dict(row) for row in rows[:limit]]
            next_cursor = None
            if len(rows) > limit:
                last = items[-1]
                next_cursor = base64.urlsafe_b64encode(_json({
                    'created_at': last['created_at'], 'id': last['id'],
                }).encode()).decode()
            return {'items': items, 'next_cursor': next_cursor}

    def get(self, session_id):
        with self.store.session_scope() as db:
            row = self._find(db, session_id)
            turns = db.scalars(select(SessionTurn).where(SessionTurn.session_id == row.id)
                               .order_by(SessionTurn.idx)).all()
            snapshots = {snap.turn_id: snap for snap in db.scalars(select(SessionSnapshot).join(
                SessionTurn, SessionSnapshot.turn_id == SessionTurn.id).where(SessionTurn.session_id == row.id))}
            result = _session_dict(row)
            result['can_write'] = row.user_id == self.principal.user_id and row.status == 'open'
            result['turns'] = []
            for turn in turns:
                snap = snapshots[turn.id]
                result['turns'].append({
                    'id': turn.id, 'idx': turn.idx, 'user_text': turn.user_text,
                    'created_at': _iso(turn.created_at), 'response': json.loads(turn.response_json),
                    'snapshot': {'hypotheses': json.loads(snap.hypotheses_json),
                                 'evidence_ids': json.loads(snap.evidence_ids_json),
                                 'belief_entropy': snap.belief_entropy},
                })
            return result

    def turn(self, session_id, *, message, answer=None, graph_repo, groq_service):
        if not message.strip() or len(message) > 4000:
            raise HTTPException(422, 'A message of 1 to 4000 characters is required.')
        with self.store.session_scope() as db:
            row = self._find(db, session_id, write=True)
            if row.status != 'open':
                raise HTTPException(409, 'Closed investigations are read only.')
            expected_count, asset_id = row.turn_count, row.asset_id
            previous = db.scalar(select(SessionTurn).where(SessionTurn.session_id == row.id)
                                 .order_by(SessionTurn.idx.desc()).limit(1))
            state = json.loads(previous.case_state_json) if previous else {}
            previous_response = json.loads(previous.response_json) if previous else None
        started = time.monotonic()
        from investigation.live_questions import QuestionController
        from investigation.grounding_runtime import annotate_response,load_configuration
        grounding_configuration=load_configuration(self.settings)
        controller = QuestionController.from_settings(self.settings)
        if answer is not None:
            if controller is None:
                raise HTTPException(409, 'No structured question is active for this investigation.')
            response = controller.answer(previous_response, answer)
        else:
            kwargs = {'question_controller': controller} if controller is not None else {}
            response = run_turn(session_id=session_id, asset_id=asset_id, message=message.strip(),
                                case_state=state, graph_repo=graph_repo, groq_service=groq_service, **kwargs)
        annotate_response(response,self.settings,structured_answer=answer is not None,configuration=grounding_configuration)
        turn_id = str(uuid.uuid4())
        response.update(turn_id=turn_id, turn_index=expected_count + 1)
        with self.store.session_scope() as db:
            self._find(db, session_id, write=True)
            claimed = db.execute(update(DiagnosticSession).where(
                DiagnosticSession.id == session_id, DiagnosticSession.status == 'open',
                DiagnosticSession.turn_count == expected_count,
            ).values(turn_count=expected_count + 1, updated_at=utc_now()))
            if claimed.rowcount != 1:
                raise HTTPException(409, 'Investigation changed during this turn. Reload before retrying.')
            turn = SessionTurn(
                id=turn_id, session_id=session_id, idx=expected_count + 1, user_text=message.strip(),
                case_state_json=_json(response['case_state']), decision=response['decision'],
                question_json=_json(response.get('question')), answer_json=_json(answer),
                reply_text=response.get('reply'), llm_status=response['llm_status'],
                grounding_json=_json(response.get('grounding')), ranker_mode=response['ranker_mode'],
                ranker_version=response['ranker_version'], latency_ms=round((time.monotonic() - started) * 1000),
                response_json=_json(response),
            )
            db.add(turn)
            db.flush()
            db.add(SessionSnapshot(turn_id=turn.id, hypotheses_json=_json(
                (response.get('beliefs') or {}).get('hypotheses', response['ranked_checks'])),
                                   evidence_ids_json=_json([r['record_id'] for r in response['evidence']]),
                                   belief_entropy=(response.get('beliefs') or {}).get('entropy')))
        return response

    def close(self, session_id, *, outcome_note, outcome_part=None, outcome_jasc=None, outcome_record_id=None):
        if not outcome_note.strip() or len(outcome_note) > 4000:
            raise HTTPException(422, 'A non-blank outcome note up to 4000 characters is required.')
        with self.store.session_scope() as db:
            row = self._find(db, session_id, write=True)
            if row.status != 'open':
                raise HTTPException(409, 'Investigation is already closed.')
            changed = db.execute(update(DiagnosticSession).where(
                DiagnosticSession.id == session_id, DiagnosticSession.status == 'open',
            ).values(status='closed', outcome_note=outcome_note.strip(), outcome_part=outcome_part,
                     outcome_jasc=outcome_jasc, outcome_record_id=outcome_record_id,
                     closed_at=utc_now(), updated_at=utc_now()))
            if changed.rowcount != 1:
                raise HTTPException(409, 'Investigation is already closed.')
            db.refresh(row)
            return _session_dict(row)

    def summary(self):
        with self.store.session_scope() as db:
            counts = dict(db.execute(select(DiagnosticSession.status, func.count()).where(*self._scope())
                                     .group_by(DiagnosticSession.status)).all())
            return {'title': 'Investigation sessions', 'link': '/app/investigations', 'stats': [
                {'label': 'Open investigations', 'value': counts.get('open', 0)},
                {'label': 'Closed investigations', 'value': counts.get('closed', 0)},
            ]}
