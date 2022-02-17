# -*- coding: utf-8 -*-
"""
Economical postprocessing for Generic Model energy system.

@author: Malte Fritz & Jonas Freißmann
"""
import pandas as pd
import numpy as np
from oemof.solph import views
from help_funcs import generate_labeldict, result_labelling
from eco_funcs import invest_sol, invest_stes


def postprocessing(results, param, data):
    """
    Perform postprocessing of optimization results.

    Parameters
    ----------
    results : dict of pandas.Series and pandas.DataFrame
        Full results from solph.processing.results() call.

    param : dict
        JSON parameter file of user defined constants.

    data : pandas.DataFrame
        csv file of user defined time dependent parameters.

    """
    data_cost_units = pd.DataFrame()

    data_gnw = views.node(results, 'Gasnetzwerk')['sequences']
    data_enw = views.node(results, 'Elektrizitätsnetzwerk')['sequences']
    data_wnw = views.node(results, 'Wärmenetzwerk')['sequences']
    data_lt_wnw = views.node(results, 'LT-Wärmenetzwerk')['sequences']
    data_wnw_node = views.node(results, 'TES Knoten')['sequences']
    data_sol_node = views.node(results, 'Sol Knoten')['sequences']

    if param['Sol']['active']:
        data_solar_source = views.node(results, 'Solarthermie')['sequences']
        data_cost_units.loc['invest', 'Sol'] = (
            invest_sol(param['Sol']['A'], col_type='flat')
            )
        data_cost_units.loc['op_cost', 'Sol'] = (
            data_solar_source[(('Solarthermie', 'Sol Knoten'), 'flow')].sum()
            * 0.01 * data_cost_units.loc['invest', 'Sol']
            / param['Sol']['A']
            * data['solar_data_' + param['Sol']['usage']].sum()
            )

    if param['EHK']['active']:
        data_cost_units.loc['invest', 'EHK'] = (
            param['EHK']['inv_spez']
            * param['EHK']['Q_N']
            * param['EHK']['amount']
            )

        data_cost_units.loc['op_cost', 'EHK'] = 0
        for i in range(1, param['EHK']['amount']+1):
            label_id = 'Elektroheizkessel_' + str(i)

            data_cost_units.loc['op_cost', 'EHK'] += (
                data_wnw[((label_id, 'Wärmenetzwerk'), 'flow')].sum()
                * param['EHK']['op_cost_var']
                + (param['EHK']['op_cost_fix']
                   * param['EHK']['Q_N'])
                )

    if param['SLK']['active']:
        data_cost_units.loc['invest', 'SLK'] = (
            param['SLK']['inv_spez']
            * param['SLK']['Q_N']
            * param['SLK']['amount']
            )

        data_cost_units.loc['op_cost', 'SLK'] = 0
        for i in range(1, param['SLK']['amount']+1):
            label_id = 'Spitzenlastkessel_' + str(i)

            data_cost_units.loc['op_cost', 'SLK'] += (
                data_wnw[((label_id, 'Wärmenetzwerk'), 'flow')].sum()
                * (param['SLK']['op_cost_var']
                   + param['param']['energy_tax'])
                + (param['SLK']['op_cost_fix']
                   * param['SLK']['Q_N'])
                )

    if param['BHKW']['active']:
        if param['BHKW']['type'] == 'constant':
            ICE_P_max_woDH = param['BHKW']['P_max_woDH']
        elif param['BHKW']['type'] == 'time series':
            ICE_P_max_woDH = data['ICE_P_max_woDH'].mean()

        data_cost_units.loc['invest', 'BHKW'] = (
            ICE_P_max_woDH
            * param['BHKW']['inv_spez']
            * param['BHKW']['amount']
            )

        data_cost_units.loc['op_cost', 'BHKW'] = 0
        for i in range(1, param['BHKW']['amount']+1):
            label_id = 'BHKW_' + str(i)

            data_cost_units.loc['op_cost', 'BHKW'] += (
                data_enw[((label_id, 'Elektrizitätsnetzwerk'), 'flow')].sum()
                * param['BHKW']['op_cost_var']
                + (param['BHKW']['op_cost_fix']
                   * ICE_P_max_woDH)
                )

    if param['GuD']['active']:
        if param['GuD']['type'] == 'constant':
            CCET_P_max_woDH = param['GuD']['P_max_woDH']
        elif param['GuD']['type'] == 'time series':
            CCET_P_max_woDH = data['CCET_P_max_woDH'].mean()

        data_cost_units.loc['invest', 'GuD'] = (
            CCET_P_max_woDH
            * param['GuD']['inv_spez']
            * param['GuD']['amount']
            )

        data_cost_units.loc['op_cost', 'GuD'] = 0
        for i in range(1, param['GuD']['amount']+1):
            label_id = 'GuD_' + str(i)

            data_cost_units.loc['op_cost', 'GuD'] += (
                data_enw[((label_id, 'Elektrizitätsnetzwerk'), 'flow')].sum()
                * param['GuD']['op_cost_var']
                + (param['GuD']['op_cost_fix']
                   * CCET_P_max_woDH)
                )

    if param['HP']['active']:
        if param['HP']['type'] == 'constant':
            HP_Q_N = (param['HP']['c_1']
                      * param['HP']['P_max']
                      + param['HP']['c_0'])
        elif param['HP']['type'] == 'time series':
            HP_Q_N = (data['c_1_hp'].mean()
                      * data['P_max_hp'].mean()
                      + data['c_0_hp'].mean())
        data_cost_units.loc['invest', 'HP'] = (
            param['HP']['inv_spez']
            * data['P_max_hp'].max()
            * HP_Q_N
            * param['HP']['amount']
            )

        data_cost_units.loc['op_cost', 'HP'] = 0
        for i in range(1, param['HP']['amount']+1):
            label_id = 'HP_' + str(i)

            data_cost_units.loc['op_cost', 'HP'] += (
                data_wnw[((label_id, 'Wärmenetzwerk'), 'flow')].sum()
                * param['HP']['op_cost_var']
                + param['HP']['op_cost_fix'] * HP_Q_N
                )

    if param['LT-HP']['active']:
        LT_HP_Q_N = data_wnw[((label_id, 'Wärmenetzwerk'), 'flow')].mean()

        data_cost_units.loc['invest', 'LT-HP'] = 0
        data_cost_units.loc['op_cost', 'LT-HP'] = 0
        for i in range(1, param['LT-HP']['amount']+1):
            label_id = 'LT-HP_' + str(i)

            data_cost_units.loc['invest', 'LT-HP'] += (
                param['HP']['inv_spez'] * LT_HP_Q_N
                )

            data_cost_units.loc['op_cost', 'LT-HP'] += (
                data_wnw[((label_id, 'Wärmenetzwerk'), 'flow')].sum()
                * param['HP']['op_cost_var']
                + param['HP']['op_cost_fix'] * LT_HP_Q_N
                )

    data_tes = pd.DataFrame()
    if param['TES']['active']:
        data_cost_units.loc['invest', 'TES'] = (
            invest_stes(param['TES']['Q'])
            * param['TES']['amount']
            )

        data_cost_units.loc['op_cost', 'TES'] = 0
        for i in range(1, param['TES']['amount']+1):
            label_id = 'TES_' + str(i)
            data_tes = pd.concat(
                [data_tes, views.node(results, label_id)['sequences']], axis=1
                )

            data_cost_units.loc['op_cost', 'TES'] += (
                data_tes[(('TES Knoten', label_id), 'flow')].sum()
                * param['TES']['op_cost_var']
                + (param['TES']['op_cost_fix']
                   * param['TES']['Q'])
                )

    if param['ST-TES']['active']:
        data_cost_units.loc['invest', 'ST-TES'] = (
            invest_stes(param['ST-TES']['Q'])
            * param['ST-TES']['amount']
            )

        data_cost_units.loc['op_cost', 'ST-TES'] = 0
        for i in range(1, param['ST-TES']['amount']+1):
            label_id = 'ST-TES_' + str(i)
            data_tes = pd.concat(
                [data_tes, views.node(results, label_id)['sequences']], axis=1
                )

            data_cost_units.loc['op_cost', 'ST-TES'] += (
                data_tes[(('Wärmenetzwerk', label_id), 'flow')].sum()
                * param['ST-TES']['op_cost_var']
                + (param['ST-TES']['op_cost_fix']
                   * param['ST-TES']['Q'])
                )

    cost_Anlagen = data_cost_units.loc['op_cost'].sum()
    invest_ges = data_cost_units.loc['invest'].sum()

    cost_gas = (data_gnw[(('Gasquelle', 'Gasnetzwerk'), 'flow')].sum()
                * (param['param']['gas_price']
                   + (param['param']['co2_price']
                      * param['param']['ef_gas'])))

    specific_costs_el_grid = (
        param['param']['elec_consumer_charges_grid']
        + data['el_spot_price']
        + (param['param']['co2_price']
           * data['ef_om'])
        )
    cost_el_grid = (
        np.array(data_enw[(('Stromquelle', 'Elektrizitätsnetzwerk'), 'flow')])
        * specific_costs_el_grid)
    cost_el_grid = cost_el_grid.sum()

    cost_el_internal = ((
        data_enw.loc[
            :, ['BHKW' in col for col in data_enw.columns]
            ].to_numpy().sum()
        + data_enw.loc[
            :, ['GuD' in col for col in data_enw.columns]
            ].to_numpy().sum()
        - data_enw[(('Elektrizitätsnetzwerk', 'Spotmarkt'), 'flow')].sum()
        ) * param['param']['elec_consumer_charges_self'])

    cost_el = cost_el_grid + cost_el_internal

    revenues_spotmarkt_timeseries = (np.array(
        data_enw[(('Elektrizitätsnetzwerk', 'Spotmarkt'), 'flow')])
                                     * (data['el_spot_price']
                                        + param['param']['vNNE']))
    revenues_spotmarkt = revenues_spotmarkt_timeseries.sum()

    revenues_chpbonus = 0
    if param['BHKW']['active']:
        revenues_chpbonus += (
            data_enw.loc[
                :, ['BHKW' in col for col in data_enw.columns]
                ].to_numpy().sum()
            * (param['BHKW']['chp_bonus'] + param['BHKW']['TEHG_bonus'])
            )
    if param['GuD']['active']:
        revenues_chpbonus += (
            data_enw.loc[
                :, ['GuD' in col for col in data_enw.columns]
                ].to_numpy().sum()
            * (param['GuD']['chp_bonus'] + param['GuD']['TEHG_bonus'])
            )
    if param['BPT']['active']:
        revenues_chpbonus += (
            data_enw.loc[
                :, ['BPT' in col for col in data_enw.columns]
                ].to_numpy().sum()
            * (param['BPT']['chp_bonus'] + param['BPT']['TEHG_bonus'])
            )

    revenues_heatdemand = (data_wnw[(('Wärmenetzwerk', 'Wärmebedarf'),
                                     'flow')].sum()
                           * param['param']['heat_price'])

    revenues_total = (
        revenues_spotmarkt + revenues_heatdemand + revenues_chpbonus
        )
    cost_total = cost_Anlagen + cost_gas + cost_el
    Gesamtbetrag = revenues_total - cost_total

    result_dfs = [
        data_wnw, data_lt_wnw, data_wnw_node, data_sol_node, data_tes,
        data_enw, data_gnw
        ]

    labeldict = generate_labeldict(param)
    for df in result_dfs:
        result_labelling(labeldict, df)

    data_dhs = pd.concat(result_dfs, axis=1)

    data_invest = pd.DataFrame(data={
        'invest_ges': [invest_ges],
        'Q_tes': [param['TES']['Q']],
        'total_heat_demand': [
            data['heat_demand'].sum() * param['param']['rel_demand']
            ],
        'Gesamtbetrag': [Gesamtbetrag],
        'revenues_spotmarkt': [revenues_spotmarkt],
        'revenues_heatdemand': [revenues_heatdemand],
        'revenues_chpbonus': [revenues_chpbonus],
        'cost_Anlagen': [cost_Anlagen],
        'cost_gas': [cost_gas],
        'cost_el': [cost_el],
        'cost_el_grid': [cost_el_grid],
        'cost_el_internal': [cost_el_internal],
        'cost_total': [cost_total],
        'revenues_total': [revenues_total]
        })

    data_emission = pd.concat([
        data_gnw['H_source'], data_enw[['P_spot_market', 'P_source']]
        ], axis=1)

    return data_dhs, data_invest, data_emission, data_cost_units
