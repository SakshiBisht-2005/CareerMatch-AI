import re 
import hashlib
import json
from pathlib import Path
import os
import requests
import chromadb
import requests
from docx import Document


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

OLLAMA_URL = "http://127.0.0.1:11434"
LLM_MODEL = "llama3.2"
EMBED_MODEL = "nomic-embed-text"

CHROMA_PATH = BASE_DIR / "chroma_db"
KNOWLEDGE_DIR = (
    BASE_DIR / "jobs" / "knowledge_base" / "job_descriptions"
)

CHUNK_SIZE = 1400
CHUNK_OVERLAP = 200
TOP_RESULTS = 5


# --------------------------------------------------
# CHROMADB
# --------------------------------------------------

def get_collection():
    """Create or retrieve the persistent ChromaDB collection."""

    client = chromadb.PersistentClient(path=str(CHROMA_PATH))

    collection = client.get_or_create_collection(
        name="job_descriptions",
        metadata={"description": "CareerMatch AI job descriptions"},
    )

    return collection


# --------------------------------------------------
# OLLAMA CONNECTION
# --------------------------------------------------

def ollama_post(endpoint, payload):
    """Send a request to the local Ollama server."""

    url = f"{OLLAMA_URL}{endpoint}"

    try:
        response = requests.post(
            url,
            json=payload,
            timeout=180,
        )
        response.raise_for_status()
        return response.json()

    except requests.exceptions.ConnectionError as exc:
        raise RuntimeError(
            "Cannot connect to Ollama. Make sure Ollama is running."
        ) from exc

    except requests.exceptions.Timeout as exc:
        raise RuntimeError(
            "Ollama took too long to respond. Please try again."
        ) from exc

    except requests.exceptions.HTTPError as exc:
        raise RuntimeError(
            f"Ollama returned an error: {exc}"
        ) from exc

def extract_application_url(text):
    match = re.search(
        r"Application URL:\s*(https?://\S+)",
        text,
        re.IGNORECASE,
    )

    if not match:
        return ""

    return match.group(1).rstrip(".,;)")

def embed_texts(texts):
    """Convert text into vectors using the Ollama embedding model."""

    if not texts:
        return []

    result = ollama_post(
        "/api/embed",
        {
            "model": EMBED_MODEL,
            "input": texts,
        },
    )

    embeddings = result.get("embeddings", [])

    if len(embeddings) != len(texts):
        raise RuntimeError(
            "Ollama returned an unexpected number of embeddings."
        )

    return embeddings


def ask_llm(prompt):
    """Ask the local Ollama language model a question."""

    result = ollama_post(
        "/api/chat",
        {
            "model": LLM_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "stream": False,
            "format": "json",
        },
    )

    content = result.get("message", {}).get("content", "")

    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "The AI returned invalid JSON. Please try again."
        ) from exc


# --------------------------------------------------
# RESUME PROFILE EXTRACTION
# --------------------------------------------------

def extract_resume_profile(resume_text):
    """Extract structured candidate information from resume text."""

    if not resume_text or not resume_text.strip():
        raise ValueError("Resume text is empty.")

    prompt = f"""
You are an expert resume analyzer.

Analyze the resume below and return ONLY valid JSON.

Use this exact JSON structure:

{{
    "name": "",
    "email": "",
    "phone": "",
    "location": "",
    "summary": "",
    "skills": [],
    "education": [],
    "experience": [],
    "projects": [],
    "certifications": [],
    "job_titles": [],
    "years_experience": 0
}}

Rules:
- Do not invent information.
- Use empty strings or empty lists when information is missing.
- Skills must be a list of skill names.
- Education, experience, projects and certifications must be lists.
- years_experience must be a number.
- Return JSON only.

RESUME:
{resume_text[:18000]}
"""

    profile = ask_llm(prompt)

    if not isinstance(profile, dict):
        raise RuntimeError("The AI returned an invalid resume profile.")

    # Ensure expected fields are available.
    defaults = {
        "name": "",
        "email": "",
        "phone": "",
        "location": "",
        "summary": "",
        "skills": [],
        "education": [],
        "experience": [],
        "projects": [],
        "certifications": [],
        "job_titles": [],
        "years_experience": 0,
    }

    for key, default in defaults.items():
        profile.setdefault(key, default)

    return profile


# --------------------------------------------------
# READ JOB DESCRIPTION FILES
# --------------------------------------------------

