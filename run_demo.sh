#!/bin/bash

echo "🚀 AI Compliance & Risk Orchestrator - Demo Setup"
echo "=================================================="

# Check if in correct directory
if [ ! -f "requirements.txt" ]; then
    echo "❌ Please run this script from the project root directory"
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Create necessary directories
mkdir -p logs temp

echo "🏁 Starting Demo..."
echo ""
echo "This will run 3 demo scenarios:"
echo "1. Normal compliant decision (no HITL)"
echo "2. Workflow with 2 HITL interruptions"
echo "3. Insufficient evidence after timeout"
echo ""

# Function to check if server is running
check_server() {
    curl -s http://localhost:8000 > /dev/null 2>&1
    return $?
}

# Start server in background
echo "🖥️  Starting server..."
cd server
python3 main.py &
SERVER_PID=$!
cd ..

# Wait for server to be ready
echo "⏳ Waiting for server to start..."
for i in {1..10}; do
    if check_server; then
        echo "✅ Server is ready!"
        break
    fi
    sleep 2
    if [ $i -eq 10 ]; then
        echo "❌ Server failed to start"
        kill $SERVER_PID 2>/dev/null
        exit 1
    fi
done

# Run demo scenarios
echo ""
echo "🎬 Running demo scenarios..."
python3 demo/demo_scenarios.py

# Cleanup
echo ""
echo "🧹 Cleaning up..."
kill $SERVER_PID 2>/dev/null

echo "✅ Demo completed!"
echo ""
echo "📚 To explore more:"
echo "• View logs in the logs/ directory"
echo "• Check the README.md for full documentation"
echo "• Run individual components for testing"