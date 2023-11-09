import os
import django
import csv
from newsbaitapp.models import Entity

# Set up the Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webapp.settings')  # Replace 'webapp.settings' with your actual settings module
django.setup()

def load_entities_from_csv(filename):
    with open(filename, mode='r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            entity = Entity(
                tag=row['tag'],
                document_indices=row['document_indices'],
                appearances=int(row['appearances']),
                occurrences=int(row['occurrences']),
                synonyms=row['synonyms'],
                n_synonyms=int(row['n_synonyms'])
            )
            entity.save()

load_entities_from_csv('entities.csv')