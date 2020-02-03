# -*- coding: utf-8 -*-
"""
Created on Thu Jul 12 07:45:32 2018

@author: witte
"""

from tespy import cmp, con, nwk, hlp, cmp_char, nwkr
import numpy as np
from matplotlib import pyplot as plt

# %% network
fluid_list = ['Ar', 'N2', 'O2', 'CO2', 'CH4', 'H2O']

nw = nwk.network(fluids=fluid_list, p_unit='bar', T_unit='C', h_unit='kJ / kg',
                 p_range=[1, 100], T_range=[10, 1500], h_range=[10, 4000])

# %% components
# gas turbine part
comp = cmp.compressor('compressor')
comp_fuel = cmp.compressor('fuel compressor')
c_c = cmp.combustion_chamber('combustion')
g_turb = cmp.turbine('gas turbine')

CH4 = cmp.source('fuel source')
air = cmp.source('ambient air')

# waste heat recovery
suph = cmp.heat_exchanger('superheater')
evap = cmp.heat_exchanger('evaporator')
drum = cmp.drum('drum')
eco = cmp.heat_exchanger('economizer')
ch = cmp.sink('chimney')

# steam turbine part
turb_hp = cmp.turbine('steam turbine high pressure')
cond_dh = cmp.condenser('district heating condenser')
mp_split = cmp.splitter('mp split')
turb_lp = cmp.turbine('steam turbine low pressure')
cond = cmp.condenser('condenser')
merge = cmp.merge('merge')
pump1 = cmp.pump('feed water pump 1')
pump2 = cmp.pump('feed water pump 2')
ls_out = cmp.sink('ls sink')
ls_in = cmp.source('ls source')
mp_valve = cmp.valve('mp valve')

# district heating
dh_in = cmp.source('district heating backflow')
dh_out = cmp.sink('district heating feedflow')

# cooling water
cw_in = cmp.source('cooling water backflow')
cw_out = cmp.sink('cooling water feedflow')

# %% connections
# gas turbine part
c_in = con.connection(air, 'out1', comp, 'in1')
c_out = con.connection(comp, 'out1', c_c, 'in1')
fuel_comp = con.connection(CH4, 'out1', comp_fuel, 'in1')
comp_cc = con.connection(comp_fuel, 'out1', c_c, 'in2')
gt_in = con.connection(c_c, 'out1', g_turb, 'in1')
gt_out = con.connection(g_turb, 'out1', suph, 'in1')

nw.add_conns(c_in, c_out, fuel_comp, comp_cc, gt_in, gt_out)

# waste heat recovery (flue gas side)
suph_evap = con.connection(suph, 'out1', evap, 'in1')
evap_eco = con.connection(evap, 'out1', eco, 'in1')
eco_ch = con.connection(eco, 'out1', ch, 'in1')

nw.add_conns(suph_evap, evap_eco, eco_ch)

# waste heat recovery (water side)
eco_drum = con.connection(eco, 'out2', drum, 'in1')
drum_evap = con.connection(drum, 'out1', evap, 'in2')
evap_drum = con.connection(evap, 'out2', drum, 'in2')
drum_suph = con.connection(drum, 'out2', suph, 'in2')

nw.add_conns(eco_drum, drum_evap, evap_drum, drum_suph)

# steam turbine
suph_ls = con.connection(suph, 'out2', ls_out, 'in1')
ls = con.connection(ls_in, 'out1', turb_hp, 'in1')
mp = con.connection(turb_hp, 'out1', mp_split, 'in1')

# extraction
mp_ws = con.connection(mp_split, 'out1', cond_dh, 'in1', design_path='cet_design_maxQ')
mp_c = con.connection(cond_dh, 'out1', pump1, 'in1', design_path='cet_design_maxQ')
mp_fw = con.connection(pump1, 'out1', merge, 'in1', design_path='cet_design_maxQ')

nw.add_conns(suph_ls, ls, mp, mp_ws, mp_c, mp_fw)

