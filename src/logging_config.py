import logging
from pathlib import Path

from src.ingestion.loader import PROJECT_ROOT


def configure_logging(
    log_file: Path | str | None = None,
    level: int = logging.INFO,
) -> None:
    path = Path(log_file) if log_file is not None else PROJECT_ROOT / "logs" / "ecommerce_pipeline.log"
    path.parent.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    if not any(
        isinstance(handler, logging.FileHandler)
        and Path(handler.baseFilename) == path.resolve()
        for handler in root_logger.handlers
    ):
        file_handler = logging.FileHandler(path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    if not any(
        isinstance(handler, logging.StreamHandler)
        and not isinstance(handler, logging.FileHandler)
        for handler in root_logger.handlers
    ):
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        root_logger.addHandler(stream_handler)
