from pathlib import Path
from typing import Union


def write_to_file(file_path: Union[str, Path], content: str, *, overwrite: bool = True) -> None:
    """Write *content* to *file_path*.

    If *overwrite* is ``False`` and *file_path* already exists, a
    ``FileExistsError`` is raised to prevent accidental data loss.

    Parameters
    ----------
    file_path : str | Path
        Destination path.
    content : str
        Text to write (UTF-8 encoded).
    overwrite : bool, default ``True``
        Whether to replace the file if it already exists.
    """
    path = Path(file_path).expanduser().resolve()
    if path.exists() and path.is_dir():
        raise IsADirectoryError(f"Cannot write to a directory: {path}")
    if path.exists() and not overwrite:
        raise FileExistsError(f"File already exists and overwrite=False: {path}")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