# backpressure
mp_v = con.connection(mp_split, 'out2', mp_valve, 'in1')
mp_ls = con.connection(mp_valve, 'out1', turb_lp, 'in1')
lp_ws = con.connection(turb_lp, 'out1', cond, 'in1')
lp_c = con.connection(cond, 'out1', pump2, 'in1')
lp_fw = con.connection(pump2, 'out1', merge, 'in2')
fw = con.connection(merge, 'out1', eco, 'in2')

nw.add_conns(mp_v, mp_ls, lp_ws, lp_c, lp_fw, fw)

# district heating
dh_i = con.connection(dh_in, 'out1', cond_dh, 'in2', design_path='cet_design_maxQ')
dh_o = con.connection(cond_dh, 'out2', dh_out, 'in1', design_path='cet_design_maxQ')

# cooling water
cw_i = con.connection(cw_in, 'out1', cond, 'in2')
cw_o = con.connection(cond, 'out2', cw_out, 'in1')

nw.add_conns(cw_i, cw_o, dh_i, dh_o)

# %% busses

# motor efficiency
x = np.array([0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55,
              0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1, 1.05, 1.1, 1.15,
              1.2, 10])
y = np.array([0.01, 0.3148, 0.5346, 0.6843, 0.7835, 0.8477, 0.8885, 0.9145,
              0.9318, 0.9443, 0.9546, 0.9638, 0.9724, 0.9806, 0.9878, 0.9938,
              0.9982, 1.0009, 1.002, 1.0015, 1, 0.9977, 0.9947, 0.9909, 0.9853,
              0.9644]) / 0.97

mot1 = cmp_char.characteristics(x=x, y=y)
mot2 = cmp_char.characteristics(x=x, y=y)
mot3 = cmp_char.characteristics(x=x, y=y)
mot4 = cmp_char.characteristics(x=x, y=y)

# generator efficiency
x = np.array([0.100, 0.345, 0.359, 0.383, 0.410, 0.432, 0.451, 0.504, 0.541,
              0.600, 0.684, 0.805, 1.000, 1.700, 10])
y = np.array([0.976, 0.989, 0.990, 0.991, 0.992, 0.993, 0.994, 0.995, 0.996,
              0.997, 0.998, 0.999, 1.000, 0.999, 0.99]) * 0.984

gen1 = cmp_char.characteristics(x=x, y=y)
gen2 = cmp_char.characteristics(x=x, y=y)

power = con.bus('power output')
power.add_comps({'c': g_turb, 'char': gen1}, {'c': comp, 'char': 1},
                {'c': comp_fuel, 'char': mot1}, {'c': turb_hp, 'char': gen2},
                {'c': pump1, 'char': mot2},
                {'c': turb_lp, 'char': mot3}, {'c': pump2, 'char': mot4})

gt_power = con.bus('gas turbine power output')
gt_power.add_comps({'c': g_turb}, {'c': comp})

heat_out = con.bus('heat output')
heat_out.add_comps({'c': cond_dh})

heat_in = con.bus('heat input')
heat_in.add_comps({'c': c_c})

nw.add_busses(power, heat_out, heat_in, gt_power)

# %% component parameters

# characteristic line for compressor isentropic efficiency
x = np.array([0.000, 0.400, 1.000, 1.600, 2.000])
y = np.array([0.500, 0.900, 1.000, 1.050, 0.9500])
cp_char1 = hlp.dc_cc(x=x, y=y, param='m')
cp_char2 = hlp.dc_cc(x=x, y=y, param='m')

# characteristic line for turbine isentropic efficiency
x = np.array([0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1,
              1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2.0, 2.1, 2.2, 2.3,
              2.4, 2.5])
y = np.array([0.7, 0.7667, 0.8229, 0.8698, 0.9081, 0.9387, 0.9623, 0.9796,
              0.9913, 0.9979, 1.0, 0.9981, 0.9926, 0.9839, 0.9725, 0.9586,
              0.9426, 0.9248, 0.9055, 0.8848, 0.8631, 0.8405, 0.8171, 0.7932,
              0.7689, 0.7444])
eta_s_gt = hlp.dc_cc(x=x, y=y, param='m')

# characteristic line for pump isentropic efficiency
x = np.array([0, 0.0625, 0.125, 0.1875, 0.25, 0.3125, 0.375, 0.4375, 0.5,
              0.5625, 0.6375, 0.7125, 0.7875, 0.9, 0.9875, 1, 1.0625, 1.125,
              1.175, 1.2125, 1.2375, 1.25, 1.5])
