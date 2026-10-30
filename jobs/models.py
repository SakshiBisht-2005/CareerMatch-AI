from django.db import models

# Create your models here.
class ResumeSubmission(models.Model):
    resume = models.FileField(upload_to="resumes/")
    job_role = models.CharField(max_length=100)
    location = models.CharField(max_length=100)
    experience = models.CharField(max_length=50)
    opportunity_type = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    extracted_text = models.TextField(blank=True)
    ai_profile = models.JSONField(default=dict, blank=True)
    matched_jobs = models.JSONField(default=list, blank=True)
    detected_skills = models.JSONField(default=list, blank=True)
    selected_roles = models.JSONField(default=list, blank=True)
    def __str__(self):
        return f"{self.job_role} - {self.location}"
