import pytest
import httpx
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from app.services.repository_service import _assert_public_github_repo
from app.services.repository_service import RepositoryService
from app.services.step_service import StepService
from app.services.pipeline_service import PipelineService
from app.schemas.repository import RepositoryUpdate
from app.schemas.internal import (
    StepUpdateRequest, LogBatchRequest, LogLine, PipelineUpdateRequest,
)
from app.models.pipeline import PipelineStatus, TriggerType
from app.models.step import StepName, StepStatus
from app.models.repository_member import RepoRole
from app.repositories.pipeline_repo import PipelineRepository
from app.repositories.repository_repo import RepositoryRepository
from app.repositories.repository_member_repo import RepositoryMemberRepository
from app.repositories.step_repo import StepRepository
from app.repositories.user_repo import UserRepository
from app.core.security import hash_password

_pipeline_repo = PipelineRepository()
_step_repo = StepRepository()
_repo_repo = RepositoryRepository()
_member_repo = RepositoryMemberRepository()
_user_repo = UserRepository()

# ── Helpers ──────────────────────────────────────────────────────────────────

async def _make_user(session, username):
    user = await _user_repo.create(session, username, hash_password("pass"))
    await session.commit()
    return user


async def _make_repo(session, user_id, url):
    repo = await _repo_repo.create(session, {
        "url": url, "default_branch": "main", "webhook_secret": "s"
    })
    await _member_repo.add(session, repo.id, user_id, RepoRole.owner.value)
    await session.commit()
    return repo


async def _make_pipeline(session, repo, status=PipelineStatus.QUEUED):
    pipeline = await _pipeline_repo.create(session, {
        "repo_id": repo.id,
        "repo_url": repo.url,
        "branch": "main",
        "trigger_type": TriggerType.manual,
        "status": status,
    })
    steps = await _step_repo.create_many(session, [
        {"pipeline_id": pipeline.id, "name": StepName.install, "order": 1, "status": StepStatus.PENDING},
        {"pipeline_id": pipeline.id, "name": StepName.build,   "order": 2, "status": StepStatus.PENDING},
        {"pipeline_id": pipeline.id, "name": StepName.test,    "order": 3, "status": StepStatus.PENDING},
    ])
    await session.commit()
    return await _pipeline_repo.get_by_id(session, pipeline.id), steps


def _mock_http_client(status_code, json_body=None):
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = json_body or {}
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    return mock_client


# ── _assert_public_github_repo ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_assert_non_github_url_raises_400():
    with pytest.raises(HTTPException) as exc:
        await _assert_public_github_repo("https://gitlab.com/org/repo")
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_assert_malformed_url_no_repo_part_raises_400():
    with pytest.raises(HTTPException) as exc:
        await _assert_public_github_repo("https://github.com/only-user")
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_assert_public_repo_passes():
    mock_client = _mock_http_client(200, {"private": False})
    with patch("httpx.AsyncClient", return_value=mock_client):
        await _assert_public_github_repo("https://github.com/org/repo")


