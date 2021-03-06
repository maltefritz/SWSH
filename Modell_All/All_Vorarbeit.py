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
from sys import exit
import oemof.solph as solph
from oemof.solph import views
import pandas as pd
import numpy as np
# from invest import invest_st


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
        raise ValueError("Choose a valid collector type: 'flat' or 'vacuum'")


def liste(parameter):
    """Get timeseries list of parameter for solph components."""
    return [parameter for p in range(0, periods)]


# %% Preprocessing

    # %% Daten einlesen

dirpath = path.abspath(path.join(__file__, "../.."))
filename = path.join(dirpath, 'Eingangsdaten\\simulation_data.csv')
data = pd.read_csv(filename, sep=";")
filename = path.join(dirpath, 'Eingangsdaten\\All_parameters.csv')
param = pd.read_csv(filename, sep=";", index_col=['plant', 'parameter'])

# TODO
cop_lt = 4.9501
A = param.loc[('Sol', 'A'), 'value']

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
if (param.loc[('LT-HP', 'active'), 'value'] == 1
    and param.loc[('Sol', 'active'), 'value'] == 0
    and param.loc[('TES', 'active'), 'value'] == 0):
    print("WARNING: You can't have the low temp heat pump active without ",
          "using either the TES or solar heat.")
    exit()
elif (param.loc[('LT-HP', 'active'), 'value'] == 0
      and (param.loc[('Sol', 'active'), 'value'] == 1
      or param.loc[('TES', 'active'), 'value'] == 1)):
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
        variable_costs=(param.loc[('param', 'gas_price'), 'value']
                        + param.loc[('param', 'co2_certificate'), 'value']))})

elec_source = solph.Source(
    label='Stromquelle',
    outputs={enw: solph.Flow(
        variable_costs=(param.loc[('param', 'elec_consumer_charges'), 'value']
                        + data['el_spot_price']))})

es_ref.add(gas_source, elec_source)

if param.loc[('Sol', 'active'), 'value'] == 1:
    solar_source = solph.Source(
        label='Solarthermie',
        outputs={lt_wnw: solph.Flow(
            variable_costs=(0.01 * invest_solar)/(A*data['solar_data'].sum()),
            nominal_value=(max(data['solar_data'])*A),
            actual_value=(data['solar_data'])/(max(data['solar_data'])),
            fixed=True)})

    es_ref.add(solar_source)

if param.loc[('MR', 'active'), 'value'] == 1:
    mr_source = solph.Source(label='Mustrun',
                             outputs={wnw: solph.Flow(
                                variable_costs=0,
                                nominal_value=float(param.loc[(
                                    "MR", "Q_N"), "value"]),
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
        variable_costs=-param.loc[('param', 'heat_price'), 'value'],
        nominal_value=max(heat_demand_local),
        actual_value=heat_demand_local/max(heat_demand_local),
        fixed=True)})

es_ref.add(elec_sink, heat_sink)

if param.loc[('EC', 'active'), 'value'] == 1:
    ec_sink = solph.Sink(label='Emergency-cooling',
                         inputs={wnw: solph.Flow(
                                 variable_costs=0)})

    es_ref.add(ec_sink)

    # %% Transformer

if param.loc[('EHK', 'active'), 'value'] == 1:
    ehk = solph.Transformer(
        label='Elektroheizkessel',
        inputs={enw: solph.Flow()},
        outputs={wnw: solph.Flow(
            nominal_value=param.loc[('EHK', 'Q_N'), 'value'],
            max=1,
            min=0,
            variable_costs=param.loc[('EHK', 'op_cost_var'), 'value'])},
        conversion_factors={wnw: param.loc[('EHK', 'eta'), 'value']})

    es_ref.add(ehk)

if param.loc[('SLK', 'active'), 'value'] == 1:
    slk = solph.Transformer(
        label='Spitzenlastkessel',
        inputs={gnw: solph.Flow()},
        outputs={wnw: solph.Flow(
            nominal_value=param.loc[('SLK', 'Q_N'), 'value'],
            max=1,
            min=0,
            variable_costs=(param.loc[('SLK', 'op_cost_var'), 'value']
                            + param.loc[('param', 'energy_tax'), 'value']))},
        conversion_factors={wnw: param.loc[('SLK', 'eta'), 'value']})

    es_ref.add(slk)

