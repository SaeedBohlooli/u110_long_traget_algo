
import logging
logger = logging.getLogger(__name__)

from trading_engine import position_helper
from trading_utils import ib_orders_async
from trading_utils import ib_contract

async def send_order(app_config, application_state, ib):

    for entry in application_state.get('screening_result', []):
        symbol = entry.get('symbol')
        side = entry.get('side')
        if position_helper.has_open_position(application_state, symbol):
            logger.info(f"send_order: Skipping order for {symbol} as there is already an open position.")
            continue
        order_ref = ib_orders_async.generate_order_ref(application_state.get('portfolio_id', {}),
                                                       event='OPEN',
                                                       symbol=symbol,
                                                       side=side,
                                                       unique_run_number=application_state.get('unique_run_number')
                                                       )
        contract = await ib_contract.get_cached_contract(ib, symbol)
        quantity = find_quantity_from_user_input(application_state, symbol)
        trade = await ib_orders_async.submit_option_order_prequalified_contract(ib, side=side, order_ref=order_ref, q_contract=contract, total_quantity=quantity)
        d = {
            'symbol': symbol,
            'side': side,
            'order_ref': order_ref,
            'status': 'OPEN_SUBMITTED',
            'quantity': quantity,
        }
        application_state.setdefault('app_positions',[]).append(d)



def find_quantity_from_user_input(application_state, symbol):
    for entry in application_state.get('user_input', {}).get('entries', []):
        if entry.get('symbol') == symbol:
            return entry.get('quantity', 0)

    return 0