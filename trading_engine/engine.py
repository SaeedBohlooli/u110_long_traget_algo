from trading_core.trading_ledger import TradingLedger
from trading_utils import *
import logging
logger = logging.getLogger(__name__)
import sys
sys.path.insert(0, f'../')

from trading_core.ws_server import WSServer
from trading_core.file_manager import FileManager
from trading_core.streamers.state_streamer import StateStreamer
from trading_core.streamers.config_streamer import ConfigStreamer
from trading_core.streamers.open_trades_streamer import OpenTradesStreamer
from trading_core.streamers.contract_strikes_streamer import ContractStrikesStreamer
from trading_core.streamers.quote_cache_streamer import QuoteCacheStreamer
from trading_core.ib_connector import IBConnector
from trading_core.market_data_store import MarketDataStore
from trading_core import market_session_guard
from trading_core import application_state_router
from trading_core import trading_ledger
from trading_core import ib_heartbeat_loop
from trading_core import engine_cycle
from trading_core import user_request_loop

# from trading_engine import marketdata_helper
from trading_engine import indicator_helper
from trading_engine import json_helper
# from trading_engine import strategy
from trading_engine import application_state_helper
from trading_engine import marketdata_helper
# from trading_engine import scanner
# from trading_engine import pricing_helper
# from trading_engine import options_helper
# from trading_engine import order_helper
# from trading_engine import exit_conditions
# from trading_engine import chart_helper
# from trading_engine import position_helper
# from trading_engine import pnl_helper
from trading_engine import user_request_helper
from trading_engine import scanner_helper
from trading_engine import order_helper
from trading_engine import position_helper



from trading_utils import position_router
from trading_utils import indicators_util


