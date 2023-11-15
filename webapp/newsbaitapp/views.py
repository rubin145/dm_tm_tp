import csv
from datetime import datetime
import ast
from copy import deepcopy
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.contrib.admin.views.decorators import staff_member_required
from .forms import RegistrationForm, UserDataAndFeedbackForm, CSVImportForm
from .models import Experiment, News, Configuration, Entity
from random import choice, shuffle, sample, randint, seed
from .ai_title_generator import ai_title_generator as title_user_optimization

def register(request):
    request.session['current_step'] = ('start',0)
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            request.session['email'] = form.cleaned_data['email']
            return redirect('section_selection')
    else:
        form = RegistrationForm()

    return render(request, 'registration.html', {'form': form})

def section_selection(request):
    sections = News.objects.order_by('section').values_list('section', flat=True).distinct()
    if request.method == "POST":
        selected_section = request.POST.get('selected_section')  
        request.session['selected_section'] = selected_section
        return redirect('tag_selection')
    return render(request, 'section_selection.html', {'sections': sections})

def tag_selection(request):
    selected_section = request.session.get('selected_section', None)
    moderator = Moderator(request.session)
    if selected_section:
        # Fetch tags from Entity model where the 'section' field matches the selected_section
        try:
            config = Configuration.objects.get()
            appearances_threshold = config.min_appearances
            print('appearances_threshold:', appearances_threshold)
        except Exception as e:
            print(e)
            appearances_threshold = 6
        tags = Entity.objects.filter(
            section=selected_section,
            appearances__gte=appearances_threshold
        ).values_list('tag', flat=True).distinct()
    else:
        # If no section has been selected, we could choose to redirect to the section selection,
        # show all tags, or handle the situation in some other way.
        tags = Entity.objects.values_list('tag', flat=True).distinct()
    if request.method == "POST":
        selected_tags = request.POST.getlist('selected_tags')  
        request.session['selected_tags'] = selected_tags
        next_step = moderator.get_next_step()
        request.session['current_step'] = next_step
        print('next_step:',next_step)
        return redirect('title_selection')
    return render(request, 'tag_selection.html', {'tags': tags})

def title_selection(request):
    current_step = request.session['current_step'][0]

    # Determine editor mode based on the step
    editor_mode = 'title_comparison' if current_step == 'title_comparison' else 'multi_article_title_selection'
    
    editor = Editor(request.session['selected_section'], request.session['selected_tags'], editor_mode)
    editor.fetch_articles()
    editor.assign_titles()
    editor.assign_positions()

    options = [(article.title, article.unique_id, article.is_ai, index) for index, article in enumerate(editor.articles, 1)]
    request.session['options'] = options

    if request.method == 'POST':
        request.session['selected_unique_id'] = request.POST.get('title_preference_uid')
        request.session['selected_title'] = request.POST.get('title_preference_text')
        request.session['selected_position'] = request.POST.get('title_preference_position')
        request.session['selected_ai'] = request.POST.get('title_preference_ai')
        print(request.session.items())
        print(register_experiment(request.session))

        return redirect('article_display')

    # Set context based on step
    context = {
        'options': options,
        'form_id': 'titleForm' if current_step == 'title_comparison' else 'multiArticleForm',
        'is_multi_article_mode': False if current_step == 'title_comparison' else True,
        'container_class': 'title-comparison-container' if current_step == 'title_comparison' else 'multi-title-comparison-container',
        'label_class': 'title-option' if current_step == 'title_comparison' else 'multi-title-option',
        'form_action_url': 'title_selection'  # This will be the same for both, as you mentioned
    }

    # Use the same template for both
    return render(request, 'title_selection.html', context)


def article_display(request):
    selected_unique_id = request.session.get('selected_unique_id', None)
    selected_title = request.session.get('selected_title', None)
    print('selected_id',selected_unique_id)
    print('selected_title',selected_title)
    
    moderator = Moderator(request.session)

    if request.method == "POST":
        concordance_score = request.POST.get('concordance_score', None)
        if concordance_score is not None:
            print(update_experiment_score(request.session,concordance_score))

            # Update the current step in the session
            next_step = moderator.get_next_step()
            request.session['current_step'] = next_step
            print('next_step:',next_step)
            # Decide where to redirect after recording the experiment
            # Assuming you have a url named 'next_step' that takes care of deciding the next step
            if next_step[0] in ['title_comparison','multi_article_title_selection']:
                return redirect('title_selection')  # Or whatever your next step url is
            else:
                return redirect(next_step[0])

    if selected_unique_id:
        article = get_object_or_404(News, unique_id=selected_unique_id)
        context = {'article_text': article.text, 'selected_title': selected_title}
    else:
        context = {'error': 'No article has been selected.'}
    return render(request, 'article_display.html', context)



