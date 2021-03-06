# -*- coding: utf-8 -*-
"""
Created on Thu Jan  9 10:07:02 2020

@author: Malte Fritz
"""

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

Q_N = abs(float(input('Gib die Nennwärmeleistung in MW ein: '))) * -1e6
# T_amb = 9.1876779
T_amb = 15
T_DH_vl = 85
T_DH_rl = 60
T_amb_out = T_amb - 10

# %% network

nw = network(fluids=['water', 'NH3', 'air'],
                 T_unit='C', p_unit='bar', h_unit='kJ / kg', m_unit='kg / s')

# %% components

# sources & sinks
cc = cycle_closer('coolant cycle closer')
cb = source('consumer back flow')
cf = sink('consumer feed flow')
amb = source('ambient air')
amb_out1 = sink('sink ambient 1')
amb_out2 = sink('sink ambient 2')

# ambient air system
sp = splitter('splitter')
fan = compressor('fan')

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

amb_fan = connection(amb, 'out1', fan, 'in1')
fan_sp = connection(fan, 'out1', sp, 'in1')
sp_su = connection(sp, 'out1', su, 'in1')
su_ev = connection(su, 'out1', ev, 'in1')
ev_amb_out = connection(ev, 'out1', amb_out1, 'in1')

nw.add_conns(amb_fan, fan_sp, sp_su, su_ev, ev_amb_out)

# connection evaporator system - compressor system

su_cp1 = connection(su, 'out2', cp1, 'in1')

nw.add_conns(su_cp1)

# compressor-system

cp1_he = connection(cp1, 'out1', ic, 'in1')
he_cp2 = connection(ic, 'out1', cp2, 'in1')
cp2_c_out = connection(cp2, 'out1', cc, 'in1')

sp_ic = connection(sp, 'out2', ic, 'in2')
ic_out = connection(ic, 'out2', amb_out2, 'in1')

nw.add_conns(cp1_he, he_cp2, sp_ic, ic_out, cp2_c_out)

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

power = bus('total compressor power')
power.add_comps({'c': cp1, 'char': mot1}, {'c': cp2, 'char': mot2},
                {'c': fan, 'char': mot3}, {'c': dhp, 'char': mot4},
                {'c': erp, 'char': mot5})
heat = bus('total delivered heat')
heat.add_comps({'c': cd})

nw.add_busses(power, heat)

# %% component parametrization

# condenser system

cd.set_attr(pr1=0.99, pr2=0.99, ttd_u=5, design=['pr2', 'ttd_u'],
            offdesign=['zeta2', 'kA'])
dhp.set_attr(eta_s=0.8, design=['eta_s'], offdesign=['eta_s_char'])
cons.set_attr(pr=0.99, design=['pr'], offdesign=['zeta'])

# air fan

fan.set_attr(eta_s=0.65, design=['eta_s'], offdesign=['eta_s_char'])

# evaporator system

kA_char1 = ldc('heat exchanger', 'kA_char1', 'DEFAULT', char_line)
kA_char2 = ldc('heat exchanger', 'kA_char2', 'EVAPORATING FLUID', char_line)

ev.set_attr(pr1=0.999, pr2=0.99, ttd_l=5,
            kA_char1=kA_char1, kA_char2=kA_char2,
            design=['pr1', 'ttd_l'], offdesign=['zeta1', 'kA'])
su.set_attr(pr1=0.999, pr2=0.99, ttd_u=2, design=['pr1', 'pr2', 'ttd_u'],
            offdesign=['zeta1', 'zeta2', 'kA'])
erp.set_attr(eta_s=0.8, design=['eta_s'], offdesign=['eta_s_char'])

# compressor system

