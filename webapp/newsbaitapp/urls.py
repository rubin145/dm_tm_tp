from django.urls import path
from . import views

urlpatterns = [
    path('inicio/', views.register, name='register'),
    path('seccion/', views.section_selection, name='section_selection'),
    path('etiquetas/', views.tag_selection, name='tag_selection'),
    path('titulos/', views.title_selection, name='title_selection'),
    path('articulo/', views.article_display, name='article_display'),
    path('gracias/', views.thank_you_view, name='thank_you'),
    path('admin/upload_entities/', views.upload_entities, name='upload_entities'),
    path('admin/upload_news/', views.upload_news, name='upload_news'),
]
