#!/bin/bash
cd /Users/sharathcgeorge/projects/whos-bombing-who

# Install dependencies if needed
pip3 install -q -r requirements.txt 2>/dev/null

# Open browser after a short delay
(sleep 2 && open http://localhost:5001) &

# Start the server
python3 app.py
