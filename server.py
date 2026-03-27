import gzip
import json
import html
import psycopg
import struct
from flask import Flask, Response, request
from collections import OrderedDict

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


def write_string(buf, s):
    data = s.encode("utf-8")
    buf += struct.pack("<I", len(data))
    buf += data
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

    if encoding == "utf-8":
        charset_meta = '<meta charset="UTF-8">'
    else:
        charset_meta = ""
    template = template.replace("{CHARSET_META}", charset_meta)

    row_parts = []
    conn = psycopg.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute("select id, name from lego_set order by id")
            for row in cur.fetchall():
                html_safe_id = html.escape(row[0])
                html_safe_name = html.escape(row[1])
                row_parts.append(
                    f'<tr><td><a href="/set?id={html_safe_id}">{html_safe_id}</a></td>'
                    f'<td>{html_safe_name}</td></tr>\n'
                )
    finally:
        conn.close()

    rows = "".join(row_parts)
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

    if not set_id:
        error = {"error": "Missing required query parameter: id"}
        return Response(json.dumps(error, indent=4), status=400, content_type="application/json")

    if set_id in cache:
        print("CACHE HIT")
        result = cache.pop(set_id)
        cache[set_id] = result
        return Response(json.dumps(result, indent=4), content_type="application/json")

    conn = psycopg.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:

            cur.execute("""
                select id, name, year, category, preview_image_url
                from lego_set
                where id = %s
            """, (set_id,))
            row = cur.fetchone()

            if row is None:
                error = {"error": f"No set found with id: {set_id}"}
                return Response(json.dumps(error, indent=4), status=404, content_type="application/json")

            set_id_db, name, year, category, preview_image_url = row

            cur.execute("""
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
            inventory_rows = cur.fetchall()

    finally:
        conn.close()

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

    print("CACHE MISS")
    if len(cache) >= CACHE_SIZE:
        cache.popitem(last=False)

    cache[set_id] = result

    return Response(json.dumps(result, indent=4), content_type="application/json")


@app.route("/api/set_binary")
def apiSetBinary():
    set_id = request.args.get("id")

    if not set_id:
        return Response(b"Missing id", status=400)

    conn = psycopg.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:

            cur.execute("""
                select id, name, year, category, preview_image_url
                from lego_set
                where id = %s
            """, (set_id,))
            row = cur.fetchone()

            if row is None:
                return Response(b"Not found", status=404)

            set_id_db, name, year, category, preview_image_url = row

            cur.execute("""
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
            inventory_rows = cur.fetchall()

    finally:
        conn.close()

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

    return Response(buf, content_type="application/octet-stream")


if __name__ == "__main__":
    app.run(port=5000, debug=True)
