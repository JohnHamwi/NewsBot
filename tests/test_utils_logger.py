from src.utils.logger import logger
import pytest
from src.utils.logger import BotLogger
from unittest.mock import MagicMock

def test_logger_methods_exist():
    assert hasattr(logger, 'debug')
    assert hasattr(logger, 'info')
    assert hasattr(logger, 'error')

def test_botlogger_command_and_metrics():
    logger = BotLogger()
    logger.logger = MagicMock()
    logger.command('testcmd', 1.23)
    metrics = logger.get_metrics()
    assert 'command_count' in metrics
    assert metrics['command_usage']['testcmd'] == 1
    assert 'command_latencies' in metrics
    assert 'testcmd' in metrics['command_latencies']

def test_botlogger_error_and_critical():
    logger = BotLogger()
    logger.logger = MagicMock()
    logger.error('errormsg', context='ctx')
    logger.critical('critmsg', context='ctx')
    assert logger.error_count == 2 