class TradingEngine:

    def __init__(self, boot):
        self.boot = boot
        self.logger = boot.logger
        self.app_config = boot.app_config
        self.application_state = boot.application_state
        self.ws = WSServer(host="0.0.0.0", port=self.app_config.get('ws_port', 6666))
        self.runtime = boot.runtime
        self.market_data = MarketDataStore()


    async def do_miscs(self, ib, app_config, application_state, interval_sec=60):
        while True:
            try:
                if engine_cycle.should_exit(application_state=application_state):
                    logger.info("[do_miscs] Exiting as requested.")
                    break
                application_state_router.populate_global_state(application_state=self.application_state)
                if self.runtime.is_due("populate_ib_account_info", interval_sec=60 * 1):
                    await populate_ib_account_info(ib, application_state, app_config.get("ib_account_id", ""))

            except Exception as e:
                logger.warning(f"@@@ Unexpected error in do_miscs: {e}")
                logger.error(f"@@@ error: {traceback.format_exc()}" )
            await asyncio.sleep(interval_sec)

    async def engine_loop(self, ib):
        run_number = 0
        await application_state_helper.initialize_application_state(ib, self.app_config, self.application_state)

        while True:
            try:
                start_time = time.time()
                run_number += 1
                current_hh_mm_ny = self.runtime.now_hhmm()
                unique_run_number_X =  self.runtime.generate_unique_run_number(run_number)
                day_of_week = self.runtime.now_day_of_week()
                symbol_number = 0
                logger.info(f"[engine] ==================== run_number: {run_number}, unique_run_number_X: {unique_run_number_X}")
                self.runtime.reload_runtime_config()
                application_state_helper.initialize_application_state_for_run(self.app_config, self.application_state)

                if engine_cycle.should_exit(application_state=self.application_state):
                    logger.info("[market_session_guard_loop] Exiting as requested.")
                    break

                if ib is None:
                    logger.warning("[engine] ib is None... so give a try to reconnect ...")
                    await asyncio.sleep(3)
                    continue

                self.app_config = self.runtime.reload_config()

                for entry in self.application_state.get('user_input', {}).get('entries', []):
                    symbol = entry.get('symbol')
                    time_frame = entry.get('time_frame')
                    quantity = entry.get('quantity')

                    symbol_number += 1
                    unique_run_number = f'{unique_run_number_X}-{symbol_number}'
                    self.application_state['unique_run_number'] = unique_run_number
                    logger.warning(f"[engine] ------------------- {symbol}, {unique_run_number}, {current_hh_mm_ny} ")
                    symbol_start_time = time.time()

                    application_state_helper.initialize_application_state_for_symbol_run(self.app_config, self.application_state)

                    if self.runtime.is_due(f'GET_NEAREST_FUTURE_CONTRACT_MONTH-{symbol}'):
                        contract_month = await ib_contract.get_nearest_future_contract_month(ib, symbol)
                        if contract_month is None:
                            logger.warning(f"@@@@@ {symbol}, no nearest future contract month found, skip the symbol for now ...")
                            continue
                        self.application_state.setdefault('contract_months',{})[symbol] = contract_month
                    if self.application_state.get('contract_months').get(symbol) is None:
                        # not good one ...
                        continue
                    contract_month = self.application_state.get('contract_months')[symbol]
                    if self.runtime.is_due(f'SUBSCRIBE_PRICE-{symbol}', interval_sec=3):
                        current_price = await ib_pricing_async.get_or_subscribe_symbol_price(ib, symbol, contract_month)
                        if current_price is None:
                            current_price = -1.0
                        self.application_state.setdefault('latest_prices', {})[symbol] = current_price

                    logger.info(f"[engine] Starting get_historical_data for {symbol}, {contract_month}")
                    df = await marketdata_helper.get_historical_data(ib, symbol, contract_month, self.app_config, self.application_state, time_frame=time_frame)
                    logger.info(f"[engine] Finished get_historical_data for {symbol}")
                    if df is None or len(df) ==0:
                        logger.warning(f"[engine] @@@@@ {symbol}, no data found, skip the symbol for now ...")
                        continue

                    df = indicators_util.compute_technical_indicators(self.app_config, self.application_state, symbol, df)

                    self.application_state.get('results').get('result_pad')[symbol] = {
                            'symbol': symbol,
                            'update_timestamp': date_utils.time_now_yyyy_mm_dd_hh_mm_ss(),
                            'quantity': quantity,
                            'time_frame': time_frame,
                            'current_price': current_price,
                        }
                    df = df[-30:]
                    self.market_data.data_store[symbol] = df

                    scanner_helper.scan(self.app_config, self.application_state, symbol, df)
                    await order_helper.send_order(self.app_config, self.application_state, ib)
                    await position_helper.check_exit_condition(self.app_config, self.application_state, ib, self.market_data)


                dfs_jsonized = json_helper.josnify_dfs_for_websocket(self.app_config, self.market_data)
                self.market_data.data_store['dfs_jsonized'] = dfs_jsonized


                # application_state_router.add_audit_message(self.application_state, str('time'))

                end_time = time.time()
                run_time_spent = round(end_time - start_time, 2)
                logger.warning(f"[engine] ==================== unique_run_number: {unique_run_number}, run_spent_time: {run_time_spent} seconds, sleep ... {self.app_config['interval_seconds']['engine_loop']}")
                self.application_state.setdefault("run_times", {})['engine_loop_run_time_spent'] = run_time_spent

            except Exception as e:
                logger.warning(f"@@@ Unexpected error in engine_loop: {e}")
                logger.error(f"@@@ error: {traceback.format_exc()}" )
                application_state_router.add_audit_message(self.application_state, str(e))

            await asyncio.sleep(self.app_config['interval_seconds']['engine_loop'])

    async def do_streem_loop(self, interval_sec=1):
        while True:
            try:
                if engine_cycle.should_exit(application_state=self.application_state):
                    logger.info("[do_streem_loop] Exiting as requested.")
                    break
                wl = self.market_data.data_store.get("dfs_jsonized", {})
                logger.info(f"[do_stream_loop] started streaming ...")
                if wl:
                    packet = {
                        "type": "dfs_jsonized",
                        "timestamp": time.time(),
                        "data": wl
                    }
                    await self.ws.broadcast(packet)
                logger.info(f"[do_stream_loop] finished streaming ...")

            except Exception as e:
                logger.warning(f"Unexpected error in spx_price_stream_loop: {e}")
            await asyncio.sleep(interval_sec)


    async def run(self):
        logger.info("Starting Trading Engine")
        ib = await IBConnector.connect_from_config(self.app_config)

        ws_server = await self.ws.start()

        # Keep existing application_state cadence unchanged unless explicitly configured.
        state_interval_sec = self.app_config.get("interval_seconds", {}).get("application_state_streamer", 1)
        state_streamer = StateStreamer(self.app_config, self.application_state, self.ws, interval_sec=state_interval_sec)
        config_streamer = ConfigStreamer(self.app_config, self.application_state, self.ws, interval_sec=60)




        self.logger.info("WebSocket server is starting...")

        await asyncio.gather(
            ws_server,
            state_streamer.run(),
            config_streamer.run(),
            self.engine_loop(ib),
            self.do_miscs(ib, self.app_config, self.application_state, interval_sec=60),
            self.do_streem_loop(interval_sec=3),
            # user_request_x.user_request_loop(self.app_config, self.application_state),
            self.boot.data_saver_manager.run(ib, interval_sec=60),
            user_request_loop.fetch_user_request_loop(self.app_config, self.application_state, interval_sec=5),
            user_request_loop.process_common_user_request_loop(ib, self.app_config, self.application_state,interval_sec=5),
            user_request_helper.process_app_user_request_loop(ib, self.app_config, self.application_state,interval_sec=1),

            ib_heartbeat_loop.ib_heartbeat_loop(ib, app_config=self.app_config,application_state=self.application_state, interval_seconds=60),
        )

