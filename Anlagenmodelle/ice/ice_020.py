# -*- coding: utf-8 -*-
"""
Created on Mon Jan  6 10:37:36 2020

@author: Malte Fritz
"""

from tespy.components import (sink, source, splitter, merge, pump,
                              heat_exchanger, heat_exchanger_simple,
                              combustion_engine)
from tespy.connections import bus, ref, connection
from tespy.networks.networks import network
from tespy.tools.characteristics import char_line, load_custom_char
from tespy.tools.data_containers import dc_cc
import numpy as np

from matplotlib import pyplot as plt

# Für das BHKW unseres Referenzsystem Land ist P_N=15MW
Q_N=abs(float(input('Gib die Nennwärmeleistung in MW ein: ')))*-1e6

# %% network

# define full fluid list for the network's variable space
fluid_list = ['Ar', 'N2', 'O2', 'CO2', 'CH4', 'H2O']
# define unit systems and fluid property ranges
nw = network(fluids=fluid_list, p_unit='bar', T_unit='C',
                 p_range=[0.1, 10], T_range=[50, 1200])

# %% components

# sinks & sources
amb = source('ambient')
sf = source('fuel')
chbp = sink('chimney bypass')
ch = sink('chimney')

cw = source('cooling water')
pump = pump('cooling water pump')

cw_split = splitter('cooling water splitter')
cw_merge = merge('cooling water merge')
fg_split = splitter('flue gas splitter')

fgc = heat_exchanger('flue gas cooler')

cons = heat_exchanger_simple('consumer')
cw_out = sink('cooling water sink')

# combustion engine
ice = combustion_engine(label='internal combustion engine')

# %% connections

amb_comb = connection(amb, 'out1', ice, 'in3')
sf_comb = connection(sf, 'out1', ice, 'in4')
comb_fg = connection(ice, 'out3', fg_split, 'in1')

fg_fgc = connection(fg_split, 'out1', fgc, 'in1')
fg_chbp = connection(fg_split, 'out2', chbp, 'in1')

fgc_ch = connection(fgc, 'out1', ch, 'in1')

nw.add_conns(sf_comb, amb_comb, comb_fg, fg_fgc, fg_chbp, fgc_ch)

cw_pu = connection(cw, 'out1', pump, 'in1')
pu_sp = connection(pump, 'out1', cw_split, 'in1')

sp_ice1 = connection(cw_split, 'out1', ice, 'in1')
sp_ice2 = connection(cw_split, 'out2', ice, 'in2')

ice1_m = connection(ice, 'out1', cw_merge, 'in1')
ice2_m = connection(ice, 'out2', cw_merge, 'in2')

nw.add_conns(cw_pu, pu_sp, sp_ice1, sp_ice2, ice1_m, ice2_m)

m_fgc = connection(cw_merge, 'out1', fgc, 'in2')
fgc_cons = connection(fgc, 'out2', cons, 'in1')
cons_out = connection(cons, 'out1', cw_out, 'in1')

nw.add_conns(m_fgc, fgc_cons, cons_out)

# %% busses
# motor efficiency
x = np.array([0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55,
              0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1, 1.05, 1.1, 1.15,
              1.2, 10])
y = 1 / (np.array([0.01, 0.3148, 0.5346, 0.6843, 0.7835, 0.8477, 0.8885,
                   0.9145, 0.9318, 0.9443, 0.9546, 0.9638, 0.9724, 0.9806,
                   0.9878, 0.9938, 0.9982, 1.0009, 1.002, 1.0015, 1, 0.9977,
                   0.9947, 0.9909, 0.9853, 0.9644])
         * 0.97)
mot = char_line(x=x, y=y)

# generator efficiency
x = np.array([0.100, 0.345, 0.359, 0.383, 0.410, 0.432, 0.451, 0.504, 0.541,
              0.600, 0.684, 0.805, 1.000, 1.700, 10])
