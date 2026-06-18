import logging
import os
import uuid

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from src.config.settings import settings

log = logging.getLogger(__name__)

APP_NAME = "ecombot"


def get_session_service():
    """Return the active session service based on SESSION_BACKEND env var."""
    backend = os.getenv("SESSION_BACKEND", "memory").lower()

    if backend == "memory":
        log.info("Session backend: InMemory (no persistence)")
        return InMemorySessionService()

    if backend == "database":
        try:
            from google.adk.sessions import DatabaseSessionService
            svc = DatabaseSessionService(db_url=settings.adk_db_url)
            log.info("Session backend: PostgreSQL (%s:%s/%s)",
                     settings.pg_host, settings.pg_port, settings.pg_db)
            return svc
        except Exception as exc:
            log.error("PostgreSQL session service unavailable: %s", exc)
            raise RuntimeError(
                "Cannot connect to PostgreSQL for session storage. "
                "Start the database with:  docker compose up -d postgres\n"
                f"Detail: {exc}"
            ) from exc

    log.warning("Unknown SESSION_BACKEND '%s', falling back to InMemory", backend)
    return InMemorySessionService()


async def make_runner(
    agent,
    user_id: str | None = None,
    session_id: str | None = None,
) -> tuple[Runner, str, str]:
    """
    Wrap an agent in a Runner with a session.
    Returns (runner, user_id, session_id).
    """
    session_service = get_session_service()
    runner = Runner(agent=agent, app_name=APP_NAME, session_service=session_service)

    if user_id is None:
        user_id = f"user-{uuid.uuid4().hex[:6]}"

    if session_id is None:
        session_id = f"session-{uuid.uuid4().hex[:8]}"
        await session_service.create_session(
            app_name=APP_NAME, user_id=user_id, session_id=session_id
        )
        log.info("Created new session: %s / %s", user_id, session_id)
    else:
        existing = await session_service.get_session(
            app_name=APP_NAME, user_id=user_id, session_id=session_id
        )
        if existing is None:
            await session_service.create_session(
                app_name=APP_NAME, user_id=user_id, session_id=session_id
            )
            log.info("Session not found — created fresh: %s", session_id)
        else:
            log.info("Reconnected to existing session: %s", session_id)

    return runner, user_id, session_id
