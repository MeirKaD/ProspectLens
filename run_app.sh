#!/bin/bash

# Start the FastAPI backend server
echo "Starting FastAPI backend server..."
cd "$(dirname "$0")/backend"
python app.py &
BACKEND_PID=$!

# Wait a moment for the backend to start
sleep 2

# Start the Vite frontend development server
echo "Starting Vite frontend development server..."
cd "$(dirname "$0")/frontend"
npm run dev &
FRONTEND_PID=$!

# Function to handle script termination
cleanup() {
  echo "Shutting down servers..."
  kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
  exit 0
}

# Set up trap to catch termination signals
trap cleanup SIGINT SIGTERM

echo "Both servers are running!"
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo "Press Ctrl+C to stop both servers"

# Keep the script running
wait