"""Energiesystem mit Speicher und Solarthermie.

@author: Malte Fritz and Jonas Freißmann

Komponenten:
    - Elektroheizkessel
    - Spitzenlastkessel
    - BHKW
    - GuD
    - Wärmepumpe
    - Solarthermie
    - TES
    - LT-Wärmepumpe

Wärmebedarf Flensburgs aus dem Jahr 2016

"""
import pandas as pd

import oemof.solph as solph
from help_funcs import topology_check
from components import (
    gas_source, electricity_source, solar_thermal_strand, must_run_source
    )
from components import (
    electricity_sink, heat_sink, ht_emergency_cooling_sink
    )
from components import electric_boiler, peak_load_boiler
from components import (
    internal_combustion_engine, combined_cycle_extraction_turbine,
    back_pressure_turbine
    )
from components import ht_heat_pump, lt_heat_pump
from components import (
    seasonal_thermal_energy_storage_strand,
    short_term_thermal_energy_storage
    )
from postprocessing import postprocessing


def main(param, data, mipgap='0.1'):
    """
    Execute main script.

    Parameters
    ----------
    param : dict
        JSON parameter file of user defined constants.

    data : pandas.DataFrame
        csv file of user defined time dependent parameters.

    mipgap : str
        termination criterion for gap between current and optimal solution.
    """
    # %% Initialize energy system

    periods = len(data)
    date_time_index = pd.date_range(data.index[0], periods=periods, freq='h')

    energysystem = solph.EnergySystem(timeindex=date_time_index)

    topology_check(param)

    # %% Energiesystem

        # %% Busses

    gnw = solph.Bus(label='Gasnetzwerk')
    enw = solph.Bus(label='Elektrizitätsnetzwerk')
    wnw = solph.Bus(label='Wärmenetzwerk')
    lt_wnw = solph.Bus(label='LT-Wärmenetzwerk')
    wnw_node = solph.Bus(label='TES Knoten')
    sol_node = solph.Bus(label='Sol Knoten')

    energysystem.add(gnw, enw, wnw, lt_wnw, wnw_node, sol_node)

    busses = {
        'gnw': gnw, 'enw': enw, 'wnw': wnw, 'lt_wnw': lt_wnw,
        'wnw_node': wnw_node, 'sol_node': sol_node
        }

        # %% Soruces

    energysystem.add(
        gas_source(param, busses),
        electricity_source(param, data, busses),
        must_run_source(param, data, busses),
        *solar_thermal_strand(param, data, busses)
        )

        # %% Sinks

    energysystem.add(
        electricity_sink(param, busses),
        heat_sink(param, data, busses),
        ht_emergency_cooling_sink(param, busses)
        )

        # %% Transformer

    energysystem.add(
        electric_boiler(param, data, busses),
        peak_load_boiler(param, data, busses),
        internal_combustion_engine(param, data, busses, periods),
        combined_cycle_extraction_turbine(param, data, busses, periods),
        back_pressure_turbine(param, data, busses, periods),
        ht_heat_pump(param, data, busses),
        lt_heat_pump(param, data, busses)
        )

        # %% Speicher

    energysystem.add(
        *seasonal_thermal_energy_storage_strand(param, busses),
        short_term_thermal_energy_storage(param, busses)
        )

    # %% Processing

        # %% Solve

    # Was bedeutet tee?
    model = solph.Model(energysystem)
    solph.constraints.limit_active_flow_count_by_keyword(
        model, 'storageflowlimit', lower_limit=0, upper_limit=1)
    # model.write('my_model.lp', io_options={'symbolic_solver_labels': True})
    model.solve(solver='gurobi', solve_kwargs={'tee': True},
                cmdline_options={"mipgap": mipgap})

        # %% Ergebnisse Energiesystem

    # Ergebnisse in results
    results = solph.processing.results(model)

    # Main- und Metaergebnisse
    energysystem.results['main'] = solph.processing.results(model)
    energysystem.results['meta'] = solph.processing.meta_results(model)

    data_dhs, data_invest, data_emission, data_cost_units = postprocessing(
        results, param, data
        )

    return (
        data_dhs, data_invest, data_emission, data_cost_units,
        energysystem.results['meta']
        )


if __name__ == '__main__':
    main()
