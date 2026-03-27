import gzip
import json
import html
import psycopg
import struct
from flask import Flask, Response, request
from collections import OrderedDict
import time

app = Flask(__name__)

DB_CONFIG = {
    "host": "localhost",
    "port": 9876,
    "dbname": "lego-db",
    "user": "lego",
    "password": "bricks",
}

CACHE_SIZE = 100
cache = OrderedDict()


class Database:
    def __init__(self):
        self.conn = None
        self.cur = None

    def execute_and_fetch_all(self, query, params=None):
        self.conn = psycopg.connect(**DB_CONFIG)
        self.cur = self.conn.cursor()
        self.cur.execute(query, params or ())
        return self.cur.fetchall()

    def close(self):
        if self.cur:
            self.cur.close()
        if self.conn:
            self.conn.close()


def write_string(buf, s):
    data = s.encode("utf-8")
    buf += struct.pack("<I", len(data))
    buf += data
    return buf


def get_sets_html(db):
    rows = db.execute_and_fetch_all(
        "select id, name from lego_set order by id"
    )

    row_parts = []
    for row in rows:
        html_safe_id = html.escape(row[0])
        html_safe_name = html.escape(row[1])

        row_parts.append(
            f'<tr><td><a href="/set?id={html_safe_id}">{html_safe_id}</a></td>'
            f'<td>{html_safe_name}</td></tr>\n'
        )

    return "".join(row_parts)


def get_set_json(db, set_id):
    rows = db.execute_and_fetch_all("""
        select id, name, year, category, preview_image_url
        from lego_set
        where id = %s
    """, (set_id,))

    if not rows:
        return json.dumps({"error": f"No set found with id: {set_id}"}, indent=4)

    set_id_db, name, year, category, preview_image_url = rows[0]

    inventory_rows = db.execute_and_fetch_all("""
        select
            i.brick_type_id,
            i.color_id,
            b.name,
            b.preview_image_url,
            i.count
        from lego_inventory i
        join lego_brick b
          on b.brick_type_id = i.brick_type_id
         and b.color_id = i.color_id
        where i.set_id = %s
        order by i.brick_type_id, i.color_id
    """, (set_id,))

    inventory = [
        {
            "brick_type_id": r[0],
            "color_id": r[1],
            "name": r[2],
            "preview_image_url": r[3],
            "count": r[4],
        }
        for r in inventory_rows
    ]

    result = {
        "id": set_id_db,
        "name": name,
        "year": year,
        "category": category,
        "preview_image_url": preview_image_url,
        "inventory": inventory,
    }

    return json.dumps(result, indent=4)


def get_set_binary(db, set_id):
    rows = db.execute_and_fetch_all("""
        select id, name, year, category, preview_image_url
        from lego_set
        where id = %s
    """, (set_id,))

    if not rows:
        return None

    set_id_db, name, year, category, preview_image_url = rows[0]

    inventory_rows = db.execute_and_fetch_all("""
        select
            i.brick_type_id,
            i.color_id,
            b.name,
            b.preview_image_url,
            i.count
        from lego_inventory i
        join lego_brick b
          on b.brick_type_id = i.brick_type_id
         and b.color_id = i.color_id
        where i.set_id = %s
        order by i.brick_type_id, i.color_id
    """, (set_id,))

    buf = b""
    buf += b"LEGO"
    buf += struct.pack("<B", 1)

    buf = write_string(buf, set_id_db)
    buf = write_string(buf, name)
    buf += struct.pack("<I", year)
    buf = write_string(buf, category)
    buf = write_string(buf, preview_image_url)

    buf += struct.pack("<I", len(inventory_rows))

    for r in inventory_rows:
        brick_type_id, color_id, bname, img_url, count = r

        buf = write_string(buf, brick_type_id)
        buf += struct.pack("<I", color_id)
        buf = write_string(buf, bname)
        buf = write_string(buf, img_url)
        buf += struct.pack("<I", count)

    return buf


@app.route("/")
def index():
    with open("templates/index.html") as f:
        template = f.read()
    return Response(template)


@app.route("/sets")
def sets():
    encoding_param = request.args.get("encoding", "utf-8").lower()
    encoding = encoding_param if encoding_param in ("utf-8", "utf-16") else "utf-8"

    with open("templates/sets.html") as f:
        template = f.read()

    charset_meta = '<meta charset="UTF-8">' if encoding == "utf-8" else ""
    template = template.replace("{CHARSET_META}", charset_meta)

    db = Database()
    try:
        rows = get_sets_html(db)
    finally:
        db.close()

    page_html = template.replace("{ROWS}", rows)

    encoded = page_html.encode(encoding)
    compressed = gzip.compress(encoded)

    return Response(
        compressed,
        content_type=f"text/html; charset={encoding}",
        headers={
            "Content-Encoding": "gzip",
            "Cache-Control": "public, max-age=60"
        },
    )


@app.route("/set")
def legoSet():
    with open("templates/set.html") as f:
        template = f.read()
    return Response(template)


@app.route("/api/set")
def apiSet():
    set_id = request.args.get("id")
    start_time = time.time()

    if not set_id:
        return Response(json.dumps({"error": "Missing required query parameter: id"}), status=400)

    if set_id in cache:
        result = cache.pop(set_id)
        cache[set_id] = result
        elapsed_ms = (time.time() - start_time) * 1000
        print(f"CACHE HIT for {set_id}: {elapsed_ms:.2f}ms")
        return Response(json.dumps(result, indent=4), content_type="application/json")

    db = Database()
    try:
        result_str = get_set_json(db, set_id)
        result = json.loads(result_str)
    finally:
        db.close()

    elapsed_ms = (time.time() - start_time) * 1000
    print(f"CACHE MISS for {set_id}: {elapsed_ms:.2f}ms")

    if len(cache) >= CACHE_SIZE:
        cache.popitem(last=False)

    cache[set_id] = result

    return Response(result_str, content_type="application/json")


@app.route("/api/set_binary")
def apiSetBinary():
    set_id = request.args.get("id")

    if not set_id:
        return Response(b"Missing id", status=400)

    db = Database()
    try:
        result = get_set_binary(db, set_id)
    finally:
        db.close()

    if result is None:
        return Response(b"Not found", status=404)

    return Response(result, content_type="application/octet-stream")


if __name__ == "__main__":
    app.run(port=5000, debug=True)
