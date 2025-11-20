import sqlite3

conn = sqlite3.connect("data/emergence.db")
cursor = conn.cursor()

print("=== DATABASE ANALYSIS ===\n")

# Count costs
cursor.execute("SELECT COUNT(*) FROM costs")
total_costs = cursor.fetchone()[0]
print(f"Total costs: {total_costs}")

# Count messages
cursor.execute("SELECT COUNT(*) FROM messages")
total_messages = cursor.fetchone()[0]
print(f"Total messages: {total_messages}")

if total_costs > 0:
    # Costs by model
    cursor.execute(
        "SELECT model, COUNT(*), SUM(total_cost), SUM(input_tokens), SUM(output_tokens) FROM costs GROUP BY model"
    )
    print("\nCosts by model:")
    for row in cursor.fetchall():
        model, count, cost, inp, out = row
        print(f"  {model}: {count} entries, ${cost:.6f}, {inp} in, {out} out")

    # Recent costs
    cursor.execute(
        "SELECT timestamp, model, total_cost, input_tokens, output_tokens FROM costs ORDER BY timestamp DESC LIMIT 5"
    )
    print("\nRecent costs:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} - ${row[2]:.6f} ({row[3]} in, {row[4]} out)")
else:
    print("\nWARNING: No costs recorded!")
    print("This means cost_tracker.record_cost() is NOT being called.")

conn.close()
