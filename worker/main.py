import os
import time
import shutil
import logging
from datetime import datetime, timezone, timedelta
from apscheduler.schedulers.blocking import BlockingScheduler
from dotenv import load_dotenv

from db.session import SessionLocal
from db.models import Run
from db.seed import seed_db
from worker.pipeline import run_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("worker")

def cleanup_stale_running_runs():
    db = SessionLocal()
    try:
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=30)
        stale_runs = (
            db.query(Run)
            .filter(Run.status == "running")
            .filter(Run.started_utc < cutoff)
            .all()
        )
        for r in stale_runs:
            logger.warning(f"Marking stale run {r.id} as failed (started {r.started_utc})")
            r.status = "failed"
            r.error_text = "Timed out or terminated prior to worker restart"
            r.ended_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        db.commit()
    except Exception as e:
        logger.error(f"Error cleaning stale running runs: {e}")
        db.rollback()
    finally:
        db.close()

def cleanup_old_run_folders():
    runs_dir = os.path.abspath(os.getenv("RUNS_DIR", "./runs"))
    if not os.path.exists(runs_dir):
        return

    cutoff = time.time() - (3 * 24 * 3600)
    for name in os.listdir(runs_dir):
        target = os.path.join(runs_dir, name)
        if os.path.isdir(target):
            try:
                if os.path.getmtime(target) < cutoff:
                    shutil.rmtree(target, ignore_errors=True)
                    logger.info(f"Cleaned up old run folder: {name}")
            except Exception as e:
                logger.warning(f"Failed to remove run folder {name}: {e}")

def run_hourly_job():
    logger.info("Starting scheduled hourly optimization pipeline...")
    try:
        run_id = run_pipeline()
        logger.info(f"Hourly pipeline run completed successfully: {run_id}")
        cleanup_old_run_folders()
    except Exception as e:
        logger.error(f"Hourly pipeline execution failed: {e}")

def poll_pending_runs():
    db = SessionLocal()
    pending_run_id = None
    try:
        pending = (
            db.query(Run)
            .filter(Run.status == "pending")
            .order_by(Run.started_utc.asc())
            .first()
        )
        if pending:
            pending_run_id = pending.id
    except Exception as e:
        logger.error(f"Error querying pending runs: {e}")
    finally:
        db.close()

    if pending_run_id:
        logger.info(f"Picked up manual pending run: {pending_run_id}")
        try:
            run_pipeline(existing_run_id=pending_run_id)
            logger.info(f"Manual run {pending_run_id} completed successfully")
            cleanup_old_run_folders()
        except Exception as e:
            logger.error(f"Manual pipeline execution {pending_run_id} failed: {e}")

def start_worker():
    load_dotenv()
    seed_db()
    cleanup_stale_running_runs()

    scheduler = BlockingScheduler()

    # Minute 5 of every hour
    scheduler.add_job(
        run_hourly_job,
        trigger="cron",
        minute=5,
        id="hourly_pipeline",
        max_instances=1,
        coalesce=True
    )

    # Poll every 10 seconds for manually queued runs
    scheduler.add_job(
        poll_pending_runs,
        trigger="interval",
        seconds=10,
        id="poll_pending",
        max_instances=1,
        coalesce=True
    )

    logger.info("SmartAirAware worker started. Waiting for jobs...")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Worker stopped.")

if __name__ == "__main__":
    start_worker()