y = np.array([0.008, 0.139, 0.273, 0.400, 0.519, 0.626, 0.722, 0.806, 0.875,
              0.931, 0.973, 1.001, 1.020, 1.016, 1.005, 1.000, 0.975, 0.929,
              0.883, 0.838, 0.784, 0.761, 0.2])
eta_s_p1 = hlp.dc_cc(x=x, y=y, param='m')
eta_s_p2 = hlp.dc_cc(x=x, y=y, param='m')

# characteristic line for district heating condenser kA hot side
x = np.array([0, 0.0001, 0.001, 0.01, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8,
              0.9, 1.0, 2.0])
y = np.array([0.025, 0.05, 0.1, 0.2, 0.4, 0.85, 0.89, 0.92, 0.945,
              0.965, 0.98, 0.99, 0.995, 1.000, 1.05])
cd_char_hot = hlp.dc_cc(x=x, y=y, param='m')

# gas turbine
comp.set_attr(pr=15, eta_s=0.85, eta_s_char=cp_char1, design=['pr', 'eta_s'], offdesign=['eta_s_char'])
comp_fuel.set_attr(eta_s=0.85, eta_s_char=cp_char2, design=['eta_s'], offdesign=['eta_s_char'])
g_turb.set_attr(eta_s=0.9, eta_s_char=eta_s_gt, design=['eta_s'], offdesign=['eta_s_char', 'cone'])
c_c.set_attr(lamb=2.5)

# steam turbine
suph.set_attr(pr1=0.99, pr2=0.98, ttd_u=50, design=['pr1', 'pr2', 'ttd_u'], offdesign=['zeta1', 'zeta2', 'kA'])
eco.set_attr(pr1=0.99, pr2=1, design=['pr1', 'pr2'], offdesign=['zeta1', 'zeta2', 'kA'])
evap.set_attr(pr1=0.99, ttd_l=20, design=['pr1', 'ttd_l'], offdesign=['zeta1', 'kA'])
turb_hp.set_attr(eta_s=0.88, eta_s_char='TRAUPEL', design=['eta_s'], offdesign=['eta_s_char', 'cone'])
turb_lp.set_attr(eta_s=0.88, eta_s_char='TRAUPEL', design=['eta_s'], offdesign=['eta_s_char', 'cone'])

cond_dh.set_attr(kA_char1=cd_char_hot, pr1=0.99, pr2=0.98, ttd_u=5, design=['ttd_u', 'pr2'], offdesign=['zeta2', 'kA'], design_path='cet_design_maxQ')
cond.set_attr(pr1=0.99, pr2=0.98, ttd_u=5, design=['ttd_u', 'pr2'], offdesign=['zeta2', 'kA'])

pump1.set_attr(eta_s=0.8, eta_s_char=eta_s_p1, design=['eta_s'], offdesign=['eta_s_char'], design_path='cet_design_maxQ')
pump2.set_attr(eta_s=0.8, eta_s_char=eta_s_p2, design=['eta_s'], offdesign=['eta_s_char'])


mp_valve.set_attr(pr=1, design=['pr'])
# %% connection parameters

# gas turbine
c_in.set_attr(T=20, p=1, fluid={'Ar': 0.0129, 'N2': 0.7553, 'H2O': 0,
                                'CH4': 0, 'CO2': 0.0004, 'O2': 0.2314})
#gt_in.set_attr(T=1315)
#gt_out.set_attr(p=1.05)
fuel_comp.set_attr(p=con.ref(c_in, 1, 0), T=con.ref(c_in, 1, 0), h0=800,
                   fluid={'CO2': 0.04, 'Ar': 0, 'N2': 0,
                          'O2': 0, 'H2O': 0, 'CH4': 0.96})

# waste heat recovery
eco_ch.set_attr(T=142, design=['T'], p=1.02)

# steam turbine
evap_drum.set_attr(m=con.ref(drum_suph, 4, 0))
suph_ls.set_attr(p=130, fluid={'CO2': 0, 'Ar': 0, 'N2': 0,
                               'O2': 0, 'H2O': 1, 'CH4': 0},
                 design=['p'])
