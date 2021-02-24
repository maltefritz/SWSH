# -*- coding: utf-8 -*-
"""
Created on Tue Sep 22 10:50:54 2020

@author: Jonas Freißmann
"""

from os.path import abspath, join
import pandas as pd
from scipy.interpolate import interp1d


def get_sorted_timeseries(data, T_vl):
    """Sort dataset by feed flow temperature.

    Produce timeseries of parameter set sorted by occurance of feed flow
    temperature from dataset.

    Parameters
    ----------
    data: DataFrame with different parameters as columns and T_vl as index
    T_vl: time series (list) of feed flow temperature
    """
    parameter_timeseries = pd.DataFrame()
    for col in data.columns:
        param_list = list()
        for T in T_vl:
            param_list += [data.loc[T, col]]
        parameter_timeseries[col] = param_list

    return parameter_timeseries


def interpolate_missing_values(data, index):
    """Fill missing parameters with interpolated values.

    Parameters
    ----------
    data: DataFrame with different parameters as columns and T_vl as index
    index: list of feed flow temperatures for desired parameters
    """
    interp_data = pd.DataFrame({'T_VL': index})
    interp_data.set_index('T_VL', inplace=True)

    for col in data.columns:
        interpolation = interp1d(data.index, data[col], kind='cubic',
                                 fill_value='extrapolate')

        param_list = list()
        for idx in index:
            param_list += [interpolation(idx)]

        interp_data[col] = param_list

    return interp_data


# %% Input data and parameters
# Define output mode
output_ccet = False
output_ice = True

# Define interpolation mode
interpolate_ccet = True
interpolate_ice = False

# Read in data
dir_path = abspath(join(__file__, '../..'))

# CCET data
read_path = join(dir_path, 'Eingangsdaten', 'ccet_parameters.csv')
params_ccet = pd.read_csv(read_path, sep=';', index_col=0)

# ICE data
read_path = join(dir_path, 'Eingangsdaten', 'ice_parameters_4.28.csv')
params_ice = pd.read_csv(read_path, sep=';', index_col=0)

# Feed flow temperature time series
read_path = join(dir_path, "Eingangsdaten",
                 "district-heating-network-data-flensburg-2016.csv")
data = pd.read_csv(read_path)

data['Datetime'] = pd.to_datetime(data['Datetime'], format='%d/%m/%y %H:%M')
col_names = ['Datum', 'T_VL', 'T_RL', 'Last']
data.columns = col_names
data.set_index('Datum', inplace=True)

tvl_list = data['T_VL'].apply(lambda x: int(x)).to_list()

# %% Data processing
# Interpolate data if desired
index = [*range(65, 125)]

if interpolate_ccet:
    params_ccet = interpolate_missing_values(params_ccet, index)

if interpolate_ice:
    params_ice = interpolate_missing_values(params_ice, index)

# Get sorted time series of parameters
param_ts_ccet = get_sorted_timeseries(params_ccet, tvl_list)

param_ts_ice = get_sorted_timeseries(params_ice, tvl_list)

# %% Data output
if output_ccet or output_ice:
    simdata_path = join(dir_path, "Eingangsdaten\\simulation_data.csv")
    simdata = pd.read_csv(simdata_path, sep=";")

    # CCET output
    if output_ccet:
        for col in param_ts_ccet:
            simdata['CCET_' + col] = param_ts_ccet[col]

    # ICE output
    if output_ice:
        for col in param_ts_ice:
            simdata['ICE_' + col] = param_ts_ice[col]

    simdata.to_csv(simdata_path, sep=";", index=False)
