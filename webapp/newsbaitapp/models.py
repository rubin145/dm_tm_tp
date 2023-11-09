from django.db import models
from solo.models import SingletonModel
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.functional import cached_property
import json
from .system_prompt import default_system_prompt

class AIConfiguration(SingletonModel):
    system_prompt = models.TextField(default=default_system_prompt)
    api_key_alias = models.CharField(max_length=50,default='dmtmtp')
    model = models.CharField(max_length=200,default="gpt-3.5-turbo")
    testing = models.BooleanField(default=False)
    extra_config = models.JSONField(default=dict,blank=True)

class APIKey(models.Model):
    alias = models.SlugField(unique=True,default='a')
    key = models.CharField(max_length=300,default='abc')
    input_tokens_count = models.IntegerField(default=0)
    output_tokens_count = models.IntegerField(default=0)
    input_spend = models.FloatField(default=0)
    output_spend = models.FloatField(default=0)
    total_spend = models.FloatField(default=0)

class AICall(models.Model):
    title = models.TextField(blank=True)
    input_token_count = models.IntegerField()
    output_token_count = models.IntegerField()
    input_spend = models.FloatField()
    output_spend = models.FloatField()
    total_spend = models.FloatField()
    organization = models.CharField(max_length=200, blank=True, null=True)  # Changed to organization to avoid trailing underscore
    n_choices = models.IntegerField()
    choices = models.JSONField(default=list)
    model_resp = models.CharField(max_length=50, blank=True, null=True)  
    model_arg = models.CharField(max_length=50)
    system_prompt = models.TextField()  # No need to specify blank=True for a TextField without a max_length
    input_prompt = models.TextField()  # Same as above
    api_key_alias = models.SlugField()
    extra_config = models.JSONField(default=dict)
    testing = models.BooleanField(default=False) 

    def __str__(self):
        return self.title

class Configuration(SingletonModel):
    title_comparison_repeats = models.PositiveIntegerField(default=2)
    multi_article_title_selection_repeats = models.PositiveIntegerField(default=2)
    num_articles_shown = models.PositiveIntegerField(default=6)
    min_appearances = models.PositiveIntegerField(default=6)

    class Meta:
        verbose_name_plural = "Configurations"

class News(models.Model):
    date = models.DateField()
    author = models.CharField(max_length=200)
    newspaper_name = models.CharField(max_length=200)
    section = models.CharField(max_length=100)
    pompadour = models.TextField()
    title = models.TextField()
    text = models.TextField()
    original_tags = models.TextField()
    article_url = models.URLField()
    newspaper_domain = models.URLField()
    entities = models.ManyToManyField('Entity')
    unique_id = models.IntegerField()

class Entity(models.Model):
    tag = models.CharField(max_length=100)
    section = models.CharField(max_length=100, null=True)
    document_indices = models.TextField()  # For storing list of indices; consider JSONField if using Postgres.
    appearances = models.IntegerField()
    occurrences = models.IntegerField()
    synonyms = models.TextField()  # Similar to document_indices
    n_synonyms = models.IntegerField()

    def __str__(self):
        return self.tag

class Experiment(models.Model):
    # Test Type Choices
    TITLE_COMPARISON = 'title_comparison'
    MULTI_ARTICLE_TITLE_SELECTION = 'multi_article_title_selection'
    SECUNDARIO_INCOMPLETO = 'secundario_incompleto'
    SECUNDARIO_COMPLETO = 'secundario_completo'
    TERCIARIO_INCOMPLETO = 'terciario_incompleto'
    TERCIARIO_COMPLETO = 'terciario_completo'
    PREFER_NOT_TO_SAY = 'prefer_not_to_say'
    TEST_TYPE_CHOICES = [
        (TITLE_COMPARISON, 'Title Comparison'),
        (MULTI_ARTICLE_TITLE_SELECTION, 'Multi Article Title Selection'),
    ]
    STUDIES_CHOICES = [
        (SECUNDARIO_INCOMPLETO, 'Secundario incompleto o menor'),
        (SECUNDARIO_COMPLETO, 'Secundario completo'),
        (TERCIARIO_INCOMPLETO, 'Terciario o Universitario incompleto'),
        (TERCIARIO_COMPLETO, 'Terciario o Universitario completo o superior'),
        (PREFER_NOT_TO_SAY, 'Prefiero no decirlo'),
    ]

    user_email = models.EmailField()
    session_id = models.CharField(max_length=100)
    randomization_seed = models.IntegerField(default=9999) #9999 no es una seed real, es porque no acepta valores nulos.

    test_type = models.CharField(max_length=50, choices=TEST_TYPE_CHOICES)
    iteration_number = models.IntegerField(default=1)

    options = models.TextField(default="[]")

    selected_article = models.ForeignKey('News', on_delete=models.CASCADE, related_name="selected_article", null=True, blank=True)
    selected_title = models.CharField(max_length=500, null=True, blank=True)
    selected_section = models.CharField(max_length=100, null=True, blank=True)  # Assuming using string identifiers for sections
    selected_tags = models.ManyToManyField('Entity', related_name="selected_tags", blank=True) 
    selected_position = models.PositiveIntegerField(null=True, blank=True)  # Position of the selected article on the screen
    selected_is_ai = models.BooleanField(default=False)  # If True, the chosen title is AI-generated

    concordance_score = models.IntegerField(null=True, blank=True)

    gender = models.CharField(max_length=20, null=True, blank=True)
    age = models.IntegerField(null=True, blank=True)
    studies = models.CharField(max_length=100, null=True, blank=True, choices=STUDIES_CHOICES)

    feedback = models.TextField(null=True, blank=True)  # Optional feedback from the user

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user_email} - {self.test_type} - Iteration {self.iteration_number}"
    
    @property
    def options_list(self):
        return json.loads(self.options)

    @options_list.setter
    def options_list(self, value):
        self.options = json.dumps(value, cls=DjangoJSONEncoder)