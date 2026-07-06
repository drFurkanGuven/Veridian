import logging
import sys

from veridian_api.core.config import Settings


def setup_logging(settings: Settings) -> None:
    level = logging.DEBUG if settings.api_debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        stream=sys.stdout,
        force=True,
    )
    logging.getLogger("uvicorn.access").setLevel(logging.INFO if settings.api_debug else logging.WARNING)
