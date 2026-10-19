from __future__ import annotations

import logging
import os
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

try:
    from celery import shared_task
except ImportError:
    def shared_task(func):
        return func

from apps.core.models import AuditLog
from apps.visits.models import ResponsePhoto

logger = logging.getLogger(__name__)


@shared_task
def cleanup_old_photos_task() -> str:
    """
    1. For soft-deleted photos: Delete physical file from disk and hard-delete the DB record.
    2. For photos older than 30 days: Delete physical file from disk to save storage,
       but KEEP the database record intact (clear image field) so audit/response history is preserved.
    3. Clean up empty media folders.
    """
    cutoff = timezone.now() - timedelta(days=30)

    # 1. Soft-deleted photos: remove file and purge row completely
    soft_deleted_photos = ResponsePhoto.all_objects.filter(deleted_at__isnull=False)
    soft_del_count = 0
    for photo in soft_deleted_photos.iterator(chunk_size=500):
        try:
            if photo.image:
                photo.image.delete(save=False)
        except Exception as exc:
            logger.warning("Could not delete file for soft-deleted photo %s: %s", photo.pk, exc)
        photo.hard_delete()
        soft_del_count += 1

    # 2. Photos older than 30 days: delete physical file from disk, but KEEP the DB row
    expired_photos = (
        ResponsePhoto.objects.filter(created_at__lt=cutoff)
        .exclude(image="")
        .exclude(image__isnull=True)
    )
    purged_file_count = 0
    for photo in expired_photos.iterator(chunk_size=500):
        try:
            if photo.image:
                photo.image.delete(save=False)
                photo.image = ""
                photo.save(update_fields=["image"])
                purged_file_count += 1
        except Exception as exc:
            logger.warning("Could not purge file for photo %s: %s", photo.pk, exc)
            continue

    # 3. Clean up empty folders in media/visits/
    _remove_empty_dirs(settings.MEDIA_ROOT)

    if purged_file_count > 0 or soft_del_count > 0:
        details = (
            f"Photo cleanup executed: {purged_file_count} image files (>30 days) removed from disk (records kept), "
            f"{soft_del_count} soft-deleted records purged."
        )
    else:
        details = "Photo cleanup executed: 0 expired photos found today (storage clean)."

    try:
        AuditLog.objects.create(
            actor=None,
            actor_label="Celery System",
            action=getattr(AuditLog.Action, "SYSTEM_CLEANUP", "SYSTEM_CLEANUP"),
            object_type="ResponsePhoto",
            object_label="Photo Storage (30 Days)",
            details=details,
        )
    except Exception as exc:
        logger.warning("Could not write audit log for photo cleanup: %s", exc)

    logger.info(details)
    return details


@shared_task
def cleanup_old_audit_logs_task() -> str:
    """Delete audit log entries older than 15 days."""
    cutoff = timezone.now() - timedelta(days=15)
    deleted_count, _ = AuditLog.objects.filter(created_at__lt=cutoff).delete()

    if deleted_count > 0:
        details = f"Audit log cleanup executed: {deleted_count} logs older than 15 days permanently purged."
    else:
        details = "Audit log cleanup executed: 0 expired logs found today (table clean)."

    try:
        AuditLog.objects.create(
            actor=None,
            actor_label="Celery System",
            action=getattr(AuditLog.Action, "SYSTEM_CLEANUP", "SYSTEM_CLEANUP"),
            object_type="AuditLog",
            object_label="Audit Log Table (15 Days)",
            details=details,
        )
    except Exception as exc:
        logger.warning("Could not write audit log for audit cleanup: %s", exc)

    logger.info(details)
    return details


def _remove_empty_dirs(path: str | os.PathLike) -> None:
    """Utility to clean up empty directories after image deletion."""
    if not os.path.exists(path):
        return
    for root, dirs, files in os.walk(path, topdown=False):
        for d in dirs:
            dir_path = os.path.join(root, d)
            try:
                if not os.listdir(dir_path):
                    os.rmdir(dir_path)
            except OSError:
                pass
