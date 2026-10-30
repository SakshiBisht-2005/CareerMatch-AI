
from pathlib import Path

from django.shortcuts import render, get_object_or_404, redirect

from .models import ResumeSubmission
from .utils import extract_resume_text
from .ai_services import extract_resume_profile, search_live_jobs
import logging

logger = logging.getLogger(__name__)

JOB_ROLE_OPTIONS = [
    "Python Developer",
    "Django Developer",
    "Full Stack Developer",
    "Backend Developer",
    "Frontend Developer",
    "Software Engineer",
    "Data Analyst",
    "Data Scientist",
    "Machine Learning Engineer",
    "AI Engineer",
    "DevOps Engineer",
    "Cloud Engineer",
    "Java Developer",
    "Web Developer",
    "Cybersecurity Analyst",
]


def get_role_options(profile):
    """Combine standard roles with roles found in the resume."""
    roles = list(JOB_ROLE_OPTIONS)

    extracted_titles = profile.get("job_titles", [])

    if isinstance(extracted_titles, list):
        for title in extracted_titles:
            if isinstance(title, str) and title.strip():
                if title not in roles:
                    roles.insert(0, title.strip())

    return roles


def home(request):
    return render(request, "jobs/home.html")


def upload_resume(request):
    if request.method != "POST":
        return render(request, "jobs/upload.html")

    resume = request.FILES.get("resume")
    job_role = request.POST.get("job_role", "").strip()
    location = request.POST.get("location", "").strip()
    experience = request.POST.get("experience", "").strip()
    opportunity_type = request.POST.get(
        "opportunity_type", ""
    ).strip()

    if not all([
        resume, job_role, location,
        experience, opportunity_type
    ]):
        return render(request, "jobs/upload.html", {
            "error": "Please complete all fields and upload your resume."
        })

    extension = Path(resume.name).suffix.lower()

    if extension not in [".pdf", ".docx"]:
        return render(request, "jobs/upload.html", {
            "error": "Please upload a PDF or DOCX resume."
        })

    if resume.size > 5 * 1024 * 1024:
        return render(request, "jobs/upload.html", {
            "error": "Your resume must be smaller than 5 MB."
        })

    submission = ResumeSubmission.objects.create(
        resume=resume,
        job_role=job_role,
        location=location,
        experience=experience,
        opportunity_type=opportunity_type,
    )

    try:
        # Extract resume text internally. Do not display it.
        text = extract_resume_text(submission.resume.path)

        if not text.strip():
            raise ValueError("No readable text was found.")

        # Ask Ollama to extract the candidate profile and skills.
        profile = extract_resume_profile(text)

        submission.extracted_text = text
        submission.ai_profile = profile
        submission.detected_skills = profile.get("skills", [])
        submission.matched_jobs = []
        submission.selected_roles = []

        submission.save()

    except Exception as exc:
        print("Resume analysis error:", exc)
        submission.delete()

        return render(request, "jobs/upload.html", {
            "error": (
                "Resume analysis failed. Please check that Ollama "
                "is running and try again."
            )
        })

    return render(request, "jobs/results.html", {
        "submission": submission,
        "profile": submission.ai_profile,
        "skills": submission.detected_skills,
        "roles": get_role_options(submission.ai_profile),
        "selected_roles": [],
        "matches": [],
    })


def search_jobs(request):
    if request.method != "POST":
        return redirect("jobs:home")

    submission_id = request.POST.get("submission_id")

    submission = get_object_or_404(
        ResumeSubmission,
        id=submission_id
    )

    selected_roles = request.POST.getlist("job_roles")

    # Prevent empty searches and excessive API usage.
    selected_roles = list(dict.fromkeys(selected_roles))[:5]

    roles = get_role_options(submission.ai_profile)

    if not selected_roles:
        return render(request, "jobs/results.html", {
            "submission": submission,
            "profile": submission.ai_profile,
            "skills": submission.detected_skills,
            "roles": roles,
            "selected_roles": [],
            "matches": submission.matched_jobs,
            "error": "Please select at least one job role.",
        })

    # Only allow roles offered on this page.
    allowed_roles = set(roles)
    selected_roles = [
        role for role in selected_roles
        if role in allowed_roles
    ]

    if not selected_roles:
        return render(request, "jobs/results.html", {
            "submission": submission,
            "profile": submission.ai_profile,
            "skills": submission.detected_skills,
            "roles": roles,
            "selected_roles": [],
            "matches": submission.matched_jobs,
            "error": "Please select a valid job role.",
        })

    all_jobs = []
    seen_jobs = set()

    try:
        # Search live jobs separately for every selected role.
        for role in selected_roles:
            jobs = search_live_jobs(
                profile=submission.ai_profile,
                job_role=role,
                location=submission.location,
                experience=submission.experience,
                opportunity_type=submission.opportunity_type,
            )

            for job in jobs:
                unique_key = (
                    job.get("application_url")
                    or (
                        job.get("job_title", "").lower(),
                        job.get("company", "").lower(),
                    )
                )

                if unique_key not in seen_jobs:
                    seen_jobs.add(unique_key)
                    job["searched_role"] = role
                    all_jobs.append(job)

        all_jobs.sort(
            key=lambda item: item.get("match_score", 0),
            reverse=True
        )

        submission.selected_roles = selected_roles
        submission.matched_jobs = all_jobs
        submission.job_role = ", ".join(selected_roles)[:100]
        submission.save()

    except Exception as exc:
        logger.exception("Live job search failed")

        return render(request, "jobs/results.html", {
            "submission": submission,
            "profile": submission.ai_profile,
            "skills": submission.detected_skills,
            "roles": roles,
            "selected_roles": selected_roles,
            "matches": submission.matched_jobs,
            "error": str(exc),
        })

    return render(request, "jobs/results.html", {
        "submission": submission,
        "profile": submission.ai_profile,
        "skills": submission.detected_skills,
        "roles": roles,
        "selected_roles": selected_roles,
        "matches": all_jobs,
    })
