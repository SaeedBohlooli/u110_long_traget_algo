import logging
from trading_utils import ib_positions_async
from trading_utils import ib_orders_async
from trading_utils import date_utils

logger = logging.getLogger(__name__)

def has_open_position(application_state, symbol):
    for p in application_state.get("app_positions",[]):
        if p["symbol"] == symbol:
            return True

    return False


async def check_exit_condition(app_config, application_state, ib, market_data):
    needs_to_be_removed = []
    for p in application_state.get("app_positions",[]):
        symbol = p["symbol"]
        side = p["side"]

        df = market_data.data_store.get(symbol)
        if df is None or df.empty:
            logger.info(f"[check_exit_condition] @@ No market data for symbol: {symbol}, skipping exit condition check.")
            continue

        open_candle_date = p["open_candle_date"]
        result = True
        for condition in app_config.get('exit_conditions', {}).get(side,[]):
            res_condition = eval(condition)
            if not res_condition:
                result = False
                break

        if not application_state.get("user_input").get("trader_enabled", True):
            logger.info(f"[check_exit_condition] Trader is disabled by user input, so closing all positions.")
            result = True

        if result:
            logger.info(f"[check_exit_condition] Exit conditions met for symbol: {symbol}, side: {side}")
            order_ref = ib_orders_async.generate_order_ref(application_state["portfolio_id"],
                                                           event="CLOSE",
                                                           symbol=symbol,
                                                           unique_run_number=application_state["unique_run_number"],
                                                           side=side)
            contract_id = p['contract_id']
            close_timestamp = date_utils.time_now_yyyy_mm_dd_hh_mm_ss()
            close_result = ib_positions_async.close_position_by_con_id(ib, symbol=symbol, side=side,
                                                                       con_id = contract_id, order_ref=order_ref, exchange="CME")
            if close_result:
                p["close_timestamp"] = close_timestamp
                p["close_candle_date"] = str(df["date"].iloc[-1])
                p["close_order_ref"] = order_ref
                p["status"] = "CLOSE_SENT"
                needs_to_be_removed.append(p)
            else:
                logger.warning(f"[check_exit_condition] Failed to close position for symbol: {symbol}, side: {side}")

        for p in needs_to_be_removed:
            application_state["app_positions"].remove(p)
            application_state.setdefault("app_positions_archive", []).append(p)

    if application_state.get("app_positions_archive"):
        application_state["app_positions_archive"] = application_state["app_positions_archive"][-60:]