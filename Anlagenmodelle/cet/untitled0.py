#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Wed Aug 28 17:09:23 2019

@author: witte
"""
import math
import numpy as np
from matplotlib import pyplot as plt
from numpy.linalg import inv
from numpy.linalg import norm

y_0 = 0.7
y_max = 1
y_inf = 0.4
x_inf = 4
x_max = 1

var = np.ones(3)

eq = np.zeros(3)
deriv = np.zeros((3,3))
residual = 1

while residual > 1e-10:

    eq[0] = math.exp(var[2] * x_inf) * (var[0] * x_inf ** 2 + var[1] * x_inf + y_0) - y_inf
    eq[1] = math.exp(var[2] * x_max) * (var[0] * x_max ** 2 + var[1] * x_max + y_0) - y_max
    eq[2] = var[2] * (var[0] * x_max ** 2 + var[1] * x_max + y_0) + 2 * var[0] * x_max + var[1]

    deriv[0, 0] = math.exp(var[2] * x_inf) * x_inf ** 2
    deriv[0, 1] = math.exp(var[2] * x_inf) * x_inf
    deriv[0, 2] = x_inf * math.exp(var[2] * x_inf) * (var[0] * x_inf ** 2 + var[1] * x_inf + y_0)
    deriv[1, 0] = math.exp(var[2] * x_max) * x_max ** 2
    deriv[1, 1] = math.exp(var[2] * x_max) * x_max
    deriv[1, 2] = x_max * math.exp(var[2] * x_max) * (var[0] * x_max ** 2 + var[1] * x_max + y_0)
    deriv[2, 0] = x_max * 2 * (var[2] + 1)
    deriv[2, 1] = var[2] * x_max + 1
    deriv[2, 2] = var[0] * x_max ** 2 + var[1] * x_max + y_0

    incr = inv(deriv).dot(-eq)
    var += incr
    residual = norm(eq)
    if var[0] > 0:
        var[0] *= -1

x = np.linspace(0, x_inf, x_inf * 10 + 1)

eta = (var[0] * x ** 2 + var[1] * x + y_0) * np.exp(var[2] * x)
plt.plot(x, eta)
plt.show()

msg = [round(a,4) for a in x]
print(msg)

msg = [round(a,4) for a in eta]
print(msg)