import json
import re

from fastapi import HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.pipeline import Pipeline, PipelineStatus, TriggerType
from app.models.step import StepName, StepStatus
from app.models.user import User
from app.repositories.log_repo import LogRepository
from app.repositories.pipeline_repo import PipelineRepository
from app.repositories.repository_member_repo import RepositoryMemberRepository
from app.repositories.repository_repo import RepositoryRepository
from app.repositories.step_repo import StepRepository
from app.schemas.pipeline import PipelineCreate

_pipeline_repo = PipelineRepository()
_step_repo = StepRepository()
_log_repo = LogRepository()
_repo_repo = RepositoryRepository()
_member_repo = RepositoryMemberRepository()

_STEP_ORDER = [
    (StepName.install, 1),
    (StepName.build,   2),
    (StepName.test,    3),
]


class PipelineService:

    async def create(
        self,
        session: AsyncSession,
        redis: Redis,
        data: PipelineCreate,
        user: User | None = None,
    ) -> Pipeline:
        existing = await _pipeline_repo.get_active_by_repo_branch(
            session, str(data.repo_url), data.branch
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "ALREADY_RUNNING", "message": f"Bu branch için zaten aktif bir pipeline var (id: {existing.id}, durum: {existing.status})"},
            )

        running_count = await _pipeline_repo.count_running(session)
        if running_count >= settings.max_concurrent_pipelines:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "MAX_PIPELINES_REACHED",
                    "message": f"Maksimum eşzamanlı pipeline sayısına ({settings.max_concurrent_pipelines}) ulaşıldı",
                },
            )

        repo = await _repo_repo.get_by_url(session, str(data.repo_url))
        if not repo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "REPO_NOT_FOUND", "message": "Bu URL için kayıtlı repository yok. Önce repoyu sisteme ekleyin."},
            )

        # Kullanıcı varsa repo üyeliğini doğrula
        if user:
            if not await _member_repo.is_member(session, repo.id, user.id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={"code": "FORBIDDEN", "message": "Bu deponun üyesi değilsiniz"},
                )

        pipeline = await _pipeline_repo.create(session, {
            "repo_id":          repo.id,
            "triggered_by_id":  user.id if user else None,
            "repo_url":         str(data.repo_url),
            "branch":           data.branch,
            "commit_hash":      data.commit_hash,
            "commit_msg":       data.commit_msg,
            "commit_author":    data.commit_author,
            "trigger_type":     data.trigger_type,
            "status":           PipelineStatus.QUEUED,
        })

        steps = await _step_repo.create_many(session, [
            {"pipeline_id": pipeline.id, "name": name, "order": order, "status": StepStatus.PENDING}
            for name, order in _STEP_ORDER
        ])
        await session.commit()

        step_ids = {step.name: step.id for step in steps}
        await redis.rpush(
            "pipeline_jobs",
            json.dumps({
                "pipeline_id": pipeline.id,
                "repo_url":    str(data.repo_url),
                "branch":      data.branch,
                "commit_hash": data.commit_hash,
                "workspace":   data.workspace or f"/shared/workspaces/{pipeline.id}",
                "steps":       [n.value for n, _ in _STEP_ORDER],
                "step_ids":    step_ids,
                "timeout_sec": settings.pipeline_timeout_sec,
            }),
        )

        return await _pipeline_repo.get_by_id(session, pipeline.id)

    async def get(self, session: AsyncSession, pipeline_id: str, user: User | None = None) -> Pipeline:
        pipeline = await _pipeline_repo.get_by_id(session, pipeline_id)
        if pipeline is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "PIPELINE_NOT_FOUND", "message": "Pipeline bulunamadı"},
            )
        if user and pipeline.repo_id:
            if not await _member_repo.is_member(session, pipeline.repo_id, user.id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={"code": "FORBIDDEN", "message": "Bu pipeline'a erişim yetkiniz yok"},
                )
        return pipeline

    async def list(
        self,
        session: AsyncSession,
        page: int,
        page_size: int,
        status_filter: str | None,
        repo_id: str | None,
        user: User | None = None,
    ) -> tuple[list[Pipeline], int]:
        return await _pipeline_repo.get_all(
            session, page, page_size, status_filter, repo_id,
            user_id=user.id if user else None,
        )

    async def _assert_can_modify(self, session: AsyncSession, pipeline: Pipeline, user: User | None) -> None:
        """Kullanıcı pipeline'ı tetikleyenin kendisi veya repo owner'ı değilse 403 döner.
        triggered_by_id kaydedilmemiş eski pipeline'larda üyelik yeterlidir (self.get zaten kontrol eder).
        """
        if user is None:
            return
        if pipeline.triggered_by_id is None:
            if pipeline.trigger_type == TriggerType.webhook:
                # Webhook pipeline: sahip yok, sadece owner yönetebilir
                if pipeline.repo_id and await _member_repo.is_owner(session, pipeline.repo_id, user.id):
                    return
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={"code": "FORBIDDEN", "message": "Webhook pipeline'ları yalnızca repo owner'ı tarafından yönetilebilir."},
                )
            return  # Eski pipeline (migration öncesi): üyelik yeterliydi, self.get() zaten doğruladı
        if pipeline.triggered_by_id == user.id:
            return
        if pipeline.repo_id and await _member_repo.is_owner(session, pipeline.repo_id, user.id):
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Bu işlem için yetkiniz yok. Yalnızca pipeline'ı tetikleyen kullanıcı veya repo owner'ı bu işlemi yapabilir."},
        )

    async def stop(self, session: AsyncSession, redis: Redis, pipeline_id: str, user: User | None = None) -> Pipeline:
        pipeline = await self.get(session, pipeline_id, user=user)
        await self._assert_can_modify(session, pipeline, user)

        if pipeline.status not in (PipelineStatus.QUEUED, PipelineStatus.RUNNING):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "INVALID_STATE", "message": f"Pipeline durdurulamaz: mevcut durum {pipeline.status}"},
            )

        updated = await _pipeline_repo.update_status(session, pipeline_id, PipelineStatus.STOPPED)
        await session.commit()

        # Runner bu anahtarı polling ile okur ve container'ı sonlandırır
        await redis.set(f"pipeline_stop:{pipeline_id}", "1", ex=3600)
        return updated

    async def delete(self, session: AsyncSession, pipeline_id: str, user: User | None = None) -> None:
        pipeline = await self.get(session, pipeline_id, user=user)
        await self._assert_can_modify(session, pipeline, user)
        if pipeline.status in (PipelineStatus.QUEUED, PipelineStatus.RUNNING):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "INVALID_STATE", "message": "Aktif pipeline silinemez. Önce durdurun."},
            )
        await _pipeline_repo.delete(session, pipeline_id)
        await session.commit()

    async def retrigger(
        self,
        session: AsyncSession,
        redis: Redis,
        pipeline_id: str,
        user: User | None = None,
    ) -> Pipeline:
        source = await self.get(session, pipeline_id, user=user)

        data = PipelineCreate(
            repo_url=source.repo_url,
            branch=source.branch,
            trigger_type=TriggerType.manual,
        )
        return await self.create(session, redis, data, user=user)

    async def get_logs(
        self,
        session: AsyncSession,
        pipeline_id: str,
        step_name: str | None,
        stream: str | None,
        page: int,
        page_size: int,
        user: User | None = None,
    ) -> tuple[list, int]:
        await self.get(session, pipeline_id, user=user)  # 404 + erişim kontrolü
        return await _log_repo.get_by_pipeline_id(
            session, pipeline_id, step_name, stream, page, page_size
        )

    async def get_report(self, session: AsyncSession, pipeline_id: str, user: User | None = None) -> dict:
        pipeline = await self.get(session, pipeline_id, user=user)

        # Test loglarından pytest çıktısını parse et — tüm sayfaları oku
        all_rows: list = []
        page, page_size = 1, 500
        while True:
            rows, total_logs = await _log_repo.get_by_pipeline_id(
                session, pipeline_id, step_name="test", page=page, page_size=page_size
            )
            all_rows.extend(rows)
            if len(all_rows) >= total_logs:
                break
            page += 1
        rows = all_rows

        total, passed, failed, skipped = 0, 0, 0, 0
        _ansi = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")  # all CSI sequences

        for log, _ in rows:
            content = _ansi.sub("", log.content).replace("\r", "")

            # Skip vitest "Test Files  N passed (N)" — totals captured in "Tests" line
            if re.search(r"test files", content, re.IGNORECASE):
                continue

            # Vitest summary: "      Tests  N failed | N passed (N)"
            if re.search(r"\bTests\b", content) and ("passed" in content or "failed" in content):
                passed_m  = re.search(r"(\d+) passed",  content)
                failed_m  = re.search(r"(\d+) failed",  content)
                skipped_m = re.search(r"(\d+) skipped", content)
                if passed_m or failed_m:
                    passed  += int(passed_m.group(1)  if passed_m  else 0)
                    failed  += int(failed_m.group(1)  if failed_m  else 0)
                    skipped += int(skipped_m.group(1) if skipped_m else 0)
                continue

            # Pytest summary: "N failed, M passed, P skipped in X.Xs"
            # Order varies: failed may come before passed
            if re.search(r"\bin \d+\.?\d*s\b", content):
                passed_m  = re.search(r"(\d+) passed",  content)
                failed_m  = re.search(r"(\d+) failed",  content)
                skipped_m = re.search(r"(\d+) skipped", content)
                if passed_m or failed_m:
                    passed  += int(passed_m.group(1)  if passed_m  else 0)
                    failed  += int(failed_m.group(1)  if failed_m  else 0)
                    skipped += int(skipped_m.group(1) if skipped_m else 0)

        total = passed + failed + skipped

        test_step = next((s for s in (pipeline.steps or []) if s.name == StepName.test), None)
        no_tests_found = (total == 0 and test_step is not None and test_step.status == StepStatus.SUCCESS)

        duration = pipeline.duration_sec or 0
        return {
            "pipeline_id":    pipeline_id,
            "status":         pipeline.status,
            "total_tests":    total,
            "passed":         passed,
            "failed":         failed,
            "skipped":        skipped,
            "duration_sec":   float(duration),
            "no_tests_found": no_tests_found,
        }
