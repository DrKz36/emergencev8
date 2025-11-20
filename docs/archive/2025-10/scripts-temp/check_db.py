import sqlite3

conn = sqlite3.connect("instance/emergence.db")
cursor = conn.cursor()

print("=== DATABASE ANALYSIS ===\n")

# Count messages
cursor.execute("SELECT COUNT(*) FROM messages")
print(f"Total Messages: {cursor.fetchone()[0]}")

# Count costs
cursor.execute("SELECT COUNT(*) FROM costs")
print(f"Total Cost Entries: {cursor.fetchone()[0]}")

# Costs by model
cursor.execute(
    "SELECT model, COUNT(*), SUM(total_cost), SUM(input_tokens), SUM(output_tokens) FROM costs GROUP BY model"
)
print("\nCosts by Model:")
for row in cursor.fetchall():
    model, count, total_cost, input_tokens, output_tokens = row
    print(
        f"  {model}: {count} entries, ${total_cost:.6f}, {input_tokens} input tokens, {output_tokens} output tokens"
    )

# Recent costs
cursor.execute(
    "SELECT timestamp, model, total_cost, input_tokens, output_tokens FROM costs ORDER BY timestamp DESC LIMIT 5"
)
print("\nRecent Cost Entries:")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]} - ${row[2]:.6f} ({row[3]} in, {row[4]} out)")

# Check messages by period (today, week, month)
cursor.execute("""
    SELECT
        COUNT(*) as total,
        SUM(CASE WHEN date(timestamp) = date('now') THEN 1 ELSE 0 END) as today,
        SUM(CASE WHEN date(timestamp) >= date('now', '-7 days') THEN 1 ELSE 0 END) as week,
        SUM(CASE WHEN date(timestamp) >= date('now', '-30 days') THEN 1 ELSE 0 END) as month
    FROM messages
""")
result = cursor.fetchone()
print("\nMessages by Period:")
print(f"  Total: {result[0]}")
print(f"  Today: {result[1]}")
print(f"  This Week: {result[2]}")
print(f"  This Month: {result[3]}")

# Check sessions
cursor.execute("SELECT COUNT(*) FROM sessions")
print(f"\nTotal Sessions: {cursor.fetchone()[0]}")

# Check documents
cursor.execute("SELECT COUNT(*) FROM documents")
print(f"Total Documents: {cursor.fetchone()[0]}")

conn.close()