y = np.array([0.976, 0.989, 0.990, 0.991, 0.992, 0.993, 0.994, 0.995, 0.996,
              0.997, 0.998, 0.999, 1.000, 0.999, 0.99]) * - 0.984
gen1 = char_line(x=x, y=y)
gen2 = char_line(x=x, y=y)

power = bus('power')
power.add_comps({'c': pump, 'char': mot}, {'c': ice, 'p': 'P', 'char': gen1})

ice_power = bus('ice_power')
ice_power.add_comps({'c': ice, 'p': 'P', 'char': gen2})

heat = bus('heat')
heat.add_comps({'c': ice, 'p': 'Q', 'char': -1}, {'c': fgc})

heat_cond = bus('heat_cond')

ti = bus('ti')
ti.add_comps({'c': ice, 'p': 'TI'})
nw.add_busses(power, heat, ti, ice_power, heat_cond)

# %% component parameters

# pump isentropic efficiency char_line
x = np.array([0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1,
              1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2.0, 2.1, 2.2, 2.3,
              2.4, 2.5])
y = np.array([0.7, 0.7667, 0.8229, 0.8698, 0.9081, 0.9387, 0.9623, 0.9796,
              0.9913, 0.9979, 1.0, 0.9981, 0.9926, 0.9839, 0.9725, 0.9586,
              0.9426, 0.9248, 0.9055, 0.8848, 0.8631, 0.8405, 0.8171, 0.7932,
              0.7689, 0.7444])
eta_s_char = dc_cc(func=char_line(x, y), param='m')
pump.set_attr(eta_s=0.8, eta_s_char=eta_s_char,
              design=['eta_s'], offdesign=['eta_s_char'])

# ice charachteristics
# thermal input to power
x= np.array([0.50, 0.75, 0.90, 1.00, 1.05])
y = np.array([2.3, 2.18, 2.14, 2.1, 2.15])
tiP_char = dc_cc(func=char_line(x, y))

# heat to power
x = np.array([0.550, 0.660, 0.770, 0.880, 0.990, 1.100])
y = np.array([0.238, 0.219, 0.203, 0.190, 0.180, 0.173])
Q1_char = dc_cc(func=char_line(x, y))
Q2_char = dc_cc(func=char_line(x, y))

# heat loss to power
x = np.array([0.50, 0.7500, 0.90, 1.000, 1.050])
y = np.array([0.32, 0.3067, 0.30, 0.295, 0.293])
Qloss_char = dc_cc(func=char_line(x, y))


# set combustion chamber fuel, air to stoichometric air ratio and thermal input
ice.set_attr(pr1=0.98, lamb=1.0, design=['pr1'], offdesign=['zeta1'],
             tiP_char=tiP_char, Q1_char=Q1_char, Q2_char=Q2_char, Qloss_char=Qloss_char)

# flue gas cooler

x1 = np.array([0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1, 1.1, 1.2,
               1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2, 2.1, 2.2, 2.3, 2.4, 2.5])
y1 = np.array([0.000, 0.164, 0.283, 0.389, 0.488, 0.581, 0.670, 0.756, 0.840,
               0.921, 1.000, 1.078, 1.154, 1.228, 1.302, 1.374, 1.446, 1.516,
               1.585, 1.654, 1.722, 1.789, 1.855, 1.921, 1.986, 2.051])
x2 = np.array([0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1, 1.1, 1.2,
               1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2, 2.1, 2.2, 2.3, 2.4, 2.5])
y2 = np.array([0.000, 0.245, 0.375, 0.480, 0.572, 0.655, 0.732, 0.804, 0.873,
               0.938, 1.000, 1.060, 1.118, 1.174, 1.228, 1.281, 1.332, 1.382,
               1.431, 1.479, 1.526, 1.572, 1.618, 1.662, 1.706, 1.749])

kA_char1 = dc_cc(func=char_line(x1, y1), param='m')
kA_char2 = dc_cc(func=char_line(x2, y2), param='m')

