from django.core.management.base import BaseCommand
from newsbaitapp.models import Entity
import csv

class Command(BaseCommand):
    help = 'Load a list of entities from a CSV file'

    def add_arguments(self, parser):
        parser.add_argument('filename', type=str, help='The CSV file to load data from')

    def handle(self, *args, **kwargs):
        filename = kwargs['filename']
        with open(filename, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                entity, created = Entity.objects.get_or_create(
                    tag=row['Tag'],
                    section=row['Section'],
                    defaults={
                        'document_indices': row['Document IDs'],
                        'appearances': int(row['Appearances']),
                        'occurrences': int(row['Occurrences']),
                        'synonyms': row['Synonyms'],
                        'n_synonyms': int(row['n_Synonyms'])
                    }
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f'Entity "{entity.tag}" created.'))
                else:
                    self.stdout.write(f'Entity "{entity.tag}" already exists.')
