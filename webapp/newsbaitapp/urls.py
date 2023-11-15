from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('section-selection/', views.section_selection, name='section_selection'),
    path('tag-selection/', views.tag_selection, name='tag_selection'),
    path('title-selection/', views.title_selection, name='title_selection'),
    path('article-display/', views.article_display, name='article_display'),
    path('thank-you/', views.thank_you_view, name='thank_you'),
    path('admin/upload_entities/', views.upload_entities, name='upload_entities'),
    path('admin/upload_news/', views.upload_news, name='upload_news'),
]
