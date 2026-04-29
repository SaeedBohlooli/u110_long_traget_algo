import logging
from trading_utils import date_utils
logger = logging.getLogger(__name__)

def scan(app_config, application_state, symbol, df):

    if not application_state.get("user_input", {}).get("trader_enabled", True):
        logger.info(f"[scan], symbol: {symbol}, trader_enabled is False, skip scanning.")
        return

    for side in ['long', 'short']:
        result = True
        for condition in app_config.get('entry_conditions', {}).get(side,[]):
            res_condition = eval(condition)
            if not res_condition:
                result = False
                break

        if result:
            logger.info(f"[scan], symbol: {symbol}, side: {side}, passed all conditions, res_condition: {res_condition}")
            d = {
                "symbol": symbol,
                "side": side,
                "res_condition": res_condition,
                "unique_run_number": application_state.get("unique_run_number"),
                'candle_date': str(df['date'].iloc[-1]),
                'timestamp': date_utils.time_now_yyyy_mm_dd_hh_mm_ss(),
                'status': 'NEW'

            }
            application_state.setdefault("scanner_result",[]).append(d )
            application_state.setdefault("entry_signals",[]).append(d )
            application_state["scanner_result"] = application_state["scanner_result"][-30:] # cut to last 30 ...


