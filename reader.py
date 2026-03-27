import struct
import sys


def read_string(f):
    length_bytes = f.read(4)
    if not length_bytes:
        raise EOFError("Unexpected end of file")

    length = struct.unpack("<I", length_bytes)[0]

    data = f.read(length)
    return data.decode("utf-8")


def read_lego_file(filename):
    with open(filename, "rb") as f:
        magic = f.read(4)
        version = struct.unpack("<B", f.read(1))[0]

        if magic != b"LEGO":
            print("Invalid file format!")
            return

        print("=== LEGO BINARY FILE ===")
        print(f"Magic: {magic}")
        print(f"Version: {version}")

        set_id = read_string(f)
        name = read_string(f)
        year = struct.unpack("<I", f.read(4))[0]
        category = read_string(f)
        preview = read_string(f)

        print("\n=== SET INFO ===")
        print(f"ID: {set_id}")
        print(f"Name: {name}")
        print(f"Year: {year}")
        print(f"Category: {category}")
        print(f"Preview URL: {preview}")

        item_count = struct.unpack("<I", f.read(4))[0]

        print(f"\n=== INVENTORY ({item_count} items) ===")

        for i in range(item_count):
            brick_type_id = read_string(f)
            color_id = struct.unpack("<I", f.read(4))[0]
            brick_name = read_string(f)
            image_url = read_string(f)
            count = struct.unpack("<I", f.read(4))[0]

            print(f"\nItem #{i+1}")
            print(f"  Brick Type ID: {brick_type_id}")
            print(f"  Color ID: {color_id}")
            print(f"  Name: {brick_name}")
            print(f"  Image URL: {image_url}")
            print(f"  Count: {count}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python reader.py <binary_file>")
        sys.exit(1)

    filename = sys.argv[1]

    try:
        read_lego_file(filename)
    except Exception as e:
        print("Error reading file:", e)
