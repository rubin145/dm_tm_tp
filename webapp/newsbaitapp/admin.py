import csv
from .models import Configuration, News, Entity, Experiment, AIConfiguration, AICall, APIKey
from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.utils.html import format_html
from django.http import HttpResponse
from django.utils.text import Truncator
from django.shortcuts import render, redirect
from django.urls import path
from django.utils.timezone import now
from .forms import CSVImportForm

@admin.register(AIConfiguration)
class AIConfigurationAdmin(admin.ModelAdmin):
    list_display = ('api_key_alias', 'model', 'testing', 'extra_config')

@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = ('alias', 'input_tokens_count', 'output_tokens_count', 'input_spend', 'output_spend', 'total_spend')

@admin.register(AICall)
class AICallAdmin(admin.ModelAdmin):
    list_display = ('title', 'input_token_count', 'output_token_count', 'total_spend', 'model_arg', 'api_key_alias', 'testing')
    search_fields = ('title','choices','model_resp','model_arg','system_prompt','input_prompt','api_key_alias','extra-config')
    list_filter = ('organization','n_choices','model_arg','api_key_alias','testing')

    def export_to_csv(self, request, queryset):
        meta = self.model._meta
        field_names = [field.name for field in meta.fields]

        # Create a timestamp for the filename
        timestamp = now().strftime("%Y%m%d_%H%M%S")
        # Format the filename with model name and timestamp, replace dots with underscores
        filename = f"{meta.app_label}_{meta.model_name}_{timestamp}.csv".replace('.', '_')

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename={filename}.csv'
        writer = csv.writer(response)

        # Write a first row with header information
        writer.writerow(field_names)

        # Write data rows
        for obj in queryset:
            row = [getattr(obj, field) for field in field_names]
            writer.writerow(row)

        return response

    export_to_csv.short_description = "Export selected AICalls to CSV"
    actions = [export_to_csv]

class EntityFilter(SimpleListFilter):
    title = 'Entity'  # or use _('entities') for translation
    parameter_name = 'entity'

    def lookups(self, request, model_admin):
        # This is where you create a tuple of lookup options.
        # You can get as creative as you want with how you generate these.
        entities = Entity.objects.all()
        return [(entity.id, entity.tag) for entity in entities]

    def queryset(self, request, queryset):
        # This is where you process the selected lookup option.
        if self.value():
            return queryset.filter(entities__id=self.value())
        return queryset
    
@admin.register(Configuration)
class ConfigurationAdmin(admin.ModelAdmin):
    list_display = ('title_comparison_repeats', 'multi_article_title_selection_repeats', 'num_articles_shown', 'min_appearances')
    # You can customize labels by defining verbose_name on the model's fields
    # or by using list_display_links to set a custom function that returns the label.

@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ('unique_id','newspaper_name', 'section', 'title', 'get_entities')
    search_fields = ('unique_id', 'title', 'entities__tag','section')
    list_filter = (EntityFilter,'section','newspaper_name')
    
    def get_entities(self, obj):
        return ", ".join([entity.tag for entity in obj.entities.all()])
    get_entities.short_description = 'Entidades'  # Label for the column

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('upload_news/', self.upload_news, name='upload_news'),
        ]
        return my_urls + urls

    def upload_news(self, request):
        if request.method == "POST":
            csv_file = request.FILES["csv_file"]
            # ... process CSV file ...
            self.message_user(request, "CSV file has been imported")
            return redirect("..")
        form = CSVImportForm()
        payload = {"form": form}
        return render(request, "admin/csv_form.html", payload)
    #def display_entities(self, obj):
    #    return ", ".join([str(entity) for entity in obj.entities.all()])
    #display_entities.short_description = 'Entities'

@admin.register(Entity)
class EntityAdmin(admin.ModelAdmin):
    list_display = ('tag', 'section', 'appearances', 'occurrences', 'n_synonyms', 'truncated_synonyms')
    # If synonyms is a large text, consider using a custom method to truncate it for the list display.
    search_fields = ('synonyms',)
    list_filter = ('section',)

    def truncated_synonyms(self, obj):
        full_synonyms = obj.synonyms
        truncated = Truncator(obj.synonyms).chars(500)  # Truncate after 500 characters
        return format_html(
            '<div title="{}">{}</div>', 
            full_synonyms,  # Full text for the tooltip
            truncated  # Displayed truncated text
        )
    truncated_synonyms.short_description = 'Synonyms'

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('upload_entities/', self.upload_entities, name='upload_entities'),
        ]
        return my_urls + urls

    def upload_entities(self, request):
        if request.method == "POST":
            csv_file = request.FILES["csv_file"]
            # ... process CSV file ...
            self.message_user(request, "CSV file has been imported")
            return redirect("..")
        form = CSVImportForm()
        payload = {"form": form}
        return render(request, "admin/csv_form.html", payload)


@admin.register(Experiment)
class ExperimentAdmin(admin.ModelAdmin):
    list_display = ('test_type', 'selected_section', 'selected_title', 'selected_is_ai', 'selected_position', 'concordance_score')
    search_fields = ('selected_tags','options')
    list_filter = ('selected_section','test_type','selected_position','selected_is_ai','concordance_score','gender','age','studies')
    
    # Add any additional fields you want to display in the list view.
    def export_to_csv(modeladmin, request, queryset):
        meta = modeladmin.model._meta
        field_names = [field.name  for field in meta.fields if field.name != 'selected_article']

        timestamp = now().strftime("%Y%m%d_%H%M%S")
        # Format the filename with model name and timestamp, replace dots with underscores
        filename = f"{meta.app_label}_{meta.model_name}_{timestamp}.csv".replace('.', '_')


        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename={filename}.csv'
        writer = csv.writer(response)

        # Write a first row with header information
        writer.writerow(
            field_names + [
                'selected_article_uid', 
                'selected_article_text', 
                'selected_article_original_title', 
                'selected_article_newspaper', 
                'selected_article_date', 
                'selected_article_url'
            ]
        )

        # Write data rows
        for obj in queryset:
            # Assuming `News` model has the fields: `unique_id`, `text`, `original_title`, `newspaper_name`, `publish_date`, `url`
            news_obj = obj.selected_article
            if news_obj:
                row = [
                    getattr(obj, field) for field in field_names
                ] + [
                    news_obj.unique_id,
                    news_obj.text,
                    news_obj.title,
                    news_obj.newspaper_name,
                    news_obj.date.strftime("%Y/%m/%d") if news_obj.date else None,
                    news_obj.article_url
                ]
            else:
                # If the Experiment does not have a related News object, fill with None or empty strings
                row = [getattr(obj, field) for field in field_names] + [None, None, None, None, None, None]

            writer.writerow(row)

        return response

    export_to_csv.short_description = "Export selected experiments to CSV"
    actions = [export_to_csv]