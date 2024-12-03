import pandas as pd
import numpy as np

def generate_new_features(X):

    if isinstance(X, np.ndarray):
        X = pd.DataFrame(X, columns=['year', 'km_driven', 'mileage', 'engine', 'max_power', 'torque', 'seats', 'max_torque_rpm'])

    X_new = X.copy()

    X_new['power_per_liter'] = X_new['max_power'] / X_new['engine']
    X_new['mileage_per_km'] = X_new['mileage'] / X_new['km_driven']

    X_new['year_squared'] = X_new['year'] ** 2

    return X_new

def log_transform(X):
    X_log = X.copy()
    for col in ['km_driven', 'torque', 'max_power']:
        X_log[col] = np.log1p(X_log[col])
    return X_log