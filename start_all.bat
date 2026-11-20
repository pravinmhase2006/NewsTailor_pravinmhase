@echo off
echo ===================================================
echo Starting NewsTailor Full-Stack Services
echo ===================================================

echo [1/3] Starting Python ML Engine on port 8000...
start cmd /k "cd ml_engine && python -m uvicorn api_service:app --port 8000 --reload"

echo [2/3] Starting Node.js Backend API on port 5000...
start cmd /k "cd backend && npm start"

echo [3/3] Starting React Frontend on port 3000...
start cmd /k "cd frontend && npm run dev"

echo All services launched!
echo Open your browser at: http://localhost:3000