def thank_you_view(request):
    if request.method == 'POST':
        form = UserDataAndFeedbackForm(request.POST)
        
        if form.is_valid():
            # Extract the data from the form
            user_email = form.cleaned_data['user_email']
            gender = form.cleaned_data['gender']
            age = form.cleaned_data['age']
            studies = form.cleaned_data['studies']
            feedback = form.cleaned_data['content']  # Assuming 'content' field for feedback
            
            # Use the separate function to update experiments
            try:
                update_experiments_with_user_data(user_email, gender, age, studies, feedback)
            except Exception as e:
                return JsonResponse({'success': False, 'message': f'Hubo un error en el envío: {e}'})

            # Return a JsonResponse indicating success
            return JsonResponse({'success': True, 'message': 'Enviado, ¡gracias!'})
        else:
            # Return a JsonResponse indicating failure
            return JsonResponse({'success': False, 'message': 'Hubo un error en el envío'})
    else:
        # If not a POST request, create an empty form instance
        user_email = request.session.get('email', '')
        form = UserDataAndFeedbackForm(initial={'user_email': user_email})
    # Render the form with any form data (if any), and potential errors (if any)
    return render(request, 'thank_you.html', {'form': form})

@staff_member_required
def upload_entities(request):
    model_name = 'Entities'
    format_specifications = ''
    if request.method == 'POST':
        form = CSVImportForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            reader = csv.DictReader(csv_file.read().decode('utf-8').splitlines())
            for row in reader:
                try:
                    entity, created = Entity.objects.get_or_create(
                        tag=row['Tag'],
                        section=row['Section'],
                        defaults={
                            'document_indices': row['Document IDs'],
                            'appearances': int(row['Appearances']),
                            'occurrences': int(row['Occurrences']),
                            'synonyms': row['Synonyms'],
                            'n_synonyms': int(row['n_Synonyms']),
                        }
                    )
                    if created:
                        messages.success(request, f'Successfully created entity "{entity.tag}" in section "{entity.section}".')
                    else:
                        messages.info(request, f'Entity "{entity.tag}" in section "{entity.section}" already exists.')
                except Exception as e:
                    # General exception handling; consider specifying the exception types
                    messages.error(request, f"Failed to process row for entity '{row.get('Tag', 'N/A')}': {e}")
            messages.success(request, "CSV file uploaded and processed.")
    else:
        form = CSVImportForm()
    return render(request, 'admin/csv_form.html', {'form': form,
                                                   'model_name': model_name,
                                                   'format_specifications': format_specifications})

@staff_member_required
def upload_news(request):
    model_name = 'News'
    format_specifications = ''
    if request.method == 'POST':
        form = CSVImportForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            reader = csv.DictReader(csv_file.read().decode('utf-8').splitlines())
            date_format = '%d %b, %Y %I:%M %p'
            
            for row in reader:
                try:
                    date_string = row['fecha'].replace('Publicado: ', '').strip()
                    date_string = " ".join(row['fecha'].split()[:-1])
                    date_string = date_string.replace('a.m.', 'AM').replace('p.m.', 'PM')
                    date_string = date_string.replace('.', '')
                    parsed_date = datetime.strptime(date_string, date_format).date()
                except ValueError as e:
                    messages.error(request, f"Invalid date format for news article '{row['titular']}': {e}")
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
                    try:
                        entities_list = ast.literal_eval(row['entities'])
                        for tag in entities_list:
                            tag_cleaned = tag.strip()
                            try:
                                entity = Entity.objects.get(tag__iexact=tag_cleaned, section=row['seccion'].strip())
                                news.entities.add(entity)
                            except Entity.DoesNotExist:
                                messages.warning(request, f"Entity '{tag_cleaned}' does not exist and was not added.")
                            except Entity.MultipleObjectsReturned:
                                messages.warning(request, f"Multiple entities found for tag '{tag_cleaned}'.")
                    except ValueError as e:
                        messages.error(request, f"Error parsing entities list for '{row['titular']}': {e}")
                    
                    messages.success(request, f'Successfully created news article "{news.title}" with ID {news.pk}.')
                else:
                    messages.info(request, f'News article "{news.title}" already exists with ID {news.pk}.')

            messages.success(request, "CSV file uploaded and processed.")
    else:
        form = CSVImportForm()
    return render(request, 'admin/csv_form.html', {'form': form,
                                                   'model_name': model_name,
                                                   'format_specifications': format_specifications})

class Moderator:
    try:
        config = Configuration.objects.get()
        title_comparison_repeats = config.title_comparison_repeats
        multi_article_title_selection_repeats = config.multi_article_title_selection_repeats
    except:
        title_comparison_repeats = 2
        multi_article_title_selection_repeats = 2
    
    def __init__(self, session):
        self.session = session
        self.current_step = self.session.get('current_step', ('start',0))
        
    def get_next_step(self):
        
        step_name, step_count = self.current_step

        if step_name == 'start':
            return ('title_comparison', 1)
            
        if step_name == 'title_comparison':
            if step_count < self.title_comparison_repeats:
                return ('title_comparison', step_count + 1)
            else:
                return ('multi_article_title_selection', 1)

        if step_name == 'multi_article_title_selection':
            if step_count < self.multi_article_title_selection_repeats:
                return ('multi_article_title_selection', step_count + 1)
            else:
                return ('thank_you', 0)
    
    def set_current_step(self, step_name, iteration):
        self.current_step = step_name, iteration
        self.session['current_step'] = self.current_step


