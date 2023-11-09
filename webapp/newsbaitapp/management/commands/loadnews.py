import ast
from django.core.management.base import BaseCommand
from newsbaitapp.models import News, Entity
from datetime import datetime
import csv

class Command(BaseCommand):
    help = 'Load a list of news articles from a CSV file'

    def add_arguments(self, parser):
        parser.add_argument('filename', type=str, help='The CSV file to load data from')
        parser.add_argument(
            '--date_format', 
            type=str, 
            help='The date format to use for parsing dates from the CSV file',
            default='%d %b, %Y %I:%M %p'  # Default format for the command
        )

    def handle(self, *args, **kwargs):
        filename = kwargs['filename']
        date_format = kwargs['date_format']

        with open(filename, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                try:
                    # Remove the 'Publicado: ' prefix from the date string
                    date_string = row['fecha'].replace('Publicado: ', '').strip()
                    if date_format == '%d %b, %Y %I:%M %p':
                        date_string = " ".join(row['fecha'].split()[:-1])
                        date_string = date_string.replace('a.m.', 'AM').replace('p.m.', 'PM')
                        date_string = date_string.replace('.', '')
                    parsed_date = datetime.strptime(date_string, date_format).date()
                except ValueError as e:
                    self.stdout.write(self.style.ERROR(f"Invalid date format for news article '{row['titular']}': {e}"))
                    continue

                news, created = News.objects.get_or_create(
                    unique_id=row['unique_id'],
                    defaults={
                        'date': parsed_date,
                        'author': row['autor'],
                        'newspaper_name': row['nombre_diario'],
                        'section': row['seccion'],
                        'pompadour': row['copete'],
                        'title': row['titular'],
                        'text': row['texto'],
                        'original_tags': row['temas'],
                        'article_url': row['url'],
                        'newspaper_domain': row['home'],
                    }
                )

                if created:
                    # Parse the entities list from the string using ast.literal_eval
                    try:
                        entities_list = ast.literal_eval(row['entities'])
                        for tag in entities_list:
                            tag_cleaned = tag.strip()
                            try:
                                entity = Entity.objects.get(tag__iexact=tag_cleaned, section=row['seccion'].strip())
                                news.entities.add(entity)
                            except Entity.DoesNotExist:
                                self.stdout.write(self.style.WARNING(f"Entity '{tag_cleaned}' does not exist and was not added."))
                            except Entity.MultipleObjectsReturned:
                                self.stdout.write(self.style.WARNING(f"Multiple entities found for tag '{tag_cleaned}'."))
                    except ValueError as e:
                        self.stdout.write(self.style.ERROR(f"Error parsing entities list for '{row['titular']}': {e}"))
                    
                    self.stdout.write(self.style.SUCCESS(f'Successfully created news article "{news.title}" with ID {news.pk}.'))
                else:
                    self.stdout.write(self.style.NOTICE(f'News article "{news.title}" already exists with ID {news.pk}.'))

