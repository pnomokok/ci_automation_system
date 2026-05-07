from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.team import Team, TeamMember
from app.models.user import User


class TeamRepository:

    async def create(self, session: AsyncSession, name: str) -> Team:
        team = Team(name=name)
        session.add(team)
        await session.flush()
        await session.refresh(team)
        return team

    async def get_by_id(self, session: AsyncSession, team_id: str) -> Team | None:
        result = await session.execute(
            select(Team).options(selectinload(Team.members)).where(Team.id == team_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, session: AsyncSession, name: str) -> Team | None:
        result = await session.execute(select(Team).where(Team.name == name))
        return result.scalar_one_or_none()

    async def get_all_for_user(self, session: AsyncSession, user_id: str) -> list[Team]:
        result = await session.execute(
            select(Team)
            .join(TeamMember, Team.id == TeamMember.team_id)
            .where(TeamMember.user_id == user_id)
        )
        return list(result.scalars().all())

    async def is_member(self, session: AsyncSession, team_id: str, user_id: str) -> bool:
        result = await session.execute(
            select(TeamMember).where(
                TeamMember.team_id == team_id,
                TeamMember.user_id == user_id,
            )
        )
        return result.scalar_one_or_none() is not None

    async def add_member(self, session: AsyncSession, team_id: str, user_id: str) -> TeamMember:
        member = TeamMember(team_id=team_id, user_id=user_id)
        session.add(member)
        await session.flush()
        return member

    async def remove_member(self, session: AsyncSession, team_id: str, user_id: str) -> bool:
        result = await session.execute(
            delete(TeamMember).where(
                TeamMember.team_id == team_id,
                TeamMember.user_id == user_id,
            )
        )
        return result.rowcount > 0

    async def get_members_with_users(self, session: AsyncSession, team_id: str) -> list[tuple[TeamMember, User]]:
        result = await session.execute(
            select(TeamMember, User)
            .join(User, TeamMember.user_id == User.id)
            .where(TeamMember.team_id == team_id)
        )
        return list(result.all())
