# Alexandria
## The Library of Today!
Alexandria s a community-focused application designed to help users find, review, discuss, and track books. Inspired by the legendary Library of Alexandria, our mission is to create a modern digital space that encourages knowledge sharing and brings communities together through literature.

# Table of Contents
- [Overview](#overview)
- [What is Alexandria?](#what-is-alexandria)
- [About 4900](#about-4900)
- [Inspiration](#inspiration)
- [Features](#features)
- [Screenshots](#screenshots)
- [Development Process](#development-process)
- [Directory Structure](#directory-structure)
- [Installation Steps](#installation-steps)
- [Progress](#progress)
- [Future Plans](#future-plans)
- [License](#license)

# Overview
Alexandria is an open-source platform that allows users to:
- Discover new books
- Write and read reviews
- Engage in discussions
- Track reading progress

Our goal is to build a vibrant community where book enthusiasts can connect and share their love for reading.

# What is Alexandria?
Alexandria is a monolithic full-stack application with the following architecture:
- **Frontend**: Developed with **Next.js** and **React**, supporting SSR (server-side rendering) and client-side interactivity
- **Backend**: Built using **Django (Python)** and **TypeScript**-based services for future extensions
- **Database**: Powered by **PostgreSQL** for relational data management
- **Authentication**: django-allauth (email + password, email verification, password reset) using Django sessions

# About 4900
**CISC 4900**, Independent and Group Projects, tasked us with creating a large-scale project which would test the skills we’ve honed during our tenure at Brooklyn College. We were also encouraged to select projects that address a real-world need or challenge, aiming to make a meaningful contribution to the community or industry. The three of us have been working together on projects for a year now, and we take all of our classes together.  Collaborating on CISC 4900 was a natural extension of our ongoing teamwork, providing us with an opportunity to tackle a complex, impactful project that draws on our collective knowledge and experience. Under the leadership of our project supervisor, Professor Priyanka Samanta, and Advisors Allen Lapid and Kathrine Chaung, we set out to build a project that not only showcased our technical capabilities but also addressed a meaningful gap in how readers discover and organize books online. Our goal was to design a platform that reimagines digital book discovery, one that balances user-friendly design with powerful backend architecture, grounded in real user needs and scalable engineering.

# Inspiration
The name and purpose of Alexandria draw inspiration from the **ancient Library of Alexandria**, a historical symbol of collective human knowledge and culture exchange. We aim to create a digital counterpart where readers come together, not just to consume books, but to engage with others and build community.

# Features
- **Book Discovery** - Search through over 28 million books provided by the Open Library API. Browse our Discover page to find curated shelves and personalized recommendations
- **Review System** - Read and write book reviews to share opinions and see what others in the community are saying
- **Book Clubs** - Join or create private/public book clubs to share reads, host discussions, and connect with readers with similar interests
- **Reading Tracker** - Track your current reads, finished books, and total time spent reading
- **User Profiles** - Edit your profile, upload avatars, and showcase your reading stats
- **Secure Authentication** - Powered by django-allauth with cookie-based sessions and CSRF protection
- **Responsive UI** - A sleek and modern interface built with Next.js and TailwindCSS that works across desktop and mobile devices

# Screenshots
![Homepage](https://raw.githubusercontent.com/Mnajm6201/Alexandria/main/public/screenshots/welcomepage_1.png)

![Homepage](https://raw.githubusercontent.com/Mnajm6201/Alexandria/main/public/screenshots/welcomepage_2.png)

![Homepage](https://raw.githubusercontent.com/Mnajm6201/Alexandria/main/public/screenshots/welcomepage_3.png)

![Homepage](https://raw.githubusercontent.com/Mnajm6201/Alexandria/main/public/screenshots/welcomepage_4.png)


# Development Process
Our development follwed modern engineering practices modeled after industry standards:
- **TDD (Test-Driven Development)** - We wrote unit tests before implementing features to ensure each component met functional requirements from the outset.
- **SCRUM** - We used SCRUM methodology with defined sprint cycles, sprint planning, retrospectives, and daily check-ins
- **White Box Testing** - We validated the internal logic and structure of functions and services via unit and integration testing
- **Black Box Testing** - We ensured frontend features, APIs, and user flows matched functional specifications 
- **JIRA Board** - We organized our project using a SCRUM-style JIRA board with sprint backlogs, task breakdowns, and story point estimation

# Directory Structure
```bash
alexandria/
├── backend/                         # Django REST API backend
│   ├── accounts/                    # User account models, auth, serializers
│   ├── api/                         # Shared backend API interfaces
│   ├── bookclubs/                   # Book club models, views, endpoints
│   ├── config/                      # Django settings and configurations
│   ├── discovery/                   # Logic for homepage discoverable content
│   ├── entity_pages/                # General-purpose entity rendering (e.g. authors, editions)
│   ├── journals/                    # User journals and entries
│   ├── library/                     # Core data models and relationships
│   ├── logs/                        # Application and audit logs
│   ├── media/                       # Media uploads (e.g., user avatars)
│   ├── reviews/                     # Book review models and logic
│   ├── search/                      # Search endpoints and result ranking
│   ├── shelves/                     # User and featured shelves
│   ├── staticfiles/                 # Static asset configuration
│   ├── userbooks/                   # User-book relationships (reading status, progress)
│   ├── .env.local                   # Environment variables for local dev
│   ├── config.py                    # WSGI/ASGI configuration
│   └── requirements.txt             # Python dependencies

├── frontend/                        # Next.js 14 frontend
│   ├── public/                      # Static files (images, icons, screenshots)
│   │   └── screenshots/             # App screenshots for README
│   ├── src/
│   │   ├── app/                     # Route-level Next.js pages (App Router)
│   │   │   ├── book/                # Book detail routes
│   │   │   ├── club/                # Book club routes
│   │   │   ├── community/           # Community-facing features
│   │   │   ├── discovery/           # Homepage discovery content
│   │   │   ├── edition/             # Edition detail pages
│   │   │   ├── profile/             # User profile and stats
│   │   │   ├── search/              # Search results and filters
│   │   │   ├── shelf/               # Individual shelf routes
│   │   │   └── shelves/             # All shelves listing and browsing
│   │   ├── components/              # Reusable UI components
│   │   │   ├── auth/                # Sign-in / sign-up form components
│   │   │   ├── club/                # Club cards, join buttons, etc.
│   │   │   ├── layout/              # Shared layout wrappers
│   │   │   ├── profiles/            # User profile modules
│   │   │   └── ui/                  # Button, form, modal, and utility components
│   │   └── globals.css              # Global styles
│   ├── .next/                       # Build artifacts (ignored)
│   └── package.json                 # Frontend dependencies and scripts

├── docs/                            # Documentation and Markdown files
├── scripts/                         # Optional utility and setup scripts
├── .gitignore
└── README.md
```

# Installation Steps
### Prerequisites
- Node.js 20+
- Python 3.12+
- PostgreSQL 14+

### Backend
```bash
cd backend
python -m venv .venv
.venv/Scripts/activate        # Windows (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
cp .env.example .env          # then fill in your Postgres password
createdb alexandria           # or: psql -U postgres -c "CREATE DATABASE alexandria;"
python manage.py migrate
python manage.py seed_books   # loads the shared book catalog (no network needed)
python manage.py runserver
```

`seed_books` loads `backend/library/fixtures/seed_books.json`, so everyone has the same books, editions, authors and Discover shelves. It is safe to re-run; `--clear` wipes the catalog first. To build a fresh catalog from Open Library, run `python manage.py build_seed_data` and commit the updated JSON.

Publication years: a book's `year_published` is when it was *first* published, and each edition's `publication_year` is that printing's own year. Every importer works the original year out the same way, in `backend/library/utils/publication_year.py`: from the years all of the book's editions came out on Open Library, ignoring single misdated editions. To correct the years of books already in your database, run `python manage.py fix_publication_years --dry-run` to preview, then without `--dry-run` to apply.

### Looking at the data
- **Django admin:** http://localhost:8000/admin/. Give your account access with `python manage.py shell -c "from library.models import User; User.objects.filter(email='you@example.com').update(is_staff=True, is_superuser=True)"`, then log in with your username and password.
- **pgAdmin 4** (installed with PostgreSQL on Windows): connect to `localhost:5432`, user `postgres`, and open `alexandria → Schemas → public → Tables`.

### Frontend
```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:3000. The frontend forwards `/api`, `/_allauth` and `/media` to Django on port 8000 (see `frontend/next.config.ts`), so no frontend environment variables are needed for local development.

### Accounts in local development
Sign up at `/auth/sign-up`. Verification and password-reset emails are printed in the Django server's terminal; open the link from there. To skip verification locally, set `ACCOUNT_EMAIL_VERIFICATION=none` in `backend/.env`.

# Progress

So far, we've accomplished:
- Session-based auth with django-allauth
-

# Future Plans
- Mobile-first PWA or native app version
- ML-based book recommendation engine using collaborative filtering
- Admin dashboard with club/user analytics
- Internationalization and localization support
- Docker-based deployment and CI/CD setup