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


# %% Preprocessing

    # %% Daten einlesen

dirpath = path.abspath(path.join(__file__, "../.."))
filename = path.join(dirpath, 'Eingangsdaten\\simulation_data.csv')
data = pd.read_csv(filename, sep=";")
filename = path.join(dirpath, 'Eingangsdaten\\All_parameters.csv')
param = pd.read_csv(filename, sep=";", index_col=['plant', 'parameter'])

    # %% Zeitreihe

periods = len(data)
date_time_index = pd.date_range('1/1/2016 00:00:00', periods=periods, freq='h')

    # %% Energiesystem erstellen

es_ref = solph.EnergySystem(timeindex=date_time_index)


# %% Komponenten

    # %% Elektroheizkessel check

# Dimensionierung
Q_ehk = 75
eta_ehk = 0.99

# Investition
op_cost_ehk = 0.5
spez_inv_ehk = 80000
invest_ehk = spez_inv_ehk * Q_ehk

    # %% Spitzenlastkessel check

# Dimensionierung
Q_slk = 75
eta_slk = 0.88

# Investition
op_cost_slk = 1.1
spez_inv_slk = 60000
invest_slk = spez_inv_slk * Q_slk

    # %% BHKW - check

# Dimensionierung
Q_in_bhkw = 225
P_max_bhkw = 103.16
P_min_bhkw = 96.89
H_L_FG_share_max_bhkw = 0.2032
H_L_FG_share_min_bhkw = 0.3603
Eta_el_max_woDH_bhkw = 0.4685
Eta_el_min_woDH_bhkw = 0.4306

# Investition
op_cost_bhkw = 10
spez_inv_bhkw = 1e6
invest_bhkw = P_max_bhkw * spez_inv_bhkw

    # %% GuD - check

# Dimensionierung - Noch nicht dimensioniert!
Q_in_gud = param.loc[('GuD', 'Q_in'), 'value']
P_max_gud = param.loc[('GuD', 'P_max_woDH'), 'value']
P_min_gud = param.loc[('GuD', 'P_min_woDH'), 'value']
H_L_FG_share_max_gud = param.loc[('GuD', 'H_L_FG_share_max'), 'value']
Eta_el_max_woDH_gud = param.loc[('GuD', 'Eta_el_max_woDH'), 'value']
Eta_el_min_woDH_gud = param.loc[('GuD', 'Eta_el_min_woDH'), 'value']
Q_CW_min = param.loc[('GuD', 'Q_CW_min'), 'value']
beta_gud = param.loc[('GuD', 'beta'), 'value']

# Investition
op_cost_gud = 4.5
spez_inv_gud = 1e+6
invest_gud = P_max_gud * spez_inv_gud

    # %% Wärmepumpe - check

Q_hp = 75

filename = path.join(dirpath, 'Eingangsdaten\\hp_char_timeseries.csv')
hp_data = pd.read_csv(filename, sep=";")

P_in_max_hp = hp_data['P_max'].to_list()
P_in_min_hp = hp_data['P_min'].to_list()

c1_hp = hp_data['c_1'].to_list()
c0_hp = hp_data['c_0'].to_list()

# Investition
op_cost_hp = 0.88
spez_inv_hp = 220350
invest_hp = spez_inv_hp * Q_hp

    # %% TES - check

# Dimensionierung
Q_tes = 150000

# Investition
op_cost_tes = 0.66
spez_inv_tes = 18750
invest_tes = spez_inv_tes * Q_tes

    # %% Solarthermie check

A = 96237.4
# eta_Kol = 0,693
# E_A = 1000

invest_solar = invest_st(A, col_type="flat")
p_solar = (0.01 * invest_solar)/(A*data['solar_data'].sum())

nom_solar = (max(data['solar_data'])*A)
act_solar = (data['solar_data']*A)/(nom_solar)


# %% Randbedinungen

    # %% Wärmebedarf
# rel_demand ist die Variable, die den Wärmebedarf der Region
# prozentual von FL angibt.

heat_demand_FL = data['heat_demand']
rel_heat_demand = 1
heat_demand_local = heat_demand_FL * rel_heat_demand
total_heat_demand = float(heat_demand_local.sum())
nom_heat_demand_local = max(heat_demand_local)
act_heat_demand_local = heat_demand_local / nom_heat_demand_local

    # %% Kosten

# Kosten für das Jahr 2016. Siehe ENKF
gas_price = 14.14
co2_certificate = 1.07
elec_consumer_charges = 85.51
heat_price = 68.59
energy_tax = 5.5

    # %% Investionskosten

invest_ges = (invest_bhkw + invest_ehk + invest_slk + invest_solar
              + invest_hp + invest_gud + invest_tes)

# %% Energiesystem

    # %% Busses

gnw = solph.Bus(label='Gasnetzwerk')
enw = solph.Bus(label='Elektrizitätsnetzwerk')
wnw = solph.Bus(label='Wärmenetzwerk')

es_ref.add(gnw, enw, wnw)

    # %% Soruces

