"""
Fix user matching pour dashboard admin
Ajoute colonne oauth_sub et mappe Google OAuth sub → email
"""
import sqlite3
import sys

# Fix Windows encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('data/emergence.db')
cursor = conn.cursor()

print("=" * 60)
print("FIX USER MATCHING - DASHBOARD ADMIN")
print("=" * 60)

# 1. Verifier si colonne oauth_sub existe
cursor.execute('PRAGMA table_info(auth_allowlist)')
cols = [r[1] for r in cursor.fetchall()]

if 'oauth_sub' not in cols:
    print("\n[1/4] Ajout colonne oauth_sub...")
    cursor.execute('ALTER TABLE auth_allowlist ADD COLUMN oauth_sub TEXT')
    conn.commit()
    print("OK - Colonne oauth_sub ajoutee")
else:
    print("\n[1/4] Colonne oauth_sub deja presente")

# 2. Mapper Google OAuth sub -> email
print("\n[2/4] Mapping Google OAuth sub -> email...")
google_sub = "110509120867290606152"  # From sessions table
email = "gonzalefernando@gmail.com"

cursor.execute('UPDATE auth_allowlist SET oauth_sub = ? WHERE email = ?', (google_sub, email))
conn.commit()
print(f"OK - Mappe {google_sub} -> {email}")

# 3. Purger guest sessions
print("\n[3/4] Purge des guest sessions...")
cursor.execute('SELECT COUNT(*) FROM sessions WHERE user_id LIKE "guest:%"')
guest_count = cursor.fetchone()[0]

if guest_count > 0:
    cursor.execute('DELETE FROM sessions WHERE user_id LIKE "guest:%"')
    conn.commit()
    print(f"OK - {guest_count} guest sessions supprimees")
else:
    print("INFO - Aucune guest session a purger")

# 4. Verifier resultat
print("\n[4/4] Verification...")
cursor.execute('SELECT email, oauth_sub FROM auth_allowlist')
for row in cursor.fetchall():
    print(f"  {row[0]} -> oauth_sub: {row[1]}")

cursor.execute('SELECT DISTINCT user_id FROM sessions WHERE user_id IS NOT NULL')
unique_users = [r[0] for r in cursor.fetchall()]
print(f"\nOK - {len(unique_users)} user_id unique(s) dans sessions:")
for uid in unique_users:
    print(f"  - {uid}")

print("\n" + "=" * 60)
print("OK - FIX TERMINE - Redemarrer backend pour appliquer")
print("=" * 60)

conn.close()
