import csv
from newsbaitapp.models import News, Entity

def load_news_from_csv(filename):
    with open(filename, mode='r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            # Create News instance without entities first
            news = News(
                date=row['fecha'],
                author=row['autor'],
                newspaper_name=row['nombre_diario'],
                section=row['seccion'],
                pompadour=row['copete'],
                title=row['titular'],
                text=row['texto'],
                original_tags=row['temas'],
                article_url=row['url'],
                newspaper_domain=row['home'],
                unique_id = row['unique_id']
            )
            news.save()
            
            # Assuming entities column in CSV contains comma-separated tags
            entity_tags = row['entities'].split(',')
            for tag in entity_tags:
                try:
                    entity = Entity.objects.get(tag=tag.strip())
                    news.entities.add(entity)
                except Entity.DoesNotExist:
                    print(f"Entity {tag} does not exist!")

load_news_from_csv('news.csv')
