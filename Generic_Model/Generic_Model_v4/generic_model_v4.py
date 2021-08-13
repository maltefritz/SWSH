"""Energiesystem mit Speicher und Solarthermie.

@author: Malte Fritz and Jonas Freißmann

Komponenten:
    - Elektroheizkessel
    - Spitzenlastkessel
    - BHKW
    - GuD
    - Wärmepumpe
    - Solarthermie
    - TES
    - LT-Wärmepumpe

Wärmebedarf Flensburgs aus dem Jahr 2016

"""
import os
import json

import pandas as pd
import numpy as np

import oemof.solph as solph
from oemof.solph import views
from help_funcs import liste, topology_check, result_labelling
from eco_funcs import invest_sol, invest_stes, chp_bonus
from components import (
    gas_source, electricity_source, solar_thermal_source, must_run_source,
    electricity_sink, heat_sink, ht_emergency_cooling_sink,
    sol_emergency_cooling_sink, electric_boiler, peak_load_boiler,
        internal_combustion_engine, combined_cycle_extraction_turbine,
        back_pressure_turbine
    )


def main(data, param, mipgap='0.1'):
    """Execute main script.

    __________
    Parameters:

    data: (DataFrame) time series data for simulation
    param: (JSON dict) scalar simulation parameters
    """

    # %% Initialize energy system

    periods = len(data)
    date_time_index = pd.date_range(data.index[0], periods=periods, freq='h')

    es_ref = solph.EnergySystem(timeindex=date_time_index)

    topology_check(param)

    # %% Energiesystem

        # %% Busses

    gnw = solph.Bus(label='Gasnetzwerk')
    enw = solph.Bus(label='Elektrizitätsnetzwerk')
    wnw = solph.Bus(label='Wärmenetzwerk')
    lt_wnw = solph.Bus(label='LT-Wärmenetzwerk')
    wnw_node = solph.Bus(label='TES Knoten')
    sol_node = solph.Bus(label='Sol Knoten')

    es_ref.add(gnw, enw, wnw, lt_wnw, wnw_node, sol_node)

    busses = {
        'gnw': gnw, 'enw': enw, 'wnw': wnw, 'lt_wnw': lt_wnw,
        'wnw_node': wnw_node, 'sol_node': sol_node
        }

        # %% Soruces

    es_ref.add(
        gas_source(param, busses),
        electricity_source(param, data, busses),
        solar_thermal_source(param, data, busses),
        must_run_source(param, data, busses)
        )

        # %% Sinks

    es_ref.add(
        electricity_sink(param, busses),
        heat_sink(param, data, busses),
        ht_emergency_cooling_sink(param, busses),
        sol_emergency_cooling_sink(param, busses)
        )

        # %% Transformer


    es_ref.add(
        electric_boiler(param, data, busses),
        peak_load_boiler(param, data, busses),
        internal_combustion_engine(param, data, busses),
        combined_cycle_extraction_turbine(param, data, busses),
        back_pressure_turbine(param, data, busses),
        )

    if param['SLK']['active']:
        if param['SLK']['type'] == 'constant':
            for i in range(1, param['SLK']['amount']+1):
                slk = solph.Transformer(
                    label='Spitzenlastkessel_' + str(i),
                    inputs={gnw: solph.Flow()},
                    outputs={wnw: solph.Flow(
                        nominal_value=param['SLK']['Q_N'],
                        max=1,
                        min=0,
                        variable_costs=(param['SLK']['op_cost_var']
                                        + param['param']['energy_tax']))},
                    conversion_factors={wnw: param['SLK']['eta']})

                es_ref.add(slk)

        elif param['SLK']['type'] == 'time series':
            for i in range(1, param['SLK']['amount']+1):
                slk = solph.Transformer(
                    label='Spitzenlastkessel_' + str(i),
                    inputs={gnw: solph.Flow()},
                    outputs={wnw: solph.Flow(
                        nominal_value=1,
                        max=data['Q_SLK'],
                        min=0,
                        variable_costs=(param['SLK']['op_cost_var']
                                        + param['param']['energy_tax']))},
                    conversion_factors={wnw: param['SLK']['eta']})

                es_ref.add(slk)

    if param['BHKW']['active']:
        if param['BHKW']['type'] == 'constant':
            for i in range(1, param['BHKW']['amount']+1):
                bhkw = solph.components.GenericCHP(
                    label='BHKW_' + str(i),
                    fuel_input={gnw: solph.Flow(
                        H_L_FG_share_max=liste(param['BHKW']['H_L_FG_share_max'], periods),
                        H_L_FG_share_min=liste(param['BHKW']['H_L_FG_share_min'], periods),
                        nominal_value=param['BHKW']['Q_in'])},
                    electrical_output={enw: solph.Flow(
                        variable_costs=(
                            param['BHKW']['op_cost_var']
                            - param['BHKW']['chp_bonus']
                            - param['BHKW']['TEHG_bonus']),
                        P_max_woDH=liste(param['BHKW']['P_max_woDH'], periods),
                        P_min_woDH=liste(param['BHKW']['P_min_woDH'], periods),
                        Eta_el_max_woDH=liste(param['BHKW']['Eta_el_max_woDH'], periods),
                        Eta_el_min_woDH=liste(param['BHKW']['Eta_el_min_woDH'], periods))},
                    heat_output={wnw: solph.Flow(
                        Q_CW_min=liste(0, periods))},
                    Beta=liste(0, periods),
                    back_pressure=False)

                es_ref.add(bhkw)

        elif param['BHKW']['type'] == 'time series':
            for i in range(1, param['BHKW']['amount']+1):
                bhkw = solph.components.GenericCHP(
                    label='BHKW_' + str(i),
                    fuel_input={gnw: solph.Flow(
                        H_L_FG_share_max=data['ICE_H_L_FG_share_max'].tolist(),
                        H_L_FG_share_min=data['ICE_H_L_FG_share_min'].tolist(),
                        nominal_value=data['ICE_Q_in'].mean())},
                    electrical_output={enw: solph.Flow(
                        variable_costs=(
                            param['BHKW']['op_cost_var']
                            - param['BHKW']['chp_bonus']
                            - param['BHKW']['TEHG_bonus']),
                        P_max_woDH=data['ICE_P_max_woDH'].tolist(),
                        P_min_woDH=data['ICE_P_min_woDH'].tolist(),
                        Eta_el_max_woDH=data['ICE_eta_el_max'].tolist(),
                        Eta_el_min_woDH=data['ICE_eta_el_min'].tolist())},
                    heat_output={wnw: solph.Flow(
                        Q_CW_min=liste(0, periods))},
                    Beta=liste(0, periods),
                    back_pressure=False)

                es_ref.add(bhkw)

    if param['GuD']['active']:
        if param['GuD']['type'] == 'constant':
            for i in range(1, param['GuD']['amount']+1):
                gud = solph.components.GenericCHP(
                    label='GuD_' + str(i),
                    fuel_input={gnw: solph.Flow(
                        H_L_FG_share_max=liste(param['GuD']['H_L_FG_share_max'], periods),
                        nominal_value=param['GuD']['Q_in'])},
                    electrical_output={enw: solph.Flow(
                        variable_costs=(
                            param['GuD']['op_cost_var']
                            - param['GuD']['chp_bonus']
                            - param['GuD']['TEHG_bonus']),
                        P_max_woDH=liste(param['GuD']['P_max_woDH'], periods),
                        P_min_woDH=liste(param['GuD']['P_min_woDH'], periods),
                        Eta_el_max_woDH=liste(param['GuD']['Eta_el_max_woDH'], periods),
                        Eta_el_min_woDH=liste(param['GuD']['Eta_el_min_woDH'], periods))},
                    heat_output={wnw: solph.Flow(
                        Q_CW_min=liste(param['GuD']['Q_CW_min'], periods))},
                    Beta=liste(param['GuD']['beta'], periods),
                    back_pressure=False)

                es_ref.add(gud)

        elif param['GuD']['type'] == 'time series':
            for i in range(1, param['GuD']['amount']+1):
                gud = solph.components.GenericCHP(
                    label='GuD_' + str(i),
                    fuel_input={gnw: solph.Flow(
                        H_L_FG_share_max=data['CCET_H_L_FG_share_max'].tolist(),
                        nominal_value=data['CCET_Q_in'].mean())},
                    electrical_output={enw: solph.Flow(
                        variable_costs=(
                            param['GuD']['op_cost_var']
                            - param['GuD']['chp_bonus']
                            - param['GuD']['TEHG_bonus']),
                        P_max_woDH=data['CCET_P_max_woDH'].tolist(),
                        P_min_woDH=data['CCET_P_min_woDH'].tolist(),
                        Eta_el_max_woDH=data['CCET_eta_el_max'].tolist(),
                        Eta_el_min_woDH=data['CCET_eta_el_min'].tolist())},
                    heat_output={wnw: solph.Flow(
                        Q_CW_min=data['CCET_Q_CW_min'].tolist())},
                    Beta=data['CCET_beta'].tolist(),
                    back_pressure=False)

                es_ref.add(gud)

    if param['BPT']['active']:
        if param['BPT']['type'] == 'constant':
            for i in range(1, param['BPT']['amount']+1):
                bpt = solph.components.GenericCHP(
                    label='bpt' + str(i),
                    fuel_input={gnw: solph.Flow(
                        H_L_FG_share_max=liste(param['bpt']['H_L_FG_share_max'], periods),
                        nominal_value=param['bpt']['Q_in'])},
                    electrical_output={enw: solph.Flow(
                        variable_costs=(
                            param['bpt']['op_cost_var']
                            - param['bpt']['chp_bonus']
                            - param['bpt']['TEHG_bonus']),
                        P_max_woDH=liste(param['bpt']['P_max_woDH'], periods),
                        P_min_woDH=liste(param['bpt']['P_min_woDH'], periods),
                        Eta_el_max_woDH=liste(param['bpt']['Eta_el_max_woDH'], periods),
                        Eta_el_min_woDH=liste(param['bpt']['Eta_el_min_woDH'], periods))},
                    heat_output={wnw: solph.Flow(
                        Q_CW_min=liste(0, periods))},
                    Beta=liste(0, periods),
                    back_pressure=True)

                es_ref.add(bpt)

        elif param['BPT']['type'] == 'time series':
            for i in range(1, param['BPT']['amount']+1):
                bpt = solph.components.GenericCHP(
                    label='bpt' + str(i),
                    fuel_input={gnw: solph.Flow(
                        H_L_FG_share_max=data['BPT_H_L_FG_share_max'].tolist(),
                        nominal_value=data['BPT_Q_in'].mean())},
                    electrical_output={enw: solph.Flow(
                        variable_costs=(
                            param['bpt']['op_cost_var']
                            - param['bpt']['chp_bonus']
                            - param['bpt']['TEHG_bonus']),
                        P_max_woDH=data['BPT_P_max_woDH'].tolist(),
                        P_min_woDH=data['BPT_P_min_woDH'].tolist(),
                        Eta_el_max_woDH=data['BPT_Eta_el_max_woDH'].tolist(),
                        Eta_el_min_woDH=data['BPT_Eta_el_min_woDH'].tolist())},
                    heat_output={wnw: solph.Flow(
                        Q_CW_min=liste(0, periods))},
                    Beta=liste(0, periods),
                    back_pressure=True)

                es_ref.add(bpt)

    # 30% m-Teillast bei 65-114°C und 50% m-Teillast bei 115-124°C
    if param['HP']['active']:
        if param['HP']['type'] == 'constant':
            for i in range(1, param['HP']['amount']+1):
                hp = solph.components.OffsetTransformer(
                    label='HP_' + str(i),
                    inputs={enw: solph.Flow(
                        nominal_value=param['HP']['P_max'],
                        max=1,
                        min=param['HP']['P_min']/param['HP']['P_max'],
                        variable_costs=(
                            param['param']['elec_consumer_charges_self']),
                        nonconvex=solph.NonConvex())},
                    outputs={wnw: solph.Flow(
                        variable_costs=(
                            param['HP']['op_cost_var'])
                        )},
                    coefficients=[param['HP']['c_0'], param['HP']['c_1']])

                es_ref.add(hp)

        elif param['HP']['type'] == 'time series':
            for i in range(1, param['HP']['amount']+1):
                hp = solph.components.OffsetTransformer(
                    label='HP_' + str(i),
                    inputs={enw: solph.Flow(
                        nominal_value=1,
                        max=data['P_max_hp'],
                        min=data['P_min_hp'],
                        variable_costs=(
                            param['param']['elec_consumer_charges_self']),
                        nonconvex=solph.NonConvex())},
                    outputs={wnw: solph.Flow(
                        variable_costs=(
                            param['HP']['op_cost_var'])
                        )},
                    coefficients=[data['c_0_hp'], data['c_1_hp']])

                es_ref.add(hp)

    # Low temperature heat pump
    if param['LT-HP']['active']:
        if param['LT-HP']['type'] == 'constant':
            for i in range(1, param['LT-HP']['amount']+1):
                lthp = solph.Transformer(
                    label="LT-HP_" + str(i),
                    inputs={lt_wnw: solph.Flow(),
                            enw: solph.Flow(
                                variable_costs=(
                                    param['param']['elec_consumer_charges_self']))},
                    outputs={wnw: solph.Flow(
                        variable_costs=(
                            param['HP']['op_cost_var']))},
                    conversion_factors={enw: 1/param['LT-HP']['cop'],
                                        lt_wnw: ((param['LT-HP']['cop']-1)
                                                 / param['LT-HP']['cop'])})

                es_ref.add(lthp)

        elif param['LT-HP']['type'] == 'time series':
            for i in range(1, param['LT-HP']['amount']+1):
                lthp = solph.Transformer(
                    label="LT-HP_" + str(i),
                    inputs={lt_wnw: solph.Flow(),
                            enw: solph.Flow(
                                variable_costs=(
                                    param['param']['elec_consumer_charges_self']))},
                    outputs={wnw: solph.Flow(
                        variable_costs=(
                            param['HP']['op_cost_var']))},
                    conversion_factors={enw: 1/data['cop_lthp'],
                                        lt_wnw: (data['cop_lthp']-1)/data['cop_lthp']})

                es_ref.add(lthp)

    # TES node
    ht_to_node = solph.Transformer(
        label='HT_to_node',
        inputs={wnw: solph.Flow()},
        outputs={wnw_node: solph.Flow(
            nominal_value=9999,
            max=1.0,
            min=0.0)},
        conversion_factors={wnw_node: 1}
        )

    lt_to_node = solph.Transformer(
        label='LT_to_node',
        inputs={lt_wnw: solph.Flow()},
        outputs={wnw_node: solph.Flow(
            nominal_value=9999,
            max=1.0,
            min=0.0)},
        conversion_factors={wnw_node: 1}
        )

    es_ref.add(ht_to_node, lt_to_node)

    # Sol node
    if param['Sol']['usage'] == 'HT':
        sol_to_ht = solph.Transformer(
            label='Sol_to_HT',
            inputs={sol_node: solph.Flow()},
            outputs={wnw: solph.Flow(
                nominal_value=9999,
                max=1.0,
                min=0.0)},
            conversion_factors={wnw: 1}
            )

        es_ref.add(sol_to_ht)

    if param['Sol']['usage'] == 'LT':
        sol_to_lt = solph.Transformer(
            label='Sol_to_LT',
            inputs={sol_node: solph.Flow()},
            outputs={lt_wnw: solph.Flow(
                nominal_value=9999,
                max=1.0,
                min=0.0)},
            conversion_factors={lt_wnw: 1}
            )

        es_ref.add(sol_to_lt)

        # %% Speicher

    # Saisonaler Speicher
    if param['TES']['active']:
        for i in range(1, param['TES']['amount']+1):
            tes = solph.components.GenericStorage(
                label='TES_' + str(i),
                nominal_storage_capacity=param['TES']['Q'],
                inputs={wnw_node: solph.Flow(
                    storageflowlimit=True,
                    nominal_value=param['TES']['Q_N_in'],
                    max=param['TES']['Q_rel_in_max'],
                    min=param['TES']['Q_rel_in_min'],
                    variable_costs=param['TES']['op_cost_var'],
                    nonconvex=solph.NonConvex(
                        minimum_uptime=int(param['TES']['min_uptime']),
                        initial_status=int(param['TES']['init_status'])))},
                outputs={lt_wnw: solph.Flow(
                    storageflowlimit=True,
                    nominal_value=param['TES']['Q_N_out'],
                    max=param['TES']['Q_rel_out_max'],
                    min=param['TES']['Q_rel_out_min'],
                    nonconvex=solph.NonConvex(
                        minimum_uptime=int(param['TES']['min_uptime'])))},
                initial_storage_level=param['TES']['init_storage'],
                balanced=param['TES']['balanced'],
                loss_rate=param['TES']['Q_rel_loss'],
                inflow_conversion_factor=param['TES']['inflow_conv'],
                outflow_conversion_factor=param['TES']['outflow_conv'])

            es_ref.add(tes)

    # Kurzzeitspeicher
    if param['ST-TES']['active']:
        for i in range(1, param['ST-TES']['amount']+1):
            st_tes = solph.components.GenericStorage(
                label='ST-TES_' + str(i),
                nominal_storage_capacity=param['ST-TES']['Q'],
                inputs={wnw: solph.Flow(
                    storageflowlimit=True,
                    nominal_value=param['ST-TES']['Q_N_in'],
                    max=param['ST-TES']['Q_rel_in_max'],
                    min=param['ST-TES']['Q_rel_in_min'],
                    variable_costs=param['ST-TES']['op_cost_var'],
                    nonconvex=solph.NonConvex(
                        initial_status=int(param['ST-TES']['init_status'])))},
                outputs={wnw: solph.Flow(
                    storageflowlimit=True,
                    nominal_value=param['ST-TES']['Q_N_out'],
                    max=param['ST-TES']['Q_rel_out_max'],
                    min=param['ST-TES']['Q_rel_out_min'],
                    nonconvex=solph.NonConvex())},
                initial_storage_level=param['ST-TES']['init_storage'],
                loss_rate=param['ST-TES']['Q_rel_loss'],
                inflow_conversion_factor=param['ST-TES']['inflow_conv'],
                outflow_conversion_factor=param['ST-TES']['outflow_conv'])

            es_ref.add(st_tes)

    # %% Processing

        # %% Solve

    # Was bedeutet tee?
    model = solph.Model(es_ref)
    solph.constraints.limit_active_flow_count_by_keyword(
        model, 'storageflowlimit', lower_limit=0, upper_limit=1)
    # model.write('my_model.lp', io_options={'symbolic_solver_labels': True})
    model.solve(solver='gurobi', solve_kwargs={'tee': True},
                cmdline_options={"mipgap": mipgap})

        # %% Ergebnisse Energiesystem

    # Ergebnisse in results
    results = solph.processing.results(model)

    # Main- und Metaergebnisse
    es_ref.results['main'] = solph.processing.results(model)
    es_ref.results['meta'] = solph.processing.meta_results(model)

    cost_df = pd.DataFrame()
    labeldict = {}

    # Busses
    data_gnw = views.node(results, 'Gasnetzwerk')['sequences']
    data_enw = views.node(results, 'Elektrizitätsnetzwerk')['sequences']
    data_wnw = views.node(results, 'Wärmenetzwerk')['sequences']
    data_lt_wnw = views.node(results, 'LT-Wärmenetzwerk')['sequences']
    data_wnw_node = views.node(results, 'TES Knoten')['sequences']
    data_sol_node = views.node(results, 'Sol Knoten')['sequences']

    labeldict[(('Gasquelle', 'Gasnetzwerk'), 'flow')] = 'H_source'
    labeldict[(('Elektrizitätsnetzwerk', 'Spotmarkt'), 'flow')] = 'P_spot_market'
    labeldict[(('Stromquelle', 'Elektrizitätsnetzwerk'), 'flow')] = 'P_source'
    labeldict[(('Wärmenetzwerk', 'Wärmebedarf'), 'flow')] = 'Q_demand'
    labeldict[(('Wärmenetzwerk', 'HT_to_node'), 'flow')] = 'Q_HT_TES'
    labeldict[(('LT-Wärmenetzwerk', 'LT_to_node'), 'flow')] = 'Q_LT_TES'

    if param['Sol']['active']:
        data_solar_source = views.node(results, 'Solarthermie')['sequences']
        cost_df.loc['invest', 'Sol'] = invest_solar
        cost_df.loc['op_cost', 'Sol'] = (
            data_solar_source[(('Solarthermie', 'Sol Knoten'), 'flow')].sum()
            * (0.01 * invest_solar)/(param['Sol']['A']*data['solar_data'].sum())
            )
        labeldict[(('Solarthermie', 'Sol Knoten'), 'flow')] = 'Q_Sol_zu'
        labeldict[(('Sol Knoten', 'Sol_to_LT'), 'flow')] = 'Q_Sol_node_LT'
        labeldict[(('Sol Knoten', 'Sol_to_HT'), 'flow')] = 'Q_Sol_node_HT'

    if param['MR']['active']:
        labeldict[(('Mustrun', 'Wärmenetzwerk'), 'flow')] = 'Q_MR'

    if param['HT-EC']['active']:
        labeldict[(('Wärmenetzwerk', 'HT-EC'), 'flow')] = 'Q_HT_EC'

    if param['Sol EC']['active']:
        labeldict[(('Sol Knoten', 'Sol EC'), 'flow')] = 'Q_Sol_EC'

    # Transformer
    if param['EHK']['active']:
        cost_df.loc['invest', 'EHK'] = (
            param['EHK']['inv_spez']
            * param['EHK']['Q_N']
            * param['EHK']['amount']
            )

        for i in range(1, param['EHK']['amount']+1):
            label_id = 'Elektroheizkessel_' + str(i)

            cost_df.loc['op_cost', 'EHK'] = (
                data_wnw[((label_id, 'Wärmenetzwerk'), 'flow')].sum()
                * param['EHK']['op_cost_var']
                + (param['EHK']['op_cost_fix']
                   * param['EHK']['Q_N'])
                )

            labeldict[((label_id, 'Wärmenetzwerk'), 'flow')] = 'Q_EHK_' + str(i)
            labeldict[(('Elektrizitätsnetzwerk', label_id), 'flow')] = 'P_zu_EHK_' + str(i)

    if param['SLK']['active']:
        cost_df.loc['invest', 'SLK'] = (
            param['SLK']['inv_spez']
            * param['SLK']['Q_N']
            * param['SLK']['amount']
            )

        for i in range(1, param['SLK']['amount']+1):
            label_id = 'Spitzenlastkessel_' + str(i)

            cost_df.loc['op_cost', 'SLK'] = (
                data_wnw[((label_id, 'Wärmenetzwerk'), 'flow')].sum()
                * (param['SLK']['op_cost_var']
                   + param['param']['energy_tax'])
                + (param['SLK']['op_cost_fix']
                   * param['SLK']['Q_N'])
                )

            labeldict[((label_id, 'Wärmenetzwerk'), 'flow')] = 'Q_SLK_' + str(i)
            labeldict[(('Gasnetzwerk', label_id), 'flow')] = 'H_SLK_' + str(i)

    if param['BHKW']['active']:
        if param['BHKW']['type'] == 'constant':
            ICE_P_max_woDH = param['BHKW']['P_max_woDH']
        elif param['BHKW']['type'] == 'time series':
            ICE_P_max_woDH = data['ICE_P_max_woDH'].mean()

        cost_df.loc['invest', 'BHKW'] = (
            ICE_P_max_woDH
            * param['BHKW']['inv_spez']
            * param['BHKW']['amount']
            )

        for i in range(1, param['BHKW']['amount']+1):
            label_id = 'BHKW_' + str(i)

            cost_df.loc['op_cost', 'BHKW'] = (
                data_enw[((label_id, 'Elektrizitätsnetzwerk'), 'flow')].sum()
                * param['BHKW']['op_cost_var']
                + (param['BHKW']['op_cost_fix']
                   * ICE_P_max_woDH)
                )

            labeldict[((label_id, 'Wärmenetzwerk'), 'flow')] = 'Q_' + label_id
            labeldict[((label_id, 'Elektrizitätsnetzwerk'), 'flow')] = 'P_' + label_id
            labeldict[(('Gasnetzwerk', label_id), 'flow')] = 'H_' + label_id

    if param['GuD']['active']:
        if param['GuD']['type'] == 'constant':
            CCET_P_max_woDH = param['GuD']['P_max_woDH']
        elif param['GuD']['type'] == 'time series':
            CCET_P_max_woDH = data['CCET_P_max_woDH'].mean()

        cost_df.loc['invest', 'GuD'] = (
            CCET_P_max_woDH
            * param['GuD']['inv_spez']
            * param['GuD']['amount']
            )

        for i in range(1, param['GuD']['amount']+1):
            label_id = 'GuD_' + str(i)

            cost_df.loc['op_cost', 'GuD'] = (
                data_enw[((label_id, 'Elektrizitätsnetzwerk'), 'flow')].sum()
                * param['GuD']['op_cost_var']
                + (param['GuD']['op_cost_fix']
                   * CCET_P_max_woDH)
                )

            labeldict[((label_id, 'Wärmenetzwerk'), 'flow')] = 'Q_' + label_id
            labeldict[((label_id, 'Elektrizitätsnetzwerk'), 'flow')] = 'P_' + label_id
            labeldict[(('Gasnetzwerk', label_id), 'flow')] = 'H_' + label_id

    if param['HP']['active']:
        if param['HP']['type'] == 'constant':
            HP_Q_N = (param['HP']['c_1']
                      * param['HP']['P_max']
                      + param['HP']['c_0'])
        elif param['HP']['type'] == 'time series':
            HP_Q_N = (data['c_1_hp'].mean()
                      * data['P_max_hp'].mean()
                      + data['c_0_hp'].mean())
        cost_df.loc['invest', 'HP'] = (
            param['HP']['inv_spez']
            * data['P_max_hp'].max()
            * HP_Q_N
            * param['HP']['amount']
            )
        for i in range(1, param['HP']['amount']+1):
            label_id = 'HP_' + str(i)

            cost_df.loc['op_cost', 'HP'] = (
                data_wnw[((label_id, 'Wärmenetzwerk'), 'flow')].sum()
                * param['HP']['op_cost_var']
                + param['HP']['op_cost_fix'] * HP_Q_N
                )

            labeldict[((label_id, 'Wärmenetzwerk'), 'flow')] = 'Q_ab_' + label_id
            labeldict[(('Elektrizitätsnetzwerk', label_id), 'flow')] = 'P_zu_' + label_id
            labeldict[(('Elektrizitätsnetzwerk', label_id), 'status')] = 'Status_' + label_id

    if param['LT-HP']['active']:
        LT_HP_Q_N = data_wnw[((label_id, 'Wärmenetzwerk'), 'flow')].mean()

        for i in range(1, param['LT-HP']['amount']+1):
            label_id = 'LT-HP_' + str(i)

            cost_df.loc['invest', 'LT-HP'] = (
                param['HP']['inv_spez'] * LT_HP_Q_N
                )

            cost_df.loc['op_cost', 'LT-HP'] = (
                data_wnw[((label_id, 'Wärmenetzwerk'), 'flow')].sum()
                * param['HP']['op_cost_var']
                + param['HP']['op_cost_fix'] * LT_HP_Q_N
                )

            labeldict[((label_id, 'Wärmenetzwerk'), 'flow')] = 'Q_ab_' + label_id
            labeldict[(('Elektrizitätsnetzwerk', label_id), 'flow')] = 'P_zu_' + label_id
            labeldict[(('LT-Wärmenetzwerk', label_id), 'flow')] = 'Q_zu_' + label_id

    # Speicher
    data_tes = pd.DataFrame()
    if param['TES']['active']:
        cost_df.loc['invest', 'TES'] = (
            invest_stes(param['TES']['Q'])
            * param['TES']['amount']
            )

        for i in range(1, param['TES']['amount']+1):
            label_id = 'TES_' + str(i)
            data_tes = pd.concat([data_tes,
                                  views.node(results, label_id)['sequences']],
                                 axis=1)

            cost_df.loc['op_cost', 'TES'] = (
                data_tes[(('TES Knoten', label_id), 'flow')].sum()
                * param['TES']['op_cost_var']
                + (param['TES']['op_cost_fix']
                   * param['TES']['Q'])
                )

            labeldict[((label_id, 'LT-Wärmenetzwerk'), 'flow')] = 'Q_ab_' + label_id
            labeldict[((label_id, 'LT-Wärmenetzwerk'), 'status')] = 'Status_ab_' + label_id
            labeldict[(('TES Knoten', label_id), 'flow')] = 'Q_zu_' + label_id
            labeldict[(('TES Knoten', label_id), 'status')] = 'Status_zu_' + label_id
            labeldict[((label_id, 'None'), 'storage_content')] = 'Speicherstand_' + label_id

    if param['ST-TES']['active']:
        cost_df.loc['invest', 'ST-TES'] = (
            invest_stes(param['ST-TES']['Q'])
            * param['ST-TES']['amount']
            )

        for i in range(1, param['ST-TES']['amount']+1):
            label_id = 'ST-TES_' + str(i)
            data_tes = pd.concat([data_tes,
                                  views.node(results, label_id)['sequences']],
                                 axis=1)

            cost_df.loc['op_cost', 'ST-TES'] = (
                data_tes[(('Wärmenetzwerk', label_id), 'flow')].sum()
                * param['ST-TES']['op_cost_var']
                + (param['ST-TES']['op_cost_fix']
                   * param['ST-TES']['Q'])
                )

            labeldict[((label_id, 'Wärmenetzwerk'), 'flow')] = 'Q_ab_' + label_id
            labeldict[((label_id, 'Wärmenetzwerk'), 'status')] = 'Status_ab_' + label_id
            labeldict[(('Wärmenetzwerk', label_id), 'flow')] = 'Q_zu_' + label_id
            labeldict[(('Wärmenetzwerk', label_id), 'status')] = 'Status_zu_' + label_id
            labeldict[((label_id, 'None'), 'storage_content')] = 'Speicherstand_' + label_id

    # Knoten
    labeldict[(('HT_to_node', 'TES Knoten'), 'flow')] = 'Q_HT_node'
    labeldict[(('LT_to_node', 'TES Knoten'), 'flow')] = 'Q_LT_node'
    labeldict[(('Sol_to_HT', 'Wärmenetzwerk'), 'flow')] = 'Q_Sol_HT'
    labeldict[(('Sol_to_LT', 'LT-Wärmenetzwerk'), 'flow')] = 'Q_Sol_LT'
    labeldict[(('Elektrizitätsnetzwerk', 'Spotmarkt'), 'flow')] = 'P_spot_market'

        # %% Zahlungsströme Ergebnis

    objective = abs(es_ref.results['meta']['objective'])


        # %% Geldflüsse

    cost_Anlagen = cost_df.loc['op_cost'].sum()
    invest_ges = cost_df.loc['invest'].sum()
    # # Primärenergiebezugskoste
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
        data_enw.loc[:, ['BHKW' in col for col in data_enw.columns]].to_numpy().sum()
        + data_enw.loc[:, ['GuD' in col for col in data_enw.columns]].to_numpy().sum()
        - data_enw[(('Elektrizitätsnetzwerk', 'Spotmarkt'), 'flow')].sum()
        ) * param['param']['elec_consumer_charges_self'])

    cost_el = cost_el_grid + cost_el_internal

    # Erlöse
    revenues_spotmarkt_timeseries = (np.array(
        data_enw[(('Elektrizitätsnetzwerk', 'Spotmarkt'), 'flow')])
                                     * (data['el_spot_price']
                                        + param['param']['vNNE']))
    revenues_spotmarkt = revenues_spotmarkt_timeseries.sum()

    revenues_chpbonus = 0
    if param['BHKW']['active']:
        revenues_chpbonus += (
            data_enw[(('BHKW', 'Elektrizitätsnetzwerk'), 'flow')].sum()
            * (param['BHKW']['chp_bonus'] + param['BHKW']['TEHG_bonus'])
            )
    if param['GuD']['active']:
        revenues_chpbonus += (
            data_enw[(('GuD', 'Elektrizitätsnetzwerk'), 'flow')].sum()
            * (param['GuD']['chp_bonus'] + param['GuD']['TEHG_bonus'])
            )
    if param['bpt']['active']:
        revenues_chpbonus += (
            data_enw[(('BPT', 'Elektrizitätsnetzwerk'), 'flow')].sum()
            * (param['bpt']['chp_bonus'] + param['bpt']['TEHG_bonus'])
            )

    revenues_heatdemand = (data_wnw[(('Wärmenetzwerk', 'Wärmebedarf'),
                                     'flow')].sum()
                           * param['param']['heat_price'])
    # Summe der Geldströme
    Gesamtbetrag = (
        revenues_spotmarkt + revenues_heatdemand + revenues_chpbonus
        - cost_Anlagen - cost_gas - cost_el
        )


        # %% Output Ergebnisse

    # Umbenennen der Spaltennamen der Ergebnisdataframes
    result_dfs = [
        data_wnw, data_lt_wnw, data_wnw_node, data_sol_node, data_tes,
        data_enw, data_gnw
        ]

    for df in result_dfs:
        result_labelling(df, labeldict)

    # Name des Modells
    # modelname = os.path.basename(__file__)[:-3]

    # Verzeichnes erzeugen, falls nicht vorhanden
    # if not os.path.exists(os.path.join(dirpath, 'Ergebnisse', modelname)):
    #     os.mkdir(os.path.join(dirpath, 'Ergebnisse', modelname))

    # Daten zum Plotten der Wärmeversorgung
    df1 = pd.concat(result_dfs, axis=1)
    # df1.to_csv(os.path.join(
    #     dirpath, 'Ergebnisse', modelname, 'data_wnw.csv'),
    #            sep=";")

    # Daten zum Plotten der Investitionsrechnung
    df2 = pd.DataFrame(data={'invest_ges': [invest_ges],
                             'Q_tes': [param['TES']['Q']],
                             'total_heat_demand': [
                                 data['heat_demand'].sum()
                                 * param['param']['rel_demand']
                                 ],
                             'Gesamtbetrag': [Gesamtbetrag],
                             'revenues_spotmarkt': [revenues_spotmarkt],
                             'revenues_heatdemand': [revenues_heatdemand],
                             'revenues_chpbonus': [revenues_chpbonus],
                             'cost_Anlagen': [cost_Anlagen],
                             'cost_gas': [cost_gas],
                             'cost_el': [cost_el]})
    # df2.to_csv(os.path.join(
    #     dirpath, 'Ergebnisse', modelname, 'data_Invest.csv'),
    #            sep=";")

    # Daten für die ökologische Bewertung
    df3 = pd.concat([data_gnw['H_source'],
                     data_enw[['P_spot_market', 'P_source']]],
                    axis=1)
    # df3.to_csv(os.path.join(
    #     dirpath, 'Ergebnisse', modelname, 'data_CO2.csv'),
    #            sep=";")

    return df1, df2, df3, cost_df, es_ref.results['meta']


if __name__ == '__main__':
    main()
