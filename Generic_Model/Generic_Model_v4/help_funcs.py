# -*- coding: utf-8 -*-
"""
Created on Fri Aug  6 13:26:11 2021

@author: Malte Fritz & Jonas Freißmann
"""

import os


def liste(parameter, periods):
    """Get timeseries list of parameter for solph components."""
    return [parameter for p in range(0, periods)]


def topology_check(param):
    """
    Check chosen topology for validity.

    Validity is checked for:
        - LT-NW
        - wird noch mehr kommen
    """
    lthp_activity = param['LT-HP']['active']
    sol_activity = param['Sol']['active']
    tes_activity = param['TES']['active']
    if (lthp_activity and not sol_activity and not tes_activity):
        msg = (
            "You can't have the low temp heat pump active without "
            + "using either the TES or solar heat."
            )
        raise TopologyError(msg)
    elif (not lthp_activity and (sol_activity or tes_activity)):
        msg = (
            "You can't use TES or solar heat without using the low"
            + " temp heat pump."
            )
        raise TopologyError(msg)


def result_labelling(labeldict, dataframe, export_missing_labels=False):
    """Rename flows to user readable names."""
    missing_labels = str()
    for col in dataframe.columns:
        if col in labeldict:
            dataframe.rename(columns={col: labeldict[col]}, inplace=True)
        else:
            print(col, ' not in labeldict')
            missing_labels += 'labeldict[' + str(col) + '] = \n'
    if export_missing_labels:
        if os.path.exists('missing_labels.txt'):
            with open('missing_labels.txt', 'a', encoding='utf-8') as file:
                file.write(missing_labels)
        else:
            with open('missing_labels.txt', 'w', encoding='utf-8') as file:
                file.write(missing_labels)


