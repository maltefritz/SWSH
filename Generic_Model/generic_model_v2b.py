"""Energiesystem mit Speicher und Solarthermie.

Created on Tue Jan  7 10:04:39 2020

@author: Malte Fritz

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
import os.path as path
import json
from sys import exit

import pandas as pd
import numpy as np

import oemof.solph as solph
from oemof.solph import views
# from invest import invest_st


def main():
    """Execute main script."""
    def invest_sol(A, col_type=''):
        """Pehnt et al. 2017, Markus [38].

        A:                Kollektorfläche der Solarthermie
        col_type:         Kollektortyp der Solarthermie
        specific_coasts:  Spezifische Kosten
        invest:           Investitionskosten
        """
        if col_type == 'flat':
            specific_costs = -34.06 * np.log(A) + 592.48
            invest = A * specific_costs
            return invest
        elif col_type == 'vacuum':
            specific_costs = -40.63 * np.log(A) + 726.64
            invest = A * specific_costs
            return invest
        else:
            raise ValueError(
                "Choose a valid collector type: 'flat' or 'vacuum'"
                )

    def liste(parameter):
        """Get timeseries list of parameter for solph components."""
        return [parameter for p in range(0, periods)]

    def result_labelling(dataframe):
        for col in dataframe.columns:
            if col in labeldict:
                dataframe.rename(columns={col: labeldict[col]}, inplace=True)
            else:
                print(col, ' not in labeldict')

    # %% Preprocessing

        # %% Daten einlesen

    dirpath = path.abspath(path.join(__file__, "../.."))
    filename = path.join(dirpath, 'Eingangsdaten\\simulation_data.csv')
    data = pd.read_csv(filename, sep=";")
    # filename = path.join(dirpath, 'Eingangsdaten\\All_parameters.csv')
    # param = pd.read_csv(filename, sep=";", index_col=['plant', 'parameter'])

    filepath = path.join(dirpath, 'Eingangsdaten\\parameter_v2a.json')
    with open(filepath, 'r') as file:
        param = json.load(file)

    # TODO
    cop_lt = 4.9501
    A = param['Sol']['A']

    invest_solar = invest_sol(A, col_type="flat")

        # %% Zeitreihe

    periods = len(data)
    date_time_index = pd.date_range('1/1/2016 00:00:00', periods=periods, freq='h')

        # %% Energiesystem erstellen

    es_ref = solph.EnergySystem(timeindex=date_time_index)

        # %% Wärmebedarf
    # rel_demand ist die Variable, die den Wärmebedarf der Region
    # prozentual von FL angibt.

    heat_demand_FL = data['heat_demand']
    rel_heat_demand = 1
    heat_demand_local = heat_demand_FL * rel_heat_demand
    total_heat_demand = float(heat_demand_local.sum())

    # %% Energiesystem

        # %% LT-WNW Plausibilität prüfen
    if (param['LT-HP']['active']
        and not param['Sol']['active']
        and not param['TES']['active']):
        print("WARNING: You can't have the low temp heat pump active without ",
              "using either the TES or solar heat.")
        exit()
    elif (not param['LT-HP']['active']
          and (param['Sol']['active']
          or param['TES']['active'])):
        print("WARNING: You can't use TES or solar heat without using the low ",
              "temp heat pump.")
        exit()


        # %% Busses

    gnw = solph.Bus(label='Gasnetzwerk')
    enw = solph.Bus(label='Elektrizitätsnetzwerk')
    wnw = solph.Bus(label='Wärmenetzwerk')
    lt_wnw = solph.Bus(label='LT-Wärmenetzwerk')

    es_ref.add(gnw, enw, wnw, lt_wnw)

        # %% Soruces

    gas_source = solph.Source(
        label='Gasquelle',
        outputs={gnw: solph.Flow(
            variable_costs=(param['param']['gas_price']
                            + param['param']['co2_certificate']))})

    elec_source = solph.Source(
        label='Stromquelle',
        outputs={enw: solph.Flow(
            variable_costs=(param['param']['elec_consumer_charges']
                            + data['el_spot_price']))})

    es_ref.add(gas_source, elec_source)

    if param['Sol']['active']:
        solar_source = solph.Source(
            label='Solarthermie',
            outputs={lt_wnw: solph.Flow(
                variable_costs=(0.01 * invest_solar)/(A*data['solar_data'].sum()),
                nominal_value=(max(data['solar_data'])*A),
                actual_value=(data['solar_data'])/(max(data['solar_data'])),
                fixed=True)})

        es_ref.add(solar_source)

    if param['MR']['active']:
        mr_source = solph.Source(label='Mustrun',
                                 outputs={wnw: solph.Flow(
                                    variable_costs=0,
                                    nominal_value=float(param['MR']['Q_N']),
                                    actual_value=1)})

        es_ref.add(mr_source)

        # %% Sinks

    elec_sink = solph.Sink(
        label='Spotmarkt',
        inputs={enw: solph.Flow(
            variable_costs=-data['el_spot_price'])})

    heat_sink = solph.Sink(
        label='Wärmebedarf',
        inputs={wnw: solph.Flow(
            variable_costs=-param['param']['heat_price'],
            nominal_value=max(heat_demand_local),
            actual_value=heat_demand_local/max(heat_demand_local),
            fixed=True)})

    es_ref.add(elec_sink, heat_sink)

    if param['HT-EC']['active']:
        ht_ec_sink = solph.Sink(label='HT-EC',
                                inputs={
                                    wnw: solph.Flow(variable_costs=0)}
                                )

        es_ref.add(ht_ec_sink)

    if param['LT-EC']['active']:
        lt_ec_sink = solph.Sink(label='LT-EC',
                                inputs={
                                    lt_wnw: solph.Flow(variable_costs=0)}
                                )

        es_ref.add(lt_ec_sink)

        # %% Transformer

    if param['EHK']['active']:
        for i in range(1, param['EHK']['amount']+1):
            ehk = solph.Transformer(
                label='Elektroheizkessel_' + str(i),
                inputs={enw: solph.Flow()},
                outputs={wnw: solph.Flow(
                    nominal_value=param['EHK']['Q_N'],
                    max=1,
                    min=0,
                    variable_costs=param['EHK']['op_cost_var'])},
                conversion_factors={wnw: param['EHK']['eta']})

            es_ref.add(ehk)

    if param['SLK']['active']:
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

    if param['BHKW']['active']:
        for i in range(1, param['BHKW']['amount']+1):
            bhkw = solph.components.GenericCHP(
                label='BHKW_' + str(i),
                fuel_input={gnw: solph.Flow(
                    H_L_FG_share_max=liste(param['BHKW']['H_L_FG_share_max']),
                    H_L_FG_share_min=liste(param['BHKW']['H_L_FG_share_min']),
                    nominal_value=param['BHKW']['Q_in'])},
                electrical_output={enw: solph.Flow(
                    variable_costs=param['BHKW']['op_cost_var'],
                    P_max_woDH=liste(param['BHKW']['P_max_woDH']),
                    P_min_woDH=liste(param['BHKW']['P_min_woDH']),
                    Eta_el_max_woDH=liste(param['BHKW']['Eta_el_max_woDH']),
                    Eta_el_min_woDH=liste(param['BHKW']['Eta_el_min_woDH']))},
                heat_output={wnw: solph.Flow(
                    Q_CW_min=liste(0),
                    Q_CW_max=liste(0))},
                Beta=liste(0),
                back_pressure=False)

            es_ref.add(bhkw)

    if param['GuD']['active']:
        for i in range(1, param['GuD']['amount']+1):
            gud = solph.components.GenericCHP(
                label='GuD_' + str(i),
                fuel_input={gnw: solph.Flow(
                    H_L_FG_share_max=liste(param['GuD']['H_L_FG_share_max']),
                    nominal_value=param['GuD']['Q_in'])},
                electrical_output={enw: solph.Flow(
                    variable_costs=param['GuD']['op_cost_var'],
                    P_max_woDH=liste(param['GuD']['P_max_woDH']),
                    P_min_woDH=liste(param['GuD']['P_min_woDH']),
                    Eta_el_max_woDH=liste(param['GuD']['Eta_el_max_woDH']),
                    Eta_el_min_woDH=liste(param['GuD']['Eta_el_min_woDH']))},
                heat_output={wnw: solph.Flow(
                    Q_CW_min=liste(param['GuD']['Q_CW_min']),
                    Q_CW_max=liste(0))},
                Beta=liste(param['GuD']['beta']),
                back_pressure=False)

            es_ref.add(gud)

    if param['BPT']['active']:
        for i in range(1, param['BPT']['amount']+1):
            bpt = solph.components.GenericCHP(
                label='bpt' + str(i),
                fuel_input={gnw: solph.Flow(
                    H_L_FG_share_max=liste(param['bpt']['H_L_FG_share_max']),
                    nominal_value=param['bpt']['Q_in'])},
                electrical_output={enw: solph.Flow(
                    variable_costs=param['bpt']['op_cost_var'],
                    P_max_woDH=liste(param['bpt']['P_max_woDH']),
                    P_min_woDH=liste(param['bpt']['P_min_woDH']),
                    Eta_el_max_woDH=liste(param['bpt']['Eta_el_max_woDH']),
                    Eta_el_min_woDH=liste(param['bpt']['Eta_el_min_woDH']))},
                heat_output={wnw: solph.Flow(
                    Q_CW_min=liste(0),
                    Q_CW_max=liste(0))},
                Beta=liste(0),
                back_pressure=True)

            es_ref.add(bpt)

    # 30% m-Teillast bei 65-114°C und 50% m-Teillast bei 115-124°C
    if param['HP']['active']:
        for i in range(1, param['HP']['amount']+1):
            hp = solph.components.OffsetTransformer(
                label='HP_' + str(i),
                inputs={enw: solph.Flow(
                    nominal_value=1,
                    max=data['P_max_hp'],
                    min=data['P_min_hp'],
                    variable_costs=param['HP']['op_cost_var'],
                    nonconvex=solph.NonConvex())},
                outputs={wnw: solph.Flow(
                    )},
                coefficients=[data['c_0_hp'], data['c_1_hp']])

            es_ref.add(hp)

    # Low temperature heat pump
    if param['LT-HP']['active']:
        for i in range(1, param['LT-HP']['amount']+1):
            lthp = solph.Transformer(
                label="LT-HP_" + str(i),
                inputs={lt_wnw: solph.Flow(),
                        enw: solph.Flow(
                            variable_costs=param['HP']['op_cost_var'])},
                outputs={wnw: solph.Flow()},
                conversion_factors={enw: 1/data['cop_lthp'],
                                    lt_wnw: (data['cop_lthp']-1)/data['cop_lthp']}
                # conversion_factors={enw: 1/cop_lt,
                #                     lt_wnw: (cop_lt-1)/cop_lt}
                )

            es_ref.add(lthp)

    ht_to_lt = solph.Transformer(
        label='HT_to_LT',
        inputs={wnw: solph.Flow()},
        outputs={lt_wnw: solph.Flow()}
        )

    es_ref.add(ht_to_lt)


        # %% Speicher

    # Saisonaler Speicher
    if param['TES']['active']:
        for i in range(1, param['TES']['amount']+1):
            tes = solph.components.GenericStorage(
                label='TES_' + str(i),
                nominal_storage_capacity=param['TES']['Q'],
                inputs={lt_wnw: solph.Flow(
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
                loss_rate=param['TES']['Q_rel_loss'],
                inflow_conversion_factor=param['TES']['inflow_conv'],
                outflow_conversion_factor=param['TES']['outflow_conv'])

            es_ref.add(tes)

    # %% Processing

        # %% Solve

    # Was bedeutet tee?
    model = solph.Model(es_ref)
    solph.constraints.limit_active_flow_count_by_keyword(
        model, 'storageflowlimit', lower_limit=0, upper_limit=1)
    # model.write('my_model.lp', io_options={'symbolic_solver_labels': True})
    model.solve(solver='gurobi', solve_kwargs={'tee': True},
                cmdline_options={"mipgap": "0.025"})

        # %% Ergebnisse Energiesystem

    # Ergebnisse in results
    results = solph.processing.results(model)

    # Main- und Metaergebnisse
    es_ref.results['main'] = solph.processing.results(model)
    es_ref.results['meta'] = solph.processing.meta_results(model)

    invest_ges = 0
    cost_Anlagen = 0
    labeldict = dict()

    # Busses
    data_gnw = views.node(results, 'Gasnetzwerk')['sequences']
    data_enw = views.node(results, 'Elektrizitätsnetzwerk')['sequences']
    data_wnw = views.node(results, 'Wärmenetzwerk')['sequences']
    data_lt_wnw = views.node(results, 'LT-Wärmenetzwerk')['sequences']

    labeldict[(('Gasquelle', 'Gasnetzwerk'), 'flow')] = 'H_source'
    labeldict[(('Elektrizitätsnetzwerk', 'Spotmarkt'), 'flow')] = (
        'P_spot_market')
    labeldict[(('Stromquelle', 'Elektrizitätsnetzwerk'), 'flow')] = 'P_source'
    labeldict[(('Wärmenetzwerk', 'Wärmebedarf'), 'flow')] = 'Q_demand'

    # Sources
    data_gas_source = views.node(results, 'Gasquelle')['sequences']
    data_elec_source = views.node(results, 'Stromquelle')['sequences']

    if param['Sol']['active']:
        data_solar_source = views.node(results, 'Solarthermie')['sequences']
        invest_ges += invest_solar
        cost_Anlagen += (
            data_solar_source[(('Solarthermie', 'LT-Wärmenetzwerk'), 'flow')].sum()
            * (0.01 * invest_solar)/(A*data['solar_data'].sum()))
        labeldict[(('Solarthermie', 'LT-Wärmenetzwerk'), 'flow')] = 'Q_Sol'

    if param['MR']['active']:
        data_mr_source = views.node(results, 'Mustrun')['sequences']
        labeldict[(('Mustrun', 'Wärmenetzwerk'), 'flow')] = 'Q_MR'

    # Sinks
    data_elec_sink = views.node(results, 'Spotmarkt')['sequences']
    data_heat_sink = views.node(results, 'Wärmebedarf')['sequences']

    if param['HT-EC']['active']:
        data_ht_ec = views.node(results, 'HT-EC')['sequences']
        labeldict[(('Wärmenetzwerk', 'HT-EC'), 'flow')] = 'Q_HT_EC'

    if param['LT-EC']['active']:
        data_lt_ec = views.node(results, 'LT-EC')['sequences']
        labeldict[(('LT-Wärmenetzwerk', 'LT-EC'), 'flow')] = 'Q_LT_EC'

    # Transformer
    if param['EHK']['active']:
        invest_ges += (param['EHK']['inv_spez']
                       * param['EHK']['Q_N']
                       * param['EHK']['amount'])

        for i in range(1, param['EHK']['amount']+1):
            label_id = 'Elektroheizkessel_' + str(i)
            data_ehk = views.node(results, label_id)['sequences']

            cost_Anlagen += (
                data_ehk[((label_id, 'Wärmenetzwerk'), 'flow')].sum()
                * param['EHK']['op_cost_var']
                + (param['EHK']['op_cost_fix']
                   * param['EHK']['Q_N'])
                )

            labeldict[((label_id, 'Wärmenetzwerk'), 'flow')] = (
                'Q_EHK_' + str(i))
            labeldict[(('Elektrizitätsnetzwerk', label_id), 'flow')] = (
                'P_zu_EHK_' + str(i))

    if param['SLK']['active']:
        invest_ges += (param['SLK']['inv_spez']
                       * param['SLK']['Q_N']
                       * param['SLK']['amount'])

        for i in range(1, param['SLK']['amount']+1):
            label_id = 'Spitzenlastkessel_' + str(i)
            data_slk = views.node(results, label_id)['sequences']

            cost_Anlagen += (
                data_slk[((label_id, 'Wärmenetzwerk'), 'flow')].sum()
                * (param['SLK']['op_cost_var']
                   + param['param']['energy_tax'])
                + (param['SLK']['op_cost_fix']
                   * param['SLK']['Q_N'])
                )

            labeldict[((label_id, 'Wärmenetzwerk'), 'flow')] = (
                'Q_SLK_' + str(i))
            labeldict[(('Gasnetzwerk', label_id), 'flow')] = 'H_SLK_' + str(i)

    if param['BHKW']['active']:
        invest_ges += (param['BHKW']['P_max_woDH']
                       * param['BHKW']['inv_spez']
                       * param['BHKW']['amount'])

        for i in range(1, param['BHKW']['amount']+1):
            label_id = 'BHKW_' + str(i)
            data_bhkw = views.node(results, label_id)['sequences']

            cost_Anlagen += (
                data_bhkw[((label_id, 'Elektrizitätsnetzwerk'), 'flow')].sum()
                * param['BHKW']['op_cost_var']
                + (param['BHKW']['op_cost_fix']
                   * param['BHKW']['P_max_woDH'])
                )

            labeldict[((label_id, 'Wärmenetzwerk'), 'flow')] = 'Q_' + label_id
            labeldict[((label_id, 'Elektrizitätsnetzwerk'), 'flow')] = (
                'P_' + label_id)
            labeldict[(('Gasnetzwerk', label_id), 'flow')] = 'H_' + label_id

    if param['GuD']['active']:
        invest_ges += (param['GuD']['P_max_woDH']
                       * param['GuD']['inv_spez']
                       * param['GuD']['amount'])

        for i in range(1, param['GuD']['amount']+1):
            label_id = 'GuD_' + str(i)
            data_gud = views.node(results, label_id)['sequences']

            cost_Anlagen += (
                data_gud[((label_id, 'Elektrizitätsnetzwerk'), 'flow')].sum()
                * param['GuD']['op_cost_var']
                + (param['GuD']['op_cost_fix']
                   * param['GuD']['P_max_woDH'])
                )

            labeldict[((label_id, 'Wärmenetzwerk'), 'flow')] = 'Q_' + label_id
            labeldict[((label_id, 'Elektrizitätsnetzwerk'), 'flow')] = (
                'P_' + label_id)
            labeldict[(('Gasnetzwerk', label_id), 'flow')] = 'H_' + label_id

    if param['HP']['active']:
        invest_ges += (param['HP']['inv_spez']
                       * data['P_max_hp'].max()
                       * param['HP']['amount'])

        for i in range(1, param['HP']['amount']+1):
            label_id = 'HP_' + str(i)
            data_hp = views.node(results, label_id)['sequences']

            cost_Anlagen += (
                data_hp[(('Elektrizitätsnetzwerk', label_id), 'flow')].sum()
                * param['HP']['op_cost_var']
                + (param['HP']['op_cost_fix']
                   * data['P_max_hp'].max())
                )

            labeldict[((label_id, 'Wärmenetzwerk'), 'flow')] = (
                'Q_ab_' + label_id)
            labeldict[(('Elektrizitätsnetzwerk', label_id), 'flow')] = (
                'P_zu_' + label_id)
            labeldict[(('Elektrizitätsnetzwerk', label_id), 'status')] = (
                'Status_' + label_id)

    if param['LT-HP']['active']:
        for i in range(1, param['LT-HP']['amount']+1):
            label_id = 'LT-HP_' + str(i)
            data_lt_hp = views.node(results, label_id)['sequences']

            invest_ges += (
                param['HP']['inv_spez']
                * data_wnw[((label_id, 'Wärmenetzwerk'), 'flow')].max()
                / data['cop_lthp'].mean())

            cost_Anlagen += (
                data_lt_hp[(('Elektrizitätsnetzwerk', label_id), 'flow')].sum()
                * param['HP']['op_cost_var']
                + (param['HP']['op_cost_fix']
                   * data_wnw[((label_id, 'Wärmenetzwerk'), 'flow')].max()
                   / data['cop_lthp'].mean())
                )

            labeldict[((label_id, 'Wärmenetzwerk'), 'flow')] = (
                'Q_ab_' + label_id)
            labeldict[(('Elektrizitätsnetzwerk', label_id), 'flow')] = (
                'P_zu_' + label_id)
            labeldict[(('LT-Wärmenetzwerk', label_id), 'flow')] = (
                'Q_zu_' + label_id)

    # Speicher
    if param['TES']['active']:
        invest_ges += (param['TES']['inv_spez']
                       * param['TES']['Q']
                       * param['TES']['amount'])

        for i in range(1, param['TES']['amount']+1):
            label_id = 'TES_' + str(i)
            data_tes = views.node(results, label_id)['sequences']

            cost_Anlagen += (
                data_tes[(('LT-Wärmenetzwerk', label_id), 'flow')].sum()
                * param['TES']['op_cost_var']
                + (param['TES']['op_cost_fix']
                   * param['TES']['Q'])
                )

            labeldict[((label_id, 'LT-Wärmenetzwerk'), 'flow')] = (
                'Q_ab_' + label_id)
            labeldict[((label_id, 'LT-Wärmenetzwerk'), 'status')] = (
                'Status_ab_' + label_id)
            labeldict[(('LT-Wärmenetzwerk', label_id), 'flow')] = (
                'Q_zu_' + label_id)
            labeldict[(('LT-Wärmenetzwerk', label_id), 'status')] = (
                'Status_zu_' + label_id)
            labeldict[((label_id, 'None'), 'storage_content')] = (
                'Speicherstand_' + label_id)

    # Knoten
    labeldict[(('HT_to_LT', 'LT-Wärmenetzwerk'), 'flow')] = 'Q_HT2LT_LT-WNW'
    labeldict[(('Wärmenetzwerk', 'HT_to_LT'), 'flow')] = 'Q_WNW_HT2LT'


        # %% Zahlungsströme Ergebnis

    objective = abs(es_ref.results['meta']['objective'])


        # %% Geldflüsse

    # # Primärenergiebezugskoste
    cost_gas = (data_gnw[(('Gasquelle', 'Gasnetzwerk'), 'flow')].sum()
                * (param['param']['gas_price']
                   + param['param']['co2_certificate']))

    el_flow = np.array(data_enw[(('Stromquelle', 'Elektrizitätsnetzwerk'),
                                 'flow')])
    cost_el_timeseries = np.array(data['el_price'])
    cost_el_array = el_flow * cost_el_timeseries
    cost_el = cost_el_array.sum()

    # Erlöse
    revenues_spotmarkt_timeseries = (np.array(data_enw[(('Elektrizitätsnetzwerk',
                                                         'Spotmarkt'), 'flow')])
                                     * np.array(data['el_spot_price']))
    revenues_spotmarkt = revenues_spotmarkt_timeseries.sum()

    revenues_heatdemand = (data_wnw[(('Wärmenetzwerk', 'Wärmebedarf'),
                                     'flow')].sum()
                           * param['param']['heat_price'])
    # Summe der Geldströme
    Gesamtbetrag = (revenues_spotmarkt + revenues_heatdemand
                    - cost_Anlagen - cost_gas - cost_el)


        # %% Output Ergebnisse

    # Umbenennen der Spaltennamen der Ergebnisdataframes
    result_dfs = [data_wnw, data_lt_wnw, data_tes, data_enw, data_gnw]

    for df in result_dfs:
        result_labelling(df)

    # Daten zum Plotten der Wärmeversorgung
    df1 = pd.concat([data_wnw, data_lt_wnw, data_tes, data_enw],
                    axis=1)
    df1.to_csv(path.join(
        dirpath, 'Ergebnisse\\Generic Model v2a\\data_wnw.csv'),
               sep=";")

    # Daten zum Plotten der Investitionsrechnung
    df2 = pd.DataFrame(data={'invest_ges': [invest_ges],
                             'Q_tes': [param['TES']['Q']],
                             'total_heat_demand': [total_heat_demand],
                             'Gesamtbetrag': [Gesamtbetrag]})
    df2.to_csv(path.join(
        dirpath, 'Ergebnisse\\Generic Model v2a\\data_Invest.csv'),
               sep=";")

    # Daten für die ökologische Bewertung
    df3 = pd.concat([data_gnw[['H_source']],
                     data_enw[['P_spot_market', 'P_source']]],
                    axis=1)
    df3.to_csv(path.join(
        dirpath, 'Ergebnisse\\Generic Model v2a\\data_CO2.csv'),
               sep=";")


if __name__ == '__main__':
    main()