cp1.set_attr(eta_s=0.85, design=['eta_s'], offdesign=['eta_s_char'])
cp2.set_attr(eta_s=0.9, pr=3, design=['eta_s'], offdesign=['eta_s_char'])
ic.set_attr(pr1=0.99, pr2=0.999, design=['pr1', 'pr2'],
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

# fan blows at constant rate
amb_fan.set_attr(T=T_amb, p=1, fluid={'air': 1, 'NH3': 0, 'water': 0},
                 offdesign=['v'])
sp_su.set_attr(offdesign=['v'])
ev_amb_out.set_attr(p=1, T=T_amb_out, design=['T'])

# compressor-system

he_cp2.set_attr(Td_bp=5, p0=20, design=['Td_bp'])
ic_out.set_attr(T=30, design=['T'])

# %% key paramter

heat.set_attr(P=Q_N)

# %% Calculation

nw.solve('design')
nw.print_results()
nw.save('hp_air')

nw.solve('offdesign', design_path='hp_air')

Q_range = np.linspace(0.3, 1.0, 8)[::-1] * Q_N
df = pd.DataFrame(columns=Q_range/Q_N)
cop_carnot = []
guetegrad = []

heat.set_attr(P=np.nan)

for Q in Q_range:
    heat.set_attr(P=Q)
    nw.solve('offdesign', design_path='hp_air')
    print('Load: ' + '%.1f' % (Q/Q_N))
    print('Power input: ' + '%.0f' % power.P.val + ' W')
    print('Heat output: ' + '%.0f' % heat.P.val + ' W')
    print('COP: ' + '%.2f' % abs(heat.P.val / power.P.val))

    if nw.lin_dep:
        guetegrad += [np.nan]
        print('Warning: Network is linear dependent')

    else:
        cop = abs(heat.P.val) / power.P.val

        T_ln_sink = (T_DH_vl - T_DH_rl) / np.log((273.15 + T_DH_vl)
                                                 / (273.15 + T_DH_rl))
        T_ln_source = (T_amb - T_amb_out) / np.log((273.15 + T_amb)
                                                   / (273.15 + T_amb_out))
        cop_car = T_ln_sink / (T_ln_sink - T_ln_source)
        cop_carnot += [cop_car]
        guetegrad += [cop / cop_car]

df.loc[0, :] = guetegrad


# %% Plotting
colors = ['#00395b', '#74adc1', '#b54036', '#ec6707', '#bfbfbf', '#999999',
          '#010101', '#00395b', '#74adc1', '#b54036', '#ec6707']

fig, ax = plt.subplots()


plt.plot(df.loc[0], '-x', Color=colors[0], markersize=7, linewidth=2)

ax.set_ylabel('Gütegrad')
ax.set_xlabel('Teillast')
ax.grid(linestyle='--')
plt.title('Gütegrad Luft-Wärmepumpe')

# plt.ylim([0.2, 0.4])
# plt.xlim([0.3, 1.2])

plt.show()


# %% Paramater für Solph

# Rechnung für c_0, c_1 und P_in nach solph
# Q und P sind in MW angegeben
gd_max = max(df)
gd_min = min(df)
cop_carnot_min = min(cop_carnot)
cop_carnot_max = max(cop_carnot)
COP_max = gd_max * cop_carnot_min
COP_min = gd_min * cop_carnot_max
Q_out_max = min(Q_range)/1e6                # Mathematisch richtig, weil
Q_out_min = max(Q_range)/1e6                # Q_range negativ ist
s_max = (Q_out_max*1e6)/Q_N
s_min = Q_out_min/Q_out_max
P_in_max = abs(Q_out_max/COP_max)
P_in_min = abs(Q_out_min/COP_min)
c_1 = abs((Q_out_max - Q_out_min))/(P_in_max - P_in_min)
c_0 = abs(Q_out_max )- c_1 * P_in_max

# %% Ausdruck Ergebnisse Solph

print('_____________________________')
print('#############################')
print()
print('Ergebnisse Luft-Wärmepumpe:')
print()
print('Q_N: ' + "%.2f" % abs(Q_N/1e6) + " MW")
print('gd_max: ' + "%.4f" % gd_max)
print('gd_min: ' + "%.4f" % gd_min)
print('COP_max_T_geg : ' + "%.4f" % COP_max)
print('COP_min_T_geg : ' + "%.4f" % COP_min)
print('c_1: ' + "%.4f" % c_1)
print('c_0: ' + "%.4f" % c_0)
print('Q_out_max: ' + "%.2f" % Q_out_max + " MW")
print('Q_out_min: ' + "%.2f" % Q_out_min + " MW")
print('P_in_max = nominal_value: ' + "%.2f" % P_in_max + " MW")
print('P_in_min: ' + "%.2f" % P_in_min + " MW")
print('solph_max: ' + "%.2f" % s_max)
print('solph_min: ' + "%.2f" % s_min)
print()
print('_____________________________')
print('#############################')
