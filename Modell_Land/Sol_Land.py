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

    # %% Zeitreihe

periods = len(data)
date_time_index = pd.date_range('1/1/2016 00:00:00', periods=periods, freq='h')

    # %% Energiesystem erstellen

es_ref = solph.EnergySystem(timeindex=date_time_index)


# %% Komponenten

    # %% Elektroheizkessel

# Dimensionierung
Q_ehk = 3
eta_ehk = 0.99

# Investition
op_cost_ehk = 0.8
spez_inv_ehk = 60000    # Aus Markus' MA
invest_ehk = spez_inv_ehk * Q_ehk

    # %% Spitzenlastkessel

# Dimensionierung
Q_slk = 3
eta_slk = 0.88

# Investition
op_cost_slk = 1
spez_inv_slk = 70000    # Aus Markus' MA
invest_slk = spez_inv_slk * Q_slk

    # %% BHKW

# Dimensionierung
Q_in_bhkw = 39
P_max_bhkw = 21.1
P_min_bhkw = 11.5
H_L_FG_share_max = 0.203
H_L_FG_share_min = 0.3603
Eta_el_max_woDH = 0.4685
Eta_el_min_woDH = 0.4307

# Investition
op_cost_bhkw = 4
spez_inv_bhkw = 2e+6 * P_max_bhkw**(-0.147)    # Trendlinie aus Excel
invest_bhkw = P_max_bhkw * spez_inv_bhkw

    # %% TES

# Dimensionierung
Q_tes = 150

# Investition
op_cost_tes = 0.66

    # %% Solarthermie

A = 4500*2    # A = 4329,1
# eta_Kol = 0,693
# E_A = 1000

invest_solar = invest_st(A, col_type="vacuum")
p_solar = (0.01 * invest_solar)/(A*data['solar_data'].sum())

nom_solar = (max(data['solar_data'])*A)
act_solar = (data['solar_data']*A)/(nom_solar)


# %% Randbedinungen

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

    # %% Investionskosten

invest_ges = invest_bhkw + invest_ehk + invest_slk + invest_solar


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

    # %% Speicher
# Saisonaler Speicher

tes = solph.components.GenericStorage(
    label='Wärmespeicher',
    nominal_storage_capacity=Q_tes,
    inputs={wnw: solph.Flow(nominal_value=nom_heat_demand_local/4,
                            max=1,
                            min=0.1,
                            variable_costs=op_cost_tes,
                            nonconvex=solph.NonConvex(
                                minimum_uptime=3, initial_status=0))},
    outputs={wnw: solph.Flow(nominal_value=nom_heat_demand_local/4,
                             max=1,
                             min=0.1,
                             nonconvex=solph.NonConvex(
                                 minimum_uptime=3, initial_status=0))},
    initial_storage_level=0.7,
    inflow_conversion_factor=1,
    outflow_conversion_factor=0.75)

es_ref.add(tes)

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
data_solar_source = outputlib.views.node(results, 'Solarthermie')['sequences']

# Sinks
data_elec_sink = outputlib.views.node(results, 'Spotmarkt')['sequences']
data_heat_sink = outputlib.views.node(results, 'Wärmebedarf')['sequences']

# Transformer
data_ehk = outputlib.views.node(results, 'Elektroheizkessel')['sequences']
data_slk = outputlib.views.node(results, 'Spitzenlastkessel')['sequences']
data_bhkw = outputlib.views.node(results, 'BHKW')['sequences']

# Speicher
data_tes = outputlib.views.node(results, 'Wärmespeicher')['sequences']


    # %% Zahlungsströme Ergebnis

objective = abs(es_ref.results['meta']['objective'])


    # %% Gesamtkosten

# costs RS
cost_stes = (data_tes[(('Wärmenetzwerk', 'Wärmespeicher'), 'flow')].sum()
             * op_cost_tes)
cost_st = (data_solar_source[(('Solarthermie', 'Wärmenetzwerk'), 'flow')].sum()
           * p_solar)
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

# Erlöse electricity
r_el = (np.array(data_enw[(('Elektrizitätsnetzwerk', 'Spotmarkt'), 'flow')])
        * np.array(data['el_spot_price']))
R_el_sum = r_el.sum()

# Gesamtkosten
ausgaben = (cost_stes + cost_st + cost_gas + cost_bhkw + cost_slk + cost_ehk
            + cost_el_sum - R_el_sum)


    # %% Output Ergebnisse

label = ['BHKW', 'EHK', 'Solar', 'SLK', 'Wärmebedarf', 'TES Ein',
         'Status TES Ein', 'TES Aus', 'Status TES Aus']
data_wnw.columns = label
del data_wnw[label[-3]], data_wnw[label[-1]]

df1 = pd.DataFrame(data=data_wnw)
df1.to_csv(path.join(dirpath, 'Ergebnisse\\Sol_Ergebnisse\\Sol_wnw.csv'),
           sep=";")

d2 = {'invest_ges': [invest_ges], 'Q_tes': [Q_tes], 'objective': [objective],
      'total_heat_demand': [total_heat_demand], 'ausgaben': [ausgaben]}
df2 = pd.DataFrame(data=d2)
df2.to_csv(path.join(dirpath, 'Ergebnisse\\Sol_Ergebnisse\\Sol_Invest.csv'),
           sep=";")

label = ['TES Ein', 'Status TES Ein', 'Speicherstand', 'TES Aus',
         'Status TES Aus']
data_tes.columns = label
del data_tes[label[0]], data_tes[label[1]], data_tes[label[3]]
del data_tes[label[4]]

df3 = pd.DataFrame(data=data_tes)
df3.to_csv(path.join(dirpath, 'Ergebnisse\\Sol_Ergebnisse\\Sol_Speicher.csv'),
           sep=";")

# Daten für die ökologische Bewertung
df3 = pd.concat([data_gnw.iloc[:, [0, 1]], data_enw.iloc[:, [2, 3]]], axis=1)
label = ['Q_in,BHKW', 'Q_in,SLK', 'P_out', 'P_in']
df3.columns = label
df3.to_csv(path.join(dirpath, 'Ergebnisse\\Sol_Ergebnisse\\Sol_CO2.csv'),
           sep=";")