ls.set_attr(p=con.ref(suph_ls, 1, 0), h=con.ref(suph_ls, 1, 0))

#mp.set_attr(p=5, design=['p'])
mp_ls.set_attr(m=con.ref(mp_ws, 0.2, 0))
#lp_ws.set_attr(p=0.8, design=['p'])

# district heating
dh_i.set_attr(T=60, p=10, fluid={'CO2': 0, 'Ar': 0, 'N2': 0,
                                 'O2': 0, 'H2O': 1, 'CH4': 0})
dh_o.set_attr(T=90)

# cooling water
cw_i.set_attr(T=15, p=5, fluid={'CO2': 0, 'Ar': 0, 'N2': 0,
                                'O2': 0, 'H2O': 1, 'CH4': 0})

cw_o.set_attr(T=30, design=['T'], offdesign=['m'])

# %% design case 1: district heating condeser layout

P = []
Q = []

heat_out.set_attr(P=-65e6)
nw.solve(mode='design', init_path='cet')
nw.print_results()
nw.save('cet_design_maxQ')
gt_power_design = gt_power.P.val
print(heat_out.P.val / heat_in.P.val, power.P.val / heat_in.P.val)
print(heat_out.P.val, power.P.val, heat_in.P.val)
print(gt_power.P.val)

# design case 2: maximum gas turbine minimum heat extraction (cet_design_minQ)
gt_power.set_attr(P=gt_power_design)
heat_out.set_attr(P=-1e5)

# local offdesign for district heating condenser
cond_dh.set_attr(local_offdesign=True)
pump1.set_attr(local_offdesign=True)
mp_ws.set_attr(local_offdesign=True)
mp_c.set_attr(local_offdesign=True)
mp_fw.set_attr(local_offdesign=True)
dh_i.set_attr(local_offdesign=True)
dh_o.set_attr(local_offdesign=True)

mp_ls.set_attr(m=np.nan)
nw.solve(mode='design', init_path='cet')
nw.save('cet_design_minQ')
nw.print_results()
m_lp_max = mp_ls.m.val_SI
print(heat_out.P.val / heat_in.P.val, power.P.val / heat_in.P.val)
print(heat_out.P.val, power.P.val)
print(mp_ls.m.val_SI / m_lp_max)

# merge the plants together: offdesign test
print('no heat, full power')
#nw.set_printoptions(print_level='none')

nw.solve(mode='offdesign', design_path='cet_design_minQ')
print(heat_out.P.val / heat_in.P.val, power.P.val / heat_in.P.val)
print(heat_out.P.val, power.P.val)
print(mp_ls.m.val_SI / m_lp_max)
nw.print_results()
P += [-power.P.val]
Q += [-heat_out.P.val]

# move to maximum heat extraction at maximum gas turbine power

heat_out.set_attr(P=-1e6)
nw.solve(mode='offdesign', design_path='cet_design_minQ')
print(heat_out.P.val / heat_in.P.val, power.P.val / heat_in.P.val)
print(heat_out.P.val, power.P.val)
print(mp_ls.m.val_SI / m_lp_max)
P += [-power.P.val]
Q += [-heat_out.P.val]

heat_out.set_attr(P=-5e6)
nw.solve(mode='offdesign', design_path='cet_design_minQ')
print(heat_out.P.val / heat_in.P.val, power.P.val / heat_in.P.val)
print(heat_out.P.val, power.P.val)
print(mp_ls.m.val_SI / m_lp_max)
P += [-power.P.val]
Q += [-heat_out.P.val]

heat_out.set_attr(P=-10e6)
nw.solve(mode='offdesign', design_path='cet_design_minQ')
print(heat_out.P.val / heat_in.P.val, power.P.val / heat_in.P.val)
print(heat_out.P.val, power.P.val)
print(mp_ls.m.val_SI / m_lp_max)
P += [-power.P.val]
Q += [-heat_out.P.val]

heat_out.set_attr(P=-20e6)
nw.solve(mode='offdesign', design_path='cet_design_minQ')
print(heat_out.P.val / heat_in.P.val, power.P.val / heat_in.P.val)
print(heat_out.P.val, power.P.val)
print(mp_ls.m.val_SI / m_lp_max)
P += [-power.P.val]
Q += [-heat_out.P.val]

