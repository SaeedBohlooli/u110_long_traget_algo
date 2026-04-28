import logging

logger = logging.getLogger(__name__)

def has_open_position(application_state, symbol):
    for p in application_state.get("app_positions",[]):
        if p["symbol"] == symbol:
            return True

    return False

