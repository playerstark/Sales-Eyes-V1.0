"""Job tracking for async intelligence research."""

import logging
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Job status values."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobTracker:
    """Track async research jobs in memory (simple implementation).

    For production, would use a real job queue (Celery, RQ, etc.).
    """

    def __init__(self):
        self.jobs: dict[str, dict] = {}

    def create_job(self, session_id: uuid.UUID) -> str:
        """Create a new job tracking record.

        Args:
            session_id: Intelligence session ID

        Returns:
            Job ID (UUID)
        """
        job_id = str(uuid.uuid4())
        self.jobs[job_id] = {
            "job_id": job_id,
            "session_id": str(session_id),
            "status": JobStatus.QUEUED,
            "progress_percent": 0,
            "current_step": "Queued",
            "message": None,
            "error": None,
            "created_at": datetime.utcnow().isoformat(),
            "started_at": None,
            "completed_at": None,
        }
        logger.info(f"Created job {job_id} for session {session_id}")
        return job_id

    def get_job(self, job_id: str) -> Optional[dict]:
        """Get job status.

        Args:
            job_id: Job ID

        Returns:
            Job dict or None if not found
        """
        return self.jobs.get(job_id)

    def update_job(
        self,
        job_id: str,
        status: Optional[str] = None,
        progress_percent: Optional[int] = None,
        current_step: Optional[str] = None,
        message: Optional[str] = None,
        error: Optional[str] = None,
    ) -> Optional[dict]:
        """Update job status.

        Args:
            job_id: Job ID
            status: New status
            progress_percent: Progress (0-100)
            current_step: Current step description
            message: Status message
            error: Error message (if failed)

        Returns:
            Updated job dict or None if not found
        """
        if job_id not in self.jobs:
            return None

        job = self.jobs[job_id]

        if status:
            job["status"] = status
            if status == JobStatus.RUNNING and not job["started_at"]:
                job["started_at"] = datetime.utcnow().isoformat()
            if status in (JobStatus.COMPLETED, JobStatus.FAILED):
                job["completed_at"] = datetime.utcnow().isoformat()

        if progress_percent is not None:
            job["progress_percent"] = min(100, max(0, progress_percent))

        if current_step:
            job["current_step"] = current_step

        if message:
            job["message"] = message

        if error:
            job["error"] = error

        logger.debug(f"Updated job {job_id}: {status or 'no status change'}")
        return job

    def mark_running(self, job_id: str, step: str = "Running") -> Optional[dict]:
        """Mark job as running."""
        return self.update_job(job_id, status=JobStatus.RUNNING, progress_percent=10, current_step=step)

    def mark_completed(self, job_id: str, message: str = "Completed") -> Optional[dict]:
        """Mark job as completed."""
        return self.update_job(
            job_id,
            status=JobStatus.COMPLETED,
            progress_percent=100,
            current_step="Completed",
            message=message
        )

    def mark_failed(self, job_id: str, error: str) -> Optional[dict]:
        """Mark job as failed."""
        return self.update_job(
            job_id,
            status=JobStatus.FAILED,
            progress_percent=0,
            current_step="Failed",
            error=error
        )


# Global job tracker instance
_job_tracker: Optional[JobTracker] = None


def get_job_tracker() -> JobTracker:
    """Get or create global job tracker."""
    global _job_tracker
    if _job_tracker is None:
        _job_tracker = JobTracker()
    return _job_tracker
