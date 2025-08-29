import numpy as np


def calc_sigmas(category, x_wind):
    '''
    category：Pasquill Stability Category
    1--A--very unstable 
    2--B--moderately unstable
    3--C--slightly unstable
    4--D--neutral
    5--E--moderately stable
    6--F--very stable

    x_wind：对应downwind格点
    2d-array，单位：m
    '''
    x = np.abs(x_wind)
    a = np.zeros(np.shape(x))
    b = np.zeros(np.shape(x))
    c = np.zeros(np.shape(x))
    d = np.zeros(np.shape(x))

    if category == 1:

        sig_x = 0.22 * x * (1 + 0.0001 * x)**(-0.5)
        sig_y = sig_x
        sig_z = 0.2 * x

    elif category == 2:

        sig_x = 0.16 * x * (1 + 0.0001 * x)**(-0.5)
        sig_y = sig_x
        sig_z = 0.12 * x

    elif category == 3:

        sig_x = 0.11 * x * (1 + 0.0001 * x)**(-0.5)
        sig_y = sig_x
        sig_z = 0.08 * x * (1 + 0.0002 * x)**(-0.5)

    elif category == 4:

        sig_x = 0.08 * x * (1 + 0.0001 * x)**(-0.5)
        sig_y = sig_x
        sig_z = 0.06 * x * (1 + 0.0015 * x)**(-0.5)

    elif category == 5:

        sig_x = 0.06 * x * (1 + 0.0001 * x)**(-0.5)
        sig_y = sig_x
        sig_z = 0.03 * x * (1 + 0.0003 * x)**(-0.5)

    elif category == 6:

        sig_x = 0.04 * x * (1 + 0.0001 * x)**(-0.5)
        sig_y = sig_x
        sig_z = 0.016 * x * (1 + 0.0003 * x)**(-0.5)

    return sig_x, sig_y, sig_z
