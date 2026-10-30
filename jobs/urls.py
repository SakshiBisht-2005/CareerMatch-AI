from django.urls import path
from . import views

app_name = "jobs"

urlpatterns = [
    path("", views.home, name="home"),
    path("upload/", views.upload_resume, name="upload"),
    path("search-jobs/", views.search_jobs, name="search_jobs"),
]