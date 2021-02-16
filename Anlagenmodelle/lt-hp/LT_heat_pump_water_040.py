"""TESPy compression heat pump model for district heating.

Created on Thu Jan  9 10:07:02 2020

@author: Malte Fritz and Jonas Freißmann
"""
import os.path as path

from tespy.components import (Sink, Source, Compressor, Condenser,
                              Pump, HeatExchangerSimple, Valve, Drum,
                              HeatExchanger, CycleCloser)
from tespy.connections import Connection, Ref, Bus
from tespy.networks import Network
from tespy.tools.characteristics import CharLine
from tespy.tools.characteristics import load_default_char as ldc
from tespy.tools import document_model

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from fluprodia import FluidPropertyDiagram


def get_fluid_property_data(connections, x_property, y_property):
    x = []
    y = []
    for c in connections:
        x += [c.get_plotting_props()[x_property]]
        y += [c.get_plotting_props()[y_property]]

    return x, y

Q_N=200 * -1e6
# Q_N = abs(float(input('Gib die Nennwärmeleistung in MW ein: '))) * -1e6
# T_amb and T_amb_out kommen von der Drammen District Heating Wärmepumpe aus
# Norwegen. T_amb ist die Außentemperatur in einem Fluß und T_amb_out die
# Differenz vom Austritt zum Eintritt
T_DH_vl = 90
T_DH_rl = 50
T_source_rl = 50
T_source_vl = 70

# %% network

nw = Network(fluids=['water', 'NH3', 'air'], T_unit='C', p_unit='bar',
             h_unit='kJ / kg', m_unit='kg / s')

# %% components

# sources & sinks
cc = CycleCloser('coolant cycle closer')
cb = Source('consumer back flow')
cf = Sink('consumer feed flow')
lt_si = Sink('low temp sink')
lt_so = Source('low temp source')

# low temp water system
pu = Pump('pump')

# consumer system

cd = Condenser('condenser')
dhp = Pump('district heating pump')
cons = HeatExchangerSimple('consumer')

# evaporator system

va = Valve('valve')
dr = Drum('drum')
ev = HeatExchanger('evaporator')
erp = Pump('evaporator reciculation pump')

# compressor-system

cp = Compressor('compressor')


# %% connections

# consumer system

c_in_cd = Connection(cc, 'out1', cd, 'in1')

cb_dhp = Connection(cb, 'out1', dhp, 'in1')
dhp_cd = Connection(dhp, 'out1', cd, 'in2')
cd_cons = Connection(cd, 'out2', cons, 'in1')
cons_cf = Connection(cons, 'out1', cf, 'in1')

nw.add_conns(c_in_cd, cb_dhp, dhp_cd, cd_cons, cons_cf)

# connection condenser - evaporator system

cd_va = Connection(cd, 'out1', va, 'in1')

nw.add_conns(cd_va)

# evaporator system

va_dr = Connection(va, 'out1', dr, 'in1')
dr_erp = Connection(dr, 'out1', erp, 'in1')
erp_ev = Connection(erp, 'out1', ev, 'in2')
ev_dr = Connection(ev, 'out2', dr, 'in2')
dr_cp = Connection(dr, 'out2', cp, 'in1')

nw.add_conns(va_dr, dr_erp, erp_ev, ev_dr, dr_cp)

# low temp water system

lt_so_pu = Connection(lt_so, 'out1', pu, 'in1')
pu_ev = Connection(pu, 'out1', ev, 'in1')
ev_lt_si = Connection(ev, 'out1', lt_si, 'in1')

nw.add_conns(lt_so_pu, pu_ev, ev_lt_si)

# compressor-system

cp_c_out = Connection(cp, 'out1', cc, 'in1')

nw.add_conns(cp_c_out)

# %% busses

# motor efficiency
x = np.array([0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55,
              0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1, 1.05, 1.1, 1.15,
              1.2, 10])
y = 1 / (np.array([0.01, 0.3148, 0.5346, 0.6843, 0.7835, 0.8477, 0.8885,
                   0.9145, 0.9318, 0.9443, 0.9546, 0.9638, 0.9724, 0.9806,
                   0.9878, 0.9938, 0.9982, 1.0009, 1.002, 1.0015, 1, 0.9977,
                   0.9947, 0.9909, 0.9853, 0.9644])
         * 0.98)

mot1 = CharLine(x=x, y=y)
mot2 = CharLine(x=x, y=y)
mot3 = CharLine(x=x, y=y)
mot4 = CharLine(x=x, y=y)

power = Bus('total compressor power')
power.add_comps({'comp': cp, 'char': mot1}, {'comp': pu, 'char': mot2},
                {'comp': dhp, 'char': mot3}, {'comp': erp, 'char': mot4})

heat = Bus('total delivered heat')
heat.add_comps({'comp': cd})

nw.add_busses(power, heat)

# %% component parametrization

# condenser system

cd.set_attr(pr1=0.99, pr2=0.99, ttd_u=5, design=['pr2', 'ttd_u'],
            offdesign=['zeta2', 'kA'])
