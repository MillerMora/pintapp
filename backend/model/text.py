"""Utilidades de texto del dominio."""

import unicodedata


def normalize_text(value: str) -> str:
    """Minúsculas y sin tildes, para comparar 'Café' con 'cafe' o 'CAFÉ'."""
    decomposed = unicodedata.normalize("NFKD", value.strip())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch)).casefold()
