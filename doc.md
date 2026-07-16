# AI Archive Platform (Basirah) — Complete System Documentation

## Table of Contents

### For Non-Technical Readers
0. [Non-Technical Guide — How Basirah Works (Plain English)](#non-technical-guide--how-basirah-works-plain-english)

### For Technical Readers
1. [System Overview](#1-system-overview)
2. [Architecture](#2-architecture)
3. [Tech Stack](#3-tech-stack)
4. [Monorepo Structure](#4-monorepo-structure)
5. [Backend (Django)](#5-backend-django)
6. [Frontend (Next.js)](#6-frontend-nextjs)
7. [Desktop App (Tauri)](#7-desktop-app-tauri)
8. [Edge Agent (Python)](#8-edge-agent-python)
9. [Shared Packages](#9-shared-packages)
10. [Database Schema](#10-database-schema)
11. [Authentication & Authorization](#11-authentication--authorization)
12. [AI/ML Pipeline](#12-aiml-pipeline)
13. [Search System](#13-search-system)
14. [WebSocket & Real-time](#14-websocket--real-time)
15. [API Reference](#15-api-reference)
16. [Configuration](#16-configuration)
17. [Docker & Deployment](#17-docker--deployment)
18. [Testing](#18-testing)
19. [CI/CD](#19-cicd)
20. [Data Flow](#20-data-flow)

---

# Non-Technical Guide — How Basirah Works (Plain English)

> **This section is for everyone** — business managers, team leads, end users, or anyone who wants to understand what this system does without needing to read code.

---

## What Problem Does Basirah Solve?

Imagine you work at a company with **thousands of documents** — invoices, contracts, employee records, reports, letters, receipts, emails, and more. They are scattered across shared drives, local folders, email attachments, and filing cabinets.

**The problem**: Finding a specific piece of information means manually opening files one by one. Need to find "all contracts mentioning pricing from last quarter"? That could take hours or days of manual work.

**Basirah solves this** by using Artificial Intelligence to automatically:
1. **Read** your documents (even scanned images and photos)
2. **Understand** what type of document it is
3. **Extract** important information (who, what, when, how much)
4. **Summarize** the content in plain language
5. **Make everything searchable** — like Google, but for your private documents
6. **Let you ask questions** in natural language and get answers grounded in your actual documents

---

## The Big Picture — Four Parts Working Together

Basirah is made up of **four main parts** that work together like a team:

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│   PART 1: Edge Agent (The Scanner)                     │
│   Runs on YOUR computer                                │
│   Scans your folders, reads your files                 │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│   PART 2: Desktop App (The Control Panel)              │
│   A native app on YOUR computer                        │
│   Lets you manage which folders to scan                │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│   PART 3: Web Application (The Main Interface)         │
│   Opens in your browser                                │
│   Where you search, chat, view documents               │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│   PART 4: Server (The Brain)                           │
│   Runs in the cloud or on your company server          │
│   Does the heavy AI processing                         │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

Let me explain each part in detail.

---

## PART 1: The Edge Agent — Your Personal Document Scanner

### What is it?
The Edge Agent is a small program that runs quietly on your computer in the background. Think of it as a **personal assistant that reads all your documents** so you don't have to.

### What does it do?

**Scanning your folders:**
- You tell it which folders on your computer to watch (e.g., "Documents," "Projects," "Invoices")
- It scans through every file in those folders — PDFs, Word documents, Excel spreadsheets, images, everything
- It remembers what it has already scanned, so it only processes new or changed files
- It works like a security camera — always watching for new documents

**Reading your files:**
- For **PDF files**: It extracts the text directly if the PDF has text, or uses OCR (Optical Character Recognition) to read text from images
- For **Word documents**: It reads the text content
- For **Excel spreadsheets**: It reads the data in cells
- For **scanned documents and photos**: It uses AI-powered OCR to read text from images — even handwriting in some cases
- For **images with text** (screenshots, photos of documents): It reads the text using the same OCR technology

**OCR — How does it read images?**
OCR stands for Optical Character Recognition. It's the same technology that:
- Google Lens uses to translate text in photos
- Your phone uses to scan business cards
- Banks use to process checks

Basirah uses two OCR engines:
- **PaddleOCR** — excellent for Arabic and English text
- **Tesseract** — a backup engine if PaddleOCR has trouble

**Preparing text for AI:**
- After reading a file, the agent breaks the text into small chunks (paragraphs of about 1000 characters)
- It cleans up the text — removing weird characters, fixing formatting
- It packages everything neatly to send to the server

### Why does it run on YOUR computer?

This is a key design decision. Here's why:

1. **Privacy**: Your actual document content stays on your machine. Only the extracted text and metadata are sent to the server. The server never sees your original files unless you explicitly upload them.

2. **Speed**: Reading documents (especially OCR on images) is very CPU-intensive. If the server had to do this for thousands of users simultaneously, it would be overwhelmed. By running on your computer, each user's machine handles its own work.

3. **Offline capability**: The agent can scan and parse documents even when disconnected from the server. It stores the results locally and syncs when connection is restored.

4. **No upload needed**: You don't need to upload massive files to the server. The agent extracts just the text (which is much smaller) and sends that.

### How does it talk to the server?

The Edge Agent communicates with the server in two ways:

1. **Heartbeat (every few seconds)**: The agent sends a quick "I'm alive" message to the server. The server responds with any pending commands (like "scan this folder" or "update your settings"). This is like a phone call that happens regularly.

2. **File sync**: When the agent finds new or changed files, it sends the extracted text and metadata to the server. This includes:
   - File name, size, type, when it was last modified
   - The extracted text content
   - Document type (if it can tell)
   - Any entities it found (names, dates, amounts)

---

## PART 2: The Desktop App — Your Control Panel

### What is it?
The Desktop App is a native application that runs on your computer (Windows, Mac, or Linux). It gives you a visual interface to control the Edge Agent.

### What does it look like?
Think of it like a settings app for the Edge Agent. It has:

**Dashboard:**
- Shows if the agent is running (green light) or stopped (red light)
- Displays how many files have been scanned
- Shows how much disk space your documents use
- Displays recent activity (what was scanned, what was synced)

**Folder Management:**
- A list of all folders the agent is watching
- You can add new folders (click "Add Folder" and browse)
- You can remove folders you no longer want to scan
- You can pause scanning temporarily

**Settings:**
- Server connection settings (URL, API key)
- Scanning preferences (file size limits, which file types to include)
- OCR settings (which language, which engine)

**File Operations:**
- View all files the agent has found
- Move files between folders
- Delete files (moved to trash, can be restored)
- See file details (size, type, when scanned)

### How does it work technically?
The Desktop App is built with **Tauri**, which is a technology that:
- Uses **React** (the same technology behind Facebook and Instagram) for the visual interface
- Uses **Rust** (a very fast, safe programming language) for the system-level operations
- The Edge Agent runs as a "sidecar" — a companion process that starts automatically when you open the desktop app

---

## PART 3: The Web Application — Where the Magic Happens

### What is it?
The Web Application is a website that you open in your browser (Chrome, Firefox, Safari). It's the main interface where you interact with all your documents using AI.

### How do you access it?
You go to a URL like `https://basirah.yourcompany.com` in your browser, log in with your email and password, and you're in.

### What can you do with it?

#### 1. Dashboard — Your Document Command Center

When you first log in, you see the **Dashboard** — an overview of everything:

- **Total documents**: How many documents have been processed
- **Documents by type**: A chart showing how many invoices, contracts, reports, etc. you have
- **Recent activity**: What was scanned and processed recently
- **Agent status**: Whether your Edge Agents are online and working
- **Storage usage**: How much space your documents take up
- **Quick actions**: Buttons to search, upload, or start a new chat

#### 2. Search — Find Anything Instantly

This is where Basirah really shines. You can search your documents in three ways:

**Keyword Search** (like Google):
- Type exact words: `"invoice #12345"` or `"John Smith contract"`
- Finds documents containing those exact words
- Fast and precise

**Semantic Search** (smart search):
- Type what you MEAN: `"contracts about pricing"` or `"employee onboarding documents"`
- Basirah understands the MEANING, not just the words
- If you search for "pricing" it will also find documents mentioning "cost," "price list," "rates," "fees"

**Hybrid Search** (best of both):
- Combines both keyword and semantic search
- Uses a mathematical formula called "Reciprocal Rank Fusion" to merge results
- Gives you the most relevant results regardless of how you phrase your question
- This is the default — and it's what makes Basirah smarter than a simple search

**What happens when you search:**
1. You type a question or keywords
2. Basirah converts your words into a mathematical representation (a "vector") that captures the meaning
3. It compares this vector against all your document embeddings (pre-computed meanings)
4. It also searches for exact keyword matches
5. It merges the results and ranks them by relevance
6. You see a list of matching documents with highlights showing where your search terms appear

#### 3. Document Management — Your Digital Filing Cabinet

All your processed documents appear in the **Documents** section:

- **List view**: See all documents with title, type, status, date, who uploaded it
- **Detail view**: Click a document to see:
  - Full extracted text
  - AI-generated summary
  - Named entities (people, organizations, dates, amounts found)
  - Document classification (invoice, contract, etc.)
  - Source file information
- **Processing status**: See if a document is still being processed
- **Filters**: Filter by document type, status, date range, tags
- **Bulk operations**: Select multiple documents to classify, tag, or move

#### 4. AI Chat — Ask Questions, Get Answers

This is the **RAG (Retrieval-Augmented Generation)** feature. It's like having a knowledgeable assistant who has read every single document in your archive.

**How it works:**
1. You type a question in natural language, like: "What were the total expenses mentioned in the Q3 reports?"
2. Basirah searches your documents for relevant information
3. It finds the most relevant chunks of text from your documents
4. It sends those chunks plus your question to an AI model (like GPT-4o)
5. The AI reads the relevant document excerpts and generates a clear answer
6. The answer includes **citations** — it tells you exactly which documents it used

**Example conversation:**
```
You: "What contracts are expiring this year?"

Basirah: "Based on your documents, I found 3 contracts expiring in 2024:

1. **ABC Corp Service Agreement** (Contract #2024-015)
   - Expires: March 15, 2024
   - Value: $45,000/year
   - Source: contracts/abc-corp-2024.pdf

2. **Office Lease Agreement** (Contract #2023-089)
   - Expires: June 30, 2024
   - Value: $120,000/year
   - Source: files/lease-downtown.docx

3. **IT Support Contract** (Contract #2024-002)
   - Expires: December 31, 2024
   - Value: $18,000/year
   - Source: documents/it-support-renewal.pdf"
```

#### 5. AI Workspace — Use AI Tools Directly

Beyond chat, you can use AI tools directly:

- **Classify**: Paste text or select a document, and AI will tell you what type it is
- **Extract**: Paste text and AI will pull out names, dates, amounts, organizations
- **Summarize**: Paste long text and get a concise summary

#### 6. Reports — Analytics and Insights

Generate reports about your document archive:

- **Archive Summary**: Overview of all documents, types, sizes
- **Processing Stats**: How many documents processed, average time, success rate
- **Search Analytics**: What people are searching for, popular queries
- **User Activity**: Who uploaded what, when, most active users
- **Storage Usage**: Disk space by document type, by user, by organization

#### 7. Workflows — Automate Repetitive Tasks

Create automated processing pipelines:

- **On Upload**: When a new file is uploaded, automatically classify it, extract entities, and summarize it
- **Scheduled**: Run processing on a schedule (e.g., every night at 2 AM)
- **Manual**: Trigger processing with one click

Example workflow: "When a new PDF is uploaded → Classify it → Extract entities → Generate summary → Add to search index"

#### 8. Settings — Configure Your System

- **Organization**: Manage your company's settings
- **AI Providers**: Choose which AI to use (OpenAI, Google Gemini, or local Ollama)
- **Team Members**: Invite colleagues, assign roles
- **API Keys**: Create keys for programmatic access

---

## PART 4: The Server — The Brain of the Operation

### What is it?
The Server is the central hub that:
- Receives data from all Edge Agents
- Processes documents with AI
- Stores everything in a database
- Serves the web application
- Handles user authentication
- Manages real-time updates

### What does it do behind the scenes?

#### Document Processing Pipeline

When a document is sent to the server, it goes through a **10-step processing pipeline** — think of it like an assembly line in a factory:

```
Step 1: RECEIVE    → Server receives file data from Edge Agent
Step 2: STORE      → Save file metadata in database
Step 3: CREATE     → Create a document record
Step 4: CLASSIFY   → AI reads the document and decides: Is this an invoice? A contract? A report?
Step 5: EXTRACT    → AI finds and extracts: names, dates, amounts, organizations, locations
Step 6: SUMMARIZE  → AI writes a brief summary of the document
Step 7: CHUNK      → Break the text into small pieces (for search)
Step 8: EMBED      → Convert each piece into a mathematical representation (vector)
Step 9: INDEX      → Store vectors in database (for semantic search)
Step 10: COMPLETE  → Mark document as fully processed and searchable
```

**Why does this take multiple steps?**
Each step does something different, and some steps depend on previous ones. You can't classify a document before you've received it. You can't summarize it before you've classified it (because classification helps the AI understand context).

**How long does it take?**
- Simple documents (1-2 pages): 5-15 seconds
- Medium documents (10-20 pages): 30-60 seconds
- Large documents (100+ pages): 2-5 minutes
- The system processes documents in the background, so you don't have to wait

#### AI Classification — What Type of Document Is This?

The AI looks at the document and assigns it to one of **19 categories**:

| Category | What It Means |
|----------|--------------|
| Invoice | A bill for goods or services |
| Receipt | Proof of payment |
| Contract | A legal agreement |
| Report | A formal report or analysis |
| Letter | A written correspondence |
| Memo | An internal memorandum |
| Email | An email message |
| Form | A fill-in form |
| Certificate | An official certificate |
| License | A license or permit |
| Agreement | A formal agreement |
| Proposal | A business proposal |
| Statement | A financial or account statement |
| Notice | An official notice |
| Minutes | Meeting minutes |
| Policy | A company policy document |
| Manual | An instruction manual |
| Other | Doesn't fit the above categories |
| Unknown | Could not determine the type |

#### Entity Extraction — Finding Important Information

The AI scans the document and extracts specific pieces of information:

| Entity Type | Example |
|-------------|---------|
| Person names | "John Smith," "Dr. Sarah Ahmed" |
| Organization names | "Acme Corp," "Ministry of Health" |
| Dates | "January 15, 2024," "Q3 2023" |
| Amounts/money | "$45,000," "1,200 SAR," "€89.50" |
| Locations | "New York," "Building 5, Floor 3" |
| Email addresses | "john@company.com" |
| Phone numbers | "+1-555-0123" |
| Reference numbers | "INV-2024-0156," "PO#7890" |
| Project names | "Project Phoenix," "Phase 2" |

#### Summarization — What's This Document About?

The AI reads the entire document and writes a concise summary. For example:

**Original document** (5-page contract):
> [5 pages of legal text about service agreement between ABC Corp and XYZ Inc...]

**AI Summary**:
> "This is a service agreement between ABC Corp (provider) and XYZ Inc (client) for IT consulting services. The agreement is effective January 1, 2024 through December 31, 2024. Total contract value is $120,000 ($10,000/month). Key terms include: 40 hours/month of consulting, 24/7 support, and a 30-day termination notice requirement."

#### Hybrid Search — How Does Search Work?

When you search, here's what happens step by step:

1. **You type**: "contracts expiring soon"
2. **Semantic search** (meaning-based):
   - Converts your words into a mathematical "meaning vector"
   - Compares this vector against all document embeddings
   - Finds documents with similar MEANING (even if they don't use the exact words)
   - Results might include: "agreement renewal dates," "contract termination," "service level agreement expiry"
3. **Keyword search** (exact match):
   - Looks for the exact words "contracts" and "expiring" and "soon"
   - Finds documents containing these specific words
4. **Merging** (Reciprocal Rank Fusion):
   - Combines results from both searches
   - Uses a formula to rank them: documents that appear high in BOTH searches get the best ranking
   - Default weighting: 70% meaning, 30% exact words
5. **Results**: You see a ranked list of the most relevant documents

#### Multi-Provider AI — Choose Your AI Brain

Basirah doesn't lock you into one AI provider. You can choose:

| Provider | What It Is | Pros | Cons |
|----------|-----------|------|------|
| **OpenAI** (GPT-4o) | Cloud AI from OpenAI | Best quality, most capable | Costs money per use, requires internet |
| **Google Gemini** | Cloud AI from Google | Good quality, competitive pricing | Requires internet |
| **Ollama** (Local) | AI running on YOUR computer | Free, private, works offline | Requires powerful hardware, less capable |

You can even switch between them per task. For example, use Ollama for simple classification (free) and OpenAI for complex summarization (better quality).

#### Real-Time Updates — Live Dashboard

When something happens, you see it immediately:

- **Agent comes online**: Dashboard shows green light
- **Files are synced**: Counter goes up in real-time
- **Document processing starts**: Progress bar appears
- **Document processing completes**: Document appears in the list
- **New search index available**: Search results become more comprehensive

This works through **WebSockets** — a technology that keeps a constant connection between your browser and the server, so updates are pushed instantly (like a live chat or stock ticker).

---

## How Does Authentication Work? — Keeping Your Data Safe

### Logging In

When you log in:
1. You enter your email and password
2. The server verifies your credentials
3. If correct, it gives you a **digital ID card** (called a JWT token)
4. Your browser stores this token
5. Every time you make a request, your browser shows this token to prove you're logged in
6. The token expires after 30 minutes for security — then you need to refresh it

### API Keys — For Machines

Edge Agents and external tools don't log in with email/password. Instead, they use **API Keys**:
- A long random string like `ak_12345678abcdef...`
- The agent includes this key in every request
- The server checks: "Is this a valid key? Who does it belong to?"
- API keys are stored as hashes (scrambled) so even if someone steals the database, they can't use the keys

### Organization Permissions — Who Can See What

Basirah supports **multi-tenancy** — meaning multiple organizations can use the same server, but each organization's data is completely isolated.

**User Roles**:
| Role | What They Can Do |
|------|-----------------|
| Admin | Everything: manage users, settings, all documents |
| Archivist | Manage documents, upload files, run processing |
| Researcher | Search, chat with AI, view documents |
| Viewer | Read-only access to documents |

**Organization Roles**:
| Role | What They Can Do |
|------|-----------------|
| Owner | Full control over the organization |
| Admin | Manage settings and members |
| Member | Standard access to organization data |

**Data Scope**:
- **Personal scope**: Only you can see your documents
- **Organization scope**: Everyone in your organization can see shared documents
- You can switch between these scopes with a toggle

---

## How Does the System Handle Multiple Languages?

Basirah supports **English and Arabic** with full **RTL (Right-to-Left)** support:

- The web interface switches between English and Arabic
- Arabic text in documents is properly displayed and searchable
- OCR reads both English and Arabic text from images
- The AI can classify and summarize documents in both languages
- The interface flips layout for Arabic (text flows right-to-left)

---

## How Does File Deduplication Work?

When the Edge Agent scans files, it calculates a **fingerprint** (SHA-256 hash) for each file. This is like a DNA test for files:

- If two files have the same fingerprint, they are identical (even if named differently)
- The system groups duplicates together
- You see: "This file has 3 copies on different machines"
- You can choose which copy to keep

---

## How Does the System Handle Errors?

The system is designed to be resilient:

**If an Edge Agent loses connection**:
- It continues scanning and parsing locally
- It stores results in a local queue
- When connection is restored, it syncs everything automatically

**If document processing fails**:
- The system retries up to 3 times with increasing delays
- If it still fails, the document is marked as "failed" with an error message
- The document is still searchable by keyword (even without AI processing)
- An admin can manually trigger re-processing

**If an AI provider is unavailable**:
- The system can fall back to another provider
- For example, if OpenAI is down, switch to Ollama (local)
- You can configure fallback chains

---

## How Does the System Scale?

**Adding more users**: Just invite them. Each user gets their own account and can join organizations.

**Adding more documents**: The system handles millions of documents. Processing happens in parallel across multiple worker processes.

**Adding more machines**: Install Edge Agents on additional computers. Each agent independently scans its assigned folders.

**Adding more AI power**: Configure multiple AI providers and distribute the load.

---

## Real-World Use Cases

### Use Case 1: Legal Firm
- Scan all case files, contracts, and correspondence
- Search for specific clauses across thousands of contracts
- Ask: "Find all contracts with non-compete clauses signed in 2023"
- Get instant answers with document citations

### Use Case 2: Hospital
- Scan patient records, lab results, and insurance documents
- Search for specific diagnoses or treatments
- Ask: "How many patients were diagnosed with diabetes in Q3?"
- Comply with data privacy (documents stay on local machines until metadata is synced)

### Use Case 3: Government Agency
- Scan official documents, permits, and correspondence
- Classify and organize thousands of documents automatically
- Search across departments for related information
- Generate reports on document processing statistics

### Use Case 4: Accounting Firm
- Scan invoices, receipts, and financial statements
- Extract amounts, dates, and vendor names automatically
- Ask: "What were the total expenses from Vendor X in 2023?"
- Automate document classification and filing

---

## Summary — What Basirah Does in One Paragraph

Basirah is an intelligent document management system that scans documents on your computer, reads them using AI (even if they're images or scanned PDFs), understands what they are, extracts important information, summarizes them, and makes everything instantly searchable. You can then search for anything using regular keywords or smart meaning-based search, or simply ask questions in plain language and get answers with citations from your actual documents. The system runs with multiple AI providers (OpenAI, Google, or local), supports English and Arabic, handles millions of documents, and keeps your data secure with organization-based access control.

---

## Technical Documentation

> **Below this point, the documentation is written for developers and technical users.**

---

## 1. System Overview

### What Is It?

**AI Archive Platform** (product name: **Basirah**) is an enterprise-grade document intelligence platform that scans, reads, classifies, organizes, searches, and manages documents using AI. It is an intelligent document management system that uses artificial intelligence to understand what is inside your files.

### Why Does It Exist?

Organizations have thousands of documents (invoices, contracts, reports, letters) scattered across drives and folders. Finding specific information requires manually opening files. This platform automates the entire lifecycle:

1. **Scans** local folders on user machines
2. **Parses** documents (OCR for images/PDFs, text extraction)
3. **Classifies** them by type (invoice, contract, etc.)
4. **Extracts** key entities (people, dates, amounts, organizations)
5. **Summarizes** content
6. **Indexes** everything for instant search
7. **Enables RAG chat** — ask questions and get answers grounded in your documents

### How It Works (High-Level)

```
User's Machine                    Cloud/Server
┌─────────────────┐              ┌──────────────────────────┐
│  Edge Agent     │   sync via   │  Django Backend          │
│  - Scans folders│──────────────│  - Receives metadata     │
│  - Parses docs  │              │  - AI Classification     │
│  - OCR          │              │  - Entity Extraction     │
│  - Extracts text│              │  - Summarization         │
│  - Chunks text  │              │  - Embedding + Indexing  │
└─────────────────┘              │  - Hybrid Search         │
        │                        │  - RAG Chat              │
┌─────────────────┐              │  - User Management       │
│  Desktop App    │              └──────────────────────────┘
│  (Tauri UI)     │                        │
│  - Folder mgmt  │              ┌──────────────────────────┐
│  - Agent status │              │  Web Frontend (Next.js)  │
│  - Settings     │              │  - Document management   │
└─────────────────┘              │  - Search interface      │
                                 │  - AI workspace          │
                                 │  - RAG chat              │
                                 │  - Dashboard & reports   │
                                 └──────────────────────────┘
```

### Key Design Decisions

| Decision | Reason |
|----------|--------|
| **Edge computing** | OCR and document parsing are CPU-intensive; running on user machines avoids server overload and keeps data local until metadata is extracted |
| **Clean Architecture** | Domain logic is pure Python with zero framework imports, making it testable and portable |
| **Multi-provider AI** | Supports OpenAI, Google Gemini, and Ollama (local) so organizations are not locked into one vendor |
| **Hybrid search** | Combines semantic (meaning-based) and keyword (exact match) search because neither alone is sufficient |
| **Organization multi-tenancy** | Data is isolated per organization; users can switch between personal and org scope |

---

## 2. Architecture

### Overall System Architecture

The system is a **distributed client-server architecture with edge computing**:

```
┌─────────────────────────────────────────────────────────┐
│                    CLIENT LAYER                          │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Web App     │  │ Desktop App  │  │ Edge Agent   │  │
│  │  (Next.js)   │  │  (Tauri)     │  │  (Python)    │  │
│  │              │  │              │  │              │  │
│  │  React 19    │  │  React 19    │  │  FastAPI     │  │
│  │  App Router  │  │  Vite        │  │  Watchdog    │  │
│  │  Zustand     │  │  Zustand     │  │  PaddleOCR   │  │
│  │  React Query │  │  React Router│  │  pdfplumber  │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
│         │                 │                 │            │
│         │    REST API     │   Local REST    │   sync     │
│         │◄────────────────┤◄────────────────┤   API      │
│         │                 │  (port 8420)    │            │
└─────────┼─────────────────┼─────────────────┼────────────┘
          │                 │                 │
          ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────┐
│                    SERVER LAYER                          │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │              Django Backend                        │ │
│  │                                                    │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐        │ │
│  │  │  REST    │  │ WebSocket│  │  Celery  │        │ │
│  │  │  API     │  │ Consumers│  │  Workers │        │ │
│  │  │  (DRF)   │  │ (Channels)│ │  (Async) │        │ │
│  │  └──────────┘  └──────────┘  └──────────┘        │ │
│  │                                                    │ │
│  │  ┌──────────────────────────────────────────────┐ │ │
│  │  │           Core (Clean Architecture)           │ │ │
│  │  │                                               │ │ │
│  │  │  Domain -> Application -> Infrastructure     │ │ │
│  │  │                                               │ │ │
│  │  │  - 7 AI Agents                               │ │ │
│  │  │  - Document Processing Pipeline              │ │ │
│  │  │  - LLM Factory (OpenAI/Gemini/Ollama)        │ │ │
│  │  │  - Hybrid Search Engine                       │ │ │
│  │  │  - Embedding Service                          │ │ │
│  │  └──────────────────────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────┘ │
│                          │                              │
│              ┌───────────┴───────────┐                  │
│              ▼                       ▼                  │
│  ┌──────────────────┐  ┌──────────────────┐            │
│  │   PostgreSQL     │  │     Redis        │            │
│  │   + pgvector     │  │                  │            │
│  │                  │  │  - Cache         │            │
│  │  - Documents     │  │  - Celery Broker │            │
│  │  - Users         │  │  - Channel Layer │            │
│  │  - Embeddings    │  │  (WebSockets)    │            │
│  │  - Files         │  │                  │            │
│  └──────────────────┘  └──────────────────┘            │
└─────────────────────────────────────────────────────────┘
```

### Backend Architecture (Clean Architecture)

The backend follows strict **Domain-Driven Design (DDD)** with **Clean Architecture**:

```
backend/
├── core/
│   ├── domain/                    # LAYER 1: Pure business logic
│   │   ├── common/                #   Base entities, value objects, events, exceptions
│   │   ├── documents/             #   Document entity, state transitions, chunks
│   │   ├── files/                 #   FileRecord entity, fingerprinting, dedup
│   │   ├── ai/                    #   Embedding, AITask entities
│   │   ├── search/                #   Search query/result entities
│   │   └── workflows/             #   Workflow entities
│   │
│   ├── application/               # LAYER 2: Use cases + interfaces (ports)
│   │   ├── use_cases/             #   Business operations
│   │   ├── interfaces/            #   Abstract repositories and services (ports)
│   │   ├── services/              #   Application services
│   │   ├── dtos/                  #   Data transfer objects
│   │   └── tools/                 #   Tool definitions for chat function calling
│   │
│   └── infrastructure/            # LAYER 3: Framework-specific implementations (adapters)
│       ├── agents/                #   7 AI agent implementations
│       ├── cache/                 #   Redis cache implementation
│       ├── db/                    #   Django ORM models + repository implementations
│       ├── messaging/             #   Celery task implementations
│       ├── pipelines/             #   Document processing pipeline + LangGraph nodes
│       └── services/              #   LLM factory, embedding service, hybrid search
│
├── apps/                          # LAYER 4: Django apps (thin wrappers)
│   ├── accounts/                  #   User, Profile, RBAC
│   ├── agents/                    #   Edge agent management
│   ├── ai/                        #   AI tasks, embeddings, providers
│   ├── apikeys/                   #   API key management
│   ├── chat/                      #   RAG chat sessions + messages
│   ├── dashboard/                 #   Dashboard stats + WebSocket
│   ├── documents/                 #   Document + ExtractedEntity
│   ├── files/                     #   FileRecord + AuditLog
│   ├── organizations/             #   Multi-tenant orgs, memberships
│   ├── reports/                   #   Report generation
│   ├── search/                    #   SearchLog + SavedSearch
│   └── workflows/                 #   Workflow + WorkflowRun
│
└── interfaces/                    # LAYER 5: External interface (REST API)
    └── api/v1/
        ├── views/                 #   14 view files
        ├── serializers/           #   11 serializer files
        ├── authentication.py      #   API key auth
        └── urls.py                #   URL routing
```

**The Dependency Rule**: Dependencies point inward. Domain has zero imports from infrastructure. Application depends only on domain. Infrastructure implements interfaces defined in application.

---

## 3. Tech Stack

### Backend

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Framework | Django 5.x | Web framework, ORM, admin |
| API | Django REST Framework (DRF) | REST API serialization, views, routing |
| API Docs | drf-spectacular | OpenAPI/Swagger documentation |
| Database | PostgreSQL 16 + pgvector | Relational data + vector search |
| ORM | Django ORM | Database queries |
| Task Queue | Celery 5.3 | Async background tasks |
| Cache/Broker | Redis 7 | Celery broker, cache, WebSocket channel layer |
| WebSockets | Django Channels | Real-time bidirectional communication |
| ASGI Server | Daphne | Handles HTTP + WebSocket |
| WSGI Server | Gunicorn | HTTP only (production fallback) |
| Validation | Pydantic 2 | Data validation (infrastructure layer) |
| AI/LLM | LangChain 0.3, LangGraph 0.2 | LLM orchestration, stateful workflows |
| Embeddings | fastembed 0.4 | Local embedding generation |
| OCR | PaddleOCR, Tesseract | Text extraction from images/PDFs |
| Document Parsing | PyMuPDF, pdfplumber, python-docx, openpyxl | Multi-format text extraction |
| File Monitoring | Watchdog 4.0 | Real-time file system changes |
| Auth | djangorestframework-simplejwt | JWT access/refresh tokens |
| Monitoring | Sentry SDK | Error tracking (production) |

### Frontend (Web)

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Framework | Next.js 15 (App Router) | React framework with SSR/SSG |
| UI Library | React 19 | Component-based UI |
| Language | TypeScript 5.7+ | Type safety |
| Styling | Tailwind CSS 3.4 | Utility-first CSS |
| UI Components | shadcn/ui | Pre-built accessible components |
| State Management | Zustand 5 | Lightweight global state |
| Data Fetching | TanStack React Query 5 | Server state caching, pagination |
| Charts | Recharts 2.15 | Dashboard visualizations |
| i18n | next-intl 4.13 | English + Arabic (RTL) |
| Icons | lucide-react | Icon library |
| HTTP Client | Axios | API calls with interceptors |

### Desktop App

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Shell | Tauri 2 (Rust) | Native desktop wrapper |
| Frontend | React 19 + Vite 6 | UI |
| Routing | react-router-dom 7 | Client-side routing |
| State | Zustand 5 | State management |
| i18n | i18next + react-i18next | English + Arabic |
| Sidecar | Edge Agent (Python binary) | Background document processing |

### Edge Agent

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Language | Python 3.10+ | Runtime |
| HTTP API | FastAPI + Uvicorn | Local REST API |
| OCR | PaddleOCR + Tesseract | Image-to-text |
| Document Parsing | pdfplumber, python-docx, openpyxl, PyMuPDF, MinerU | Multi-format parsing |
| WebSocket | websockets 13 | Real-time server communication |
| HTTP Client | httpx 0.27 | Async HTTP requests |
| Config | PyYAML 6 | YAML configuration |
| Build | PyInstaller | Binary distribution |

---

## 4. Monorepo Structure

The project uses **Turborepo** + **pnpm workspaces** for monorepo management:

```
ai-archive-platform/
├── package.json              # Root scripts (build, dev, lint, test)
├── pnpm-workspace.yaml       # Workspace definition
├── turbo.json                # Turborepo task pipeline
├── .npmrc                    # pnpm shamefully-hoist=true
│
├── backend/                  # Python Django backend
├── frontend/                 # Next.js web app
├── desktop/                  # Tauri desktop app
├── edge_agent/               # Python edge agent
│
├── packages/
│   ├── common-types/         # Shared TypeScript Zod schemas
│   └── common-python/        # Shared Python DTOs
│
├── tests/                    # Root-level tests
│   ├── unit/                 # Domain + application unit tests
│   ├── integration/          # API + repository integration tests
│   └── fixtures/             # Shared test fixtures
│
├── docker/                   # Docker Compose configs
│   ├── docker-compose.yml    # Production
│   └── docker-compose.dev.yml # Development
│
└── .github/workflows/        # CI/CD pipelines
    └── ci.yml
```

### What Turborepo Does

Turborepo orchestrates tasks across the monorepo:
- `turbo build` — builds all packages in dependency order
- `turbo dev` — runs all dev servers in parallel
- `turbo lint` — lints all packages
- `turbo test` — runs all tests

### Workspace Dependencies

```
frontend ──depends-on──► common-types
desktop  ──depends-on──► common-types
backend  ──depends-on──► common-python
```

---

## 5. Backend (Django)

### Entry Points

| File | Purpose |
|------|---------|
| `backend/manage.py` | Django management commands (migrate, createsuperuser, etc.) |
| `backend/config/asgi.py` | ASGI application (HTTP + WebSocket via Daphne) |
| `backend/config/wsgi.py` | WSGI application (Gunicorn) |
| `backend/config/celery.py` | Celery app configuration |
| `backend/config/urls.py` | Root URL routing |

### Settings

Settings are split by environment in `backend/config/settings/`:

| File | Purpose |
|------|---------|
| `base.py` | All shared settings (287 lines) |
| `development.py` | Dev overrides (debug toolbar, CORS localhost) |
| `production.py` | Prod overrides (Sentry, SSL, static files) |
| `testing.py` | Test overrides (in-memory database, faster hashing) |

**Key settings from `base.py`**:
- Database: PostgreSQL via `POSTGRES_*` env vars
- Redis: `REDIS_URL` for channels + cache, `CELERY_BROKER_URL` for task queue
- JWT: HS256, access token 30 min, refresh token 7 days
- CORS: configurable origins (default: localhost:3000, localhost:5173)
- Rate limiting: 50/hour anonymous, 200/hour authenticated
- Page size: 50 items

### Django Apps (13 apps)

Each app is a thin wrapper containing models, views, and serializers. Business logic lives in `core/`.

#### accounts
- **User**: UUID PK, email (unique), role (admin/archivist/researcher/viewer), `last_login_ip`, `current_organization` FK
- **Profile**: OneToOne with User, phone, avatar, department, job_title, bio, timezone
- **Roles**: 4 roles controlling feature access

#### organizations
- **Organization**: UUID PK, name, slug (unique), description
- **Membership**: Links User + Organization with role (owner/admin/member)
- **Invitation**: Email-based invites with token, expiry, status tracking
- **Multi-tenancy**: All data is scoped to organizations

#### files
- **FileRecord**: UUID PK, organization FK, owner FK, path, mime_type, size_bytes, status, source (uploaded/api/agent), agent FK, content_hash (SHA-256), tags, metadata, duplicate_group_id
- **AuditLog**: Tracks every action (create/read/update/delete/upload/download/scan/process/classify/search/login/logout) with user, resource_type, resource_id, details, ip_address

#### documents
- **Document**: UUID PK, organization FK, owner FK, file_id, doc_type (19 categories), processing_status, title, author, subject, language, word_count, page_count, chunk_count, classification_confidence, tags, extracted_text, markdown, content_blocks (JSON), tables (JSON), images (JSON), summary, error_message, OCR metadata
- **ExtractedEntity**: Named entities with type (person/organization/date/amount/location/email/phone/reference_number/project_name), name, context, confidence, source (pipeline/agent)

#### ai
- **AITask**: Tracks AI operations (classify/extract/summarize/embed), status, document_id, tokens_used, model_used
- **Embedding**: Vector storage with vector_id, embedding (JSON list), metadata, document_id, file_id, chunk_index
- **ProviderConfig**: LLM/embedding provider configs (openai/google/ollama), capabilities, api_key, base_url, model_name, is_active, is_default

#### chat
- **ChatSession**: User + organization, title, is_active
- **ChatMessage**: session FK, role (user/assistant/system), content, sources (JSON), tool_calls (JSON), tokens_used, model_used

#### search
- **SearchLog**: query analytics (query, search_type, result_count, search_time_ms)
- **SavedSearch**: User-saved queries with name, query, filters

#### workflows
- **Workflow**: name, trigger_type (manual/on_upload/scheduled), steps (JSON), is_active
- **WorkflowRun**: Execution tracking with status, input/output data, current_step, total_steps

#### reports
- **Report**: report_type (archive_summary/processing_stats/search_analytics/user_activity/storage_usage/custom), title, status, data (JSON)

#### agents
- **Agent**: UUID PK, organization FK, user FK, agent_id (unique), name, status (online/offline/syncing/error), sync_scope, platform, hostname, agent_version, capabilities (JSON), last_seen, files_count
- **AgentFolder**: Monitored folder with local_path, label, is_active, file_count
- **AgentCommand**: Push commands to agents (sync/scan/process/config_update/shutdown/update/restart)

#### apikeys
- **ApiKey**: name, prefix (first 8 chars), key_hash (SHA-256), is_active. `create_key()` returns raw key, `verify_key()` checks hash.

### AI Agents (7 agents)

Located in `backend/core/infrastructure/agents/`:

| Agent | Purpose |
|-------|---------|
| BaseAgent | Abstract base with `execute(task)` interface |
| ArchiveAgent | Archive management operations |
| ClassificationAgent | Document classification into categories |
| FileAgent | File operations and management |
| ReportAgent | Report generation |
| SearchAgent | Search operations |
| SummaryAgent | Document summarization |

### Document Processing Pipeline

Located in `backend/core/infrastructure/pipelines/document_pipeline.py`:

```
10-Step Pipeline:
1. Load file record from DB
2. Create/find document entity
3. Get extracted text (from edge agent pre-processing)
4. [OCR skipped on server - done by edge agent]
5. Classify document (LLM) -> 19 categories
6. Extract named entities (LLM) -> person, org, date, amount, etc.
7. Generate summary (LLM)
8. Chunk text (1000 chars, 200 overlap, natural boundaries)
9. Generate embeddings + index to pgvector
10. Mark document as completed
```

**Pipeline Nodes** (`backend/core/infrastructure/pipelines/nodes/`):
- `chunk_node.py` — Text splitting at natural boundaries
- `classify_node.py` — LLM-based document classification
- `embed_index_node.py` — Embedding generation + pgvector storage
- `entity_node.py` — Named entity extraction
- `summarize_node.py` — LLM-based summarization

**Error handling**: Exponential backoff retry (max 3 retries, base delay 1s). Embedding failures are non-fatal — document remains keyword-searchable.

### LLM Factory

Located in `backend/core/infrastructure/services/llm_factory.py`:

| Provider | Implementation | Use Case |
|----------|---------------|----------|
| OpenAI | `OpenAILLMProvider` | GPT-4o, GPT-4o-mini (supports custom base_url for OpenAI-compatible APIs) |
| Google Gemini | `GoogleLLMProvider` | Vertex AI integration |
| Ollama | `OllamaLLMProvider` | Local LLM deployment (no API key needed) |

Each provider implements: `classify()`, `extract()`, `summarize()`, `chat_with_tools()`.

### Embedding Service

Located in `backend/core/infrastructure/services/embedding_service.py`:

| Provider | Implementation | Details |
|----------|---------------|---------|
| FastEmbed | `FastEmbedProvider` | Local multilingual model (384 dimensions), no API key needed |
| LangChain | `LangChainEmbeddingProvider` | Configurable model via ProviderConfig |

### Hybrid Search Engine

Located in `backend/core/infrastructure/services/hybrid_search.py`:

```
Search Flow:
Query -> Semantic Search (pgvector cosine similarity)
     -> Keyword Search (PostgreSQL tsvector/tsquery)
     -> Reciprocal Rank Fusion (merge with configurable weights)
     -> Ranked Results (default: 70% semantic, 30% keyword)
```

### Celery Background Tasks

| Task | Purpose | Retries | Timeout |
|------|---------|---------|---------|
| `process_document_task` | Full document processing pipeline | 3 | 30 min |
| `generate_embedding_task` | Generate embedding vectors | 5 | - |
| `classify_document_task` | Classify documents using LLM | 3 | - |

---

## 6. Frontend (Next.js)

### Entry Points

| File | Purpose |
|------|---------|
| `frontend/src/app/layout.tsx` | Root layout (providers, theme) |
| `frontend/src/app/page.tsx` | Root page (redirects to locale) |
| `frontend/src/app/[locale]/layout.tsx` | Locale-aware layout with next-intl |
| `frontend/src/middleware.ts` | Auth guard + i18n locale routing |

### App Router Structure

```
frontend/src/app/
├── layout.tsx                    # Root layout (providers, theme, toast)
├── page.tsx                      # Redirect to /[locale]
├── not-found.tsx                 # 404 page
├── globals.css                   # Global styles
└── [locale]/
    ├── layout.tsx                # Locale layout (next-intl provider)
    ├── (auth)/
    │   ├── login/page.tsx        # Login form
    │   ├── register/page.tsx     # Registration (supports invitation tokens)
    │   └── invitations/accept/   # Accept org invitation
    └── (dashboard)/
        ├── agents/               # Agent management (list, setup, download)
        ├── ai-workspace/         # AI workspace (classify, extract, summarize)
        ├── chat/                 # RAG chat interface
        ├── dashboard/            # Main dashboard (stats, charts, activity)
        ├── documents/            # Document management (list, detail, process)
        ├── files/                # File management (list, upload, download)
        ├── ocr/                  # OCR management
        ├── reports/              # Reports (summary, analytics)
        ├── scan/                 # Scan management
        ├── search/               # Search interface (hybrid search)
        ├── settings/             # Settings (org, providers, members)
        └── workflows/            # Workflow management
```

### State Management

**Zustand Stores** (`frontend/src/stores/`):
- `auth-store.ts` — Persisted tokens (accessToken, refreshToken), user data, isAuthenticated
- `ui-store.ts` — UI state (sidebar open, theme, etc.)

**React Query** — Server state management for all API data (caching, pagination, refetching)

### API Client

Located in `frontend/src/lib/api.ts`:
- Axios instance with base URL `/api/v1`
- **Request interceptor**: Attaches JWT Bearer token from auth store
- **Response interceptor**: On 401, refreshes token and retries; queues concurrent requests during refresh

### Key Components

| Component | Purpose |
|-----------|---------|
| `ChatInterface` | RAG-powered chat with document context and source citations |
| `DashboardStats` | Aggregated statistics cards |
| `ChartsSection` | Recharts visualizations (bar, line, pie, area) |
| `RecentActivity` | Audit log activity feed |
| `Recommendations` | AI-powered document recommendations |
| `OrganizationSwitcher` | Multi-org switching UI |
| `ScopeSelector` | Personal vs Organization data scope toggle |
| `ProviderEditForm` | AI provider configuration UI |
| `DownloadAgentDialog` | Agent download with OS detection |
| `SetupDeviceModal` | Onboarding device setup |

### WebSocket Integration

Located in `frontend/src/hooks/use-dashboard-ws.ts`:
- Connects to `ws://{backend}/ws/dashboard?token={jwt}`
- Receives: `agent_status_changed`, `files_synced`, `document_update`, `processing_update`
- Auto-reconnect with exponential backoff (1s → 30s)

### i18n

- **Library**: next-intl
- **Languages**: English (`en.json`), Arabic (`ar.json`)
- **RTL**: Full right-to-left support for Arabic
- **Locale routing**: `/en/...` and `/ar/...` prefixes

### Middleware

Located in `frontend/src/middleware.ts`:
- Locale detection and routing
- Auth guard: redirects to `/login` if no token
- Redirects authenticated users away from auth pages (except `desktop_callback`)

---

## 7. Desktop App (Tauri)

### What Is Tauri?

Tauri is a framework for building native desktop applications with web technologies. It uses a Rust backend for system-level operations and a web frontend (React) for the UI. The desktop app wraps the edge agent as a sidecar binary.

### Entry Points

| File | Purpose |
|------|---------|
| `desktop/src/main.tsx` | React entry point |
| `desktop/src/App.tsx` | React Router with protected routes |
| `desktop/src-tauri/tauri.conf.json` | Tauri config (window, CSP, bundle, sidecar) |
| `desktop/src-tauri/Cargo.toml` | Rust dependencies |

### Pages

| Route | Page | Purpose |
|-------|------|---------|
| `/login` | LoginPage | Authentication |
| `/dashboard` | DashboardPage | Agent status, stats, file sync |
| `/folders` | FoldersPage | Manage monitored folders |
| `/trash` | TrashPage | Deleted files |
| `/settings` | SettingsPage | Configuration |

### WebSocket Connection

Located in `desktop/src/hooks/use-agent-ws.ts`:
- Connects to `ws://localhost:8420/api/ws` (local edge agent)
- Handles events: `scan_completed`, `scan_failed`, `file_created/deleted/modified`, `status_changed`, `metrics_updated`, `sync_completed`
- Auto-reconnect with exponential backoff
- Keepalive: responds to ping with pong

### Stores

| Store | Purpose |
|-------|---------|
| `auth-store.ts` | Authentication state |
| `agent-store.ts` | Agent status, files, metrics, processing state |
| `config-store.ts` | Configuration |

### Build & Distribution

- Built with `pnpm tauri build`
- Produces platform-specific installers: `.deb` (Linux), `.dmg` (macOS), `.exe` (Windows)
- Distributed as zip with installer + config.json + install script
- Edge agent bundled as a sidecar binary

---

## 8. Edge Agent (Python)

### What Is the Edge Agent?

The edge agent is a Python application that runs on user machines. It scans local folders, parses documents (OCR, text extraction), and syncs pre-processed metadata to the server. This keeps heavy processing off the server and keeps raw document data local until only metadata is needed.

### Entry Points

| File | Purpose |
|------|---------|
| `edge_agent/__main__.py` | Entry point (subcommands: `api`, `cli`) |
| `edge_agent/cli.py` | CLI interface (commands: run, status, sync, register, scan, etc.) |
| `edge_agent/api/server.py` | FastAPI application |
| `edge_agent/api/routes.py` | 30+ API endpoints |
| `edge_agent/config.yaml` | Default configuration |

### Core Components

| Component | File | Purpose |
|-----------|------|---------|
| Scanner | `core/scanner.py` | Recursive folder scanning, SHA-256 fingerprinting, MIME detection |
| Watcher | `core/watcher.py` | Real-time file system monitoring (Watchdog library) |
| Sync Engine | `core/sync_engine.py` | Registers with server, sends heartbeats, syncs file metadata |
| Worker | `core/worker.py` | Background job processing |
| Job Queue | `core/job_queue.py` | Local job management |
| Event Bus | `core/event_bus.py` | Real-time event system for WebSocket push |
| Chunker | `core/chunker.py` | Text chunking for embeddings |
| Cache | `core/cache.py` | Local caching |
| Models | `core/models.py` | Local data models |

### OCR Engines

| Engine | Purpose |
|--------|---------|
| PaddleOCR | Primary OCR (Arabic + English support) |
| Tesseract | Fallback OCR |

### Document Parsers

| Parser | Format |
|--------|--------|
| PyMuPDF | PDF |
| pdfplumber | PDF text extraction |
| python-docx | Microsoft Word |
| openpyxl | Microsoft Excel |
| Pillow / OpenCV | Images |
| MinerU | Advanced document parsing (optional) |

### FastAPI API (30+ endpoints)

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Health check |
| `GET /status` | Agent status (worker, watcher, files, queue, memory) |
| `GET /capabilities` | Detected capabilities |
| `GET/PUT /config` | Configuration management |
| `POST /register` | Register with SaaS backend |
| `POST /heartbeat` | Send heartbeat to backend |
| `POST /sync` | Sync files to backend |
| `GET/POST/DELETE /folders` | Folder management |
| `POST /folders/rescan` | Rescan folder |
| `GET /files` | List files |
| `POST /scan` | Scan a specific file |
| `POST /parse-file` | Parse a file (OCR + extraction) |
| `GET/POST /jobs` | Job management |
| `POST /files/move\|rename\|delete\|copy\|restore\|archive` | File operations |
| `WS /ws` | WebSocket for real-time events |

### CLI Commands

```bash
edge-agent run          # Start agent (API + watcher + worker)
edge-agent status       # Show agent status
edge-agent health       # Health check
edge-agent config get   # Get configuration
edge-agent config set   # Set configuration
edge-agent scan         # Scan folders
edge-agent sync         # Sync to server
edge-agent pause        # Pause agent
edge-agent resume       # Resume agent
edge-agent metrics      # Show metrics
edge-agent files        # List files
edge-agent folders      # List folders
edge-agent logs         # View logs
```

### Build & Distribution

- Built with PyInstaller (`edge_agent/build.py`)
- Distributed as zip with binary + config.yaml + install script
- Supports Linux, macOS, Windows
- Auto-registration via JWT token from server

---

## 9. Shared Packages

### common-types (TypeScript)

Located in `packages/common-types/`:
- **Purpose**: Shared Zod schemas used by both frontend and desktop
- **Benefit**: Single source of truth for TypeScript types, runtime validation

| Module | Contents |
|--------|----------|
| `agent.ts` | Agent, AgentFolder, AgentCommand schemas |
| `auth.ts` | LoginRequest, AuthResponse schemas |
| `document.ts` | Document, DocumentChunk, DocumentType schemas |
| `file.ts` | FileRecord, ScanResult, FileOperationResult |
| `search.ts` | SearchRequest, SearchResult, SavedSearch |
| `pipeline.ts` | PipelineResult |
| `dashboard.ts` | DashboardStats, ActivityItem |
| `provider.ts` | ProviderConfig |
| `common.ts` | Shared utility types |

### common-python (Python)

Located in `packages/common-python/`:
- **Purpose**: Shared Python DTOs used by backend and edge agent
- **Benefit**: Consistent data structures between server and client

| Module | Contents |
|--------|----------|
| `models.py` | FileMetadata, ExtractionResult, ContentBlock, ParsedTable, ParsedImage, DocumentProcessedEvent |
| `constants.py` | Shared constants |
| `config.py` | Shared configuration |
| `utils.py` | Utility functions |
| `validation.py` | Data validation |

---

## 10. Database Schema

### Entity Relationship Diagram

```
┌──────────────┐     ┌──────────────────┐     ┌──────────────┐
│    User      │────►│   Membership     │◄────│ Organization │
│              │     │                  │     │              │
│ - id (UUID)  │     │ - user (FK)      │     │ - id (UUID)  │
│ - email      │     │ - organization   │     │ - name       │
│ - role       │     │ - role           │     │ - slug       │
│ - org (FK)   │     └──────────────────┘     └──────────────┘
└──────┬───────┘
       │
       ├──► Profile (1:1)
       ├──► FileRecord (owner)
       ├──► Document (owner)
       ├──► ChatSession
       ├──► SavedSearch
       ├──► Agent
       ├──► ApiKey
       └──► AuditLog

┌──────────────┐     ┌──────────────────┐
│  FileRecord  │────►│    Document      │
│              │     │                  │
│ - id (UUID)  │     │ - id (UUID)      │
│ - org (FK)   │     │ - file_id        │
│ - owner (FK) │     │ - doc_type       │
│ - path       │     │ - processing_status│
│ - mime_type  │     │ - extracted_text │
│ - size_bytes │     │ - summary        │
│ - status     │     │ - markdown       │
│ - source     │     │ - content_blocks │
│ - agent (FK) │     │ - tables         │
│ - content_hash│    │ - images         │
│ - tags       │     └────────┬─────────┘
│ - metadata   │              │
└──────────────┘              ▼
                     ┌──────────────────┐
                     │ ExtractedEntity  │
                     │                  │
                     │ - document (FK)  │
                     │ - entity_type    │
                     │ - name           │
                     │ - context        │
                     │ - confidence     │
                     └──────────────────┘

┌──────────────┐     ┌──────────────────┐
│    Agent     │────►│  AgentFolder     │
│              │     │                  │
│ - id (UUID)  │     │ - agent (FK)     │
│ - org (FK)   │     │ - local_path     │
│ - user (FK)  │     │ - label          │
│ - agent_id   │     │ - is_active      │
│ - name       │     │ - file_count     │
│ - status     │     └──────────────────┘
│ - platform   │
│ - capabilities│    ┌──────────────────┐
└──────┬───────┘────►│  AgentCommand    │
       │             │                  │
       │             │ - agent (FK)     │
       │             │ - command_type   │
       │             │ - payload        │
       │             │ - status         │
       │             │ - result         │
       │             └──────────────────┘
       │
       └──► ApiKey (1:1)

┌──────────────┐     ┌──────────────────┐
│  AITask      │     │   Embedding      │
│              │     │                  │
│ - id (UUID)  │     │ - id (UUID)      │
│ - task_type  │     │ - vector_id      │
│ - status     │     │ - embedding (vec)│
│ - document_id│     │ - metadata       │
│ - tokens_used│     │ - document_id    │
│ - model_used │     │ - file_id        │
└──────────────┘     │ - chunk_index    │
                     └──────────────────┘

┌──────────────┐     ┌──────────────────┐
│ ChatSession  │────►│  ChatMessage     │
│              │     │                  │
│ - id (UUID)  │     │ - session (FK)   │
│ - user (FK)  │     │ - role           │
│ - org (FK)   │     │ - content        │
│ - title      │     │ - sources (JSON) │
└──────────────┘     │ - tool_calls     │
                     │ - tokens_used    │
                     └──────────────────┘

┌──────────────┐     ┌──────────────────┐
│  Workflow    │────►│  WorkflowRun     │
│              │     │                  │
│ - id (UUID)  │     │ - workflow (FK)  │
│ - org (FK)   │     │ - status         │
│ - name       │     │ - input_data     │
│ - trigger_type│    │ - output_data    │
│ - steps (JSON)│    │ - current_step   │
└──────────────┘     └──────────────────┘

┌──────────────┐     ┌──────────────────┐
│  SearchLog   │     │  SavedSearch     │
│              │     │                  │
│ - org (FK)   │     │ - user (FK)      │
│ - query      │     │ - name           │
│ - search_type│     │ - query          │
│ - result_count│    │ - filters (JSON) │
│ - time_ms    │     └──────────────────┘
└──────────────┘

┌──────────────┐     ┌──────────────────┐
│  ApiKey      │     │   AuditLog       │
│              │     │                  │
│ - org (FK)   │     │ - org (FK)       │
│ - user (FK)  │     │ - user (FK)      │
│ - name       │     │ - action         │
│ - prefix     │     │ - resource_type  │
│ - key_hash   │     │ - resource_id    │
│ - is_active  │     │ - details (JSON) │
└──────────────┘     │ - ip_address     │
                     └──────────────────┘

┌──────────────────┐
│ ProviderConfig   │
│                  │
│ - name (unique)  │
│ - provider_type  │  (openai/google/ollama)
│ - capabilities   │  (["llm", "embedding"])
│ - api_key        │
│ - base_url       │
│ - model_name     │
│ - is_active      │
│ - is_default     │
└──────────────────┘
```

---

## 11. Authentication & Authorization

### Authentication Methods

#### 1. JWT (Primary)

Used by the web frontend and desktop app.

| Property | Value |
|----------|-------|
| Library | djangorestframework-simplejwt |
| Algorithm | HS256 |
| Access token lifetime | Configurable (default: 30 minutes) |
| Refresh token lifetime | Configurable (default: 7 days) |
| Token rotation | Enabled |
| Blacklisting | After rotation |
| Header | `Authorization: Bearer <token>` |

**Flow**:
```
1. User sends POST /api/v1/auth/login with email + password
2. Server returns { access, refresh } tokens
3. Client stores tokens in Zustand (persisted to localStorage)
4. Client attaches access token to every request via Axios interceptor
5. On 401, client uses refresh token to get new access token
6. On refresh failure, client redirects to login
```

#### 2. API Key

Used by edge agents and programmatic access.

| Property | Value |
|----------|-------|
| Prefix | `ak_` |
| Storage | SHA-256 hash (never stored in plain text) |
| Header | `X-API-Key: ak_...` |
| Identification | First 8 chars stored as `prefix` for lookup |

**Flow**:
```
1. User creates API key via POST /api/v1/api-keys
2. Server returns raw key (shown once)
3. Client stores key, sends via X-API-Key header
4. Server hashes key, looks up by prefix, verifies hash
```

#### 3. WebSocket Authentication

Used for real-time connections (dashboard, agent communication).

| Priority | Method | Format |
|----------|--------|--------|
| 1 | API Key | `?api_key=ak_...` query parameter |
| 2 | JWT | `?token=eyJ...` query parameter |
| 3 | Session cookie | Browser cookie |
| 4 | Anonymous | Fallback (limited access) |

### Authorization

#### User Roles

| Role | Description |
|------|-------------|
| Admin | Full system access, manage users and settings |
| Archivist | Manage documents, files, and classifications |
| Researcher | Search, chat, and analyze documents |
| Viewer | Read-only access |

#### Organization Roles

| Role | Description |
|------|-------------|
| Owner | Full org control, manage members |
| Admin | Manage org settings and members |
| Member | Standard access within org |

#### Permissions

- **Default**: `IsAuthenticated` for all endpoints
- **Custom**: `IsAgentOwner` for agent management
- **Throttling**: Anonymous 50/hour, Authenticated 200/hour
- **Multi-tenant**: Organization-scoped data isolation

#### Organization Scoping

Located in `backend/apps/organizations/mixins.py`:
- `OrgScopedMixin`: Filters querysets by user's scope
- Scope determined by `?scope=personal|organization` query param
- Auto-detected from user's `current_organization` field

---

## 12. AI/ML Pipeline

### Document Processing Pipeline

The core AI pipeline orchestrates the entire document understanding process:

```
┌─────────────┐
│  1. Load    │  Load file record from DB
│  File       │
└──────┬──────┘
       ▼
┌─────────────┐
│  2. Create  │  Create or find existing document entity
│  Document   │
└──────┬──────┘
       ▼
┌─────────────┐
│  3. Get     │  Retrieve pre-processed text from edge agent
│  Text       │  (no server-side OCR)
└──────┬──────┘
       ▼
┌─────────────┐
│  4. Classify│  LLM classifies into 19 categories:
│  (LLM)      │  invoice, receipt, contract, report, letter,
│             │  memo, email, form, certificate, license,
│             │  agreement, proposal, statement, notice,
│             │  minutes, policy, manual, other, unknown
└──────┬──────┘
       ▼
┌─────────────┐
│  5. Extract │  LLM extracts named entities:
│  Entities   │  person, organization, date, amount,
│  (LLM)      │  location, email, phone, reference_number
└──────┬──────┘
       ▼
┌─────────────┐
│  6. Summarize│  LLM generates document summary
│  (LLM)      │
└──────┬──────┘
       ▼
┌─────────────┐
│  7. Chunk   │  Split text into chunks:
│  Text       │  - 1000 characters per chunk
│             │  - 200 character overlap
│             │  - Splits at natural boundaries (sentences, paragraphs)
└──────┬──────┘
       ▼
┌─────────────┐
│  8. Embed   │  Generate vector embeddings for each chunk
│  + Index    │  Store in pgvector for semantic search
└──────┬──────┘
       ▼
┌─────────────┐
│  9. Mark    │  Update document status to "completed"
│  Completed  │
└─────────────┘
```

### LLM Providers

The system supports multiple LLM providers via a factory pattern:

```
LLMFactory
├── OpenAILLMProvider
│   - Uses: openai SDK
│   - Models: GPT-4o, GPT-4o-mini (configurable)
│   - Supports: custom base_url for OpenAI-compatible APIs
│
├── GoogleLLMProvider
│   - Uses: google-generativeai SDK
│   - Models: Gemini Pro, Gemini Flash
│
└── OllamaLLMProvider
    - Uses: HTTP API to local Ollama server
    - Models: Any model pulled in Ollama
    - Benefit: No API key needed, fully local
```

Each provider implements:
- `classify(text)` → Document category
- `extract(text)` → Named entities
- `summarize(text)` → Document summary
- `chat_with_tools(messages, tools)` → RAG response with function calling

### Embedding Models

| Provider | Model | Dimensions | Use Case |
|----------|-------|-----------|----------|
| FastEmbed | ibm-granite/granite-embedding-97m-multilingual-r2 | 384 | Local, no API key, multilingual |
| LangChain | Configurable via ProviderConfig | Varies | Production with API-backed models |

### RAG (Retrieval-Augmented Generation)

The chat system uses RAG to provide document-grounded answers:

```
User Question
    │
    ▼
┌─────────────┐
│  Embed      │  Convert question to vector
│  Question   │
└──────┬──────┘
       ▼
┌─────────────┐
│  Hybrid     │  Search pgvector (semantic) + tsvector (keyword)
│  Search     │  Merge with Reciprocal Rank Fusion
└──────┬──────┘
       ▼
┌─────────────┐
│  Retrieve   │  Get top-k relevant document chunks
│  Chunks     │
└──────┬──────┘
       ▼
┌─────────────┐
│  Build      │  System prompt + context chunks + user question
│  Prompt     │
└──────┬──────┘
       ▼
┌─────────────┐
│  LLM        │  Generate answer with source citations
│  Response   │
└─────────────┘
```

### Tool Calling (Chat Function Calling)

The chat system can invoke platform tools via LLM function calling:

| Tool | Purpose |
|------|---------|
| `search_documents` | Hybrid search with filters |
| `get_document_details` | Retrieve document metadata |
| `list_agents` | List registered edge agents |
| `trigger_agent_scan` | Send scan command to agent |
| `trigger_agent_sync` | Send sync command to agent |
| `run_workflow` | Trigger workflow execution |
| `get_workflow_list` | List available workflows |
| `move_document` | Update document metadata |
| `get_recommendations` | Find similar documents |

---

## 13. Search System

### Search Types

| Type | Implementation | Best For |
|------|---------------|----------|
| **Semantic** | pgvector cosine similarity | Meaning-based queries ("find contracts about pricing") |
| **Keyword** | PostgreSQL tsvector/tsquery | Exact matches ("invoice #12345") |
| **Hybrid** | Reciprocal Rank Fusion merge | Best of both worlds (default) |

### Hybrid Search Flow

```
User Query
    │
    ├──► Semantic Search (pgvector)
    │    - Embed query vector
    │    - Cosine similarity against all document embeddings
    │    - Return top-k with similarity scores
    │
    ├──► Keyword Search (PostgreSQL)
    │    - Convert query to tsquery
    │    - Search tsvector index on extracted_text
    │    - Return top-k with TF scores
    │
    └──► Reciprocal Rank Fusion (RRF)
         - Merge results from both searches
         - Rank by: score = Σ 1/(k + rank) for each result
         - Default weights: 70% semantic, 30% keyword
         - Return unified ranked results
```

### Reciprocal Rank Fusion Formula

```
RRF_score(d) = Σ 1/(k + rank_i(d))

Where:
- k = 60 (constant, prevents high-ranking documents from dominating)
- rank_i(d) = rank of document d in search result list i
- Summed across all search methods
```

### Search Analytics

- **SearchLog**: Tracks every search query, type, result count, and response time
- **SavedSearch**: Users can save frequently used queries with filters
- **Search History**: Accessible via API for user review

---

## 14. WebSocket & Real-time

### WebSocket Endpoints

| Endpoint | Purpose |
|----------|---------|
| `ws/dashboard/` | Real-time dashboard updates |
| `ws/agent/{agent_id}/` | Real-time agent communication |
| `ws/processing/` | Processing status updates |

### Dashboard WebSocket

**Route**: `ws://{backend}/ws/dashboard?token={jwt}`

**Server → Client Events**:
| Event | Payload | Purpose |
|-------|---------|---------|
| `agent_status_changed` | agent_id, status | Agent online/offline/syncing |
| `files_synced` | agent_id, count, total_size | Files synced from agent |
| `document_update` | document_id, status | Document processing status |
| `processing_update` | task_id, progress, status | Pipeline progress |

**Client → Server Messages**:
| Message | Purpose |
|---------|---------|
| `subscribe_document` | Subscribe to document updates |
| `unsubscribe_document` | Unsubscribe from document updates |

### Agent WebSocket

**Route**: `ws://{backend}/ws/agent/{agent_id}/`

**Agent → Server**:
| Message | Purpose |
|---------|---------|
| `heartbeat` | Keepalive + status report |
| `sync_files` | Send pre-processed file metadata |
| `command_result` | Report command execution result |

**Server → Agent**:
| Message | Purpose |
|---------|---------|
| `heartbeat_ack` | Acknowledge heartbeat + send pending commands + config |
| `sync_ack` | Acknowledge file sync |
| `command` | Push new command to agent |
| `config_update` | Push configuration changes |

### Agent Command System

Agents can receive push commands from the server:

| Command Type | Purpose |
|-------------|---------|
| `sync` | Trigger file sync |
| `scan` | Trigger folder scan |
| `process` | Process specific file |
| `config_update` | Update agent configuration |
| `shutdown` | Shut down agent |
| `update` | Update agent binary |
| `restart` | Restart agent |
| `start_scan` | Start continuous scanning |
| `stop_scan` | Stop continuous scanning |

### Real-time Architecture

```
┌─────────────┐     WebSocket      ┌─────────────┐
│  Web Client │◄──────────────────►│   Django    │
│  (Next.js)  │                    │  Channels   │
└─────────────┘                    │  + Redis    │
                                   │  Channel    │
┌─────────────┐     WebSocket      │  Layer      │
│  Edge Agent │◄──────────────────►│             │
│  (Python)   │                    └─────────────┘
└─────────────┘
```

**Channel Layer**: Redis-backed, enables cross-process WebSocket communication (multiple Django workers can share connections).

---

## 15. API Reference

### Backend API v1 (`/api/v1/`)

#### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/login` | JWT login (email + password) |
| POST | `/api/v1/auth/register` | User registration |
| POST | `/api/v1/auth/logout` | JWT logout (token blacklist) |
| POST | `/api/v1/token/refresh` | JWT token refresh |

#### Users

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/users/` | List users |
| GET | `/api/v1/users/{id}/` | Get user |
| PUT | `/api/v1/users/{id}/` | Update user |
| GET | `/api/v1/users/me/` | Get current user |

#### Files

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/files/` | List files |
| POST | `/api/v1/files/` | Upload file |
| GET | `/api/v1/files/{id}/` | Get file |
| DELETE | `/api/v1/files/{id}/` | Delete file |
| POST | `/api/v1/files/{id}/scan/` | Scan file |
| POST | `/api/v1/files/{id}/upload/` | Upload file content |
| GET | `/api/v1/files/{id}/download/` | Download file |

#### Documents

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/documents/` | List documents |
| POST | `/api/v1/documents/` | Create document |
| GET | `/api/v1/documents/{id}/` | Get document |
| PUT | `/api/v1/documents/{id}/` | Update document |
| DELETE | `/api/v1/documents/{id}/` | Delete document |
| POST | `/api/v1/documents/{id}/process/` | Trigger processing |
| POST | `/api/v1/documents/{id}/classify/` | Classify document |
| POST | `/api/v1/documents/{id}/extract/` | Extract entities |

#### AI

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/ai/classify` | Classify text |
| POST | `/api/v1/ai/extract` | Extract entities |
| POST | `/api/v1/ai/summarize` | Summarize text |
| GET | `/api/v1/ai/providers` | List AI providers |

#### Chat (RAG)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/chat/sessions` | List chat sessions |
| POST | `/api/v1/chat/sessions` | Create chat session |
| GET | `/api/v1/chat/sessions/{id}/messages` | List messages |
| POST | `/api/v1/chat/sessions/{id}/messages` | Send message (RAG) |

#### Dashboard

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/dashboard/stats` | Aggregated statistics |
| GET | `/api/v1/dashboard/charts` | Chart data |
| GET | `/api/v1/dashboard/activity` | Activity feed |
| GET | `/api/v1/dashboard/recommendations` | AI recommendations |

#### Search

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/api/v1/search/search` | Hybrid/semantic/keyword search |
| GET | `/api/v1/search/history` | Search history |
| GET/POST/DELETE | `/api/v1/search/saved` | Saved searches |
| GET/POST | `/api/v1/search/quick-search` | Lightweight search |

#### Agents

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/api/v1/agents/` | List/create agents |
| GET/PUT/DELETE | `/api/v1/agents/{id}/` | Agent CRUD |
| POST | `/api/v1/agents/{id}/setup` | Quick setup (returns JWT) |
| POST | `/api/v1/agents/auto-register` | Auto-registration |
| GET | `/api/v1/agents/{id}/download` | Download agent binary |
| POST | `/api/v1/agents/{id}/heartbeat` | Agent heartbeat |
| GET/POST | `/api/v1/agents/{id}/commands` | Fetch/report commands |
| POST | `/api/v1/agents/{id}/commands/create` | Push command |
| GET/POST | `/api/v1/agents/{id}/folders` | Manage folders |
| POST | `/api/v1/agents/{id}/sync` | Sync files |
| POST | `/api/v1/agents/{id}/files/move` | Move files |
| POST | `/api/v1/agents/{id}/files/move-folder` | Move files between folders |

#### Organizations

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/api/v1/organizations/` | List/create organizations |
| GET/PUT/DELETE | `/api/v1/organizations/{id}/` | Organization CRUD |
| GET/POST | `/api/v1/memberships/` | Manage memberships |
| GET/POST | `/api/v1/invitations/` | Manage invitations |

#### Other

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health/` | Health check |
| GET | `/api/v1/schema/` | OpenAPI schema |
| GET | `/api/v1/docs/` | Swagger UI |
| GET | `/admin/` | Django admin |

---

## 16. Configuration

### Environment Variables

**File**: `.env` (template in `.env.example`)

| Variable | Purpose | Example |
|----------|---------|---------|
| `DJANGO_SECRET_KEY` | Django secret | `your-secret-key` |
| `POSTGRES_DB` | Database name | `ai_archive` |
| `POSTGRES_USER` | Database user | `postgres` |
| `POSTGRES_PASSWORD` | Database password | `password` |
| `POSTGRES_HOST` | Database host | `localhost` |
| `POSTGRES_PORT` | Database port | `5432` |
| `REDIS_URL` | Redis URL | `redis://localhost:6379/0` |
| `CELERY_BROKER_URL` | Celery broker | `redis://localhost:6379/1` |
| `OPENAI_API_KEY` | OpenAI API key | `sk-...` |
| `GOOGLE_API_KEY` | Google Gemini key | `AIza...` |
| `OLLAMA_BASE_URL` | Ollama server | `http://localhost:11434` |
| `DEFAULT_LLM_PROVIDER` | Default AI provider | `openai` |
| `DEFAULT_LLM_MODEL` | Default model | `gpt-4o` |
| `EMBEDDING_DIMENSION` | Embedding size | `384` |
| `EMBEDDING_MODEL` | Embedding model | `ibm-granite/granite-embedding-97m-multilingual-r2` |
| `MAX_UPLOAD_SIZE_MB` | Upload limit | `100` |
| `CORS_ALLOWED_ORIGINS` | CORS origins | `http://localhost:3000` |
| `NEXT_PUBLIC_API_URL` | Frontend API URL | `http://localhost:8000` |
| `NEXT_PUBLIC_WS_URL` | Frontend WebSocket URL | `ws://localhost:8000` |
| `FRONTEND_URL` | Backend → Frontend URL | `http://localhost:3000` |
| `SENTRY_DSN` | Sentry error tracking | `https://...` |
| `JWT_ACCESS_LIFETIME_MINUTES` | Access token lifetime | `30` |
| `JWT_REFRESH_LIFETIME_DAYS` | Refresh token lifetime | `7` |

### Edge Agent Configuration

**File**: `edge_agent/config.yaml`

```yaml
server:
  url: http://localhost:8000
  api_key: ak_...

folders:
  - path: /home/user/Documents
    label: Documents
  - path: /home/user/Desktop
    label: Desktop

scanner:
  ignore_patterns:
    - "*.tmp"
    - ".DS_Store"
    - "__pycache__"
  max_file_size_mb: 100

ocr:
  engine: paddleocr  # or tesseract
  languages: [en, ar]

sync:
  interval_minutes: 5
  auto_sync: true

watcher:
  enabled: true
  debounce_seconds: 2

llm:
  provider: openai
  model: gpt-4o-mini
```

### Docker Compose Configuration

**File**: `docker/docker-compose.yml`

| Service | Image | Ports | Memory Limit |
|---------|-------|-------|-------------|
| postgres | pgvector/pgvector:pg16 | 5432 | 1GB |
| redis | redis:7-alpine | 6379 | 512MB |
| web | Django (daphne) | 8000 | 1GB |
| worker | Celery worker | - | 2GB |
| beat | Celery beat | - | 512MB |
| frontend | Next.js | 3000 | 512MB |

---

## 17. Docker & Deployment

### Production Deployment

```bash
# Start all services
cd docker
docker-compose up -d

# View logs
docker-compose logs -f web

# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser
```

### Development Deployment

```bash
# Start with hot reload
cd docker
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Backend only
cd backend
pip install -r requirements/development.txt
python manage.py runserver

# Frontend only
cd frontend
pnpm install
pnpm dev

# Edge agent only
cd edge_agent
pip install -e .
edge-agent run
```

### Dockerfile Stages

**Backend** (`backend/Dockerfile`):
```
base → builder → production → development
```
- Base: Python 3.12-slim + system deps (libpq, OpenCV, Tesseract, poppler)
- Production: Non-root user (django), daphne ASGI server
- Development: Django runserver with hot reload

**Frontend** (`frontend/Dockerfile`):
```
base → deps → builder → production → development
```
- Production: Node.js 20-alpine, standalone output, non-root user (node)
- Development: npm run dev

### Edge Agent Distribution

```bash
# Build binary
cd edge_agent
python build.py

# Produces: dist/edge-agent (PyInstaller binary)
# Distribute as: edge-agent.zip (binary + config.yaml + install script)
```

### Desktop App Distribution

```bash
# Build desktop app
cd desktop
pnpm tauri build

# Produces:
# - Linux: .deb installer
# - macOS: .dmg installer
# - Windows: .exe installer
```

---

## 18. Testing

### Backend Tests

**Framework**: pytest + pytest-django + pytest-cov + pytest-asyncio

**Structure**:
```
backend/tests/
├── conftest.py          # Shared fixtures
├── mocks.py             # Mock objects
├── unit/                # Domain + application unit tests
├── integration/         # API + repository integration tests
```

**Running**:
```bash
cd backend
pytest                          # Run all tests
pytest tests/unit/              # Unit tests only
pytest tests/integration/       # Integration tests only
pytest --cov=core --cov-report=html  # Coverage report
```

### Frontend Tests

**Framework**: Vitest + @testing-library/react + jsdom

**Structure**:
```
frontend/src/__tests__/
```

**Running**:
```bash
cd frontend
pnpm test                # Run all tests
pnpm test:watch          # Watch mode
pnpm test:coverage       # Coverage report
```

### Edge Agent Tests

**Framework**: pytest + pytest-asyncio

**Structure**:
```
edge_agent/tests/
├── test_cache.py
├── test_chunker.py
├── test_cli.py
├── test_config.py
├── test_event_bus.py
├── test_job_queue.py
├── test_llm_client.py
├── test_local_db.py
├── test_log_capture.py
├── test_metrics.py
├── test_migrate.py
├── test_models.py
├── test_ocr_engine.py
├── test_plugin_loader.py
├── test_routes.py
├── test_scanner.py
├── test_sync_engine.py
├── test_watcher.py
├── test_worker.py
└── test_ws_client.py
```

**Running**:
```bash
cd edge_agent
pytest                          # Run all tests
pytest tests/test_scanner.py    # Single test file
```

### Root-Level Tests

```
tests/
├── unit/
│   ├── domain/              # Domain entity tests
│   └── application/         # Use case tests
├── integration/
│   ├── api/                 # API endpoint tests
│   ├── repositories/        # Repository tests
│   └── services/            # Service tests
└── fixtures/                # Shared test data
```

---

## 19. CI/CD

### GitHub Actions Pipeline

**File**: `.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_DB: test_db
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
      redis:
        image: redis:7-alpine
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r backend/requirements/development.txt
      - run: cd backend && pytest tests/ --cov=core

  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install ruff
      - run: ruff check backend/
      - run: ruff format --check backend/

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: pnpm install
      - run: pnpm --filter frontend typecheck
      - run: pnpm --filter frontend test
      - run: pnpm --filter frontend build
```

### Pre-commit Hooks

**File**: `.pre-commit-config.yaml`

| Hook | Purpose |
|------|---------|
| `ruff` | Python linting |
| `ruff-format` | Python formatting |
| `trailing-whitespace` | Remove trailing whitespace |
| `check-yaml` | Validate YAML files |
| `check-json` | Validate JSON files |

**Setup**:
```bash
pip install pre-commit
pre-commit install
```

---

## 20. Data Flow

### Complete Document Lifecycle

```
1. USER SETUP
   └─► User installs edge agent on their machine
   └─► User configures folders to monitor
   └─► Agent registers with server (JWT auth)
   └─► Agent starts heartbeat loop

2. FILE DISCOVERY
   └─► Agent scanner recursively scans configured folders
   └─► SHA-256 fingerprint calculated for each file
   └─► MIME type detected
   └─► New/changed files identified

3. DOCUMENT PARSING (Edge Agent)
   └─► PDF → PyMuPDF/pdfplumber extracts text
   └─► DOCX → python-docx extracts text
   └─► XLSX → openpyxl extracts data
   └─► Images → PaddleOCR/Tesseract extracts text
   └─► Text chunked (1000 chars, 200 overlap)

4. SYNC TO SERVER
   └─► Agent sends metadata + extracted text via POST /api/v1/agents/{id}/sync
   └─► Server creates FileRecord + Document
   └─► Server acknowledges sync

5. AI PROCESSING (Server)
   └─► Celery worker picks up process_document_task
   └─► Pipeline classifies document (LLM)
   └─► Pipeline extracts entities (LLM)
   └─► Pipeline generates summary (LLM)
   └─► Pipeline chunks text
   └─► Pipeline generates embeddings
   └─► Embeddings stored in pgvector
   └─► Document marked as completed

6. SEARCH & RETRIEVAL
   └─► User searches via web frontend
   └─► Hybrid search: semantic + keyword
   └─► Results ranked by Reciprocal Rank Fusion
   └─► User views document details

7. RAG CHAT
   └─► User asks question in chat
   └─► Question embedded
   └─► Relevant chunks retrieved via hybrid search
   └─► Chunks + question sent to LLM
   └─► LLM generates grounded answer with sources

8. REAL-TIME UPDATES
   └─► WebSocket pushes dashboard updates
   └─► Agent status changes broadcast
   └─► Document processing progress streamed
   └─► File sync notifications sent
```

### Multi-Tenant Data Flow

```
User A (Org 1)          User B (Org 2)
    │                       │
    ▼                       ▼
┌─────────┐            ┌─────────┐
│ Scope:  │            │ Scope:  │
│ Org 1   │            │ Org 2   │
└────┬────┘            └────┬────┘
     │                      │
     ▼                      ▼
┌─────────────────────────────────┐
│      Organization Scoping       │
│                                 │
│  QuerySet.filter(               │
│      organization=user.org      │
│  )                              │
│                                 │
│  User A sees only Org 1 data    │
│  User B sees only Org 2 data    │
└─────────────────────────────────┘
```

### Authentication Flow

```
1. LOGIN
   User → POST /api/v1/auth/login {email, password}
   Server → Validates credentials
   Server → Returns {access_token, refresh_token}
   Client → Stores tokens in Zustand (persisted)

2. API REQUEST
   Client → GET /api/v1/documents/ Authorization: Bearer <access_token>
   Server → Validates JWT
   Server → Returns data

3. TOKEN REFRESH
   Client → On 401, POST /api/v1/token/refresh {refresh_token}
   Server → Validates refresh token
   Server → Returns new {access_token, refresh_token}
   Client → Updates stored tokens, retries original request

4. LOGOUT
   Client → POST /api/v1/auth/logout {refresh_token}
   Server → Blacklists refresh token
   Client → Clears stored tokens
```

---

## Appendix A: File Paths Quick Reference

| Component | Path |
|-----------|------|
| Backend entry | `backend/manage.py` |
| Backend settings | `backend/config/settings/base.py` |
| Backend URLs | `backend/config/urls.py` |
| API v1 URLs | `backend/interfaces/api/v1/urls.py` |
| Domain layer | `backend/core/domain/` |
| Application layer | `backend/core/application/` |
| Infrastructure layer | `backend/core/infrastructure/` |
| AI agents | `backend/core/infrastructure/agents/` |
| Pipeline | `backend/core/infrastructure/pipelines/` |
| LLM factory | `backend/core/infrastructure/services/llm_factory.py` |
| Hybrid search | `backend/core/infrastructure/services/hybrid_search.py` |
| Frontend entry | `frontend/src/app/layout.tsx` |
| Frontend middleware | `frontend/src/middleware.ts` |
| Frontend API client | `frontend/src/lib/api.ts` |
| Frontend stores | `frontend/src/stores/` |
| Desktop entry | `desktop/src/App.tsx` |
| Tauri config | `desktop/src-tauri/tauri.conf.json` |
| Edge agent entry | `edge_agent/__main__.py` |
| Edge agent API | `edge_agent/api/routes.py` |
| Edge agent scanner | `edge_agent/core/scanner.py` |
| Edge agent config | `edge_agent/config.yaml` |
| Common types | `packages/common-types/src/` |
| Common Python | `packages/common-python/common/` |
| Docker Compose | `docker/docker-compose.yml` |
| CI/CD | `.github/workflows/ci.yml` |

---

## Appendix B: Key Commands

```bash
# Backend
python manage.py migrate                    # Run migrations
python manage.py createsuperuser            # Create admin user
python manage.py runserver                  # Start dev server
celery -A config worker -l info             # Start Celery worker
celery -A config beat -l info               # Start Celery beat

# Frontend
pnpm install                                # Install dependencies
pnpm dev                                    # Start dev server
pnpm build                                  # Build for production
pnpm test                                   # Run tests
pnpm lint                                   # Lint code

# Desktop
pnpm tauri dev                              # Start dev mode
pnpm tauri build                            # Build for production

# Edge Agent
edge-agent run                              # Start agent
edge-agent status                           # Check status
edge-agent scan                             # Scan folders
edge-agent sync                             # Sync to server

# Docker
docker-compose up -d                        # Start all services
docker-compose logs -f                      # View logs
docker-compose down                         # Stop all services

# Monorepo
turbo build                                 # Build all packages
turbo dev                                   # Run all dev servers
turbo lint                                  # Lint all packages
turbo test                                  # Run all tests
```
