
import logging
logger = logging.getLogger(__name__)

from trading_engine import position_helper
from trading_utils import ib_orders_async
from trading_utils import ib_contract
from trading_utils import date_utils
from trading_core.runtime_manager import RuntimeManager
async def send_order(app_config, application_state, ib):

    for entry in application_state.get('scanner_result', []):
        symbol = entry.get('symbol')
        side = entry.get('side')

        if position_helper.has_open_position(application_state, symbol):
            logger.info(f"[send_order]: Skipping order for {symbol} as there is already an open position.")
            continue

        candle_date = entry.get('candle_date')
        if not RuntimeManager.should_run_once(f"ORDER-SENT-{candle_date}-{symbol}"):
            logger.info(f"[send_order] Skipping order for {symbol} as it has already been sent for candle date {candle_date}.")
            continue

        order_ref = ib_orders_async.generate_order_ref(application_state.get('portfolio_id', {}),
                                                       event='OPEN',
                                                       symbol=symbol,
                                                       side=side,
                                                       unique_run_number=application_state.get('unique_run_number')
                                                       )
        contract_month = application_state.get("contract_months", {}).get(symbol)
        if contract_month is None:
            logger.info(f"[send_order] Skipping order for {symbol} as contract month is not found.")
            continue

        contract = await ib_contract.get_cached_contract(ib, symbol, contract_month=contract_month)
        quantity = find_quantity_from_user_input(application_state, symbol)
        trade = await ib_orders_async.submit_option_order_prequalified_contract(ib, side=side, order_ref=order_ref, q_contract=contract, total_quantity=quantity)
        d = {
            'symbol': symbol,
            'side': side,
            'order_ref': order_ref,
            'status': 'OPEN_SUBMITTED',
            'quantity': quantity,
            'scan_candle_date' : entry.get('candle_date'),
            'scan_timestamp': entry.get('timestamp'),
            'open_unique_run_number': application_state.get('unique_run_number'),
            'open_candle_date': entry.get('candle_date'),
            'open_timestamp': date_utils.time_now_yyyy_mm_dd_hh_mm_ss(),
            'open_order_ref': order_ref,
            'contract_id': contract.conId if contract else None,
        }
        application_state.setdefault('app_positions',[]).append(d)



def find_quantity_from_user_input(application_state, symbol):
    for entry in application_state.get('user_input', {}).get('entries', []):
        if entry.get('symbol') == symbol:
            return entry.get('quantity', 0)

    return 0