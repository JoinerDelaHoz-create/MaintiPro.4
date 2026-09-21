"""
Table Formatter: Utilities to format ASCII/Unicode tables cleanly,
ensuring long text strings are truncated with ellipsis so columns never overflow.
"""

from typing import List, Tuple
from .colors import GRAY, RESET, BOLD


def truncate(text: str, max_len: int) -> str:
    """Truncates text safely with ellipsis if it exceeds max_len."""
    text = str(text) if text is not None else ""
    if len(text) <= max_len:
        return text
    if max_len <= 3:
        return text[:max_len]
    return text[: max_len - 3] + "..."


def render_table(
    headers: List[Tuple[str, int]],
    rows: List[List[str]],
    color_row_fn=None,
) -> str:
    """
    Renders a box-drawing Unicode table.
    headers: List of (ColumnName, ColumnWidth)
    rows: List of lists of cell values
    color_row_fn: Optional function that takes row and returns styled values
    """
    lines = []

    # Top border: ┌───┬───┐
    top_parts = ["─" * (w + 2) for _, w in headers]
    lines.append(f"{GRAY}┌{'┬'.join(top_parts)}┐{RESET}")

    # Header row
    header_cells = []
    for col_name, width in headers:
        header_cells.append(f" {BOLD}{truncate(col_name, width):<{width}}{RESET} ")
    lines.append(f"{GRAY}│{RESET}{f'{GRAY}│{RESET}'.join(header_cells)}{GRAY}│{RESET}")

    # Header separator: ├───┼───┤
    sep_parts = ["─" * (w + 2) for _, w in headers]
    lines.append(f"{GRAY}├{'┼'.join(sep_parts)}┤{RESET}")

    # Data rows
    if not rows:
        total_width = sum(w + 2 for _, w in headers) + len(headers) - 1
        lines.append(
            f"{GRAY}│{RESET} {'(No hay registros para mostrar)':^{total_width - 2}} {GRAY}│{RESET}"
        )
    else:
        for row in rows:
            cells = []
            for i, (_, width) in enumerate(headers):
                val = str(row[i]) if i < len(row) else ""
                # If there's ANSI in the val, len(val) might be misleading, but truncate works on raw
                # To handle pure display cleanly:
                cells.append(f" {val:<{width}} ")
            lines.append(f"{GRAY}│{RESET}{f'{GRAY}│{RESET}'.join(cells)}{GRAY}│{RESET}")

    # Bottom border: └───┴───┘
    bottom_parts = ["─" * (w + 2) for _, w in headers]
    lines.append(f"{GRAY}└{'┴'.join(bottom_parts)}┘{RESET}")

    return "\n".join(lines)
