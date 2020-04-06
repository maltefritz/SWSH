"""Energiesystem mit Speicher und Solarthermie.

Created on Tue Jan  7 10:04:39 2020

@author: Malte Fritz

Komponenten:
    - BHKW
    - Elektroheizkessel
    - Spitzenlastkessel
    - TES
    - Solarthermie
Wärmebedarf von 1/20 von dem Wärmebedarf Flensburgs aus dem Jahr 2016

"""
import os.path as path
import oemof.solph as solph
import oemof.tabular.facades as fc
import oemof.outputlib as outputlib
import pandas as pd
import numpy as np
# from invest import invest_st


def invest_st(A, col_type=''):
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

invest_solar = invest_st(A, col_type="flat")

    # %% Zeitreihe

periods = len(data)
date_time_index = pd.date_range('1/1/2016 00:00:00', periods=periods, freq='h')

    # %% Energiesystem erstellen

es_ref = solph.EnergySystem(timeindex=date_time_index)


# %% Randbedinungen

    # %% Wärmebedarf
# rel_demand ist die Variable, die den Wärmebedarf der Region
# prozentual von FL angibt.

heat_demand_FL = data['heat_demand']
rel_heat_demand = 1
heat_demand_local = heat_demand_FL * rel_heat_demand
total_heat_demand = float(heat_demand_local.sum())

# %% Energiesystem

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

solar_source = solph.Source(
    label='Solarthermie',
    outputs={lt_wnw: solph.Flow(
        variable_costs=(0.01 * invest_solar)/(A*data['solar_data'].sum()),
        nominal_value=(max(data['solar_data'])*A),
        actual_value=(data['solar_data'])/(max(data['solar_data'])),
        fixed=True)})

es_ref.add(gas_source, elec_source, solar_source)

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

    # %% Transformer

ehk = solph.Transformer(
    label='Elektroheizkessel',
    inputs={enw: solph.Flow()},
    outputs={wnw: solph.Flow(
        nominal_value=param.loc[('EHK', 'Q_N'), 'value'],
        max=1,
        min=0,
        variable_costs=param.loc[('EHK', 'op_cost_var'), 'value'])},
    conversion_factors={wnw: param.loc[('EHK', 'eta'), 'value']})

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
        Q_CW_min=[0 for p in range(0, periods)])},
    Beta=[0 for p in range(0, periods)],
    back_pressure=False)

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
        Q_CW_min=liste(param.loc[('GuD', 'Q_CW_min'), 'value']))},
    Beta=liste(param.loc[('GuD', 'beta'), 'value']),
    back_pressure=False)

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

es_ref.add(ehk, slk, bhkw, gud, hp)

    # %% Speicher

# Saisonaler Speicher

tes = solph.components.GenericStorage(
    label='Wärmespeicher',
    nominal_storage_capacity=param.loc[('TES', 'Q'), 'value'],
    inputs={wnw: solph.Flow(
        nominal_value=85,
        max=1,
        min=0.1,
        variable_costs=param.loc[('TES', 'op_cost_var'), 'value'],
        nonconvex=solph.NonConvex(
            minimum_uptime=int(param.loc[('TES', 'min_uptime'), 'value']),
            initial_status=int(param.loc[('TES', 'init_status'), 'value'])))},
    outputs={lt_wnw: solph.Flow(
        nominal_value=85,
        max=1,
        min=0.1,
        nonconvex=solph.NonConvex(
            minimum_uptime=int(param.loc[('TES', 'min_uptime'), 'value']),
            initial_status=int(param.loc[('TES', 'init_status'), 'value'])))},
    initial_storage_level=param.loc[('TES', 'init_storage'), 'value'],
    inflow_conversion_factor=param.loc[('TES', 'inflow_conv'), 'value'],
    outflow_conversion_factor=param.loc[('TES', 'outflow_conv'), 'value'])

# Low temperature heat pump

# lthp = fc.HeatPump(
#             label="LT-WP",
#             carrier="electricity",
#             carrier_cost=param.loc[('HP', 'op_cost_var'), 'value'],
#             capacity=200,
#             tech="hp",
#             cop=cop_lt,
#             electricity_bus=enw,
#             high_temperature_bus=wnw,
#             low_temperature_bus=lt_wnw)

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

es_ref.add(tes, lthp)

# %% Processing

    # %% Solve

