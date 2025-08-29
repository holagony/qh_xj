# -*- coding: utf-8 -*-
"""
Created on Mon Apr 29 13:07:02 2024

@author: EDY
"""

import sys
import numpy as np
from scipy.special import erfcinv as erfcinv
from Module09.wrapped.sigma_puff_calculation import calc_sigmas


def gauss_puff_func(Q, u, dir1, x, y, z, xs, ys, H, STABILITY, t, delt_t, i):
    u1 = u
    x1 = x - xs  # shift the coordinates so that stack is centre point
    y1 = y - ys

    # components of u in x and y directions
    wx = u1 * np.sin((dir1 - 180.) * np.pi / 180.)
    wy = u1 * np.cos((dir1 - 180.) * np.pi / 180.)

    # Need angle between point x, y and the wind direction, so use scalar product:
    dot_product = wx * x1 + wy * y1

    # product of magnitude of vectors:
    magnitudes = u1 * np.sqrt(x1**2. + y1**2.)

    # angle between wind and point (x,y)
    subtended = np.arccos(dot_product / (magnitudes + 1e-15))

    # distance to point x,y from stack
    hypotenuse = np.sqrt(x1**2 + y1**2)

    # distance along the wind direction to perpendilcular line that intesects
    # x,y
    downwind = np.cos(subtended) * hypotenuse

    # Now calculate distance cross wind.
    crosswind = np.sin(subtended) * hypotenuse

    ind = np.where(downwind > 0)
    # C = np.zeros((len(x), len(y)))
    C = np.zeros(np.shape(x))

    # sig_y = sqrt(2*Dy*downwind/u1)
    # sig_z = sqrt(2*Dz*downwind/u1)

    # calculate sigmas based on stability and distance downwind
    (sig_x, sig_y, sig_z) = calc_sigmas(STABILITY + 1, downwind)

    # 计算公式
    part_A = Q / (((2 * np.pi)**(3 / 2)) * sig_x[ind] * sig_y[ind] * sig_z[ind])
    part_B = (np.exp(-(z[ind] - H)**2 / (2 * sig_z[ind]**2)) + np.exp(-(z[ind] + H)**2 / (2 * sig_z[ind]**2)))
    part_C = np.exp(-crosswind[ind]**2 / (sig_y[ind]**2))
    part_D = np.exp(-(downwind[ind] - u1 * (t - i * delt_t))**2 / (2 * sig_x[ind]**2))
    C[ind] = part_A * part_B * part_C * part_D

    return C
