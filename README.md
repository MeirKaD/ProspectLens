# Person Qualification System

This project consists of a FastAPI backend and a React frontend for qualifying persons based on their name and event details.

## Project Structure

- `backend/` - FastAPI application that interfaces with the qualification agent
- `frontend/` - React application built with Vite
- `run_app.sh` - Script to run both backend and frontend servers

## Setup

### Backend

1. Navigate to the backend directory:

```bash
cd backend
```

2. Install the required dependencies (preferably in a virtual environment):

```bash
pip install -r requirements.txt
```

3. Run the FastAPI server:

```bash
python app.py
```

The backend server will run on http://localhost:8000.

### Frontend

1. Navigate to the frontend directory:

```bash
cd frontend
```

2. Install the required dependencies:

```bash
npm install
```

3. Run the development server:

```bash
npm run dev
```

The frontend server will run on http://localhost:3000.

## Running Both Servers

You can use the provided script to run both servers simultaneously:

```bash
./run_app.sh
```

## API Endpoints

- `POST /api/qualify` - Submit a person's name and event details for qualification

## Features

- Submit a person's name for qualification
- Provide event details and requirements
- View qualification results including score, reasoning, and information sources
- Dynamic form for adding multiple event requirements