#!/bin/bash

# Login and get token
echo "Logging in..."
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"test@test.com\",\"password\":\"test1234\"}" \
  | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
  echo "Failed to get token"
  exit 1
fi

echo "Got token: ${TOKEN:0:20}..."
echo ""
echo "Fetching style box allocation..."
echo ""

# Call style box endpoint
curl -s http://localhost:8000/api/v1/holdings/style-box \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -m json.tool
