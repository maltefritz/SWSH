# -*- coding: utf-8 -*-
"""
Created on Fri Aug  6 13:26:11 2021

@author: Malte Fritz
"""

from sys import exit


def liste(parameter, periods):
    """Get timeseries list of parameter for solph components."""
    return [parameter for p in range(0, periods)]


def topology_check(param):
    """Check chosen topology for validity:
        - LT-NW
        - wird noch mehr kommen
        """
    if (param['LT-HP']['active']
        and not param['Sol']['active']
        and not param['TES']['active']):
        print("WARNING: You can't have the low temp heat pump active without ",
              "using either the TES or solar heat.")
        exit()
    elif (not param['LT-HP']['active']
          and (param['Sol']['active']
          or param['TES']['active'])):
        print("WARNING: You can't use TES or solar heat without using the low",
              " temp heat pump.")
        exit()


def result_labelling(dataframe, labeldict):
    """Change columns names of result dataframes."""
    for col in dataframe.columns:
        if col in labeldict:
            dataframe.rename(columns={col: labeldict[col]}, inplace=True)
        else:
            print(col, ' not in labeldict')


class ComponentTypeError(Exception):
    """Exception raised for errors with component type."""

    def __init__(self, user_type, component):
        self.user_type = user_type
        self.component = component
        super().__init__()

    def __str__(self):
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
        return (
            f"The chosen usage '{self.user_usage}' of the solar thermal source"
            + " is neither 'HT' nor a 'LT'."
            )


if __name__ == '__main__':
    raise SolarUsageError('user_usage')
