import logging

from src.utils.base_logger import base_logger


def test_base_logger_is_logger():
    assert isinstance(base_logger, logging.Logger)
