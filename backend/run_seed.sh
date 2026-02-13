#!/bin/bash
cd /Users/chris/github/ChrisLanks27/nest-egg/backend
source venv/bin/activate 2>/dev/null || true
python scripts/seed_mock_data.py
