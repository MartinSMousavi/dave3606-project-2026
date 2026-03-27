import gzip
import json
import html
import struct
import psycopg
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

MAGIC_NUMBER = 0x4C45474F  # "LEGO" in ASCII
VERSION = 0x01


def encode_string(s):
    """Encode a string as length-prefixed UTF-8 bytes"""
    if s is None:
        s = ""
    encoded = s.encode('utf-8')
    return struct.pack('>H', len(encoded)) + encoded


def write_binary_set(set_data, inventory):
    """Write Lego set data to binary format"""
    buffer = bytearray()
    

    buffer.extend(struct.pack('>I', MAGIC_NUMBER))
    buffer.extend(struct.pack('>B', VERSION))
    buffer.extend(struct.pack('>B', 0))
    buffer.extend(struct.pack('>H', len(inventory))) 
    
    buffer.extend(encode_string(set_data['id']))
    buffer.extend(encode_string(set_data['name']))
    buffer.extend(struct.pack('>i', set_data.get('year', 0) or 0))
    buffer.extend(encode_string(set_data.get('category', '')))
    buffer.extend(encode_string(set_data.get('preview_image_url', '')))
    
    for brick in inventory:
        buffer.extend(encode_string(brick['brick_type_id']))
        buffer.extend(struct.pack('>i', brick['color_id']))
        buffer.extend(encode_string(brick.get('name', '')))
        buffer.extend(encode_string(brick.get('preview_image_url', '')))
        buffer.extend(struct.pack('>Q', brick.get('count', 0) or 0))
    
    return bytes(buffer)


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
    format_type = request.args.get("format", "json").lower()

    if not set_id:
        error = {"error": "Missing required query parameter: id"}
        return Response(json.dumps(error, indent=4), status=400, content_type="application/json")

    if format_type == "binary":
        return get_binary_set(set_id)

    return get_json_set(set_id)


def get_binary_set(set_id):
    """Fetch Lego set data and return as binary format"""
    cache_key = f"{set_id}:binary"
    if cache_key in cache:
        print("CACHE HIT (binary)")
        result = cache.pop(cache_key)
        cache[cache_key] = result
        binary_data = result if isinstance(result, bytes) else write_binary_set(result['set'], result['inventory'])
        return Response(
            binary_data,
            content_type="application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="{set_id}.lgo"',
                "Cache-Control": "public, max-age=60"
            }
        )

    conn = psycopg.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, name, year, category, preview_image_url
                FROM lego_set
                WHERE id = %s
            """, (set_id,))
            row = cur.fetchone()

            if row is None:
                error = {"error": f"No set found with id: {set_id}"}
                return Response(json.dumps(error, indent=4), status=404, content_type="application/json")

            set_id_db, name, year, category, preview_image_url = row

            cur.execute("""
                SELECT
                    i.brick_type_id,
                    i.color_id,
                    b.name,
                    b.preview_image_url,
                    i.count
                FROM lego_inventory i
                JOIN lego_brick b
                  ON b.brick_type_id = i.brick_type_id
                 AND b.color_id = i.color_id
                WHERE i.set_id = %s
                ORDER BY i.brick_type_id, i.color_id
            """, (set_id,))
            inventory_rows = cur.fetchall()

    finally:
        conn.close()

    set_data = {
        "id": set_id_db,
        "name": name,
        "year": year,
        "category": category,
        "preview_image_url": preview_image_url,
    }

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

    binary_data = write_binary_set(set_data, inventory)

    print("CACHE MISS (binary)")
    cache_key = f"{set_id}:binary"
    if len(cache) >= CACHE_SIZE:
        cache.popitem(last=False)
    
    cache[cache_key] = binary_data

    return Response(
        binary_data,
        content_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{set_id}.lgo"',
            "Cache-Control": "public, max-age=60"
        }
    )


def get_json_set(set_id):
    """Original JSON endpoint logic"""
    if set_id in cache:
        print("CACHE HIT (json)")
        result = cache.pop(set_id)
        cache[set_id] = result
        return Response(json.dumps(result, indent=4), content_type="application/json")

    conn = psycopg.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, name, year, category, preview_image_url
                FROM lego_set
                WHERE id = %s
            """, (set_id,))
            row = cur.fetchone()

            if row is None:
                error = {"error": f"No set found with id: {set_id}"}
                return Response(json.dumps(error, indent=4), status=404, content_type="application/json")

            set_id_db, name, year, category, preview_image_url = row

            cur.execute("""
                SELECT
                    i.brick_type_id,
                    i.color_id,
                    b.name,
                    b.preview_image_url,
                    i.count
                FROM lego_inventory i
                JOIN lego_brick b
                  ON b.brick_type_id = i.brick_type_id
                 AND b.color_id = i.color_id
                WHERE i.set_id = %s
                ORDER BY i.brick_type_id, i.color_id
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

    print("CACHE MISS (json)")
    if len(cache) >= CACHE_SIZE:
        cache.popitem(last=False)

    cache[set_id] = result

    return Response(json.dumps(result, indent=4), content_type="application/json")


if __name__ == "__main__":
    app.run(port=5000, debug=True)