fgc.set_attr(pr1=0.99, pr2=0.99,
             kA_char1=kA_char1, kA_char2=kA_char2,
             design=['pr1', 'pr2'], offdesign=['zeta1', 'zeta2', 'kA'])

# consumer

cons.set_attr(pr=0.99)

# %% connection parameters


# air and fuel
amb_comb.set_attr(p=1.05, T=20, fluid={'Ar': 0.0129, 'N2': 0.7553, 'H2O': 0,
                                       'CH4': 0, 'CO2': 0.0004, 'O2': 0.2314})
sf_comb.set_attr(T=20, fluid={'CO2': 0, 'Ar': 0, 'N2': 0,
                              'O2': 0, 'H2O': 0, 'CH4': 1})

# flue gas outlet
#m_fgc.set_attr(T=75, design=['T'])
fgc_ch.set_attr(T=150, design=['T'])
fg_chbp.set_attr(m=0)

# cooling water cylce
cw_pu.set_attr(p=10, T=50,
               fluid={'CO2': 0, 'Ar': 0, 'N2': 0, 'O2': 0, 'H2O': 1, 'CH4': 0})

fgc_cons.set_attr(T=90, fluid0={'H2O': 1})
# splitting mass flow in half
sp_ice1.set_attr(m=ref(sp_ice2, 1, 0))

# cycle closing
cons_out.set_attr(p=ref(cw_pu, 1, 0), h=ref(cw_pu, 1, 0))

# %% solving
heat.set_attr(P=Q_N)

P_L = []
Q_L = []

mode = 'design'
nw.solve(mode=mode) #, init_path='ice_stable') #ice_stable nicht mehr vorhanden, bzw. noch nach altem dev Stand erzeugt
nw.print_results()
nw.save('ice_design')
print(power.P.val, heat.P.val,
      -power.P.val / ti.P.val, -heat.P.val / ti.P.val)

Q_in_BHKW = ti.P.val

ice_P_design = ice.P.val

ice.set_attr(P=ice_P_design)
heat.set_attr(P=np.nan)

mode = 'offdesign'
nw.solve(mode=mode, init_path='ice_design', design_path='ice_design')
nw.print_results()
P_L += [abs(power.P.val)]
Q_L += [abs(heat.P.val)]

#############################
#1 max P über Bypass

print('Open bypass, shut down flue gas cooler at maximum power output')

m_bypass = [0, 1/3, 1, 3]
fg_chbp.set_attr(m=np.nan)
fgc_ch.set_attr(m=np.nan) #warum NaN setzen, wenn später mit Faktor multipliziert werden soll?

for m in m_bypass:
    fg_chbp.set_attr(m=ref(fgc_ch, m, 0))
    nw.solve(mode=mode, init_path='ice_design', design_path='ice_design')
    print(power.P.val, heat.P.val,
          -power.P.val / ti.P.val, -heat.P.val / ti.P.val)
    P_L += [abs(power.P.val)]
    Q_L += [abs(heat.P.val)]

# close main chimney
fg_chbp.set_attr(m=np.nan)
fgc_ch.set_attr(m=np.nan)
fgc_ch.set_attr(m=0.01)
nw.solve(mode=mode, init_path='ice_design', design_path='ice_design')
print(power.P.val, heat.P.val,
      -power.P.val / ti.P.val, -heat.P.val / ti.P.val)
P_L += [abs(power.P.val)]
Q_L += [abs(heat.P.val)]

P_max_woDH = abs(power.P.val)
eta_el_max = abs(power.P.val) / ti.P.val
H_L_FG_min1 = 1 - abs(power.P.val + heat.P.val)/ ti.P.val

##############################
# min P über Bypass
print('Open bypass, shut down flue gas cooler at minimum power output')

