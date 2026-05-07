from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.team import Team
from app.models.user import User
from app.repositories.team_repo import TeamRepository
from app.repositories.user_repo import UserRepository
from app.schemas.team import TeamCreate

_team_repo = TeamRepository()
_user_repo = UserRepository()


class TeamService:

    async def create(self, session: AsyncSession, data: TeamCreate, creator: User) -> Team:
        existing = await _team_repo.get_by_name(session, data.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "TEAM_NAME_TAKEN", "message": "Bu takım adı zaten kullanılıyor"},
            )
        team = await _team_repo.create(session, data.name)
        await _team_repo.add_member(session, team.id, creator.id)
        await session.commit()
        return await _team_repo.get_by_id(session, team.id)

    async def get(self, session: AsyncSession, team_id: str, user: User) -> Team:
        team = await _team_repo.get_by_id(session, team_id)
        if team is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "TEAM_NOT_FOUND", "message": "Takım bulunamadı"},
            )
        if not await _team_repo.is_member(session, team_id, user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "FORBIDDEN", "message": "Bu takımın üyesi değilsiniz"},
            )
        return team

    async def list_for_user(self, session: AsyncSession, user: User) -> list[Team]:
        return await _team_repo.get_all_for_user(session, user.id)

    async def add_member(self, session: AsyncSession, team_id: str, username: str, requester: User) -> dict:
        await self.get(session, team_id, requester)  # üyelik + 404 kontrolü

        target = await _user_repo.get_by_username(session, username)
        if target is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "USER_NOT_FOUND", "message": f"'{username}' kullanıcısı bulunamadı"},
            )
        if await _team_repo.is_member(session, team_id, target.id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "ALREADY_MEMBER", "message": "Kullanıcı zaten bu takımın üyesi"},
            )
        await _team_repo.add_member(session, team_id, target.id)
        await session.commit()
        return {"team_id": team_id, "user_id": target.id, "username": target.username}

    async def remove_member(self, session: AsyncSession, team_id: str, user_id: str, requester: User) -> None:
        await self.get(session, team_id, requester)  # üyelik + 404 kontrolü

        removed = await _team_repo.remove_member(session, team_id, user_id)
        if not removed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "MEMBER_NOT_FOUND", "message": "Kullanıcı bu takımın üyesi değil"},
            )
        await session.commit()

    async def list_members(self, session: AsyncSession, team_id: str, user: User) -> list[dict]:
        await self.get(session, team_id, user)
        rows = await _team_repo.get_members_with_users(session, team_id)
        return [
            {"user_id": member.user_id, "username": u.username, "joined_at": member.created_at}
            for member, u in rows
        ]