def read_job_description(file_path):
    """Read a supported job-description file."""

    extension = file_path.suffix.lower()

    if extension in [".txt", ".md"]:
        return file_path.read_text(encoding="utf-8")

    if extension == ".docx":
        document = Document(file_path)

        parts = [
            paragraph.text
            for paragraph in document.paragraphs
            if paragraph.text.strip()
        ]

        for table in document.tables:
            for row in table.rows:
                parts.append(
                    " | ".join(cell.text for cell in row.cells)
                )

        return "\n".join(parts)

    if extension == ".pdf":
        import pymupdf

        parts = []

        with pymupdf.open(file_path) as pdf:
            for page in pdf:
                page_text = page.get_text("text").strip()

                if page_text:
                    parts.append(page_text)

        return "\n".join(parts)

    return ""


# --------------------------------------------------
# TEXT CHUNKING
# --------------------------------------------------

def split_text(text):
    """Split long job descriptions into overlapping chunks."""

    text = text.strip()

    if not text:
        return []

    chunks = []
    start = 0

    while start < len(text):
        end = start + CHUNK_SIZE
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = end - CHUNK_OVERLAP

    return chunks


# --------------------------------------------------
# INDEX JOB DESCRIPTIONS IN CHROMADB
# --------------------------------------------------

def index_job_descriptions():
    """
    Read job descriptions and save their embeddings in ChromaDB.

    Put .txt, .md, .docx or .pdf files inside:
    jobs/knowledge_base/job_descriptions/
    """

    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)

    supported_extensions = {
        ".txt", ".md", ".docx", ".pdf"
    }

    collection = get_collection()

    total_chunks = 0

    files = [
        path
        for path in KNOWLEDGE_DIR.rglob("*")
        if path.is_file()
        and path.suffix.lower() in supported_extensions
    ]

    for file_path in files:
        content = read_job_description(file_path)

        if not content.strip():
            continue

        chunks = split_text(content)

        if not chunks:
            continue

        embeddings = embed_texts(chunks)

        ids = []
        metadatas = []

        for index, chunk in enumerate(chunks):
            unique_text = (
                f"{file_path.resolve()}|{index}|{chunk}"
            )

            chunk_id = hashlib.sha256(
                unique_text.encode("utf-8")
            ).hexdigest()

            ids.append(chunk_id)

            application_url = extract_application_url(content)

            metadatas.append({
                "source": file_path.name,
                "chunk": index,
                "application_url": application_url or "Not provided",
            })

        collection.upsert(
            ids=ids,
            documents=chunks,
            embeddings=embeddings,
            metadatas=metadatas,
        )

        total_chunks += len(chunks)

    return total_chunks


# --------------------------------------------------
# RETRIEVE RELEVANT JOB DESCRIPTIONS
# --------------------------------------------------

def retrieve_job_descriptions(query, limit=TOP_RESULTS):
    """Find job descriptions related to a candidate's profile."""

    collection = get_collection()

    if collection.count() == 0:
        return []

    query_embedding = embed_texts([query])[0]

    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(limit, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]

    retrieved = []

    for document, metadata in zip(documents, metadatas):
        retrieved.append({
            "text": document,
            "source": metadata.get("source", "Unknown"),
            "application_url": metadata.get(
            "application_url", "Not provided"
            ),
        })

    return retrieved


# --------------------------------------------------
# MATCH RESUME WITH JOBS
# --------------------------------------------------

def match_resume_to_jobs(
    profile,
    job_role,
    location,
    experience,
    opportunity_type,
):
    """Compare a resume with relevant job descriptions."""

    skills = profile.get("skills", [])
    job_titles = profile.get("job_titles", [])
    summary = profile.get("summary", "")

    search_query = f"""
    Target job role: {job_role}
    Preferred location: {location}
    Experience level: {experience}
    Opportunity type: {opportunity_type}
    Candidate skills: {", ".join(map(str, skills))}
    Previous job titles: {", ".join(map(str, job_titles))}
    Candidate summary: {summary}
    """

    # Index the knowledge-base files before searching.
    index_job_descriptions()

    job_descriptions = retrieve_job_descriptions(search_query)

    if not job_descriptions:
        return {
            "matches": [],
            "message": (
                "No job descriptions found. Add job-description "
                "files to the knowledge-base folder."
            ),
        }

    context = ""

    for index, job in enumerate(job_descriptions, start=1):
        context += (
            f"\nJOB {index}\n"
            f"Source: {job['source']}\n"
            f"Application URL: {job['application_url']}\n"
            f"Description:\n{job['text']}\n"
        )

    prompt = f"""
You are CareerMatch AI, an expert recruitment assistant.

Compare the candidate's resume profile with the supplied job
descriptions.

Return ONLY valid JSON using this structure:

{{
    "matches": [
        {{
            "job_title": "",
            "source": "",
            "match_score": 0,
            "matching_skills": [],
            "missing_skills": [],
            "reason": ""
        }}
    ]
}}

Rules:
- match_score must be between 0 and 100.
- Do not invent job descriptions or requirements.
- Use only the supplied job descriptions.
- Explain why each job matches the candidate.
- List relevant missing skills.
- Return the best matches first.
- If there are no suitable matches, return an empty matches list.
- Treat scores as estimates, not hiring guarantees.

CANDIDATE PROFILE:
{json.dumps(profile, ensure_ascii=False)}

USER PREFERENCES:
Job role: {job_role}
Location: {location}
Experience: {experience}
Opportunity type: {opportunity_type}

RELEVANT JOB DESCRIPTIONS:
{context}
"""

    result = ask_llm(prompt)

    if not isinstance(result, dict):
        raise RuntimeError("The AI returned an invalid matching result.")

    matches = result.get("matches", [])

    if not isinstance(matches, list):
        matches = []

    source_urls = {
    job["source"]: job["application_url"]
    for job in job_descriptions
}

    for match in matches:
        match_source = match.get("source", "")
        url = source_urls.get(match_source, "")

        if url.startswith(("https://", "http://")):
            match["application_url"] = url
        else:
            match["application_url"] = ""

    return {
        "matches": matches
    }




