# -*- coding: utf-8 -*-
"""
Created on Fri Apr  3 09:15:38 2020

@author: Jonas Freißmann
"""

import oemof.solph as solph
from oemof.solph import views
import pandas as pd
import numpy as np


def main(params):
    """Execute main program."""
    def liste(parameter):
        """Get timeseries list of parameter for solph components."""
        return [parameter for p in range(0, periods)]

    def getGuD(params):
        """Create GuD component."""
        kwk = solph.components.GenericCHP(
            label='KWK',
            fuel_input={gnw: solph.Flow(
                H_L_FG_share_max=liste(params['H_L_FG_share_max']),
                nominal_value=params['Q_in'])},
            electrical_output={enw: solph.Flow(
                variable_costs=param.loc[('GuD', 'op_cost_var'), 'value'],
                P_max_woDH=liste(params['P_max_woDH']),
                P_min_woDH=liste(params['P_min_woDH']),
                Eta_el_max_woDH=liste(params['eta_el_max']),
                Eta_el_min_woDH=liste(params['eta_el_min']))},
            heat_output={wnw: solph.Flow(
                Q_CW_min=liste(params['Q_CW_min']),
                Q_CW_max=liste(0))},
            Beta=liste(params['beta']),
            back_pressure=False)

        return kwk

    param = pd.read_csv('All_parameters.csv', sep=";",
                        index_col=['plant', 'parameter'])

    periods = 100
    date_time_index = pd.date_range('1/1/2016 00:00:00', periods=periods,
                                    freq='h')

    # %% Energiesystem erstellen

    es_ref = solph.EnergySystem(timeindex=date_time_index)

    gnw = solph.Bus(label='Gasnetzwerk')
    enw = solph.Bus(label='Elektrizitätsnetzwerk')
    wnw = solph.Bus(label='Wärmenetzwerk')

    es_ref.add(gnw, enw, wnw)

    gas_source = solph.Source(label='Gasquelle',
                              outputs={gnw: solph.Flow()})

    heat_dummy_source = solph.Source(label='Wärmedummy',
                                     outputs={wnw: solph.Flow(
                                         variable_costs=99999)})

    es_ref.add(gas_source, heat_dummy_source)

    c_el = [-100] * 50 + [100] * 50
    demand = np.linspace(0, 100, 50).tolist() * 2

    df = pd.DataFrame({'c_el': c_el, 'demand': demand})

    elec_sink = solph.Sink(
        label='Spotmarkt',
        inputs={enw: solph.Flow(
            variable_costs=df['c_el'])})

    heat_sink = solph.Sink(
        label='Wärmebedarf',
        inputs={wnw: solph.Flow(
            nominal_value=max(df['demand']),
            actual_value=df['demand']/max(df['demand']),
            fixed=True)})

    es_ref.add(elec_sink, heat_sink)

    ##### KWK #####

    es_ref.add(getGuD(params))

    ##### KWK #####

    model = solph.Model(es_ref)
    model.solve(solver='gurobi', solve_kwargs={'tee': True},
                cmdline_options={"mipgap": "0.01"})

    results = solph.processing.results(model)

    # Main- und Metaergebnisse
    es_ref.results['main'] = solph.processing.results(model)
    es_ref.results['meta'] = solph.processing.meta_results(model)

    data_wnw = views.node(results, 'Wärmenetzwerk')['sequences']
    data_kwk = views.node(results, 'KWK')['sequences']
    data_kwk.reset_index(drop=True, inplace=True)

    return (data_wnw, data_kwk)
