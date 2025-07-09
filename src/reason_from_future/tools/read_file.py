from pathlib import Path
from typing import Union


def read_file(file_path: Union[str, Path]) -> str:
    """Return the text contents of *file_path*.

    Parameters
    ----------
    file_path : str | Path
        Path to the file that should be read.  Relative paths are resolved
        against the current working directory.

    Returns
    -------
    str
        Entire contents of the file as a UTF-8 string.

    Raises
    ------
    FileNotFoundError
        If *file_path* does not exist.
    IsADirectoryError
        If *file_path* refers to a directory instead of a file.
    """
    path = Path(file_path).expanduser().resolve()

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if path.is_dir():
        raise IsADirectoryError(f"Expected a file but found directory: {path}")

    return path.read_text(encoding="utf-8")
