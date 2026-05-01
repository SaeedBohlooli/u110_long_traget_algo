import asyncio
import logging
import traceback
from trading_core import engine_cycle
from trading_utils import date_utils

logger = logging.getLogger(__name__)

def process_user_requests(app_config, application_state):
    for user_request in application_state.get('user_requests', []):
        request_type = user_request.get('request_type', '')
        if 'ENGINE_PROCESSED' in user_request.get('status', ''):
            continue
        logger.info(f"[process_user_requests] Processing user request: {user_request}")
        if request_type.upper() == 'ADD_TO_USER_INPUT':
            user_request['status'] += '|ENGINE_PROCESSED'
            symbol = user_request.get('symbol', '')
            quantity = user_request.get('quantity', 0)
            time_frame = user_request.get('time_frame', '')

            application_state.setdefault('user_input', {}).setdefault('entries', []).append({
                'symbol': symbol,
                'quantity': quantity,
                'time_frame': time_frame,
                'web_request_id': user_request.get('web_request_id', '')})
        elif request_type.upper() == 'SET_TRADER_ENABLED':
            user_request['status'] += '|ENGINE_PROCESSED'
            application_state.setdefault('user_input', {})['trader_enabled'] = True
        elif request_type.upper() == 'SET_TRADER_DISABLED':
            user_request['status'] += '|ENGINE_PROCESSED'
            application_state.setdefault('user_input', {})['trader_enabled'] = False
        elif request_type.upper() == 'REMOVE_FROM_USER_INPUT':
            user_request['status'] += '|ENGINE_PROCESSED'
            symbol = user_request.get('symbol', '')
            for x in application_state.get("user_input", {}).get("entries", []):
                if x.get('symbol') == symbol:
                    logger.info(f"[process_user_requests] Removing from user input: {user_request}")
                    application_state.get('user_input').get('entries').remove(x)
                    break
            for s, x in application_state.get("results", {}).get("result_pad", {}).items():
                if s == symbol:
                    logger.info(f"[process_user_requests] Removing from results_pad: {user_request}")
                    application_state.get('results').get('result_pad').pop(s, None)
                    break

async def process_app_user_request_loop(ib, app_config, application_state, interval_sec=5):
    while True:
        try:
            if engine_cycle.should_exit(application_state=application_state):
                logger.info("[process_app_user_request_loop] Exiting as requested.")
                break
            process_user_requests(app_config, application_state)
            logger.info("[process_app_user_request_loop]...")
            await asyncio.sleep(interval_sec)
        except Exception as e:
            logger.warning(f"[process_app_user_request_loop] @@@  Unexpected error: {e}")
            logger.error(f"[process_app_user_request_loop] @@@ error: {traceback.format_exc()}" )
            await asyncio.sleep(interval_sec)