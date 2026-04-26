import logging
import pandas as pd
from trading_utils import streaming_util
logger = logging.getLogger(__name__)
from pprint import pformat


def josnify_dfs_for_websocket(app_config, market_data):
    output_map = {}
    for symbol, value in market_data.data_store.items():
        if not isinstance(value, pd.DataFrame):
            # Keep non-DataFrame payloads untouched (e.g., already-jsonized maps).
            output_map[symbol] = value
            if app_config.get('debug'):
                logger.info(f"Skipping date serialization for non-DataFrame key '{symbol}' ({type(value).__name__})")
            continue

        df = value
        # Serialize `date` values to plain strings before JSON conversion.
        df_for_stream = df.copy()
        if app_config.get('debug'):
            logger.info(f"df_for_stream ({symbol}) preview:\n{df_for_stream.tail(3).to_markdown()}")

        if 'date' in df_for_stream.columns:
            parsed_dates = pd.to_datetime(df_for_stream['date'], errors='coerce')
            formatted_dates = parsed_dates.dt.strftime('%Y-%m-%d %H:%M:%S')
            df_for_stream['date'] = formatted_dates.where(
                parsed_dates.notna(),
                df_for_stream['date'].astype(str)
            )

        output_map[symbol] = streaming_util.convert_df_to_dic_for_stream(df_for_stream)

    # if app_config.get('debug'):
    #     logger.info(f"output_map: {pformat(output_map)}")
    return output_map
