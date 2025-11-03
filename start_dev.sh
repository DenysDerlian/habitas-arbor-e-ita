#!/bin/bash
# Habitas Development Environment Startup Script
# This script starts both TailwindCSS watcher and Django server

echo "🚀 Starting Habitas Development Environment..."
echo ""

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
HABITAS_DIR="$SCRIPT_DIR/habitas"
JSTOOLCHAIN_DIR="$HABITAS_DIR/jstoolchain"

# Add conda node to PATH
export PATH="$HOME/anaconda3/envs/habitasVenv/bin:$PATH"

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down services..."
    kill $TAILWIND_PID 2>/dev/null
    kill $DJANGO_PID 2>/dev/null
    echo "✅ Services stopped"
    exit 0
}

# Trap Ctrl+C
trap cleanup SIGINT SIGTERM

# Start TailwindCSS watcher
echo "📦 Starting TailwindCSS watcher..."
cd "$JSTOOLCHAIN_DIR"
npx tailwindcss -i ../input.css -o ../static/css/output.css --watch > /tmp/tailwind.log 2>&1 &
TAILWIND_PID=$!
echo "   ✅ TailwindCSS running (PID: $TAILWIND_PID)"
echo ""

# Wait a moment for TailwindCSS to start
sleep 2

# Start Django server
echo "🌐 Starting Django development server..."
cd "$HABITAS_DIR"
/bin/python3 manage.py runserver &
DJANGO_PID=$!
echo "   ✅ Django running (PID: $DJANGO_PID)"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 Habitas is ready!"
echo ""
echo "📍 Application: http://localhost:8000/"
echo "🔧 Admin Panel: http://localhost:8000/admin/"
echo ""
echo "Press Ctrl+C to stop all services"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Wait for both processes
wait $DJANGO_PID $TAILWIND_PID