@pytest.mark.asyncio
async def test_assert_private_repo_raises_400():
    mock_client = _mock_http_client(200, {"private": True})
    with patch("httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(HTTPException) as exc:
            await _assert_public_github_repo("https://github.com/org/repo")
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_assert_404_repo_raises_400():
    mock_client = _mock_http_client(404)
    with patch("httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(HTTPException) as exc:
            await _assert_public_github_repo("https://github.com/org/repo")
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_assert_unexpected_status_raises_400():
    mock_client = _mock_http_client(503)
    with patch("httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(HTTPException) as exc:
            await _assert_public_github_repo("https://github.com/org/repo")
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_assert_network_error_raises_400():
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=httpx.RequestError("timeout"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    with patch("httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(HTTPException) as exc:
            await _assert_public_github_repo("https://github.com/org/repo")
    assert exc.value.status_code == 400


# ── RepositoryService ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_repo_service_update_not_found(db_session):
    svc = RepositoryService()
    with pytest.raises(HTTPException) as exc:
        await svc.update(db_session, "nonexistent-id", RepositoryUpdate(default_branch="dev"), "user-id")
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_repo_service_update_forbidden(db_session):
    user = await _make_user(db_session, "rs_owner1")
    other = await _make_user(db_session, "rs_other1")
    repo = await _make_repo(db_session, user.id, "https://github.com/svc/upd1")
    svc = RepositoryService()
    with pytest.raises(HTTPException) as exc:
        await svc.update(db_session, repo.id, RepositoryUpdate(default_branch="dev"), other.id)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_repo_service_update_empty_patch_returns_unchanged(db_session):
    user = await _make_user(db_session, "rs_owner2")
    repo = await _make_repo(db_session, user.id, "https://github.com/svc/upd2")
    svc = RepositoryService()
    result = await svc.update(db_session, repo.id, RepositoryUpdate(), user.id)
    assert result.id == repo.id


@pytest.mark.asyncio
async def test_repo_service_delete_not_found(db_session, mock_redis):
    svc = RepositoryService()
    with pytest.raises(HTTPException) as exc:
        await svc.delete(db_session, "nonexistent-id", "user-id", mock_redis)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_repo_service_delete_forbidden(db_session, mock_redis):
    user = await _make_user(db_session, "rs_owner3")
    other = await _make_user(db_session, "rs_other3")
    repo = await _make_repo(db_session, user.id, "https://github.com/svc/del1")
    svc = RepositoryService()
    with pytest.raises(HTTPException) as exc:
        await svc.delete(db_session, repo.id, other.id, mock_redis)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_repo_service_delete_stops_active_pipelines(db_session, mock_redis):
    user = await _make_user(db_session, "rs_owner4")
    repo = await _make_repo(db_session, user.id, "https://github.com/svc/del2")
    await _make_pipeline(db_session, repo, status=PipelineStatus.RUNNING)
    svc = RepositoryService()
    await svc.delete(db_session, repo.id, user.id, mock_redis)
    mock_redis.set.assert_called()


# ── StepService ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_step_update_nonexistent_raises_404(db_session):
    svc = StepService()
    with pytest.raises(HTTPException) as exc:
        await svc.update_step(db_session, "no-id", StepUpdateRequest(status=StepStatus.RUNNING))
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_step_update_to_running(db_session):
    user = await _make_user(db_session, "ss_user1")
    repo = await _make_repo(db_session, user.id, "https://github.com/svc/ss1")
    _, steps = await _make_pipeline(db_session, repo)

    svc = StepService()
    result = await svc.update_step(db_session, steps[0].id, StepUpdateRequest(status=StepStatus.RUNNING))
    assert result["status"] == StepStatus.RUNNING


@pytest.mark.asyncio
async def test_step_update_to_success_calculates_duration(db_session):
    user = await _make_user(db_session, "ss_user2")
    repo = await _make_repo(db_session, user.id, "https://github.com/svc/ss2")
    _, steps = await _make_pipeline(db_session, repo)
    now = datetime.now(timezone.utc)

    svc = StepService()
    await svc.update_step(db_session, steps[0].id, StepUpdateRequest(
        status=StepStatus.RUNNING, started_at=now
    ))
    result = await svc.update_step(db_session, steps[0].id, StepUpdateRequest(
        status=StepStatus.SUCCESS, exit_code=0,
        finished_at=now + timedelta(seconds=15)
    ))
    assert result["status"] == StepStatus.SUCCESS


@pytest.mark.asyncio
async def test_step_update_to_failed_with_exit_code(db_session):
    user = await _make_user(db_session, "ss_user3")
    repo = await _make_repo(db_session, user.id, "https://github.com/svc/ss3")
    _, steps = await _make_pipeline(db_session, repo)

    svc = StepService()
    result = await svc.update_step(db_session, steps[1].id, StepUpdateRequest(
        status=StepStatus.FAILED, exit_code=1
    ))
    assert result["status"] == StepStatus.FAILED


@pytest.mark.asyncio
async def test_add_logs_nonexistent_step_raises_404(db_session):
    now = datetime.now(timezone.utc)
    svc = StepService()
    with pytest.raises(HTTPException) as exc:
        await svc.add_logs(db_session, "no-id", LogBatchRequest(lines=[
            LogLine(line_number=1, stream="stdout", timestamp=now, content="x")
        ]))
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_add_logs_returns_saved_count(db_session):
    user = await _make_user(db_session, "log_user1")
    repo = await _make_repo(db_session, user.id, "https://github.com/svc/log1")
    _, steps = await _make_pipeline(db_session, repo)
    now = datetime.now(timezone.utc)

    svc = StepService()
    result = await svc.add_logs(db_session, steps[0].id, LogBatchRequest(lines=[
        LogLine(line_number=1, stream="stdout", timestamp=now, content="Installing..."),
        LogLine(line_number=2, stream="stderr", timestamp=now, content="Warning"),
    ]))
    assert result["saved"] == 2


@pytest.mark.asyncio
async def test_update_pipeline_nonexistent_raises_404(db_session):
    svc = StepService()
    with pytest.raises(HTTPException) as exc:
        await svc.update_pipeline(db_session, "no-id", PipelineUpdateRequest(status=PipelineStatus.SUCCESS))
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_update_pipeline_to_running(db_session):
    user = await _make_user(db_session, "ps_user1")
    repo = await _make_repo(db_session, user.id, "https://github.com/svc/ps1")
    pipeline, _ = await _make_pipeline(db_session, repo)

    svc = StepService()
    result = await svc.update_pipeline(db_session, pipeline.id,
                                       PipelineUpdateRequest(status=PipelineStatus.RUNNING))
    assert result["status"] == PipelineStatus.RUNNING


@pytest.mark.asyncio
async def test_update_pipeline_to_failed(db_session):
    user = await _make_user(db_session, "ps_user2")
    repo = await _make_repo(db_session, user.id, "https://github.com/svc/ps2")
    pipeline, _ = await _make_pipeline(db_session, repo)

    svc = StepService()
    result = await svc.update_pipeline(db_session, pipeline.id,
                                       PipelineUpdateRequest(status=PipelineStatus.FAILED))
    assert result["status"] == PipelineStatus.FAILED


@pytest.mark.asyncio
async def test_update_pipeline_to_stopped(db_session):
    user = await _make_user(db_session, "ps_user3")
    repo = await _make_repo(db_session, user.id, "https://github.com/svc/ps3")
    pipeline, _ = await _make_pipeline(db_session, repo, status=PipelineStatus.RUNNING)

    svc = StepService()
    result = await svc.update_pipeline(db_session, pipeline.id,
                                       PipelineUpdateRequest(status=PipelineStatus.STOPPED))
    assert result["status"] == PipelineStatus.STOPPED


# ── PipelineService ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pipeline_service_create_no_repo_raises_404(db_session, mock_redis):
    from app.schemas.pipeline import PipelineCreate
    svc = PipelineService()
    with pytest.raises(HTTPException) as exc:
        await svc.create(db_session, mock_redis, PipelineCreate(
            repo_url="https://github.com/no/exist", branch="main"
        ))
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_pipeline_service_stop_finished_raises_409(db_session, mock_redis):
    user = await _make_user(db_session, "pls_user1")
    repo = await _make_repo(db_session, user.id, "https://github.com/svc/pls1")
    pipeline, _ = await _make_pipeline(db_session, repo, status=PipelineStatus.SUCCESS)

    svc = PipelineService()
    with pytest.raises(HTTPException) as exc:
        await svc.stop(db_session, mock_redis, pipeline.id, user=user)
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_pipeline_service_stop_queued_succeeds(db_session, mock_redis):
    user = await _make_user(db_session, "pls_user2")
    repo = await _make_repo(db_session, user.id, "https://github.com/svc/pls2")
    pipeline, _ = await _make_pipeline(db_session, repo, status=PipelineStatus.QUEUED)

    svc = PipelineService()
    result = await svc.stop(db_session, mock_redis, pipeline.id, user=user)
    assert result.status == PipelineStatus.STOPPED


@pytest.mark.asyncio
async def test_pipeline_service_delete_active_raises_409(db_session):
    user = await _make_user(db_session, "pld_user1")
    repo = await _make_repo(db_session, user.id, "https://github.com/svc/pld1")
    pipeline, _ = await _make_pipeline(db_session, repo, status=PipelineStatus.RUNNING)

    svc = PipelineService()
    with pytest.raises(HTTPException) as exc:
        await svc.delete(db_session, pipeline.id, user=user)
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_pipeline_service_delete_finished_succeeds(db_session):
    user = await _make_user(db_session, "pld_user2")
    repo = await _make_repo(db_session, user.id, "https://github.com/svc/pld2")
    pipeline, _ = await _make_pipeline(db_session, repo, status=PipelineStatus.SUCCESS)

    svc = PipelineService()
    await svc.delete(db_session, pipeline.id, user=user)


@pytest.mark.asyncio
async def test_pipeline_service_get_report_empty_logs(db_session):
    user = await _make_user(db_session, "rep_user1")
    repo = await _make_repo(db_session, user.id, "https://github.com/svc/rep1")
    pipeline, _ = await _make_pipeline(db_session, repo, status=PipelineStatus.SUCCESS)

    svc = PipelineService()
    report = await svc.get_report(db_session, pipeline.id)
    assert report["pipeline_id"] == pipeline.id
    assert report["total_tests"] == 0


@pytest.mark.asyncio
async def test_pipeline_service_get_report_nonexistent_raises_404(db_session):
    svc = PipelineService()
    with pytest.raises(HTTPException) as exc:
        await svc.get_report(db_session, "no-id")
    assert exc.value.status_code == 404
