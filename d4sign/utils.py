import re
from pathlib import Path


UUID_PATTERN = re.compile(
    r"[0-9a-fA-F]{8}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{12}"
)

PDF_HEADER = b"%PDF-"


def extract_uuid(value: str | None) -> str | None:

    if not value:
        return None

    match = UUID_PATTERN.search(value)

    return match.group(0) if match else None


def valid_uuid(value: str | None) -> bool:

    if not value:
        return False

    return bool(
        UUID_PATTERN.fullmatch(
            value.strip()
        )
    )


def sanitize_filename(name: str) -> str:

    if not name:
        return "SEM_NOME"

    name = name.strip()

    name = re.sub(
        r'[<>:"/\\|?*\x00-\x1f]',
        "_",
        name,
    )

    name = re.sub(
        r"\s+",
        " ",
        name,
    )

    name = name.rstrip(" .")

    return name[:180] or "SEM_NOME"


def is_pdf(path: Path) -> bool:

    if not path.exists():
        return False

    try:

        if path.stat().st_size < 5:
            return False

        with path.open("rb") as file:
            return file.read(5) == PDF_HEADER

    except OSError:
        return False