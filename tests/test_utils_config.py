from src.utils.config import Config
import os

def test_config_debug_mode():
    assert isinstance(Config.DEBUG_MODE, bool)

def test_config_status_structure():
    status = Config.get_config_status()
    assert isinstance(status, dict)

def test_get_config_status():
    status = Config.get_config_status()
    assert isinstance(status, dict)
    assert 'discord_token' in status

def test_get_guild_id():
    gid = Config.get_guild_id()
    assert isinstance(gid, int)

def test_is_admin():
    admin_id = Config.ADMIN_ROLE_ID
    if admin_id:
        assert Config.is_admin([admin_id])
        assert not Config.is_admin([0])

def test_get_channel_id():
    for t in ['news', 'errors', 'log']:
        cid = Config.get_channel_id(t)
        assert cid is None or isinstance(cid, int) 