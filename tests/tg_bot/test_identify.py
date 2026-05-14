#!/usr/bin/env python
import requests
import json

url = 'http://localhost:8000/api/bot/identify/'
params = {'tg_id': 123456789}

try:
    response = requests.get(url, params=params)
    print(f'Status Code: {response.status_code}')
    print(f'Response Headers: {response.headers}')
    print(f'Response Body: {response.text}')
    if response.status_code == 200:
        data = response.json()
        print('\nParsed JSON:')
        print(json.dumps(data, indent=2, ensure_ascii=False))
except Exception as e:
    print(f'Error: {e}')