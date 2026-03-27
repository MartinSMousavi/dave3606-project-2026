import json
import struct
from server import get_sets_html, get_set_json, get_set_binary


class MockDatabase:
    def __init__(self):
        self.queries = []

    def execute_and_fetch_all(self, query, params=None):
        self.queries.append((query, params))

        if "from lego_set order by id" in query:
            return [
                ("1", "Set One"),
                ("2", "Set Two"),
            ]
        if "from lego_set" in query and "where id" in query:
            return [
                ("1", "Test Set", 2020, "Test Category", "img.png")
            ]

        if "from lego_inventory" in query:
            return [
                ("brick1", 1, "Brick Name", "img2.png", 3),
                ("brick2", 2, "Brick Name 2", "img3.png", 5),
            ]

        return []

    def close(self):
        pass

def test_get_sets_html():
    db = MockDatabase()

    html = get_sets_html(db)

    assert "Set One" in html
    assert "Set Two" in html
    assert '<a href="/set?id=1">' in html

    assert len(db.queries) == 1
    assert "select id, name from lego_set" in db.queries[0][0]



def test_get_set_json():
    db = MockDatabase()

    result_str = get_set_json(db, "1")
    result = json.loads(result_str)

    assert result["id"] == "1"
    assert result["name"] == "Test Set"
    assert result["year"] == 2020

    assert len(result["inventory"]) == 2
    assert result["inventory"][0]["brick_type_id"] == "brick1"
    assert result["inventory"][1]["count"] == 5

    assert len(db.queries) == 2
    assert "from lego_set" in db.queries[0][0]
    assert "from lego_inventory" in db.queries[1][0]

def test_get_set_json_not_found():
    class EmptyDB(MockDatabase):
        def execute_and_fetch_all(self, query, params=None):
            return []

    db = EmptyDB()

    result_str = get_set_json(db, "999")
    result = json.loads(result_str)

    assert "error" in result

def test_get_set_binary():
    db = MockDatabase()

    binary = get_set_binary(db, "1")

    assert binary is not None

    assert binary[:4] == b"LEGO"

    version = struct.unpack("<B", binary[4:5])[0]
    assert version == 1

    assert len(db.queries) == 2



def test_get_set_binary_not_found():
    class EmptyDB(MockDatabase):
        def execute_and_fetch_all(self, query, params=None):
            return []

    db = EmptyDB()

    binary = get_set_binary(db, "999")

    assert binary is None
