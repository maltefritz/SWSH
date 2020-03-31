"""TESPy compression heat pump model for district heating.

Created on Thu Jan  9 10:07:02 2020

@author: Malte Fritz and Jonas Freißmann
"""
import os.path as path

from tespy.networks import network
from tespy.components import (sink, source, splitter, compressor, condenser,
                              pump, heat_exchanger_simple, valve, drum,
                              heat_exchanger, cycle_closer)
from tespy.connections import connection, ref, bus
from tespy.tools.characteristics import char_line
from tespy.tools.characteristics import load_default_char as ldc

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from fluprodia.statesdiagram import StatesDiagram

Q_N=200 * -1e6
# Q_N = abs(float(input('Gib die Nennwärmeleistung in MW ein: '))) * -1e6
# T_amb and T_amb_out kommen von der Drammen District Heating Wärmepumpe aus
# Norwegen. T_amb ist die Außentemperatur in einem Fluß und T_amb_out die
# Differenz vom Austritt zum Eintritt
T_amb = 9.19
T_DH_vl = 90
T_DH_rl = 50
T_source_rl = 50
T_source_vl = 70

# %% network

nw = network(fluids=['water', 'NH3', 'air'], T_unit='C', p_unit='bar',
             h_unit='kJ / kg', m_unit='kg / s')

# %% components

# sources & sinks
cc = cycle_closer('coolant cycle closer')
cb = source('consumer back flow')
cf = sink('consumer feed flow')
amb = source('ambient air')
amb_out1 = sink('sink ambient 1')
amb_out2 = sink('sink ambient 2')
lt_so = source('low temp source')

# ambient air system
fa = compressor('fan')
pu = pump('pump')

# consumer system

cd = condenser('condenser')
dhp = pump('district heating pump')
cons = heat_exchanger_simple('consumer')

# evaporator system

ves = valve('valve')
dr = drum('drum')
ev = heat_exchanger('evaporator')
su = heat_exchanger('superheater')
erp = pump('evaporator reciculation pump')

# compressor-system

cp1 = compressor('compressor 1')
cp2 = compressor('compressor 2')
ic = heat_exchanger('intercooler')

# %% connections

# consumer system

c_in_cd = connection(cc, 'out1', cd, 'in1')

cb_dhp = connection(cb, 'out1', dhp, 'in1')
dhp_cd = connection(dhp, 'out1', cd, 'in2')
cd_cons = connection(cd, 'out2', cons, 'in1')
cons_cf = connection(cons, 'out1', cf, 'in1')

nw.add_conns(c_in_cd, cb_dhp, dhp_cd, cd_cons, cons_cf)

# connection condenser - evaporator system

cd_ves = connection(cd, 'out1', ves, 'in1')

nw.add_conns(cd_ves)

# evaporator system

ves_dr = connection(ves, 'out1', dr, 'in1')
dr_erp = connection(dr, 'out1', erp, 'in1')
erp_ev = connection(erp, 'out1', ev, 'in2')
ev_dr = connection(ev, 'out2', dr, 'in2')
dr_su = connection(dr, 'out2', su, 'in2')

nw.add_conns(ves_dr, dr_erp, erp_ev, ev_dr, dr_su)

# new feature

amb_fa = connection(amb, 'out1', fa, 'in1')
fa_ic = connection(fa, 'out1', ic, 'in2')
ic_out = connection(ic, 'out2', amb_out2, 'in1')

nw.add_conns(amb_fa, fa_ic, ic_out)

# connection evaporator system - compressor system

lt_so_pu = connection(lt_so, 'out1', pu, 'in1')
pu_su = connection(pu, 'out1', su, 'in1')
su_ev = connection(su, 'out1', ev, 'in1')
ev_amb_out = connection(ev, 'out1', amb_out1, 'in1')
su_cp1 = connection(su, 'out2', cp1, 'in1')

nw.add_conns(lt_so_pu, pu_su, su_ev, ev_amb_out, su_cp1)

# compressor-system

