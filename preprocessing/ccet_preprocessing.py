# -*- coding: utf-8 -*-
"""
Created on Tue Sep 22 10:50:54 2020

@author: Jonas Freißmann
"""

from os.path import abspath, join
import pandas as pd
from scipy.interpolate import interp1d

output = True
# output = False

dir_path = abspath(join(__file__, '../..'))
read_path = join(dir_path, 'Eingangsdaten', 'ccet_parameters.csv')

params = pd.read_csv(read_path, sep=';', index_col=0)

index = [*range(65, 125)]

interp_params = pd.DataFrame({'T_VL': index})
interp_params.set_index('T_VL', inplace=True)


for col in params.columns:
    interpolation = interp1d(params.index, params[col], kind='cubic',
                             fill_value='extrapolate')

    param_list = list()
    for idx in index:
        param_list += [interpolation(idx)]

    interp_params[col] = param_list

read_path = join(dir_path, "Eingangsdaten",
                 "district-heating-network-data-flensburg-2016.csv")
data = pd.read_csv(read_path)

data['Datetime'] = pd.to_datetime(data['Datetime'], format='%d/%m/%y %H:%M')

col_names = ['Datum', 'T_VL', 'T_RL', 'Last']
data.columns = col_names

data.set_index('Datum', inplace=True)

tvl_list = data['T_VL'].apply(lambda x: int(x)).to_list()

P_max_woDH = list()
P_min_woDH = list()
eta_el_max = list()
eta_el_min = list()
H_L_FG_share_max = list()
Q_CW_min = list()
Q_in = list()
beta = list()

interp_timeseries = pd.DataFrame()

for col in interp_params.columns:
    param_list = list()
    for T in tvl_list:
        param_list += [interp_params.loc[T, col]]
    interp_timeseries[col] = param_list

if output:
    simdata_path = join(dir_path, "Eingangsdaten\\simulation_data.csv")
    simdata = pd.read_csv(simdata_path, sep=";")

    for col in interp_timeseries:
        simdata[col + '_ccet'] = interp_timeseries[col]

    simdata.to_csv(simdata_path, sep=";", index=False)