gas_source = solph.Source(label='Gasquelle',
                          outputs={gnw: solph.Flow(
                                   variable_costs=gas_price+co2_certificate)})

elec_source = solph.Source(label='Stromquelle',
                           outputs={enw: solph.Flow(
                                    variable_costs=(elec_consumer_charges
                                                    + data['el_spot_price']))})

solar_source = solph.Source(label='Solarthermie',
                            outputs={wnw: solph.Flow(variable_costs=p_solar,
                                                     nominal_value=nom_solar,
                                                     actual_value=act_solar,
                                                     fixed=True)})

es_ref.add(gas_source, elec_source, solar_source)
# es_ref.add(gas_source, elec_source)

    # %% Sinks

elec_sink = solph.Sink(label='Spotmarkt',
                       inputs={enw: solph.Flow(
                               variable_costs=-data['el_spot_price'])})

heat_sink = solph.Sink(label='Wärmebedarf',
                       inputs={wnw: solph.Flow(
                               variable_costs=-heat_price,
                               nominal_value=nom_heat_demand_local,
                               actual_value=act_heat_demand_local,
                               fixed=True)})

es_ref.add(elec_sink, heat_sink)

    # %% Transformer

ehk = solph.Transformer(label='Elektroheizkessel',
                        inputs={enw: solph.Flow()},
                        outputs={wnw: solph.Flow(nominal_value=Q_ehk,
                                                 max=1,
                                                 min=0,
                                                 variable_costs=op_cost_ehk)},
                        conversion_factors={wnw: eta_ehk})

slk = solph.Transformer(label='Spitzenlastkessel',
                        inputs={gnw: solph.Flow()},
                        outputs={wnw: solph.Flow(
                            nominal_value=Q_slk,
                            max=1,
                            min=0,
                            variable_costs=op_cost_slk+energy_tax)},
                        conversion_factors={wnw: eta_slk})

bhkw = solph.components.GenericCHP(
    label='BHKW',
    fuel_input={gnw: solph.Flow(
        H_L_FG_share_max=[H_L_FG_share_max_bhkw for p in range(0, periods)],
        H_L_FG_share_min=[H_L_FG_share_min_bhkw for p in range(0, periods)],
        nominal_value=Q_in_bhkw)},
    electrical_output={enw: solph.Flow(
        variable_costs=op_cost_bhkw,
        P_max_woDH=[P_max_bhkw for p in range(0, periods)],
        P_min_woDH=[P_min_bhkw for p in range(0, periods)],
        Eta_el_max_woDH=[Eta_el_max_woDH_bhkw for p in range(0, periods)],
        Eta_el_min_woDH=[Eta_el_min_woDH_bhkw for p in range(0, periods)])},
    heat_output={wnw: solph.Flow(
        Q_CW_min=[0 for p in range(0, periods)])},
    Beta=[0 for p in range(0, periods)],
    back_pressure=False)


gud = solph.components.GenericCHP(
    label='GuD',
    fuel_input={gnw: solph.Flow(
        H_L_FG_share_max=[H_L_FG_share_max_gud for p in range(0, periods)],
        nominal_value=Q_in_gud)},
    electrical_output={enw: solph.Flow(
        variable_costs=op_cost_gud,
        P_max_woDH=[P_max_gud for p in range(0, periods)],
        P_min_woDH=[P_min_gud for p in range(0, periods)],
        Eta_el_max_woDH=[Eta_el_max_woDH_gud for p in range(0, periods)],
        Eta_el_min_woDH=[Eta_el_min_woDH_gud for p in range(0, periods)])},
    heat_output={wnw: solph.Flow(
        Q_CW_min=[Q_CW_min for p in range(0, periods)])},
    Beta=[beta_gud for p in range(0, periods)],
    back_pressure=False)

hp = solph.components.OffsetTransformer(
    label='Wärmepumpe',
    inputs={enw: solph.Flow(nominal_value=1,
                            max=P_in_max_hp,
                            min=P_in_min_hp,
                            nonconvex=solph.NonConvex())},
    outputs={wnw: solph.Flow(variable_costs=op_cost_hp)},
    coefficients=[c0_hp, c1_hp])

es_ref.add(ehk, slk, bhkw, gud, hp)

    # %% Speicher

# Saisonaler Speicher

tes = solph.components.GenericStorage(
    label='Wärmespeicher',
    nominal_storage_capacity=Q_tes,
    inputs={wnw: solph.Flow(nominal_value=nom_heat_demand_local,
                            max=1,
                            min=0.1,
                            variable_costs=op_cost_tes,
                            nonconvex=solph.NonConvex(
                                minimum_uptime=3, initial_status=0))},
    outputs={wnw: solph.Flow(nominal_value=nom_heat_demand_local,
                             max=1,
                             min=0.1,
                             nonconvex=solph.NonConvex(
                                 minimum_uptime=3, initial_status=0))},
    initial_storage_level=0.1,
    inflow_conversion_factor=1,
    outflow_conversion_factor=0.75)

