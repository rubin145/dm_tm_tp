from django.db.models.signals import post_migrate, post_save
from django.db.models import Sum
from django.dispatch import receiver
from .models import Configuration, AIConfiguration, APIKey, AICall

@receiver(post_migrate)
def create_default_configuration(sender, **kwargs):
    if not Configuration.objects.exists():
        Configuration.objects.create()
    
    if not AIConfiguration.objects.exists():
        AIConfiguration.objects.create()

    if not APIKey.objects.exists():
        APIKey.objects.create()

@receiver(post_save, sender=AICall)
def update_api_key(sender, instance, **kwargs):
    # Get the corresponding APIKey instance
    try:
        api_key = APIKey.objects.get(alias=instance.api_key_alias)
    except APIKey.DoesNotExist:
        return  # or handle the absence of the APIKey as you see fit

    # Update the APIKey fields based on the AICall instance
    related_calls = AICall.objects.filter(api_key_alias=api_key.alias)
    api_key.input_tokens_count = related_calls.aggregate(Sum('input_token_count'))['input_token_count__sum'] or 0
    api_key.output_tokens_count = related_calls.aggregate(Sum('output_token_count'))['output_token_count__sum'] or 0
    api_key.input_spend = related_calls.aggregate(Sum('input_spend'))['input_spend__sum'] or 0
    api_key.output_spend = related_calls.aggregate(Sum('output_spend'))['output_spend__sum'] or 0
    api_key.total_spend = related_calls.aggregate(Sum('total_spend'))['total_spend__sum'] or 0

    api_key.save()