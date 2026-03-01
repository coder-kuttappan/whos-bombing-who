#!/bin/bash
cd /Users/sharathcgeorge/projects/whos-bombing-who

# Install dependencies if needed
pip3 install -q -r requirements.txt 2>/dev/null

# Generate conflict data
python3 generate.py

# Open browser and serve locally
(sleep 1 && open http://localhost:8000) &
python3 -m http.server 8000