heat_out.set_attr(P=-30e6)
nw.solve(mode='offdesign', design_path='cet_design_minQ')
print(heat_out.P.val / heat_in.P.val, power.P.val / heat_in.P.val)
print(heat_out.P.val, power.P.val)
print(mp_ls.m.val_SI / m_lp_max)
P += [-power.P.val]
Q += [-heat_out.P.val]

heat_out.set_attr(P=-40e6)
nw.solve(mode='offdesign', design_path='cet_design_minQ')
print(heat_out.P.val / heat_in.P.val, power.P.val / heat_in.P.val)
print(heat_out.P.val, power.P.val)
print(mp_ls.m.val_SI / m_lp_max)
P += [-power.P.val]
Q += [-heat_out.P.val]

heat_out.set_attr(P=-50e6)
nw.solve(mode='offdesign', design_path='cet_design_minQ')
print(heat_out.P.val / heat_in.P.val, power.P.val / heat_in.P.val)
print(heat_out.P.val, power.P.val)
print(mp_ls.m.val_SI / m_lp_max)
P += [-power.P.val]
Q += [-heat_out.P.val]

heat_out.set_attr(P=-60e6)
nw.solve(mode='offdesign', design_path='cet_design_minQ')
print(heat_out.P.val / heat_in.P.val, power.P.val / heat_in.P.val)
print(heat_out.P.val, power.P.val)
print(mp_ls.m.val_SI / m_lp_max)
P += [-power.P.val]
Q += [-heat_out.P.val]

heat_out.set_attr(P=-65e6)
nw.solve(mode='offdesign', design_path='cet_design_minQ')
print(heat_out.P.val / heat_in.P.val, power.P.val / heat_in.P.val)
print(heat_out.P.val, power.P.val)
print(mp_ls.m.val_SI / m_lp_max)
P += [-power.P.val]
Q += [-heat_out.P.val]

#print('maximum heat, full power')
#heat_out.set_attr(P=np.nan)
#mp_ls.set_attr(m=0.1 * m_lp_max)
#nw.solve(mode='offdesign', design_path='cet_design_minQ')
#print(heat_out.P.val / power.P.val)
#print(heat_out.P.val, power.P.val)
#print(mp_ls.m.val_SI / m_lp_max)
#nw.print_results()
#mp_ls.set_attr(m=np.nan)
#P += [-power.P.val]
#Q += [-heat_out.P.val]

# back to design case, but minimum gas turbine power
print('no heat, minimum power')
gt_power.set_attr(P=gt_power_design / 2)
heat_out.set_attr(P=-1e5)
nw.solve(mode='offdesign',
         init_path='cet_design_minQ',
         design_path='cet_design_minQ')
print(heat_out.P.val / heat_in.P.val, power.P.val / heat_in.P.val)
print(heat_out.P.val, power.P.val)
print(mp_ls.m.val_SI / m_lp_max)
P += [-power.P.val]
Q += [-heat_out.P.val]

heat_out.set_attr(P=-1e6)
nw.solve(mode='offdesign', design_path='cet_design_minQ')
print(heat_out.P.val / heat_in.P.val, power.P.val / heat_in.P.val)
print(heat_out.P.val, power.P.val)
print(mp_ls.m.val_SI / m_lp_max)
P += [-power.P.val]
Q += [-heat_out.P.val]

heat_out.set_attr(P=-5e6)
nw.solve(mode='offdesign', design_path='cet_design_minQ')
print(heat_out.P.val / heat_in.P.val, power.P.val / heat_in.P.val)
print(heat_out.P.val, power.P.val)
print(mp_ls.m.val_SI / m_lp_max)
P += [-power.P.val]
Q += [-heat_out.P.val]

heat_out.set_attr(P=-10e6)
nw.solve(mode='offdesign', design_path='cet_design_minQ')
print(heat_out.P.val / heat_in.P.val, power.P.val / heat_in.P.val)
print(heat_out.P.val, power.P.val)
print(mp_ls.m.val_SI / m_lp_max)
P += [-power.P.val]
Q += [-heat_out.P.val]

