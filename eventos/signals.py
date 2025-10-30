from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import Event, EventChangeLog
from django.contrib.auth import get_user_model

@receiver(pre_save, sender=Event)
def log_event_changes(sender, instance, **kwargs):
    if not instance.pk:
        return  # Solo para actualizaciones, no creación
    try:
        old_event = Event.objects.get(pk=instance.pk)
    except Event.DoesNotExist:
        return
    fields_to_track = ["event_name", "description", "date", "start_datetime", "end_datetime", "status", "category", "image", "organizer"]
    for field in fields_to_track:
        old_value = getattr(old_event, field, None)
        new_value = getattr(instance, field, None)
        if old_value != new_value:
            EventChangeLog.objects.create(
                event=instance,
                changed_by=getattr(instance, '_changed_by', None),
                change_type="datos evento" if field not in ["status"] else "estado",
                field_changed=field,
                old_value=str(old_value),
                new_value=str(new_value)
            )