es_ref.add(tes)

# %% Processing

    # %% Solve

# Was bedeutet tee?
model = solph.Model(es_ref)
model.solve(solver='gurobi', solve_kwargs={'tee': True},
            cmdline_options={"mipgap": "0.01"})

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

# Speicher
data_tes = outputlib.views.node(results, 'Wärmespeicher')['sequences']


    # %% Zahlungsströme Ergebnis

objective = abs(es_ref.results['meta']['objective'])


    # %% Geldflüss

# Ausgaben
# # Anlagenbettriebskosten
cost_tes = (data_tes[(('Wärmenetzwerk', 'Wärmespeicher'), 'flow')].sum()
            * op_cost_tes
            + (param.loc[('TES', 'op_cost_fix'), 'value']
               * param.loc[('TES', 'Q'), 'value']))
cost_st = (data_solar_source[(('Solarthermie', 'Wärmenetzwerk'), 'flow')].sum()
           * p_solar)
cost_bhkw = (data_bhkw[(('BHKW', 'Elektrizitätsnetzwerk'), 'flow')].sum()
             * op_cost_bhkw
             + (param.loc[('BHKW', 'op_cost_fix'), 'value']
                * param.loc[('BHKW', 'P_max_woDH'), 'value']))
cost_gud = (data_gud[(('GuD', 'Elektrizitätsnetzwerk'), 'flow')].sum()
            * op_cost_gud
            + (param.loc[('GuD', 'op_cost_fix'), 'value']
               * param.loc[('GuD', 'P_max_woDH'), 'value']))
cost_slk = (data_slk[(('Spitzenlastkessel', 'Wärmenetzwerk'), 'flow')].sum()
            * (op_cost_slk + energy_tax)
            + (param.loc[('SLK', 'op_cost_fix'), 'value']
               * param.loc[('SLK', 'Q_N'), 'value']))
cost_hp = (data_hp[(('Elektrizitätsnetzwerk', 'Wärmepumpe'), 'flow')].sum()
           * op_cost_hp
           + (param.loc[('HP', 'op_cost_fix'), 'value']
               * hp_data.loc[:, 'P_max'].max()))
cost_ehk = (data_ehk[(('Elektroheizkessel', 'Wärmenetzwerk'), 'flow')].sum()
            * op_cost_ehk
            + (param.loc[('EHK', 'op_cost_fix'), 'value']
               * param.loc[('EHK', 'Q_N'), 'value']))

cost_Anlagen = (cost_tes + cost_st + cost_bhkw + cost_gud
                + cost_slk + cost_hp + cost_ehk)

# # Primärenergiebezugskoste
cost_gas = (data_gnw[(('Gasquelle', 'Gasnetzwerk'), 'flow')].sum()
            * (gas_price + co2_certificate))

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

# Summe der Geldströme
Gesamtbetrag = (revenues_spotmarkt
                - cost_Anlagen - cost_gas - cost_el)
Betrag_ohnePrimär = (revenues_spotmarkt
                     - cost_Anlagen)


    # %% Output Ergebnisse

label = ['BHKW', 'EHK', 'GuD', 'Solar', 'SLK', 'Wärmebedarf', 'TES Ein',
         'Status TES Ein', 'Wärmepumpe', 'TES Aus', 'Status TES Aus']
data_wnw.columns = label
del data_wnw[label[-4]], data_wnw[label[-1]]

df1 = pd.DataFrame(data=data_wnw)
df1.to_csv(path.join(dirpath, 'Ergebnisse\\Vorarbeit\\Vor_wnw.csv'),
           sep=";")

d2 = {'invest_ges': [invest_ges], 'Q_tes': [Q_tes], 'objective': [objective],
      'total_heat_demand': [total_heat_demand], 'Gesamtbetrag': [Gesamtbetrag],
      'Betrag_ohnePrimär': [Betrag_ohnePrimär]}
df2 = pd.DataFrame(data=d2)
df2.to_csv(path.join(dirpath, 'Ergebnisse\\Vorarbeit\\Vor_Invest.csv'),
           sep=";")

label = ['TES Ein', 'Status TES Ein', 'Speicherstand', 'TES Aus',
         'Status TES Aus']
data_tes.columns = label
del data_tes[label[0]], data_tes[label[1]], data_tes[label[3]]
del data_tes[label[4]]

df3 = pd.DataFrame(data=data_tes)
df3.to_csv(path.join(dirpath, 'Ergebnisse\\Vorarbeit\\Vor_Speicher.csv'),
           sep=";")

# Daten für die ökologische Bewertung
df3 = pd.concat([data_gnw.iloc[:, [0, 1, 2]], data_enw.iloc[:, [2, 3]]],
                axis=1)
label = ['Q_in,BHKW', 'Q_in,GuD', 'Q_in,SLK', 'P_out', 'P_in']
df3.columns = label
df3.to_csv(path.join(dirpath, 'Ergebnisse\\Vorarbeit\\Vor_CO2.csv'),
           sep=";")
