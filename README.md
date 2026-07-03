# AI Archive Platform

Enterprise AI Document Intelligence Platform - scan, understand, organize, search, and manage documents with AI.

## Architecture

Clean Architecture + Domain-Driven Design (DDD):

```
backend/
├── core/
│   ├── domain/          # Pure business logic (zero framework imports)
│   ├── application/     # Use cases, interfaces (ports)
│   └── infrastructure/  # Django ORM, Celery, external services
├── apps/                # Django apps (thin wrappers)
├── interfaces/          # DRF views, serializers, URLs
└── config/              # Django settings, Celery config

frontend/
├── src/
│   ├── app/             # Next.js App Router pages
│   ├── components/      # React components
│   ├── lib/             # API client, utilities
│   ├── stores/          # Zustand state management
│   └── types/           # TypeScript types
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Django 5.x + DRF |
| Database | PostgreSQL 16 + pgvector |
| Task Queue | Celery + Redis |
| AI/LLM | LangGraph + LangChain (OpenAI, Google, Ollama) |
| OCR | PaddleOCR + Tesseract |
| Frontend | Next.js 15 + React 19 + TypeScript |
| UI | shadcn/ui + Tailwind CSS |
| Charts | Recharts |

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.12+
- Node.js 20+

### 1. Clone and configure

```bash
cp .env.example .env
# Edit .env with your settings
```

### 2. Start with Docker

```bash
cd docker
docker compose up -d
```

### 3. Access

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000/api/v1/
- **Django Admin**: http://localhost:8000/admin/

### Development Setup

#### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements/development.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

#### Frontend

```bash
cd frontend
pnpm install
pnpm dev
```

## API Endpoints

```
/api/v1/
├── auth/login          # JWT login
├── auth/register       # User registration
├── auth/logout         # JWT logout (blacklist)
├── users/              # User management
├── files/              # File operations
│   ├── scan/           # Scan folders
│   ├── upload/         # Upload files
│   └── [id]/download/  # Download files
├── documents/          # Document management
│   ├── process/        # Process documents
│   ├── classify/       # AI classification
│   └── extract/        # Metadata extraction
├── search              # Hybrid search (semantic + keyword)
├── ai/                 # AI operations
│   ├── classify/       # Classify documents
│   ├── extract/        # Extract structured data
│   └── summarize/      # Generate summaries
├── chat/               # RAG chat interface
├── dashboard/          # Dashboard statistics
└── workflows/          # Automation workflows
```

## Modules

### Module 1 - File Scanner
- Recursive folder scanning
- File fingerprinting (SHA-256)
- Duplicate detection
- Change monitoring (Watchdog)
- Storage abstraction (Local, S3, MinIO)

### Module 2 - Document Reader
- PDF (PyMuPDF + pdfplumber)
- DOCX (python-docx)
- XLSX (openpyxl)
- TXT/CSV
- Images (OpenCV)

### Module 3 - OCR
- PaddleOCR (Arabic + English)
- Tesseract fallback
- Confidence scoring
- Image preprocessing

### Module 4 - AI Processing
- Document classification
- Structured data extraction
- Embedding generation (pgvector)
- Multi-provider LLM support

### Module 5 - Search
- Semantic search (pgvector)
- Full-text search (PostgreSQL)
- Hybrid search (RRF merging)
- Natural language queries

### Module 6 - AI Chat (RAG)
- Document-grounded answers
- Source citations
- Chat history

### Module 7 - File Operations
- Rename, move, copy
- Audit logging

### Module 8 - Dashboard
- Processing statistics
- Document type distribution
- Recent activity

## Environment Variables

See `.env.example` for all required variables.

## License

Proprietary
