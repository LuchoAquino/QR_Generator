# QR Generator Backend API

FastAPI backend application for generating and tracking QR codes. It supports both SQLite for local development and PostgreSQL for production deployments.

## Features
- QR Code generation and tracking
- Analytics: Total scans and daily breakdown (last 30 days)
- RESTful API documentation automatically generated via Swagger UI
- Support for persistent PostgreSQL databases (e.g. Supabase)

## Requirements
- Python 3.9+
- See `requirements.txt` for specific dependencies

## Local Development setup

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/Scripts/activate  # Windows
   # source venv/bin/activate  # macOS/Linux
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the development server:
   ```bash
   uvicorn main:app --reload --port 8001
   ```
   The API will be available at `http://localhost:8001`.
   You can view the Swagger UI documentation at `http://localhost:8001/docs`.

## Environment Variables

The backend uses a `.env` file for configuration. 

```env
# Database connection string (defaults to local SQLite if omitted)
# For Supabase/PostgreSQL, use: postgresql://postgres:[PASSWORD]@[HOST]:6543/postgres
DATABASE_URL=sqlite:///./qr_tracker.db

# Base URL used for the QR tracking redirects
# Useful for making the QR codes scannable over a LAN or on a production domain
BASE_URL=http://localhost:8001
```

## Production Deployment (Render)
This backend is fully compatible with Render's free tier. Make sure to set the `Start Command` in Render to:
```bash
uvicorn main:app --host 0.0.0.0
```
Also, ensure the `BASE_URL` matches your `.onrender.com` domain, and provide a PostgreSQL connection string for persistence.
