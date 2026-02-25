# SakhiSetu Frontend

React frontend for the SakhiSetu Women Government Scheme Navigator.

## Setup

```bash
cd frontend
npm install
```

## Run

```bash
npm run dev
```

Opens at **http://localhost:5173**. The dev server proxies `/api` to the backend at `http://localhost:8000`.

## Build

```bash
npm run build
npm run preview  # Preview production build
```

## Prerequisites

Start the FastAPI backend first:

```bash
cd ..
uvicorn app.main:app --reload --port 8000
```