if param.loc[('BHKW', 'active'), 'value'] == 1:
    bhkw = solph.components.GenericCHP(
        label='BHKW',
        fuel_input={gnw: solph.Flow(
            H_L_FG_share_max=liste(param.loc[('BHKW', 'H_L_FG_share_max'), 'value']),
            H_L_FG_share_min=liste(param.loc[('BHKW', 'H_L_FG_share_min'), 'value']),
            nominal_value=param.loc[('BHKW', 'Q_in'), 'value'])},
        electrical_output={enw: solph.Flow(
            variable_costs=param.loc[('BHKW', 'op_cost_var'), 'value'],
            P_max_woDH=liste(param.loc[('BHKW', 'P_max_woDH'), 'value']),
            P_min_woDH=liste(param.loc[('BHKW', 'P_min_woDH'), 'value']),
            Eta_el_max_woDH=liste(param.loc[('BHKW', 'Eta_el_max_woDH'), 'value']),
            Eta_el_min_woDH=liste(param.loc[('BHKW', 'Eta_el_min_woDH'), 'value']))},
        heat_output={wnw: solph.Flow(
            Q_CW_min=liste(0),
            Q_CW_max=liste(0))},
        Beta=liste(0),
        back_pressure=False)

    es_ref.add(bhkw)

if param.loc[('GuD', 'active'), 'value'] == 1:
    gud = solph.components.GenericCHP(
        label='GuD',
        fuel_input={gnw: solph.Flow(
            H_L_FG_share_max=liste(param.loc[('GuD', 'H_L_FG_share_max'), 'value']),
            nominal_value=param.loc[('GuD', 'Q_in'), 'value'])},
        electrical_output={enw: solph.Flow(
            variable_costs=param.loc[('GuD', 'op_cost_var'), 'value'],
            P_max_woDH=liste(param.loc[('GuD', 'P_max_woDH'), 'value']),
            P_min_woDH=liste(param.loc[('GuD', 'P_min_woDH'), 'value']),
            Eta_el_max_woDH=liste(param.loc[('GuD', 'Eta_el_max_woDH'), 'value']),
            Eta_el_min_woDH=liste(param.loc[('GuD', 'Eta_el_min_woDH'), 'value']))},
        heat_output={wnw: solph.Flow(
            Q_CW_min=liste(param.loc[('GuD', 'Q_CW_min'), 'value']),
            Q_CW_max=liste(0))},
        Beta=liste(param.loc[('GuD', 'beta'), 'value']),
        back_pressure=False)

    es_ref.add(gud)

if param.loc[('BPT', 'active'), 'value'] == 1:
    bpt = solph.components.GenericCHP(
        label='bpt',
        fuel_input={gnw: solph.Flow(
            H_L_FG_share_max=liste(param.loc[('bpt', 'H_L_FG_share_max'), 'value']),
            nominal_value=param.loc[('bpt', 'Q_in'), 'value'])},
        electrical_output={enw: solph.Flow(
            variable_costs=param.loc[('bpt', 'op_cost_var'), 'value'],
            P_max_woDH=liste(param.loc[('bpt', 'P_max_woDH'), 'value']),
            P_min_woDH=liste(param.loc[('bpt', 'P_min_woDH'), 'value']),
            Eta_el_max_woDH=liste(param.loc[('bpt', 'Eta_el_max_woDH'), 'value']),
            Eta_el_min_woDH=liste(param.loc[('bpt', 'Eta_el_min_woDH'), 'value']))},
        heat_output={wnw: solph.Flow(
            Q_CW_min=liste(0),
            Q_CW_max=liste(0))},
        Beta=liste(0),
        back_pressure=True)

    es_ref.add(bpt)