dhp.set_attr(eta_s=0.8, design=['eta_s'], offdesign=['eta_s_char'])
cons.set_attr(pr=0.99, design=['pr'], offdesign=['zeta'])

# low temp water system

pu.set_attr(eta_s=0.75, design=['eta_s'], offdesign=['eta_s_char'])

# evaporator system

kA_char1 = ldc('heat exchanger', 'kA_char1', 'DEFAULT', CharLine)
kA_char2 = ldc('heat exchanger', 'kA_char2', 'EVAPORATING FLUID', CharLine)

ev.set_attr(pr1=0.98, pr2=0.99, ttd_l=5,
            kA_char1=kA_char1, kA_char2=kA_char2,
            design=['pr1', 'ttd_l'], offdesign=['zeta1', 'kA'])
erp.set_attr(eta_s=0.8, design=['eta_s'], offdesign=['eta_s_char'])

# compressor system

cp.set_attr(eta_s=0.85, design=['eta_s'], offdesign=['eta_s_char'])


# %% connection parametrization

# condenser system

c_in_cd.set_attr(fluid={'air': 0, 'NH3': 1, 'water': 0})
cb_dhp.set_attr(T=T_DH_rl, p=10, fluid={'air': 0, 'NH3': 0, 'water': 1})
cd_cons.set_attr(T=T_DH_vl)
cons_cf.set_attr(h=Ref(cb_dhp, 1, 0), p=Ref(cb_dhp, 1, 0))

# evaporator system cold side

erp_ev.set_attr(m=Ref(va_dr, 1.25, 0), p0=5)
dr_cp.set_attr(p0=17, h0=1650)

# low temp water system

lt_so_pu.set_attr(p=10, T=T_source_vl,
                  fluid={'air': 0, 'NH3': 0, 'water': 1})
# pu_ev.set_attr(offdesign=['v'])
ev_lt_si.set_attr(p=10, T=T_source_rl)


# %% key paramter

heat.set_attr(P=Q_N)

# %% Calculation

nw.solve('design')
nw.print_results()
nw.save('hp_water')
document_model(nw)

cop = abs(heat.P.val) / power.P.val
print('COP:', cop)
print('P_out:', power.P.val/1e6)
print('Q_out:', heat.P.val/1e6)

cp.eta_s_char.char_func.extrapolate = True


h = np.arange(0, 3000 + 1, 200)
T_max = 300
T = np.arange(-75, T_max + 1, 25).round(8)

# Diagramm

p_values = np.array([
    10, 20, 50, 100, 200, 500, 1000,
    2000, 5000, 10000, 20000, 50000, 100000]) * 1e-2
Q_values = np.linspace(0, 100, 11)

isolines = {
    'p': {
        'values': p_values
    },
    'Q': {'values': Q_values}
}

diagram = FluidPropertyDiagram(fluid='NH3')
diagram.set_unit_system(p='bar', T='°C', h='kJ/kg', s='kJ/kgK', Q='%')
diagram.set_isolines(p=p_values, Q=Q_values)
diagram.calc_isolines()

# plot_comps = [dr, erp, ev, dr, cp, cd, va]
plot_comps = [dr, cp, cd, va]
tespy_results = dict()
tespy_results.update(
    {comp.label: comp.get_plotting_data()[1] for comp in plot_comps})


for key, data in tespy_results.items():
    tespy_results[key]['datapoints'] = diagram.calc_individual_isoline(**data)


diagram.set_limits(x_min=0, x_max=2000, y_min=1e0, y_max=1e3)
diagram.draw_isolines(diagram_type='logph', isoline_data=isolines)
for key in tespy_results.keys():
    # if not key == 'compressor':
    datapoints = tespy_results[key]['datapoints']
    diagram.ax.plot(datapoints['h'], datapoints['p'], color='#ff0000')
    diagram.ax.scatter(datapoints['h'][0], datapoints['p'][0], color='#ff0000')
diagram.save('logph_Diagramm.pdf')



# %% Auslegung Temperaturbereich District Heating

# T_range = range(66, 125)
# cop_range = []

# for T in T_range:
#     cd_cons.set_attr(T=T)
#     if T == T_range[0]:
#         nw.solve('offdesign', design_path='hp_water', init_path='hp_water')
#     else:
#         nw.solve('offdesign', design_path='hp_water')
#     print('T_VL:   ', cd_cons.T.val)
#     print('Vor CD: ', cp_c_out.T.val)
#     print('Nach CD:', cd_va.T.val)
#     if nw.lin_dep:
#         cop_range += [np.nan]
#     else:
#         cop_range += [abs(heat.P.val) / power.P.val]

# #     diagram.ax.scatter(*get_fluid_property_data(connections, 'h', 'p'),
# #                        c=(((T-66)/125, 0, 0)))

# # diagram.save('logph_Diagramm.pdf')

# # % Ergebnisse erxportieren

# df = pd.DataFrame({'T_DH_VL / C': T_range, 'COP': cop_range})

# dirpath = path.abspath(path.join(__file__, "../../.."))
# writepath = path.join(dirpath, 'Eingangsdaten', 'LT-Wärmepumpe_Wasser.csv')
# df.to_csv(writepath, sep=';', na_rep='#N/A', index=False)