# Was bedeutet tee?
model = solph.Model(es_ref)
model.solve(solver='gurobi', solve_kwargs={'tee': True},
            cmdline_options={"mipgap": "0.1"})

    # %% Ergebnisse Energiesystem

# Ergebnisse in results
results = outputlib.processing.results(model)

# Main- und Metaergebnisse
es_ref.results['main'] = outputlib.processing.results(model)
es_ref.results['meta'] = outputlib.processing.meta_results(model)

# Busses
data_gnw = outputlib.views.node(results, 'Gasnetzwerk')['sequences']
data_enw = outputlib.views.node(results, 'Elektrizitätsnetzwerk')['sequences']
data_wnw = outputlib.views.node(results, 'Wärmenetzwerk')['sequences']
data_lt_wnw = outputlib.views.node(results, 'LT-Wärmenetzwerk')['sequences']

# Sources
data_gas_source = outputlib.views.node(results, 'Gasquelle')['sequences']
data_elec_source = outputlib.views.node(results, 'Stromquelle')['sequences']
data_solar_source = outputlib.views.node(results, 'Solarthermie')['sequences']

# Sinks
data_elec_sink = outputlib.views.node(results, 'Spotmarkt')['sequences']
data_heat_sink = outputlib.views.node(results, 'Wärmebedarf')['sequences']

# Transformer
data_ehk = outputlib.views.node(results, 'Elektroheizkessel')['sequences']
data_slk = outputlib.views.node(results, 'Spitzenlastkessel')['sequences']
data_bhkw = outputlib.views.node(results, 'BHKW')['sequences']
data_gud = outputlib.views.node(results, 'GuD')['sequences']
data_hp = outputlib.views.node(results, 'Wärmepumpe')['sequences']
data_lt_hp = outputlib.views.node(results, 'LT-WP')['sequences']

# Speicher
data_tes = outputlib.views.node(results, 'Wärmespeicher')['sequences']


    # %% Investionskosten

invest_ehk = (param.loc[('EHK', 'inv_spez'), 'value']
              * param.loc[('EHK', 'Q_N'), 'value'])

invest_slk = (param.loc[('SLK', 'inv_spez'), 'value']
              * param.loc[('SLK', 'Q_N'), 'value'])

invest_bhkw = (param.loc[('BHKW', 'P_max_woDH'), 'value']
               * param.loc[('BHKW', 'inv_spez'), 'value'])

invest_gud = (param.loc[('GuD', 'P_max_woDH'), 'value']
              * param.loc[('GuD', 'inv_spez'), 'value'])

invest_hp = (param.loc[('HP', 'inv_spez'), 'value']
             * data['P_max_hp'].max())

invest_lt_hp = (param.loc[('HP', 'inv_spez'), 'value']
                * data_wnw[(('LT-WP', 'Wärmenetzwerk'), 'flow')].max()/cop_lt)

invest_tes = (param.loc[('TES', 'inv_spez'), 'value']
              * param.loc[('TES', 'Q'), 'value'])

invest_ges = (invest_solar + invest_ehk + invest_slk + invest_bhkw
              + invest_gud + invest_hp + invest_lt_hp + invest_tes)

    # %% Zahlungsströme Ergebnis

objective = abs(es_ref.results['meta']['objective'])


    # %% Geldflüsse

# Ausgaben

# # Anlagenbettriebskosten
cost_tes = (data_tes[(('Wärmenetzwerk', 'Wärmespeicher'), 'flow')].sum()
            * param.loc[('TES', 'op_cost_var'), 'value']
            + (param.loc[('TES', 'op_cost_fix'), 'value']
               * param.loc[('TES', 'Q'), 'value']))

cost_st = (data_solar_source[(('Solarthermie', 'LT-Wärmenetzwerk'), 'flow')].sum()
           * (0.01 * invest_solar)/(A*data['solar_data'].sum()))

cost_bhkw = (data_bhkw[(('BHKW', 'Elektrizitätsnetzwerk'), 'flow')].sum()
             * param.loc[('BHKW', 'op_cost_var'), 'value']
             + (param.loc[('BHKW', 'op_cost_fix'), 'value']
                * param.loc[('BHKW', 'P_max_woDH'), 'value']))

