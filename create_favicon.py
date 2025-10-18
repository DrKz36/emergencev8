#!/usr/bin/env python3
"""Generate favicon.ico from emergence_logo.png"""

from PIL import Image

print("Création favicon.ico depuis emergence_logo.png...")

# Charger le logo
img = Image.open('assets/emergence_logo.png')

# Redimensionner en plusieurs tailles pour le .ico (16x16, 32x32, 48x48)
sizes = [(16, 16), (32, 32), (48, 48)]
icons = []

for size in sizes:
    resized = img.resize(size, Image.Resampling.LANCZOS)
    icons.append(resized)

# Sauvegarder en tant que .ico multi-résolution
icons[0].save('favicon.ico', format='ICO', sizes=[(16,16), (32,32), (48,48)], append_images=icons[1:])

print("✅ favicon.ico créé avec succès!")
print("   Tailles: 16x16, 32x32, 48x48")