# 30% m-Teillast bei 65-114°C und 50% m-Teillast bei 115-124°C
if param.loc[('HP', 'active'), 'value'] == 1:
    hp = solph.components.OffsetTransformer(
        label='Wärmepumpe',
        inputs={enw: solph.Flow(
            nominal_value=1,
            max=data['P_max_hp'],
            min=data['P_min_hp'],
            variable_costs=param.loc[('HP', 'op_cost_var'), 'value'],
            nonconvex=solph.NonConvex())},
        outputs={wnw: solph.Flow(
            )},
        coefficients=[data['c_0_hp'], data['c_1_hp']])

    es_ref.add(hp)


    # %% Speicher

# Saisonaler Speicher
if param.loc[('TES', 'active'), 'value'] == 1:
    tes = solph.components.GenericStorage(
        label='Wärmespeicher',
        nominal_storage_capacity=param.loc[('TES', 'Q'), 'value'],
        inputs={wnw: solph.Flow(
            storageflowlimit=True,
            nominal_value=param.loc[('TES', 'Q_N_in'), 'value'],
            max=param.loc[('TES', 'Q_rel_in_max'), 'value'],
            min=param.loc[('TES', 'Q_rel_in_min'), 'value'],
            variable_costs=param.loc[('TES', 'op_cost_var'), 'value'],
            nonconvex=solph.NonConvex(
                minimum_uptime=int(param.loc[('TES', 'min_uptime'), 'value']),
                initial_status=int(param.loc[('TES', 'init_status'), 'value'])))},
        outputs={lt_wnw: solph.Flow(
            storageflowlimit=True,
            nominal_value=param.loc[('TES', 'Q_N_out'), 'value'],
            max=param.loc[('TES', 'Q_rel_out_max'), 'value'],
            min=param.loc[('TES', 'Q_rel_out_min'), 'value'],
            nonconvex=solph.NonConvex(
                minimum_uptime=int(param.loc[('TES', 'min_uptime'), 'value'])))},
        initial_storage_level=param.loc[('TES', 'init_storage'), 'value'],
        loss_rate=param.loc[('TES', 'Q_rel_loss'), 'value'],
        inflow_conversion_factor=param.loc[('TES', 'inflow_conv'), 'value'],
        outflow_conversion_factor=param.loc[('TES', 'outflow_conv'), 'value'])

    es_ref.add(tes)

# Low temperature heat pump

if param.loc[('LT-HP', 'active'), 'value'] == 1:
    lthp = solph.Transformer(
        label="LT-WP",
        inputs={lt_wnw: solph.Flow(),
                enw: solph.Flow(
                    variable_costs=param.loc[('HP', 'op_cost_var'), 'value'])},
        outputs={wnw: solph.Flow()},
        conversion_factors={enw: 1/data['cop_lthp'],
                            lt_wnw: (data['cop_lthp']-1)/data['cop_lthp']}
        # conversion_factors={enw: 1/cop_lt,
        #                     lt_wnw: (cop_lt-1)/cop_lt}
        )

    es_ref.add(lthp)

# %% Processing

    # %% Solve

# Was bedeutet tee?
model = solph.Model(es_ref)
solph.constraints.limit_active_flow_count_by_keyword(
    model, 'storageflowlimit', lower_limit=0, upper_limit=1)
model.solve(solver='gurobi', solve_kwargs={'tee': True},
            cmdline_options={"mipgap": "0.10"})

    # %% Ergebnisse Energiesystem

# Ergebnisse in results
results = solph.processing.results(model)

# Main- und Metaergebnisse
es_ref.results['main'] = solph.processing.results(model)
es_ref.results['meta'] = solph.processing.meta_results(model)

invest_ges = 0
cost_Anlagen = 0
labeldict = {}

# Busses
data_gnw = views.node(results, 'Gasnetzwerk')['sequences']
data_enw = views.node(results, 'Elektrizitätsnetzwerk')['sequences']
data_wnw = views.node(results, 'Wärmenetzwerk')['sequences']
data_lt_wnw = views.node(results, 'LT-Wärmenetzwerk')['sequences']

