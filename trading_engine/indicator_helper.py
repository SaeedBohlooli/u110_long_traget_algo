import logging
logger = logging.getLogger(__name__)


def populate_features(symbol, df, app_config, market_data):
    df = df[-30:]
    for label, indic in app_config.get('indicators', []).items():
        nam = indic['name']
        formula = indic['formula']
        exec(formula, {'df': df})

    market_data.data_store[symbol] = df

    if app_config.get('debud'):
        logger.info(f"[populate_features] {df[-3:].to_markdown()}")
    return df