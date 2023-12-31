from django import forms
from django.forms import HiddenInput

class RegistrationForm(forms.Form):
    email = forms.EmailField(label="Enter your email")

class UserDataAndFeedbackForm(forms.Form):
    user_email = forms.EmailField(widget=forms.HiddenInput(), required=False)
    
    GENDER_CHOICES = [
        ('', '---------'),  # This empty choice represents no answer
        ('male', 'Masculino'),
        ('female', 'Femenino'),
        ('other', 'Otro'),
        ('prefer_not_to_say', 'Prefiero no decirlo'),
    ]
    STUDIES_CHOICES = [
        # Assuming these are the choices from the Experiment model or similar
        ('', '---------'),  # This empty choice represents no answer
        ('secundario_incompleto', 'Secundario incompleto o menor'),
        ('secundario_completo', 'Secundario completo'),
        ('terciario_incompleto', 'Terciario o Universitario incompleto'),
        ('terciario_completo', 'Terciario o Universitario completo o superior'),
        ('prefer_not_to_say', 'Prefiero no decirlo'),
        # Add any other options here
    ]

    gender = forms.ChoiceField(choices=GENDER_CHOICES, label='Género', required=False, initial='prefer_not_to_say')
    age = forms.IntegerField(label='Edad', min_value=0, max_value=120, required=False, initial=None)
    studies = forms.ChoiceField(choices=STUDIES_CHOICES, label='Nivel de estudios', required=False, initial='prefer_not_to_say')
    content = forms.CharField(
        widget=forms.Textarea(attrs={'placeholder': 'Si querés dejarnos un comentario, este es el lugar...'}),
        label='',
        required=False
    )

    def __init__(self, *args, **kwargs):
        super(UserDataAndFeedbackForm, self).__init__(*args, **kwargs)
        self.fields['content'].required = False

class CSVImportForm(forms.Form):
    csv_file = forms.FileField()