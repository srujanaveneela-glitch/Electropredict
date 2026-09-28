import sqlite3

conn = sqlite3.connect("instance/electropredict.db")
conn.row_factory = sqlite3.Row
rows = conn.execute(
    "SELECT id, brand, name, category, image_url FROM products ORDER BY id"
).fetchall()
for row in rows:
    print(f"{row['id']} | {row['brand']} | {row['name']} | {row['category']} | {row['image_url']}")
print("TOTAL:", len(rows))
conn.close()