def generate_labeldict(param):
    """Generate dictionary of labels to rename flows."""
    labeldict = dict()

    labeldict[(('Gasquelle', 'Gasnetzwerk'), 'flow')] = 'H_source'
    labeldict[(('Elektrizitätsnetzwerk', 'Spotmarkt'), 'flow')] = 'P_spot_market'
    labeldict[(('Stromquelle', 'Elektrizitätsnetzwerk'), 'flow')] = 'P_source'
    labeldict[(('Wärmenetzwerk', 'Wärmebedarf'), 'flow')] = 'Q_demand'
    labeldict[(('Wärmenetzwerk', 'HT_to_node'), 'flow')] = 'Q_HT_TES'
    labeldict[(('LT-Wärmenetzwerk', 'LT_to_node'), 'flow')] = 'Q_LT_TES'

    if param['Sol']['active']:
        labeldict[(('Solarthermie', 'Sol Knoten'), 'flow')] = 'Q_Sol_zu'
        labeldict[(('Sol Knoten', 'Sol_to_LT'), 'flow')] = 'Q_Sol_node_LT'
        labeldict[(('Sol Knoten', 'Sol_to_HT'), 'flow')] = 'Q_Sol_node_HT'

    if param['MR']['active']:
        labeldict[(('Mustrun', 'Wärmenetzwerk'), 'flow')] = 'Q_MR'

    if param['HT-EC']['active']:
        labeldict[(('Wärmenetzwerk', 'HT-EC'), 'flow')] = 'Q_HT_EC'

    if param['Sol EC']['active']:
        labeldict[(('Sol Knoten', 'Sol EC'), 'flow')] = 'Q_Sol_EC'

    if param['EHK']['active']:
        for i in range(1, param['EHK']['amount']+1):
            label_id = 'Elektroheizkessel_' + str(i)
            labeldict[((label_id, 'Wärmenetzwerk'), 'flow')] = (
                'Q_EHK_' + str(i)
                )
            labeldict[(('Elektrizitätsnetzwerk', label_id), 'flow')] = (
                'P_zu_EHK_' + str(i)
                )

    if param['SLK']['active']:
        for i in range(1, param['SLK']['amount']+1):
            label_id = 'Spitzenlastkessel_' + str(i)
            labeldict[((label_id, 'Wärmenetzwerk'), 'flow')] = (
                'Q_SLK_' + str(i)
                )
            labeldict[(('Gasnetzwerk', label_id), 'flow')] = 'H_SLK_' + str(i)

    if param['BHKW']['active']:
        for i in range(1, param['BHKW']['amount']+1):
            label_id = 'BHKW_' + str(i)
            labeldict[((label_id, 'Wärmenetzwerk'), 'flow')] = 'Q_' + label_id
            labeldict[((label_id, 'Elektrizitätsnetzwerk'), 'flow')] = (
                'P_' + label_id
                )
            labeldict[(('Gasnetzwerk', label_id), 'flow')] = 'H_' + label_id

    if param['GuD']['active']:
        for i in range(1, param['GuD']['amount']+1):
            label_id = 'GuD_' + str(i)
            labeldict[((label_id, 'Wärmenetzwerk'), 'flow')] = 'Q_' + label_id
            labeldict[((label_id, 'Elektrizitätsnetzwerk'), 'flow')] = (
                'P_' + label_id
                )
            labeldict[(('Gasnetzwerk', label_id), 'flow')] = 'H_' + label_id

    if param['HP']['active']:
        for i in range(1, param['HP']['amount']+1):
            label_id = 'HP_' + str(i)
            labeldict[((label_id, 'Wärmenetzwerk'), 'flow')] = (
                'Q_ab_' + label_id
                )
            labeldict[(('Elektrizitätsnetzwerk', label_id), 'flow')] = (
                'P_zu_' + label_id
                )
            labeldict[(('Elektrizitätsnetzwerk', label_id), 'status')] = (
                'Status_' + label_id
                )

    if param['LT-HP']['active']:
        for i in range(1, param['LT-HP']['amount']+1):
            label_id = 'LT-HP_' + str(i)
            labeldict[((label_id, 'Wärmenetzwerk'), 'flow')] = (
                'Q_ab_' + label_id
                )
            labeldict[(('Elektrizitätsnetzwerk', label_id), 'flow')] = (
                'P_zu_' + label_id
                )
            labeldict[(('LT-Wärmenetzwerk', label_id), 'flow')] = (
                'Q_zu_' + label_id
                )

    if param['TES']['active']:
        for i in range(1, param['TES']['amount']+1):
            label_id = 'TES_' + str(i)

            labeldict[((label_id, 'LT-Wärmenetzwerk'), 'flow')] = (
                'Q_ab_' + label_id
                )
            labeldict[((label_id, 'LT-Wärmenetzwerk'), 'status')] = (
                'Status_ab_' + label_id
                )
            labeldict[(('TES Knoten', label_id), 'flow')] = (
                'Q_zu_' + label_id
                )
            labeldict[(('TES Knoten', label_id), 'status')] = (
                'Status_zu_' + label_id
                )
            labeldict[((label_id, 'None'), 'storage_content')] = (
                'Speicherstand_' + label_id
                )

    if param['ST-TES']['active']:
        for i in range(1, param['ST-TES']['amount']+1):
            label_id = 'ST-TES_' + str(i)
            labeldict[((label_id, 'Wärmenetzwerk'), 'flow')] = (
                'Q_ab_' + label_id
                )
            labeldict[((label_id, 'Wärmenetzwerk'), 'status')] = (
                'Status_ab_' + label_id
                )
            labeldict[(('Wärmenetzwerk', label_id), 'flow')] = (
                'Q_zu_' + label_id
                )
            labeldict[(('Wärmenetzwerk', label_id), 'status')] = (
                'Status_zu_' + label_id
                )
            labeldict[((label_id, 'None'), 'storage_content')] = (
                'Speicherstand_' + label_id
                )

    labeldict[(('HT_to_node', 'TES Knoten'), 'flow')] = 'Q_HT_node'
    labeldict[(('LT_to_node', 'TES Knoten'), 'flow')] = 'Q_LT_node'
    labeldict[(('Sol_to_HT', 'Wärmenetzwerk'), 'flow')] = 'Q_Sol_HT'
    labeldict[(('Sol_to_LT', 'LT-Wärmenetzwerk'), 'flow')] = 'Q_Sol_LT'
    labeldict[(('Elektrizitätsnetzwerk', 'Spotmarkt'), 'flow')] = (
        'P_spot_market'
        )

    return labeldict


class ComponentTypeError(Exception):
    """Exception raised for errors with component type."""

    def __init__(self, user_type, component):
        self.user_type = user_type
        self.component = component
        super().__init__()

    def __str__(self):
        """Generate error message."""
        return (
            f"The chosen component type '{self.user_type}' of {self.component}"
            + " is neither 'constant' nor a 'time series'."
            )


class SolarUsageError(Exception):
    """Exception raised for errors with usage solar thermal source."""

    def __init__(self, user_usage):
        self.user_usage = user_usage
        super().__init__()

    def __str__(self):
        """Generate error message."""
        return (
            f"The chosen usage '{self.user_usage}' of the solar thermal source"
            + " is neither 'HT' nor a 'LT'."
            )


class TopologyError(Exception):
    """Exception raised for errors with usage solar thermal source."""


if __name__ == '__main__':
    raise TopologyError('user_usage')
