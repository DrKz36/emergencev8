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

# HTML part (second base64 section)
html_part = parts[2].split(b'--===============')[0]
decoded_html = base64.b64decode(html_part.strip()).decode('utf-8')

print("=" * 80)
print("EMAIL HTML CONTENT (searching for enriched sections)")
print("=" * 80)

# Search for key sections
sections_to_find = [
    "Analyse de Patterns",
    "Erreurs Détaillées",
    "Code Suspect",
    "Commits Récents",
    "error_patterns",
    "errors_detailed",
    "KeyError",
    "stack_trace"
]

for section in sections_to_find:
    if section in decoded_html:
        print(f"✅ Found: {section}")
        # Show context
        idx = decoded_html.find(section)
        context = decoded_html[max(0, idx-100):min(len(decoded_html), idx+200)]
        print(f"   Context: ...{context}...")
        print()
    else:
        print(f"❌ NOT FOUND: {section}")

print()
print("=" * 80)
print("Checking specific data fields:")
print("=" * 80)

# Check for specific data that should be there
if "Logs analysés: 0" in decoded_html:
    print("❌ Logs analyzés shows 0 (should be 120)")
else:
    print("✅ Logs analysés not showing 0")

if "Erreurs: 0" in decoded_html or "Erreurs Détectées</div>" in decoded_html:
    print("❌ Errors shows 0 (should be 8)")
else:
    print("✅ Errors not showing 0")

# Save HTML to file for inspection
with open('email_html_output.html', 'w', encoding='utf-8') as f:
    f.write(decoded_html)
print()
print("💾 Full HTML saved to: email_html_output.html")
