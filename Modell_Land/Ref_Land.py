"""Referenzenergiesystem.

Created on Tue Nov 26 11:11:34 2019

@author: Malte Fritz und Jonas Freißmann

Komponenten:
    - BHKW
    - Elektroheizkessel
    - Spitzenlastkessel
Wärmebedarf von 1/20 von dem Wärmebedarf Flensburgs aus dem Jahr 2016

"""
import os.path as path
import oemof.solph as solph
import oemof.outputlib as outputlib
import pandas as pd
import numpy as np


# %% Preprocessing

    # %% Daten einlesen

dirpath = path.abspath(path.join(__file__, "../.."))
filename = path.join(dirpath, 'Eingangsdaten\\simulation_data.csv')
data = pd.read_csv(filename, sep=";")

    # %% Zeitreihe

periods = len(data)
date_time_index = pd.date_range('1/1/2016 00:00:00', periods=periods, freq='h')

    # %% Energiesystem erstellen

es_ref = solph.EnergySystem(timeindex=date_time_index)


# %% Komponenten

    # %% Elektroheizkessel

# Dimensionierung
Q_ehk = 3
op_cost_ehk = 0.8
eta_ehk = 0.99

# Investition
spez_inv_ehk = 60000    # Aus Markus' MA
invest_ehk = spez_inv_ehk * Q_ehk

    # %% Spitzenlastkessel

# Dimensionierung
Q_slk = 3
op_cost_slk = 1
eta_slk = 0.88

# Investition
spez_inv_slk = 70000    # Aus Markus' MA
invest_slk = spez_inv_slk * Q_slk

    # %% BHKW

# Dimensionierung
Q_in_bhkw = 45
P_max_bhkw = 21.1
P_min_bhkw = 11.5
H_L_FG_share_max = 0.203
H_L_FG_share_min = 0.3603
Eta_el_max_woDH = 0.4685
Eta_el_min_woDH = 0.4307
op_cost_bhkw = 4

# Investition
spez_inv_bhkw = 2e+6 * P_max_bhkw**(-0.147)    # Trendlinie aus Excel
invest_bhkw = P_max_bhkw * spez_inv_bhkw


# %% Randbedingungen

    # %% Wärmebedarf

# rel_demand ist die Variable, die den Wärmebedarf der Region
# prozentual von FL angibt.
heat_demand_FL = data['heat_demand']
rel_heat_demand = 0.05
heat_demand_local = heat_demand_FL * rel_heat_demand
total_heat_demand = float(heat_demand_local.sum())
nom_heat_demand_local = max(heat_demand_local)
act_heat_demand_local = heat_demand_local / nom_heat_demand_local

    # %% Kosten

gas_price = 14.14
co2_certificate = 1.07
elec_consumer_charges = 85.51
heat_price = 68.59
energy_tax = 5.5


    # %% Investitionkosten

invest_ges = invest_bhkw + invest_ehk + invest_slk


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

es_ref.add(gas_source, elec_source)

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
                        outputs={wnw: solph.Flow(nominal_value=Q_slk,
                                                 max=1,
                                                 min=0,
                                                 variable_costs=(op_cost_slk+energy_tax))},
                        conversion_factors={wnw: eta_slk})


bhkw = solph.components.GenericCHP(
                        label='BHKW',
                        fuel_input={gnw: solph.Flow(
                            H_L_FG_share_max=[H_L_FG_share_max for p in range(0, periods)],
                            H_L_FG_share_min=[H_L_FG_share_min for p in range(0, periods)],
                            nominal_value=Q_in_bhkw)},
                        electrical_output={enw: solph.Flow(
                            variable_costs=op_cost_bhkw,
                            P_max_woDH=[P_max_bhkw for p in range(0, periods)],
                            P_min_woDH=[P_min_bhkw for p in range(0, periods)],
                            Eta_el_max_woDH=[Eta_el_max_woDH for p in range(0, periods)],
                            Eta_el_min_woDH=[Eta_el_min_woDH for p in range(0, periods)])},
                        heat_output={wnw: solph.Flow(
                            Q_CW_min=[0 for p in range(0, periods)])},
                        Beta=[0 for p in range(0, periods)],
                        back_pressure=False)

es_ref.add(ehk, slk, bhkw)


# %% Processing

    # %% Solve
# Was bedeutet tee?
model = solph.Model(es_ref)
model.solve(solver='gurobi', solve_kwargs={'tee': True},
            cmdline_options={"mipgap": "0.001"})

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

# Sinks
data_elec_sink = outputlib.views.node(results, 'Spotmarkt')['sequences']
data_heat_sink = outputlib.views.node(results, 'Wärmebedarf')['sequences']

# Transformer
data_ehk = outputlib.views.node(results, 'Elektroheizkessel')['sequences']
data_slk = outputlib.views.node(results, 'Spitzenlastkessel')['sequences']
data_bhkw = outputlib.views.node(results, 'BHKW')['sequences']


    #%% Zahlungsströme Ergebnis

objective = abs(es_ref.results['meta']['objective'])

    #%% Gesamtkosten

# costs RS
cost_gas = (data_gnw[(('Gasquelle', 'Gasnetzwerk'), 'flow')].sum()
            * (gas_price + co2_certificate))
cost_bhkw = (data_bhkw[(('BHKW', 'Elektrizitätsnetzwerk'), 'flow')].sum()
             * op_cost_bhkw)
cost_slk = (data_slk[(('Spitzenlastkessel', 'Wärmenetzwerk'), 'flow')].sum()
            * (op_cost_slk + energy_tax))
cost_ehk = (data_ehk[(('Elektroheizkessel', 'Wärmenetzwerk'), 'flow')].sum()
            * op_cost_ehk)

# cost electricity
el_flow = np.array(data_enw[(('Stromquelle', 'Elektrizitätsnetzwerk'),
                             'flow')])
cost_el = np.array(data['el_price'])

cost_el_array = el_flow * cost_el
cost_el_sum = cost_el_array.sum()

# erlöse electricity
r_el = (np.array(data_enw[(('Elektrizitätsnetzwerk', 'Spotmarkt'), 'flow')])
        * np.array(data['el_spot_price']))
R_el_sum = r_el.sum()

# Gesamtkosten
ausgaben = cost_gas + cost_bhkw + cost_slk + cost_ehk + cost_el_sum - R_el_sum


    #%% Output Ergebnisse

label = ['BHKW', 'EHK', 'SLK', 'Wärmebedarf']
data_wnw.columns = label

df1 = pd.DataFrame(data=data_wnw)
df1.to_csv(path.join(dirpath, 'Ergebnisse\\Ref_Ergebnisse\\Ref_wnw.csv'),
           sep=";")

d2 = {'invest_ges': [invest_ges], 'objective': [objective],
      'total_heat_demand': [total_heat_demand], 'ausgaben': [ausgaben]}
df2 = pd.DataFrame(data=d2)
df2.to_csv(path.join(dirpath, 'Ergebnisse\\Ref_Ergebnisse\\Ref_Invest.csv'),
           sep=";")