def search_live_jobs(
    profile,
    job_role,
    location,
    experience,
    opportunity_type
):
    api_key = os.getenv("SERPAPI_API_KEY")

    if not api_key:
        raise RuntimeError("SerpApi API key is missing.")

    skills = profile.get("skills", [])

    if not isinstance(skills, list):
        skills = []

    skills_text = " ".join(str(skill) for skill in skills[:3])

    # Try progressively broader searches.
    queries = [
        f"{job_role} jobs",
        f"{job_role} {skills_text} jobs",
        f"{job_role} hiring",
    ]

    # Use the location supplied by the user.
    search_location = location.strip()

    def fetch_jobs(query, use_location=True):
        params = {
            "engine": "google_jobs",
            "q": query,
            "hl": "en",
            "gl": "in",
            "api_key": api_key,
        }

        if use_location and search_location:
            params["location"] = search_location

        response = requests.get(
            "https://serpapi.com/search.json",
            params=params,
            timeout=40
        )

        try:
            data = response.json()
        except ValueError:
            raise RuntimeError(
                f"SerpApi returned an invalid response: "
                f"HTTP {response.status_code}"
            )

        if response.status_code != 200:
            raise RuntimeError(
                data.get("error", f"SerpApi HTTP {response.status_code}")
            )

        if data.get("error"):
            error = data["error"]

            # Google sometimes returns this message when a query
            # has no results. Let the next broader query run.
            if "hasn't returned any results" in error.lower():
                return []

            raise RuntimeError(f"SerpApi error: {error}")

        return data.get("jobs_results", [])

    raw_jobs = []

    # First try the preferred location.
    for query in queries:
        raw_jobs = fetch_jobs(query, use_location=True)

        if raw_jobs:
            break

    # If no jobs are found, retry without the location.
    if not raw_jobs and search_location:
        for query in queries:
            raw_jobs = fetch_jobs(query, use_location=False)

            if raw_jobs:
                break

    results = []
    seen = set()

    for job in raw_jobs:
        title = job.get("title", "Job title unavailable")
        company = job.get("company_name", "Company not listed")
        job_location = job.get("location", "Location not listed")

        apply_options = job.get("apply_options", [])

        application_url = None
        application_label = "View Job"

        if apply_options:
            application_url = apply_options[0].get("link")
            application_label = apply_options[0].get(
                "title", "Apply Now"
            )

        if not application_url:
            application_url = job.get("share_link")

        # Avoid duplicate listings.
        unique_key = (
            title.lower(),
            company.lower(),
            job_location.lower()
        )

        if unique_key in seen:
            continue

        seen.add(unique_key)

        description = job.get("description", "")
        detected = job.get("detected_extensions", {})

        matching_skills = [
            str(skill)
            for skill in skills
            if str(skill).lower() in description.lower()
        ]

        score = (
            round(len(matching_skills) / len(skills) * 100)
            if skills else 0
        )

        results.append({
            "job_title": title,
            "company": company,
            "location": job_location,
            "via": job.get("via", ""),
            "salary": detected.get("salary", ""),
            "schedule_type": detected.get("schedule_type", ""),
            "posted_at": detected.get("posted_at", ""),
            "description": description,
            "matching_skills": matching_skills,
            "match_score": score,
            "application_url": application_url,
            "application_label": application_label,
        })

    results.sort(
        key=lambda item: item["match_score"],
        reverse=True
    )

    return results