cp1_he = connection(cp1, 'out1', ic, 'in1')
he_cp2 = connection(ic, 'out1', cp2, 'in1')
cp2_c_out = connection(cp2, 'out1', cc, 'in1')

nw.add_conns(cp1_he, he_cp2, cp2_c_out)

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

mot1 = char_line(x=x, y=y)
mot2 = char_line(x=x, y=y)
mot3 = char_line(x=x, y=y)
mot4 = char_line(x=x, y=y)
mot5 = char_line(x=x, y=y)
mot6 = char_line(x=x, y=y)

power = bus('total compressor power')
power.add_comps({'c': cp1, 'char': mot1}, {'c': cp2, 'char': mot2},
                {'c': pu, 'char': mot3}, {'c': dhp, 'char': mot4},
                {'c': erp, 'char': mot5}, {'c': fa, 'char': mot6})
heat = bus('total delivered heat')
heat.add_comps({'c': cd})

nw.add_busses(power, heat)

# %% component parametrization

# condenser system

cd.set_attr(pr1=0.99, pr2=0.99, ttd_u=5, design=['pr2', 'ttd_u'],
            offdesign=['zeta2', 'kA'])
dhp.set_attr(eta_s=0.8, design=['eta_s'], offdesign=['eta_s_char'])
cons.set_attr(pr=0.99, design=['pr'], offdesign=['zeta'])

# fan

fa.set_attr(eta_s=0.80, pr=1.005, design=['eta_s'], offdesign=['eta_s_char'])

# water pump

pu.set_attr(eta_s=0.75, design=['eta_s'], offdesign=['eta_s_char'])

# evaporator system

kA_char1 = ldc('heat exchanger', 'kA_char1', 'DEFAULT', char_line)
kA_char2 = ldc('heat exchanger', 'kA_char2', 'EVAPORATING FLUID', char_line)

ev.set_attr(pr1=0.98, pr2=0.99, ttd_l=5,
            kA_char1=kA_char1, kA_char2=kA_char2,
            design=['pr1', 'ttd_l'], offdesign=['zeta1', 'kA'])
su.set_attr(pr1=0.98, pr2=0.99, ttd_u=2, design=['pr1', 'pr2', 'ttd_u'],
            offdesign=['zeta1', 'zeta2', 'kA'])
erp.set_attr(eta_s=0.8, design=['eta_s'], offdesign=['eta_s_char'])

# compressor system

cp1.set_attr(eta_s=0.9, design=['eta_s'], offdesign=['eta_s_char'])
cp2.set_attr(eta_s=0.9, pr=1.79, design=['eta_s'], offdesign=['eta_s_char'])
ic.set_attr(pr1=0.99, pr2=0.98, design=['pr1', 'pr2'],
            offdesign=['zeta1', 'zeta2', 'kA'])

# %% connection parametrization

# condenser system

c_in_cd.set_attr(fluid={'air': 0, 'NH3': 1, 'water': 0})
cb_dhp.set_attr(T=T_DH_rl, p=10, fluid={'air': 0, 'NH3': 0, 'water': 1})
cd_cons.set_attr(T=T_DH_vl)
cons_cf.set_attr(h=ref(cb_dhp, 1, 0), p=ref(cb_dhp, 1, 0))

# evaporator system cold side

erp_ev.set_attr(m=ref(ves_dr, 1.25, 0), p0=5)
su_cp1.set_attr(p0=5, h0=1700)

# evaporator system hot side

# pumping at constant rate in partload
# amb_fa.set_attr(T=T_amb, p=1, m=0, fluid={'air': 1, 'NH3': 0, 'water': 0},
#                 offdesign=['v'])
amb_fa.set_attr(T=T_amb, p=1, fluid={'air': 1, 'NH3': 0, 'water': 0},
                offdesign=['v'])
ev_amb_out.set_attr(p=10, T=T_source_rl, design=['T'])

# compressor-system

he_cp2.set_attr(Td_bp=5, p0=20, design=['Td_bp'])
# ic_out.set_attr(design=['T'])
ic_out.set_attr(T=20, design=['T'])

