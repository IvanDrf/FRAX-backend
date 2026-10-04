from uuid import uuid4


def generate_file_name(ext: str) -> str:
    ext = ext if ext.startswith(".") else "." + ext

    return f"{uuid4()}{ext}"
