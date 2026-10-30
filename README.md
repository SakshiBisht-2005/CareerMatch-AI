# 🚀 CareerMatch AI

### AI-Powered Career Guidance & Job Matching Platform

CareerMatch AI is an intelligent career guidance and job-matching platform designed to help users discover career opportunities based on their resumes, skills, experience, and preferences.

The application uses Artificial Intelligence to analyze resumes, identify relevant skills, and find suitable job opportunities.

## ✨ Features

- **Resume Upload:** Upload resumes in PDF and DOCX formats.
- **OCR Support:** Extract text from scanned PDF documents.
- **AI Resume Analysis:** Analyze resume content and identify important skills.
- **Skill Extraction:** Automatically detect technical and professional skills.
- **AI Integration:** Use locally running Ollama language models for AI-powered analysis.
- **RAG Integration:** Use ChromaDB for vector storage and retrieval-based functionality.
- **Live Job Search:** Search for real job opportunities using the Google Jobs results provided through SerpApi.
- **Job Matching:** Identify relevant opportunities based on selected job roles and resume skills.
- **Multiple Job Roles:** Select multiple career roles to search for opportunities.
- **Application Links:** Access available job application links.
- **Career Preferences:** Search based on location, experience, and opportunity type.

## 🛠️ Technology Stack

| Technology | Purpose |
|---|---|
| Python | Backend programming |
| Django | Web framework |
| HTML5 | Page structure |
| CSS3 | Website styling |
| JavaScript | Frontend interactions |
| Ollama | Local AI model integration |
| ChromaDB | Vector database |
| PyMuPDF | PDF text extraction |
| Tesseract OCR | Scanned PDF text recognition |
| python-docx | DOCX text extraction |
| SerpApi | Google Jobs search results |
| SQLite | Database |

## 📂 Project Structure

```text
CareerMatch-AI/
│
├── config/
│   ├── settings.py
│   ├── urls.py
│   └── ...
│
├── jobs/
│   ├── migrations/
│   ├── templates/
│   │   └── jobs/
│   ├── static/
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── ai_services.py
│   ├── pdf_processor.py
│   └── utils.py
│
├── media/
├── manage.py
├── requirements.txt
├── .gitignore
└── README.md
```

## ⚙️ Installation and Setup

### 1. Clone the repository

```bash
git clone https://github.com/YOUR-USERNAME/CareerMatch-AI.git
```

### 2. Navigate to the project directory

```bash
cd CareerMatch-AI
```

### 3. Create a virtual environment

```bash
python -m venv .venv
```

### 4. Activate the virtual environment

**Windows CMD:**

```bash
.venv\Scripts\activate
```

### 5. Install dependencies

```bash
pip install -r requirements.txt
```

### 6. Configure environment variables

Create a `.env` file in the project root directory:

```env
SERPAPI_API_KEY=your_serpapi_api_key
```

Never upload your `.env` file or expose your API keys publicly.

### 7. Install and configure Ollama

Download Ollama:

https://ollama.com/

Pull the required models:

```bash
ollama pull llama3.2
ollama pull nomic-embed-text
```

Make sure Ollama is running before using the AI features.

### 8. Install Tesseract OCR

Install Tesseract OCR for scanned PDF text extraction.

https://github.com/UB-Mannheim/tesseract/wiki

Make sure Tesseract is installed and accessible to your application.

### 9. Run database migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 10. Start the Django development server

```bash
python manage.py runserver
```

Open your browser:

```text
http://127.0.0.1:8000/
```

## 🔑 API Configuration

CareerMatch AI uses SerpApi to retrieve Google Jobs search results.

Get an API key:

https://serpapi.com/

Add the key to your local `.env` file.

Do not commit API keys, passwords, or other private credentials to GitHub.

## 🧠 How It Works

1. The user uploads a resume.
2. The application extracts text from the uploaded PDF or DOCX.
3. OCR is used when scanned PDF text needs recognition.
4. Ollama analyzes the resume and identifies relevant skills and profile information.
5. The user selects one or more preferred job roles.
6. The application searches for relevant live job listings.
7. Job opportunities are displayed with matching information and available application links.

## 🔮 Future Improvements

- Interactive AI career assessment.
- Personalized career roadmaps.
- Skill-gap analysis.
- Recommended courses and certifications.
- AI-powered interview preparation.
- Resume improvement suggestions.
- Job application tracking.
- Fantasy adventure-inspired career exploration UI.

## 🔒 Security Notes

- Keep API keys in environment variables.
- Never commit `.env`, database credentials, or private user resumes.
- Validate uploaded files before processing.
- Use Django's security settings before deploying publicly.

## 👨‍💻 Author

Developed as an AI-powered career guidance and job-matching project.

## 📄 License

This project is available under the MIT License. Add a `LICENSE` file if you choose to distribute it under that license.