class Editor:
    def __init__(self, section, tags, test_type):
        self.section = section
        self.tags = tags
        self.test_type = test_type
        self.articles = []




    def fetch_articles(self):
        """
        Fetches the relevant articles based on section and tags.
        """
        # Fetch all articles that match the section
        tag_list = self.tags[0].split(',') #esto debe ser arreglado antes, la lista de selected_tags se ve así: ['bolsillos cifras,represas,SEC'] (es una lista de un string con tags concatenadas)
        # Filter articles that match at least one tag
        matching_articles = News.objects.filter(
            section=self.section,
            entities__tag__in=tag_list
        ).distinct()

        # Define number of articles based on test type
        if self.test_type == "title_comparison":
            num_articles = 1
        else:
            try:
                num_articles = Configuration.objects.get().num_articles_shown
            except:
                num_articles = 6

        # If there are more matching articles than the required number, select a random subset
        self.articles = sample(list(matching_articles), min(num_articles, len(matching_articles)))
        
        #para duplicar en caso de title_comparison
        if len(self.articles) == 1:
            self.articles.append(deepcopy(self.articles[0]))

    def assign_titles(self):
        """
        Assigns titles to fetched articles.
        """
        # Randomly select an article to be assigned an AI-generated title
        #ai_article = choice(self.articles)
        ai_article_index = randint(0,len(self.articles)-1)
        
        for i in range(len(self.articles)):
            if i == ai_article_index:
                self.articles[i].title = title_user_optimization(self.articles[i].text, self.tags)['title']
                self.articles[i].is_ai = True
            # For other articles, the title remains the same as fetched
            else:
                self.articles[i].is_ai = False

    def assign_positions(self):
        """
        Assigns positions to fetched articles.
        """
        # Shuffle the articles to randomize the order
        shuffle(self.articles)
        # After shuffling, the position of an article can be inferred from its index in the list
        # (i.e., self.articles[0] is in position 1, self.articles[1] is in position 2, etc.)

    def get_articles_with_positions(self):
        """
        Returns articles along with their positions.
        """
        return list(enumerate(self.articles, 1))


def register_experiment(session):
    try:
    # Assuming `unique_id` is a field on your `News` model that you're using to identify articles.
        selected_news = News.objects.get(unique_id=session['selected_unique_id'])
    except News.DoesNotExist:
    # Handle the case where the news item doesn't exist
        return 'Experiment registration failed: News article not found'

    try:
        experiment = Experiment.objects.create(
            user_email = session.get('email'),
            session_id = session.session_key,
            #randomization_seed = ...,
            test_type = session['current_step'][0],
            iteration_number = session['current_step'][1],
            selected_article = selected_news,
            selected_title = session['selected_title'],
            selected_section = session['selected_section'],
            selected_position = session['selected_position'],  # Assuming this is the position/order in the experiment
            selected_is_ai = session['selected_ai'],  # Assuming all titles in comparison are AI-generated, modify as needed
        )
        tag_names = session['selected_tags'][0].split(',') if session['selected_tags'] else []
        
        tags = Entity.objects.filter(tag__in=tag_names)
        if not tags.exists():
            return 'Tag names provided do not match any tags in the database'
# Set the tags using the .set() method
        experiment.selected_tags.set(tags)

        experiment.options_list = session['options']
        experiment.save()

        return 'Experiment registration success'
    except News.DoesNotExist:
        return 'News article not found'
    except Entity.DoesNotExist:
        return 'One or more tags not found'
    except Exception as e:
        return f'Experiment registration failed: {e}'

def update_experiment_score(session,concordance_score):
    last_experiment = Experiment.objects.filter(user_email=session['email']).last()
    if last_experiment:
        last_experiment.concordance_score = concordance_score
        last_experiment.save()
    else:
        # Handle case where experiment is not found
        print("Experiment not found.") 

def update_experiments_with_user_data(user_email, gender, age, studies, feedback):
    # Fetch all experiments with the provided email
    experiments = Experiment.objects.filter(user_email=user_email)
    if len(experiments) == 0:
        if user_email == '':
            raise Exception('No hay un mail cargado')
        else:
            raise Exception('No hay registros con ese mail para actualizar')
    for experiment in experiments:
        # Update fields
        experiment.gender = gender
        experiment.age = age
        experiment.studies = studies
        
        # Concatenate new feedback with existing, separated by a "|"
        if experiment.feedback:
            experiment.feedback += f" | {feedback}"
        else:
            experiment.feedback = feedback
            
        # Save changes
        experiment.save()