labeldict[(('Gasquelle', 'Gasnetzwerk'), 'flow')] = 'H_source'
labeldict[(('Elektrizitätsnetzwerk', 'Spotmarkt'), 'flow')] = 'P_spot_market'
labeldict[(('Stromquelle', 'Elektrizitätsnetzwerk'), 'flow')] = 'P_source'
labeldict[(('Wärmenetzwerk', 'Wärmebedarf'), 'flow')] = 'Q_demand'

# Sources
data_gas_source = views.node(results, 'Gasquelle')['sequences']
data_elec_source = views.node(results, 'Stromquelle')['sequences']

if param.loc[('Sol', 'active'), 'value'] == 1:
    data_solar_source = views.node(results, 'Solarthermie')['sequences']
    invest_ges += invest_solar
    cost_Anlagen += (data_solar_source[(('Solarthermie', 'LT-Wärmenetzwerk'), 'flow')].sum()
                     * (0.01 * invest_solar)/(A*data['solar_data'].sum()))
    labeldict[(('Solarthermie', 'LT-Wärmenetzwerk'), 'flow')] = 'Q_Sol'

if param.loc[('MR', 'active'), 'value'] == 1:
    data_mr_source = views.node(results, 'Mustrun')['sequences']
    labeldict[(('Mustrun', 'Wärmenetzwerk'), 'flow')] = 'Q_MR'

# Sinks
data_elec_sink = views.node(results, 'Spotmarkt')['sequences']
data_heat_sink = views.node(results, 'Wärmebedarf')['sequences']

if param.loc[('EC', 'active'), 'value'] == 1:
    data_mr_source = views.node(results, 'Emergency-cooling')['sequences']
    labeldict[(('Wärmenetzwerk', 'Emergency-cooling'), 'flow')] = 'Q_EC'

# Transformer
if param.loc[('EHK', 'active'), 'value'] == 1:
    data_ehk = views.node(results, 'Elektroheizkessel')['sequences']
    invest_ges += (param.loc[('EHK', 'inv_spez'), 'value']
                   * param.loc[('EHK', 'Q_N'), 'value'])
    cost_Anlagen += (data_ehk[(('Elektroheizkessel', 'Wärmenetzwerk'), 'flow')].sum()
                     * param.loc[('EHK', 'op_cost_var'), 'value']
                     + (param.loc[('EHK', 'op_cost_fix'), 'value']
                        * param.loc[('EHK', 'Q_N'), 'value']))
    labeldict[(('Elektroheizkessel', 'Wärmenetzwerk'), 'flow')] = 'Q_EHK'
    labeldict[(('Elektrizitätsnetzwerk', 'Elektroheizkessel'), 'flow')] = 'P_zu_EHK'

if param.loc[('SLK', 'active'), 'value'] == 1:
    data_slk = views.node(results, 'Spitzenlastkessel')['sequences']
    invest_ges += (param.loc[('SLK', 'inv_spez'), 'value']
                   * param.loc[('SLK', 'Q_N'), 'value'])
    cost_Anlagen += (data_slk[(('Spitzenlastkessel', 'Wärmenetzwerk'), 'flow')].sum()
                     * (param.loc[('SLK', 'op_cost_var'), 'value']
                     + param.loc[('param', 'energy_tax'), 'value'])
                     + (param.loc[('SLK', 'op_cost_fix'), 'value']
                        * param.loc[('SLK', 'Q_N'), 'value']))
    labeldict[(('Spitzenlastkessel', 'Wärmenetzwerk'), 'flow')] = 'Q_SLK'
    labeldict[(('Gasnetzwerk', 'Spitzenlastkessel'), 'flow')] = 'H_SLK'

