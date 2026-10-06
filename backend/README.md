# Rakthasethu Backend API

FastAPI backend service for Rakthasethu, an intelligent blood donation management and donor-matching platform.

---

## 1. Database Setup Options

The backend database connection is entirely driven by the `DATABASE_URL` environment variable. Developers may choose either **Docker PostgreSQL** (recommended for quick isolation) or **Native PostgreSQL**.

### Option A: Docker PostgreSQL Setup (Recommended)
Run the isolated PostgreSQL 16 container from the project root:
```bash
# From project root (c:\Users\ASUS\Desktop\rakthasethu)
docker compose up -d
```
* **Container Name:** `rakthasethu-postgres`
* **Host Port:** `5433` (mapped to internal container port `5432` to avoid conflicts)
* **Database Name:** `rakthasethu`
* **Persistent Volume:** `rakthasethu_postgres_data`

In `backend/.env`:
```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5433/rakthasethu
```

### Option B: Native PostgreSQL Setup
If you run PostgreSQL directly on your host machine:
1. Create the database:
   ```sql
   CREATE DATABASE rakthasethu;
   ```
2. Configure `backend/.env` with your local port (typically `5432`):
   ```env
   DATABASE_URL=postgresql+asyncpg://postgres:<your_password>@localhost:5432/rakthasethu
   ```

> **Note for Team Members:** Application code never hardcodes ports. The database port and credentials always come directly from `DATABASE_URL`.

---

## 2. Environment Setup

### 1. Python Environment
```bash
# Navigate to backend directory
cd backend

# Create & activate virtual environment (Python 3.12+)
python -m venv .venv
.venv\Scripts\activate   # Windows
# or: source .venv/bin/activate  # Linux/macOS

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables
```bash
copy .env.example .env   # Windows
# or: cp .env.example .env # Linux/macOS
```

---

## 3. Verify Database Connection

Run the included verification script to confirm database reachability:
```bash
python verify_db.py
```
Expected output:
```text
Testing connection to: localhost:5433/rakthasethu
[SUCCESS] Connected to PostgreSQL!
Database Name: rakthasethu
User:          postgres
Version:       PostgreSQL 16.x...
```

---

## 4. Run Development Server

```bash
uvicorn app.main:app --reload --port 8000
```

* **Health Check:** `http://127.0.0.1:8000/health`
* **Interactive API Docs (Swagger):** `http://127.0.0.1:8000/docs`
