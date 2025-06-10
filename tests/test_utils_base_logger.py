from src.utils.base_logger import base_logger
import logging

def test_base_logger_is_logger():
    assert isinstance(base_logger, logging.Logger) 