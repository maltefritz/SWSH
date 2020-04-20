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

from time import time

Q_N = abs(float(input('Gib die Nennwärmeleistung in MW ein: '))) * -1e6
# T_amb and T_amb_out kommen von der Drammen District Heating Wärmepumpe aus
# Norwegen. T_amb ist die Außentemperatur in einem Fluß und T_amb_out die
# Differenz vom Austritt zum Eintritt
T_amb = 8
T_DH_vl = 90
T_DH_rl = 50
T_amb_out = T_amb - 4

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

# ambient air system
sp = splitter('splitter')
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

amb_pu = connection(amb, 'out1', pu, 'in1')
pu_sp = connection(pu, 'out1', sp, 'in1')
sp_su = connection(sp, 'out1', su, 'in1')
su_ev = connection(su, 'out1', ev, 'in1')
ev_amb_out = connection(ev, 'out1', amb_out1, 'in1')

nw.add_conns(amb_pu, pu_sp, sp_su, su_ev, ev_amb_out)

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
                {'c': pu, 'char': mot3}, {'c': dhp, 'char': mot4},
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
cp2.set_attr(eta_s=0.9, pr=3, design=['eta_s'], offdesign=['eta_s_char'])
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
amb_pu.set_attr(T=T_amb, p=1, fluid={'air': 0, 'NH3': 0, 'water': 1},
                offdesign=['v'])
sp_su.set_attr(offdesign=['v'])
ev_amb_out.set_attr(p=1, T=T_amb_out, design=['T'])

# compressor-system

he_cp2.set_attr(Td_bp=5, p0=20, design=['Td_bp'])
ic_out.set_attr(T=10, design=['T'])

# %% key paramter

heat.set_attr(P=Q_N)

# %% Calculation

nw.solve('design')
nw.print_results()
nw.save('hp_water')

cp1.eta_s_char.func.extrapolate = True
cp2.eta_s_char.func.extrapolate = True

nw.solve('offdesign', design_path='hp_water')
nw.set_attr(iterinfo=False)

T_db = []
P_max = []
P_min = []
c_1 = []
c_0 = []

T_range = range(70, 126)
Q_range = np.linspace(0.3, 1.0, 8)[::-1] * Q_N
df = pd.DataFrame(columns=Q_range/Q_N)

for T in T_range:
    cd_cons.set_attr(T=T)
    cop_carnot = []
    guetegrad = []
    P_list = []

    heat.set_attr(P=np.nan)
    tmp = time()

    for Q in Q_range:
        heat.set_attr(P=Q)
        if Q == Q_range[0]:
            nw.solve('offdesign', design_path='hp_water', init_path='hp_water')
        else:
            nw.solve('offdesign', design_path='hp_water')

        if nw.lin_dep:
            guetegrad += [np.nan]
            print('Warning: Network is linear dependent')

        else:
            cop = abs(heat.P.val) / power.P.val
            P_list += [power.P.val]

            Q_source = abs(ev.Q.val + su.Q.val)
            SQ_source = abs(ev.SQ2.val + su.SQ2.val)

            Q_sink = abs(cd.Q.val)
            SQ_sink = abs(cd.SQ1.val)

            T_m_sink = Q_sink / SQ_sink
            T_m_source = Q_source / SQ_source

            T_ln_sink = (T_DH_vl - T_DH_rl) / np.log((273.15 + T_DH_vl)
                                                     / (273.15 + T_DH_rl))
            T_ln_source = (T_amb - T_amb_out) / np.log((273.15 + T_amb)
                                                       / (273.15 + T_amb_out))

            cop_car = T_m_sink / (T_m_sink - T_m_source)
            cop_carnot += [cop_car]

            guetegrad += [cop / cop_car]

    T_db += [T]
    P_max += [abs(max(P_list))/1e6]
    P_min += [abs(min(P_list))/1e6]
    c_1 += [abs((Q_range[0] - Q_range[-1])/1e6)/(P_max[-1] - P_min[-1])]
    c_0 += [abs(Q_range[0]/1e6) - c_1[-1] * P_max[-1]]

    df.loc[0, :] = guetegrad
    solph_komp = {'T_DH_VL / C': T_db, 'P_max / MW': P_max,
                  'P_min / MW': P_min, 'c_1': c_1, 'c_0': c_0}
    df3 = pd.DataFrame(solph_komp)
    print(time() - tmp)
    tmp = time()

    # %% Plotting
    colors = ['#00395b', '#74adc1', '#b54036', '#ec6707', '#bfbfbf', '#999999',
              '#010101', '#00395b', '#74adc1', '#b54036', '#ec6707']

    fig, ax = plt.subplots()

    df2 = pd.DataFrame({'Power P': np.array(P_list)/1e6,
                        'Heat Q': abs(Q_range)/1e6})
    df2.index = df2['Power P']
    del df2['Power P']

    plt.plot(df2, '-x', Color=colors[0],
             markersize=7, linewidth=2)
    ax.set_ylabel('Wärmestrom Q in MW')
    ax.set_xlabel('Leistung P in MW')
    ax.grid(linestyle='--')
    plt.title('PQ-Diagramm für T= ' + str(T))

    plt.show()
    print(time() - tmp)

dirpath = path.abspath(path.join(__file__, "../../.."))
writepath = path.join(dirpath, 'Eingangsdaten', 'Wärmepumpe_Wasser.csv')
df3.to_csv(writepath, sep=';', na_rep='#N/A', index=False)
