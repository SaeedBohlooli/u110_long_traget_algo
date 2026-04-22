

def populate_features(df, app_config, application_state):

    for indic in app_config.get('indicators', []):
        nam = indic['name']
        formula = indic['formula']
        df[nam] = eval(formula)

    return df