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
lt_si = sink('low temp sink')
lt_so = source('low temp source')

# low temp water system
pu = pump('pump')

# consumer system

cd = condenser('condenser')
dhp = pump('district heating pump')
cons = heat_exchanger_simple('consumer')

# evaporator system

va = valve('valve')
dr = drum('drum')
ev = heat_exchanger('evaporator')
erp = pump('evaporator reciculation pump')

# compressor-system

cp = compressor('compressor')


# %% connections

# consumer system

c_in_cd = connection(cc, 'out1', cd, 'in1')

cb_dhp = connection(cb, 'out1', dhp, 'in1')
dhp_cd = connection(dhp, 'out1', cd, 'in2')
cd_cons = connection(cd, 'out2', cons, 'in1')
cons_cf = connection(cons, 'out1', cf, 'in1')

nw.add_conns(c_in_cd, cb_dhp, dhp_cd, cd_cons, cons_cf)

# connection condenser - evaporator system

cd_va = connection(cd, 'out1', va, 'in1')

nw.add_conns(cd_va)

# evaporator system

va_dr = connection(va, 'out1', dr, 'in1')
dr_erp = connection(dr, 'out1', erp, 'in1')
erp_ev = connection(erp, 'out1', ev, 'in2')
ev_dr = connection(ev, 'out2', dr, 'in2')
dr_cp = connection(dr, 'out2', cp, 'in1')

nw.add_conns(va_dr, dr_erp, erp_ev, ev_dr, dr_cp)

# low temp water system

lt_so_pu = connection(lt_so, 'out1', pu, 'in1')
pu_ev = connection(pu, 'out1', ev, 'in1')
ev_lt_si = connection(ev, 'out1', lt_si, 'in1')

nw.add_conns(lt_so_pu, pu_ev, ev_lt_si)

# compressor-system

cp_c_out = connection(cp, 'out1', cc, 'in1')

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

mot1 = char_line(x=x, y=y)
mot2 = char_line(x=x, y=y)
mot3 = char_line(x=x, y=y)
mot4 = char_line(x=x, y=y)

power = bus('total compressor power')
power.add_comps({'c': cp, 'char': mot1}, {'c': pu, 'char': mot2},
                {'c': dhp, 'char': mot3}, {'c': erp, 'char': mot4})

heat = bus('total delivered heat')
heat.add_comps({'c': cd})

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

kA_char1 = ldc('heat exchanger', 'kA_char1', 'DEFAULT', char_line)
kA_char2 = ldc('heat exchanger', 'kA_char2', 'EVAPORATING FLUID', char_line)

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
cons_cf.set_attr(h=ref(cb_dhp, 1, 0), p=ref(cb_dhp, 1, 0))

# evaporator system cold side

erp_ev.set_attr(m=ref(va_dr, 1.25, 0), p0=5)
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

cop = abs(heat.P.val) / power.P.val
print('COP:', cop)
print('P_out:', power.P.val/1e6)
print('Q_out:', heat.P.val/1e6)

cp.eta_s_char.func.extrapolate = True

# cd_cons.set_attr(T=110)
# nw.solve('offdesign', design_path='hp_water', init_path='hp_water')
# nw.print_results()

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
diagram.ax.scatter(dr_cp.get_plotting_props()['h'], dr_cp.get_plotting_props()['p'])
diagram.ax.scatter(cp_c_out.get_plotting_props()['h'], cp_c_out.get_plotting_props()['p'])
diagram.ax.scatter(cd_va.get_plotting_props()['h'], cd_va.get_plotting_props()['p'])
diagram.ax.scatter(va_dr.get_plotting_props()['h'], va_dr.get_plotting_props()['p'])
diagram.save('logph_Diagramm.pdf')



# %% Auslegung Temperaturbereich District Heating

T_range = range(66, 125)
cop_range = []

for T in T_range:
    cd_cons.set_attr(T=T)
    if T == T_range[0]:
        nw.solve('offdesign', design_path='hp_water', init_path='hp_water')
    else:
        nw.solve('offdesign', design_path='hp_water')
    print('T_VL:   ', cd_cons.T.val)
    print('Vor CD: ', cp_c_out.T.val)
    print('Nach CD:', cd_va.T.val)
    if nw.lin_dep:
        cop_range += [np.nan]
    else:
        cop_range += [abs(heat.P.val) / power.P.val]
    diagram.ax.scatter(dr_cp.get_plotting_props()['h'],
                       dr_cp.get_plotting_props()['p'], c=(((T-66)/125, 0, 0)))
    diagram.ax.scatter(cp_c_out.get_plotting_props()['h'],
                       cp_c_out.get_plotting_props()['p'],
                       c=(((T-66)/125, 0, 0)))
    diagram.ax.scatter(cd_va.get_plotting_props()['h'],
                       cd_va.get_plotting_props()['p'], c=(((T-66)/125, 0, 0)))
    diagram.ax.scatter(va_dr.get_plotting_props()['h'],
                       va_dr.get_plotting_props()['p'], c=(((T-66)/125, 0, 0)))
#     df.loc[T] = eps

diagram.save('logph_Diagramm.pdf')
