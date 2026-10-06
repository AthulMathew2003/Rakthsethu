import asyncio
from typing import AsyncGenerator
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.enums import BloodGroup, UserRole
from app.models.hospital import Hospital
from app.models.user import User

# Test engine using NullPool to prevent asyncpg connection concurrency clashes
test_engine = create_async_engine(settings.DATABASE_URL, echo=False, poolclass=NullPool)
TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        async with TestingSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def super_admin_user(db_session: AsyncSession) -> User:
    user = User(
        user_code="TEST_ADMIN",
        email="superadmin@test.com",
        hashed_password=hash_password("adminpassword123"),
        full_name="Super Administrator",
        role=UserRole.SUPER_ADMIN,
        is_active=True,
    )
    # Check if user already exists
    from sqlalchemy import select
    res = await db_session.execute(select(User).where(User.email == "superadmin@test.com"))
    existing = res.scalar_one_or_none()
    if existing:
        return existing

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def super_admin_headers(super_admin_user: User) -> dict:
    token = create_access_token(
        subject=str(super_admin_user.id),
        role=super_admin_user.role.value,
        hospital_id=None,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def test_hospital(db_session: AsyncSession) -> Hospital:
    from sqlalchemy import select
    res = await db_session.execute(select(Hospital).where(Hospital.hospital_code == "TEST_HOSP01"))
    existing = res.scalar_one_or_none()
    if existing:
        return existing

    hospital = Hospital(
        hospital_code="TEST_HOSP01",
        name="Kottayam Medical College",
        hospital_type="Government",
        district="Kottayam",
        address="Gandhi Nagar, Kottayam, Kerala",
        phone="+914812597200",
        is_active=True,
    )
    db_session.add(hospital)
    await db_session.commit()
    await db_session.refresh(hospital)
    return hospital


@pytest_asyncio.fixture
async def hospital_admin_user(db_session: AsyncSession, test_hospital: Hospital) -> User:
    from sqlalchemy import select
    res = await db_session.execute(select(User).where(User.email == "hospadmin@test.com"))
    existing = res.scalar_one_or_none()
    if existing:
        return existing

    user = User(
        user_code="TEST_HOSP_ADMIN",
        hospital_id=test_hospital.id,
        email="hospadmin@test.com",
        hashed_password=hash_password("password123"),
        full_name="Hospital Admin User",
        role=UserRole.HOSPITAL_ADMIN,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def hospital_admin_headers(hospital_admin_user: User) -> dict:
    token = create_access_token(
        subject=str(hospital_admin_user.id),
        role=hospital_admin_user.role.value,
        hospital_id=hospital_admin_user.hospital_id,
    )
    return {"Authorization": f"Bearer {token}"}