ice.set_attr(P=ice_P_design * 0.55) # Pmin als 0.55*Pmax hardcodet?
m_bypass = [0, 1 / 3, 1, 3]
fg_chbp.set_attr(m=np.nan)
fgc_ch.set_attr(m=np.nan)

for m in m_bypass:
    fg_chbp.set_attr(m=ref(fgc_ch, m, 0))
    nw.solve(mode=mode, init_path='ice_design', design_path='ice_design')
    print(power.P.val, heat.P.val,
          -power.P.val / ti.P.val, -heat.P.val / ti.P.val)
    P_L += [abs(power.P.val)]
    Q_L += [abs(heat.P.val)]

# close main chimney
fg_chbp.set_attr(m=np.nan)
fgc_ch.set_attr(m=np.nan)
fgc_ch.set_attr(m=0.01)
nw.solve(mode=mode, init_path='ice_design', design_path='ice_design')
print(power.P.val, heat.P.val,
      -power.P.val / ti.P.val, -heat.P.val / ti.P.val)
P_L += [abs(power.P.val)]
Q_L += [abs(heat.P.val)]

P_min_woDH = abs(power.P.val)
eta_el_min = abs(power.P.val) / ti.P.val
H_L_FG_min2 = 1 - abs(power.P.val + heat.P.val)/ ti.P.val

H_L_FG_min = (H_L_FG_min1 + H_L_FG_min2)/2

##############################
# min Q (Opened Bypass), from min P to max P
print('Opened bypass, go from minimum to maximum power')

ice_power = np.linspace(ice_P_design * 0.55, ice_P_design, 5)
fg_chbp.set_attr(m=np.nan)
fgc_ch.set_attr(m=np.nan)

fgc_ch.set_attr(m=0.01)

for P in ice_power:
    ice.set_attr(P=P)
    nw.solve(mode=mode, init_path='ice_design', design_path='ice_design')
    print(power.P.val, heat.P.val,
          -power.P.val / ti.P.val, -heat.P.val / ti.P.val)
    P_L += [abs(power.P.val)]
    Q_L += [abs(heat.P.val)]

##############################
# max Q (Closed Bypass), from min P to max P
print('Closed bypass, go from minimum to maximum power')

fg_chbp.set_attr(m=np.nan)
fgc_ch.set_attr(m=np.nan)

fg_chbp.set_attr(m=0)

for P in ice_power:
    ice.set_attr(P=P)
    nw.solve(mode=mode, init_path='ice_design', design_path='ice_design')
    print(power.P.val, heat.P.val,
          -power.P.val / ti.P.val, -heat.P.val / ti.P.val)
    P_L += [abs(power.P.val)]
    Q_L += [abs(heat.P.val)]
    if P == ice_power[0]:
        H_L_FG_max1 = 1 - abs(power.P.val + heat.P.val)/ ti.P.val
    elif P == ice_power[-1]:
        H_L_FG_max2 = 1 - abs(power.P.val + heat.P.val)/ ti.P.val

H_L_FG_max = (H_L_FG_max1 + H_L_FG_max2)/2

# P_Q_Diagramm

plt.plot(Q_L, P_L, 'x')
plt.show()

print('_____________________________')
print('#############################')
print()
print('Ergebnisse:')
print()
print('Q_N: ' + "%.2f" % abs(Q_N/1e6) + " MW")
print('Q_in_BHKW: ' + "%.2f" % (Q_in_BHKW/1e6) + " MW")
print('P_max_woDH: ' + "%.2f" % (P_max_woDH/1e6) + " MW")
print('eta_el_max: ' + "%.4f" % eta_el_max)
print('P_min_woDH: ' + "%.2f" % (P_min_woDH/1e6) + " MW")
print('eta_el_min: ' + "%.4f" % eta_el_min)
print('H_L_FG_max: ' + "%.4f" % H_L_FG_max)
print('H_L_FG_min: ' + "%.4f" % H_L_FG_min)
print()
print('_____________________________')
print('#############################')