# new feature

lt_so_pu.set_attr(p=10, T=T_source_vl, design=['T'],
                  fluid={'air': 0, 'NH3': 0, 'water': 1})
pu_su.set_attr(offdesign=['v'])

# %% key paramter

heat.set_attr(P=Q_N)

# %% Calculation

nw.solve('design')
nw.print_results()
nw.save('hp_water')

cop = abs(heat.P.val) / power.P.val
print(cop)
print(power.P.val/1e6)
print(heat.P.val/1e6)

# cp1.eta_s_char.func.extrapolate = True
# cp2.eta_s_char.func.extrapolate = True

# nw.solve('offdesign', design_path='hp_water')

# cop = abs(heat.P.val) / power.P.val
# print(cop)
# print(power.P.val/1e6)
# print(heat.P.val/1e6)

h = np.arange(0, 3000 + 1, 200)
T_max = 300
T = np.arange(-75, T_max + 1, 25).round(8)

# Diagramm

diagram = StatesDiagram(fluid='NH3')
diagram.set_unit_system(p_unit='bar', T_unit='°C', h_unit='kJ/kg', s_unit='kJ/kgK')
# diagram.set_isolines(p=p, v=v, h=h, T=T)
diagram.isobar()
diagram.isochor()
diagram.isoquality()
diagram.isoenthalpy()
diagram.isotherm()
diagram.isoentropy()
p_values = np.array([
    10, 20, 50, 100, 200, 500, 1000,
    2000, 5000, 10000, 20000, 50000, 100000]) * 1e-2
Q_values = np.linspace(0, 100, 11)

# isolines = {
#     'p': {
#         'values': p_values
#     },
#     'Q': {'values': Q_values},
#     'h': {},
#     'v': {}
# }
# diagram.set_limits(x_min=0, x_max=8, y_min=-75, y_max=300)
# diagram.draw_isolines(diagram_type='Ts')
# diagram.save('Ts_Diagramm.pdf')

# isolines = {
#     'p': {
#         'values': p_values
#     },
#     'Q': {'values': Q_values},
#     'T': {},
#     'v': {}
# }
# diagram.set_limits(x_min=0, x_max=8, y_min=0, y_max=2000)
# diagram.draw_isolines(diagram_type='hs')
# diagram.save('hs_Diagramm.pdf')

isolines = {
    'p': {
        'values': p_values
    },
    'Q': {'values': Q_values},
    'T': {},
    'v': {}
}
diagram.set_limits(x_min=0, x_max=2000, y_min=1e-1, y_max=1e3)
diagram.draw_isolines(diagram_type='logph')
diagram.ax.scatter(su_cp1.get_plotting_props()['h'], su_cp1.get_plotting_props()['p'])
diagram.ax.scatter(cp1_he.get_plotting_props()['h'], cp1_he.get_plotting_props()['p'])
diagram.ax.scatter(he_cp2.get_plotting_props()['h'], he_cp2.get_plotting_props()['p'])
diagram.ax.scatter(cp2_c_out.get_plotting_props()['h'], cp2_c_out.get_plotting_props()['p'])
diagram.ax.scatter(cd_ves.get_plotting_props()['h'], cd_ves.get_plotting_props()['p'])
diagram.ax.scatter(ves_dr.get_plotting_props()['h'], ves_dr.get_plotting_props()['p'])
diagram.ax.scatter(dr_su.get_plotting_props()['h'], dr_su.get_plotting_props()['p'])
diagram.save('logph_Diagramm.pdf')



# %% Auslegung Temperaturbereich District Heating

# T_range = range(88, 92)
# cop_range = []

# for T in T_range:
#     cd_cons.set_attr(T=T)
#     if T == T_range[0]:
#         nw.solve('offdesign', design_path='hp_water', init_path='hp_water')
#     else:
#         nw.solve('offdesign', design_path='hp_water')

#     if nw.lin_dep:
#         cop_range += [np.nan]
#     else:
#         cop_range += [abs(heat.P.val) / power.P.val]

# #     df.loc[T] = eps