cost_gud = (data_gud[(('GuD', 'Elektrizitätsnetzwerk'), 'flow')].sum()
            * param.loc[('GuD', 'op_cost_var'), 'value']
            + (param.loc[('GuD', 'op_cost_fix'), 'value']
               * param.loc[('GuD', 'P_max_woDH'), 'value']))

cost_slk = (data_slk[(('Spitzenlastkessel', 'Wärmenetzwerk'), 'flow')].sum()
            * (param.loc[('SLK', 'op_cost_var'), 'value']
               + param.loc[('param', 'energy_tax'), 'value'])
            + (param.loc[('SLK', 'op_cost_fix'), 'value']
               * param.loc[('SLK', 'Q_N'), 'value']))

cost_hp = (data_hp[(('Elektrizitätsnetzwerk', 'Wärmepumpe'), 'flow')].sum()
           * param.loc[('HP', 'op_cost_var'), 'value']
           + (param.loc[('HP', 'op_cost_fix'), 'value']
              * data['P_max_hp'].max()))

cost_lt_hp = (data_lt_hp[(('Elektrizitätsnetzwerk', 'LT-WP'), 'flow')].sum()
              * param.loc[('HP', 'op_cost_var'), 'value']
              + (param.loc[('HP', 'op_cost_fix'), 'value']
                 * data_wnw[(('LT-WP', 'Wärmenetzwerk'), 'flow')].max()
                 / cop_lt))

cost_ehk = (data_ehk[(('Elektroheizkessel', 'Wärmenetzwerk'), 'flow')].sum()
            * param.loc[('EHK', 'op_cost_var'), 'value']
            + (param.loc[('EHK', 'op_cost_fix'), 'value']
               * param.loc[('EHK', 'Q_N'), 'value']))

cost_Anlagen = (cost_tes + cost_st + cost_bhkw + cost_gud
                + cost_slk + cost_hp + cost_lt_hp + cost_ehk)

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

# Daten zum Plotten der Wärmeversorgung
data_wnw.columns = ['BHKW', 'EHK', 'GuD', 'LT-WP ab', 'SLK', 'Bedarf',
                    'TES Ein', 'Status TES Ein', 'WP']
data_lt_wnw.columns = ['LT-WP zu', 'Solar', 'TES Aus', 'Status TES Aus']
data_tes.columns = ['TES Ein', 'Status TES Ein', 'TES Aus', 'Status TES Aus',
                    'Speicherstand']
data_enw.columns = ['P_BHKW', 'P_zu_EHK', 'P_zu_LTWP', 'P_ab_ges', 'P_zu_WP',
                    'P_GuD', 'P_zu_ges']

df1 = pd.concat([data_wnw[['BHKW', 'EHK', 'GuD', 'LT-WP ab', 'SLK', 'Bedarf',
                           'TES Ein', 'WP']],
                 data_lt_wnw[['LT-WP zu', 'Solar', 'TES Aus']],
                 data_tes[['Speicherstand']],
                 data_enw[['P_BHKW', 'P_GuD']]],
                axis=1)
df1.to_csv(path.join(dirpath, 'Ergebnisse\\Vorarbeit\\Vor_wnw.csv'),
           sep=";")

# Daten zum Plotten der Investitionsrechnung
d2 = {'invest_ges': [invest_ges], 'invest_solar': [invest_solar],
      'invest_ehk': [invest_ehk], 'invest_slk': [invest_slk],
      'invest_bhkw': [invest_bhkw], 'invest_gud': [invest_gud],
      'invest_hp': [invest_hp], 'invest_tes': [invest_tes],
      'Q_tes': [param.loc[('TES', 'Q'), 'value']],
      'total_heat_demand': [total_heat_demand], 'Gesamtbetrag': [Gesamtbetrag]}
df2 = pd.DataFrame(data=d2)
df2.to_csv(path.join(dirpath, 'Ergebnisse\\Vorarbeit\\Vor_Invest.csv'),
           sep=";")

# Daten für die ökologische Bewertung
df3 = pd.concat([data_gnw[(('Gasquelle', 'Gasnetzwerk'), 'flow')],
                 data_enw[['P_ab_ges', 'P_zu_ges']]],
                axis=1)
df3.columns = ['Gas_in', 'P_out', 'P_in']
df3.to_csv(path.join(dirpath, 'Ergebnisse\\Vorarbeit\\Vor_CO2.csv'), sep=";")
