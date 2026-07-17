from celery import Celery

from agent_yhzh.config import settings


celery_app = Celery(
    "agent_yhzh",
    broker=settings.redis_url,
    backend=settings.redis_url,
)
celery_app.conf.update(
    task_track_started=True,
    task_time_limit=300,
    task_soft_time_limit=270,
)


@celery_app.task(name="agent_yhzh.health")
def worker_health() -> dict[str, str]:
    return {"status": "ok"}