heat_out.set_attr(P=-20e6)
nw.solve(mode='offdesign', design_path='cet_design_minQ')
print(heat_out.P.val / heat_in.P.val, power.P.val / heat_in.P.val)
print(heat_out.P.val, power.P.val)
print(mp_ls.m.val_SI / m_lp_max)
P += [-power.P.val]
Q += [-heat_out.P.val]

heat_out.set_attr(P=-30e6)
nw.solve(mode='offdesign', design_path='cet_design_minQ')
print(heat_out.P.val / heat_in.P.val, power.P.val / heat_in.P.val)
print(heat_out.P.val, power.P.val)
print(mp_ls.m.val_SI / m_lp_max)
P += [-power.P.val]
Q += [-heat_out.P.val]

heat_out.set_attr(P=-40e6)
nw.solve(mode='offdesign', design_path='cet_design_minQ')
print(heat_out.P.val / heat_in.P.val, power.P.val / heat_in.P.val)
print(heat_out.P.val, power.P.val)
print(mp_ls.m.val_SI / m_lp_max)
P += [-power.P.val]
Q += [-heat_out.P.val]

print('maximum heat, minimum power')
heat_out.set_attr(P=np.nan)
mp_ls.set_attr(m=0.1 * m_lp_max)
nw.solve(mode='offdesign', design_path='cet_design_minQ')
print(heat_out.P.val / heat_in.P.val, power.P.val / heat_in.P.val)
print(heat_out.P.val, power.P.val)
print(mp_ls.m.val_SI / m_lp_max)
nw.print_results()
mp_ls.set_attr(m=np.nan)
P += [-power.P.val]
Q += [-heat_out.P.val]

# from minimum to maximum gas turbine power at maximum heat extraction

print('minimum power to maximum power at maximum heat')

gt_power.set_attr(P=gt_power_design * 0.6)
mp_ls.set_attr(m=0.1 * m_lp_max)
nw.solve(mode='offdesign', design_path='cet_design_minQ')
print(heat_out.P.val / heat_in.P.val, power.P.val / heat_in.P.val)
print(heat_out.P.val, power.P.val)
print(mp_ls.m.val_SI / m_lp_max)
P += [-power.P.val]
Q += [-heat_out.P.val]

gt_power.set_attr(P=gt_power_design * 0.7)
mp_ls.set_attr(m=0.1 * m_lp_max)
nw.solve(mode='offdesign', design_path='cet_design_minQ')
print(heat_out.P.val / heat_in.P.val, power.P.val / heat_in.P.val)
print(heat_out.P.val, power.P.val)
print(mp_ls.m.val_SI / m_lp_max)
P += [-power.P.val]
Q += [-heat_out.P.val]

gt_power.set_attr(P=gt_power_design * 0.8)
mp_ls.set_attr(m=0.1 * m_lp_max)
nw.solve(mode='offdesign', design_path='cet_design_minQ')
print(heat_out.P.val / heat_in.P.val, power.P.val / heat_in.P.val)
print(heat_out.P.val, power.P.val)
print(mp_ls.m.val_SI / m_lp_max)
P += [-power.P.val]
Q += [-heat_out.P.val]

gt_power.set_attr(P=gt_power_design * 0.9)
mp_ls.set_attr(m=0.1 * m_lp_max)
nw.solve(mode='offdesign', design_path='cet_design_minQ')
print(heat_out.P.val / heat_in.P.val, power.P.val / heat_in.P.val)
print(heat_out.P.val, power.P.val)
print(mp_ls.m.val_SI / m_lp_max)
P += [-power.P.val]
Q += [-heat_out.P.val]

gt_power.set_attr(P=gt_power_design)
mp_ls.set_attr(m=0.1 * m_lp_max)
nw.solve(mode='offdesign', design_path='cet_design_minQ')
print(heat_out.P.val / heat_in.P.val, power.P.val / heat_in.P.val)
print(heat_out.P.val, power.P.val)
print(mp_ls.m.val_SI / m_lp_max)
P += [-power.P.val]
Q += [-heat_out.P.val]

plt.plot(Q, P, 'x')
plt.show()
