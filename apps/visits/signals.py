from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import ResponsePhoto, VisitResponse
from .services import recompute_visit_metrics


@receiver([post_save, post_delete], sender=VisitResponse)
def _recompute_on_response_change(sender, instance: VisitResponse, **kwargs):  # noqa: ARG001
    recompute_visit_metrics(instance.visit)


@receiver(post_delete, sender=ResponsePhoto)
def _delete_photo_file(sender, instance: ResponsePhoto, **kwargs):  # noqa: ARG001
    if instance.image:
        instance.image.delete(save=False)
