"""TESPy heat pipe model using ambient air as heatsource.

Created on Thu Jan  9 10:07:02 2020

@author: Malte Fritz
"""

import numpy as np
import pandas as pd

from tespy.networks import network
from tespy.components import (sink, source, splitter, compressor, condenser,
                              pump, heat_exchanger_simple, valve, drum,
                              heat_exchanger, cycle_closer)
from tespy.connections import connection, ref
from tespy.tools.characteristics import char_line
from tespy.tools.characteristics import load_default_char as ldc

# Auslegung für 200kW

Q_N=abs(float(input('Gib die Nennwärmeleistung in kW ein: ')))*-1e3

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

cp1_ic = connection(cp1, 'out1', ic, 'in1')
ic_cp2 = connection(ic, 'out1', cp2, 'in1')
cp2_c_out = connection(cp2, 'out1', cc, 'in1')

sp_ic = connection(sp, 'out2', ic, 'in2')
ic_out = connection(ic, 'out2', amb_out2, 'in1')

nw.add_conns(cp1_ic, ic_cp2, sp_ic, ic_out, cp2_c_out)

# %% component parametrization

# condenser system

cd.set_attr(pr1=0.99, pr2=0.99, ttd_u=5, design=['pr2', 'ttd_u'],
            offdesign=['zeta2', 'kA'])
dhp.set_attr(eta_s=0.8, design=['eta_s'], offdesign=['eta_s_char'])
cons.set_attr(pr=0.99, design=['pr'], offdesign=['zeta'])

# ambient air

fan.set_attr(eta_s=0.8, pr=1.005, design=['eta_s'], offdesign=['eta_s_char'])

# evaporator system

kA_char1 = ldc('heat exchanger', 'kA_char1', 'EVAPORATING FLUID', char_line)
kA_char2 = ldc('heat exchanger', 'kA_char2', 'EVAPORATING FLUID', char_line)

ev.set_attr(pr1=0.999, pr2=0.99, ttd_l=5,
            kA_char1=kA_char1, kA_char2=kA_char2,
            design=['pr1', 'ttd_l'], offdesign=['zeta1', 'kA'])
su.set_attr(pr1=0.999, pr2=0.99, ttd_u=2, design=['pr1', 'pr2', 'ttd_u'],
            offdesign=['zeta1', 'zeta2', 'kA'])
erp.set_attr(eta_s=0.8, design=['eta_s'], offdesign=['eta_s_char'])

# compressor system

x = np.array([0.000, 0.400, 1.000, 1.500])
y = np.array([0.500, 0.900, 1.000, 1.025])
gen = char_line(x=x, y=y)
cp1.set_attr(eta_s=0.8, design=['eta_s'], offdesign=['eta_s_char'],
             eta_s_char=gen)
cp2.set_attr(eta_s=0.8, pr=5, design=['eta_s'], offdesign=['eta_s_char'],
             eta_s_char=gen)
ic.set_attr(pr1=0.98, pr2=0.999, design=['pr1', 'pr2'],
            offdesign=['zeta1', 'zeta2', 'kA'])

# %% connection parametrization

# condenser system

c_in_cd.set_attr(fluid={'air': 0, 'NH3': 1, 'water': 0})
cb_dhp.set_attr(T=60, p=10, fluid={'air': 0, 'NH3': 0, 'water': 1})
cd_cons.set_attr(T=90)
cons_cf.set_attr(h=ref(cb_dhp, 1, 0), p=ref(cb_dhp, 1, 0))

# evaporator system cold side

erp_ev.set_attr(m=ref(ves_dr, 4, 0), p0=5)
su_cp1.set_attr(p0=5, h0=1700)

# evaporator system hot side

amb_fan.set_attr(T=12, p=4, fluid={'air': 1, 'NH3': 0, 'water': 0})
# sp_su.set_attr(offdesign=['v'])
ev_amb_out.set_attr(T=ref(amb_fan, 1, -4))

# compressor-system

ic_cp2.set_attr(T=40, p0=10, design=['T'])
ic_out.set_attr(T=30, design=['T'], offdesign=['v'])

# %% key paramter

cons.set_attr(Q=Q_N)

# %% Calculation

nw.solve('design')
nw.print_results()
nw.save('heat_pump_air')

# T_range ist die vorzugegbenden Außentemperaturen und Q_range bildet die
# abgegebende Wärme beim Konsumenten ab und somit die Auslegung der Wärmepumpe
T_range = [6, 9, 12, 15, 18, 21, 24]
# T_range = [0, 3, 6, 9, 12, 15, 18, 21, 24, 27]
Q_range = np.array([20e3, 40e3, 60e3, 80e3, 100e3, 120e3, 140e3, 160e3, 180e3, 200e3, 220e3])
# Q_range = np.array([10e6, 12.5e6, 15e6, 17.5e6, 20e6, 22.5e6, 25e6])
# Q_range = np.array([5e6, 7.5e6, 10e6, 12.5e6, 15e6, 17.5e6, 20e6, 22.5e6, 25e6, 27.5e6])
df = pd.DataFrame(columns=Q_range / -cons.Q.val)

for T in T_range:
    amb_fan.set_attr(T=T)
    eps = []

    for Q in Q_range:
        cons.set_attr(Q=-Q)
        try:
            nw.solve('offdesign',
                     init_path='OD_air_' + str(Q/1e3),
                     design_path='heat_pump_air')
        except FileNotFoundError:
            nw.solve('offdesign', init_path='heat_pump_air',
                     design_path='heat_pump_air')

        if nw.lin_dep:
            eps += [np.nan]

        else:
            nw.save('OD_air_' + str(Q/1e3))
            eps += [abs(cd.Q.val) / (cp1.P.val + cp2.P.val + erp.P.val
                                     + fan.P.val)]
            # Hier wird der COP berechnet: Q_out / P_in

    df.loc[T] = eps

df.to_csv('COP_air.csv')


# %% Paramater für Solph

# Rechnung für c_0, c_1 und P_in nach solph
# Q und P sind in MW angegeben
COP_max_all = df.max(axis=1)
COP_max = max(COP_max_all)
COP_min_all = df.min(axis=1)
COP_min = min(COP_min_all)
Q_out_max = max(Q_range)/1e6
Q_out_min = min(Q_range)/1e6
s_max = (Q_out_max*1e6)/(abs(Q_N))
s_min = Q_out_min/Q_out_max
P_in_max = Q_out_max/COP_max
P_in_min = Q_out_min/COP_min
c_1 = (Q_out_max - Q_out_min)/(P_in_max - P_in_min)
c_0 = Q_out_max - c_1 * P_in_max


# %% Ausdruck Ergebnisse Solph

print('_____________________________')
print('#############################')
print()
print('Ergebnisse:')
print()
print('Q_N: ' + "%.2f" % abs(Q_N/1e6) + " MW")
print('COP_max: ' + "%.4f" % COP_max)
print('COP_min: ' + "%.4f" % COP_min)
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