if param.loc[('BHKW', 'active'), 'value'] == 1:
    data_bhkw = data_bhkw = views.node(results, 'BHKW')['sequences']
    invest_ges += (param.loc[('BHKW', 'P_max_woDH'), 'value']
                   * param.loc[('BHKW', 'inv_spez'), 'value'])
    cost_Anlagen += (data_bhkw[(('BHKW', 'Elektrizitätsnetzwerk'), 'flow')].sum()
                     * param.loc[('BHKW', 'op_cost_var'), 'value']
                     + (param.loc[('BHKW', 'op_cost_fix'), 'value']
                        * param.loc[('BHKW', 'P_max_woDH'), 'value']))
    labeldict[(('BHKW', 'Wärmenetzwerk'), 'flow')] = 'Q_BHKW'
    labeldict[(('BHKW', 'Elektrizitätsnetzwerk'), 'flow')] = 'P_BHKW'
    labeldict[(('Gasnetzwerk', 'BHKW'), 'flow')] = 'H_BHKW'

if param.loc[('GuD', 'active'), 'value'] == 1:
    data_gud = data_gud = views.node(results, 'GuD')['sequences']
    invest_ges += (param.loc[('GuD', 'P_max_woDH'), 'value']
                   * param.loc[('GuD', 'inv_spez'), 'value'])
    cost_Anlagen += (data_gud[(('GuD', 'Elektrizitätsnetzwerk'), 'flow')].sum()
                     * param.loc[('GuD', 'op_cost_var'), 'value']
                     + (param.loc[('GuD', 'op_cost_fix'), 'value']
                        * param.loc[('GuD', 'P_max_woDH'), 'value']))
    labeldict[(('GuD', 'Wärmenetzwerk'), 'flow')] = 'Q_GuD'
    labeldict[(('GuD', 'Elektrizitätsnetzwerk'), 'flow')] = 'P_GuD'
    labeldict[(('Gasnetzwerk', 'GuD'), 'flow')] = 'H_GuD'

if param.loc[('HP', 'active'), 'value'] == 1:
    data_hp = views.node(results, 'Wärmepumpe')['sequences']
    invest_ges += (param.loc[('HP', 'inv_spez'), 'value']
                   * data['P_max_hp'].max())
    cost_Anlagen += (data_hp[(('Elektrizitätsnetzwerk', 'Wärmepumpe'), 'flow')].sum()
                     * param.loc[('HP', 'op_cost_var'), 'value']
                     + (param.loc[('HP', 'op_cost_fix'), 'value']
                        * data['P_max_hp'].max()))
    labeldict[(('Wärmepumpe', 'Wärmenetzwerk'), 'flow')] = 'Q_ab_HP'
    labeldict[(('Elektrizitätsnetzwerk', 'Wärmepumpe'), 'flow')] = 'P_zu_HP'
    labeldict[(('Elektrizitätsnetzwerk', 'Wärmepumpe'), 'status')] = 'Status_HP'

if param.loc[('LT-HP', 'active'), 'value'] == 1:
    data_lt_hp = views.node(results, 'LT-WP')['sequences']
    invest_ges += (param.loc[('HP', 'inv_spez'), 'value']
                   * data_wnw[(('LT-WP', 'Wärmenetzwerk'), 'flow')].max()
                   / data['cop_lthp'].mean())
    cost_Anlagen += (data_lt_hp[(('Elektrizitätsnetzwerk', 'LT-WP'), 'flow')].sum()
                     * param.loc[('HP', 'op_cost_var'), 'value']
                     + (param.loc[('HP', 'op_cost_fix'), 'value']
                        * data_wnw[(('LT-WP', 'Wärmenetzwerk'), 'flow')].max()
                        / data['cop_lthp'].mean()))
    labeldict[(('LT-WP', 'Wärmenetzwerk'), 'flow')] = 'Q_ab_LT-HP'
    labeldict[(('Elektrizitätsnetzwerk', 'LT-WP'), 'flow')] = 'P_zu_LT-HP'
    labeldict[(('LT-Wärmenetzwerk', 'LT-WP'), 'flow')] = 'Q_zu_LT-HP'

