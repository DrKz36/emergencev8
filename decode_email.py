#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import base64

# Fix encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Read email file
with open(r'C:\Users\Admin\Downloads\🛡️ Guardian ÉMERGENCE - UNKNOWN - 19_10 20_50.eml', 'rb') as f:
    data = f.read()

# Split parts
parts = data.split(b'Content-Transfer-Encoding: base64')

# Text part (first base64 section)
text_part = parts[1].split(b'--===============')[0]
decoded_text = base64.b64decode(text_part.strip()).decode('utf-8')

print("=" * 80)
print("EMAIL TEXT CONTENT (first 3000 chars)")
print("=" * 80)
print(decoded_text[:3000])
print()
print("=" * 80)