# Speicher
if param.loc[('TES', 'active'), 'value'] == 1:
    data_tes = views.node(results, 'Wärmespeicher')['sequences']
    invest_ges += (param.loc[('TES', 'inv_spez'), 'value']
                   * param.loc[('TES', 'Q'), 'value'])
    cost_Anlagen += (data_tes[(('Wärmenetzwerk', 'Wärmespeicher'), 'flow')].sum()
                     * param.loc[('TES', 'op_cost_var'), 'value']
                     + (param.loc[('TES', 'op_cost_fix'), 'value']
                        * param.loc[('TES', 'Q'), 'value']))
    labeldict[(('Wärmespeicher', 'LT-Wärmenetzwerk'), 'flow')] = 'Q_ab_TES'
    labeldict[(('Wärmespeicher', 'LT-Wärmenetzwerk'), 'status')] = 'Status_ab_TES'
    labeldict[(('Wärmenetzwerk', 'Wärmespeicher'), 'flow')] = 'Q_zu_TES'
    labeldict[(('Wärmenetzwerk', 'Wärmespeicher'), 'status')] = 'Status_zu_TES'
    labeldict[(('Wärmespeicher', 'None'), 'storage_content')] = 'Speicherstand'


    # %% Zahlungsströme Ergebnis

objective = abs(es_ref.results['meta']['objective'])


    # %% Geldflüsse

# # Primärenergiebezugskoste
cost_gas = (data_gnw[(('Gasquelle', 'Gasnetzwerk'), 'flow')].sum()
            * (param.loc[('param', 'gas_price'), 'value']
               + param.loc[('param', 'co2_certificate'), 'value']))

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
                       * param.loc[('param', 'heat_price'), 'value'])
# Summe der Geldströme
Gesamtbetrag = (revenues_spotmarkt + revenues_heatdemand
                - cost_Anlagen - cost_gas - cost_el)


    # %% Output Ergebnisse

# Umbenennen der Spaltennamen der Ergebnisdataframes

for col in data_wnw.columns:
    if col in labeldict:
        data_wnw.rename(columns={col: labeldict[col]}, inplace=True)
    else:
        print(col, ' not in labeldict')

for col in data_lt_wnw.columns:
    if col in labeldict:
        data_lt_wnw.rename(columns={col: labeldict[col]}, inplace=True)
    else:
        print(col, ' not in labeldict')

for col in data_tes.columns:
    if col in labeldict:
        data_tes.rename(columns={col: labeldict[col]}, inplace=True)
    else:
        print(col, ' not in labeldict')

for col in data_enw.columns:
    if col in labeldict:
        data_enw.rename(columns={col: labeldict[col]}, inplace=True)
    else:
        print(col, ' not in labeldict')

for col in data_gnw.columns:
    if col in labeldict:
        data_gnw.rename(columns={col: labeldict[col]}, inplace=True)
    else:
        print(col, ' not in labeldict')


# Daten zum Plotten der Wärmeversorgung

df1 = pd.concat([data_wnw[['Q_BHKW', 'Q_EHK', 'Q_GuD', 'Q_ab_LT-HP', 'Q_SLK',
                           'Q_demand', 'Q_zu_TES', 'Q_ab_HP']],
                 data_lt_wnw[['Q_zu_LT-HP', 'Q_Sol', 'Q_ab_TES']],
                 data_tes[['Speicherstand']],
                 data_enw[['P_BHKW', 'P_GuD', 'P_zu_HP', 'P_zu_LT-HP']]],
                axis=1)
df1.to_csv(path.join(dirpath, 'Ergebnisse\\Vorarbeit\\Vor_wnw.csv'),
           sep=";")


# Daten zum Plotten der Investitionsrechnung

df2 = pd.DataFrame(data={'invest_ges': [invest_ges],
                         'Q_tes': [param.loc[('TES', 'Q'), 'value']],
                         'total_heat_demand': [total_heat_demand],
                         'Gesamtbetrag': [Gesamtbetrag]})
df2.to_csv(path.join(dirpath, 'Ergebnisse\\Vorarbeit\\Vor_Invest.csv'),
           sep=";")


# Daten für die ökologische Bewertung

df3 = pd.concat([data_gnw[['H_source']],
                 data_enw[['P_spot_market', 'P_source']]],
                axis=1)
df3.to_csv(path.join(dirpath, 'Ergebnisse\\Vorarbeit\\Vor_CO2.csv'), sep=";")
