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
        # vertical distribution (simga_z)
        ind = np.where((x < 100) & (x > 0))
        a[ind] = 122.800
        b[ind] = 0.94470

        ind = np.where((x >= 100) & (x < 150))
        a[ind] = 158.080
        b[ind] = 1.05420

        ind = np.where((x >= 150) & (x < 200))
        a[ind] = 170.220
        b[ind] = 1.09320

        ind = np.where((x >= 200) & (x < 250))
        a[ind] = 179.520
        b[ind] = 1.12620

        ind = np.where((x >= 250) & (x < 300))
        a[ind] = 217.410
        b[ind] = 1.26440

        ind = np.where((x >= 300) & (x < 400))
        a[ind] = 258.89
        b[ind] = 1.40940

        ind = np.where((x >= 400) & (x < 500))
        a[ind] = 346.75
        b[ind] = 1.7283

        ind = np.where((x >= 500) & (x < 3110))
        a[ind] = 453.85
        b[ind] = 2.1166

        ind = np.where((x >= 3110))
        a[ind] = 453.85
        b[ind] = 2.1166

        # cross-wind distribution
        c[:] = 24.1670
        d[:] = 2.5334

    elif category == 2:
        # vertical distribution (simga_z)
        ind = np.where((x < 200) & (x > 0))
        a[ind] = 90.673
        b[ind] = 0.93198

        ind = np.where((x >= 200) & (x < 400))
        a[ind] = 98.483
        b[ind] = 0.98332

        ind = np.where(x >= 400)
        a[ind] = 109.3
        b[ind] = 1.09710

        # cross-wind distribution
        c[:] = 18.3330
        d[:] = 1.8096

    elif category == 3:
        # vertical distribution (simga_z)
        a[:] = 61.141
        b[:] = 0.91465

        # cross-wind distribution
        c[:] = 12.5
        d[:] = 1.0857

    elif category == 4:
        # vertical distribution (simga_z)
        ind = np.where((x < 300) & (x > 0))
        a[ind] = 34.459
        b[ind] = 0.86974

        ind = np.where((x >= 300) & (x < 1000))
        a[ind] = 32.093
        b[ind] = 0.81066

        ind = np.where((x >= 1000) & (x < 3000))
        a[ind] = 32.093
        b[ind] = 0.64403

        ind = np.where((x >= 3000) & (x < 10000))
        a[ind] = 33.504
        b[ind] = 0.60486

        ind = np.where((x >= 10000) & (x < 30000))
        a[ind] = 36.650
        b[ind] = 0.56589

        ind = np.where(x >= 30000)
        a[ind] = 44.053
        b[ind] = 0.51179

        # cross-wind distribution
        c[:] = 8.3330
        d[:] = 0.72382

    elif category == 5:
        # vertical distribution (simga_z)
        ind = np.where((x < 100) & (x > 0))
        a[ind] = 24.26
        b[ind] = 0.83660

        ind = np.where((x >= 100) & (x < 300))
        a[ind] = 23.331
        b[ind] = 0.81956

        ind = np.where((x >= 300) & (x < 1000))
        a[ind] = 21.628
        b[ind] = 0.75660

        ind = np.where((x >= 1000) & (x < 2000))
        a[ind] = 21.628
        b[ind] = 0.63077

        ind = np.where((x >= 2000) & (x < 4000))
        a[ind] = 22.534
        b[ind] = 0.57154

        ind = np.where((x >= 4000) & (x < 10000))
        a[ind] = 24.703
        b[ind] = 0.50527

        ind = np.where((x >= 10000) & (x < 20000))
        a[ind] = 26.970
        b[ind] = 0.46713

        ind = np.where((x >= 20000) & (x < 40000))
        a[ind] = 35.420
        b[ind] = 0.37615

        ind = np.where(x >= 40000)
        a[ind] = 47.618
        b[ind] = 0.29592

        # cross-wind distribution
        c[:] = 6.25
        d[:] = 0.54287

    elif category == 6:
        # vertical distribution (simga_z)
        ind = np.where((x < 200) & (x > 0))
        a[ind] = 15.209
        b[ind] = 0.81558

        ind = np.where((x >= 200) & (x < 700))
        a[ind] = 14.457
        b[ind] = 0.78407

        ind = np.where((x >= 700) & (x < 1000))
        a[ind] = 13.953
        b[ind] = 0.68465

        ind = np.where((x >= 1000) & (x < 2000))
        a[ind] = 13.953
        b[ind] = 0.63227

        ind = np.where((x >= 2000) & (x < 3000))
        a[ind] = 14.823
        b[ind] = 0.54503

        ind = np.where((x >= 3000) & (x < 7000))
        a[ind] = 16.187
        b[ind] = 0.46490

        ind = np.where((x >= 7000) & (x < 15000))
        a[ind] = 17.836
        b[ind] = 0.41507

        ind = np.where((x >= 15000) & (x < 30000))
        a[ind] = 22.651
        b[ind] = 0.32681

        ind = np.where((x >= 30000) & (x < 60000))
        a[ind] = 27.074
        b[ind] = 0.27436

        ind = np.where(x >= 60000)
        a[ind] = 34.219
        b[ind] = 0.21716

        # cross-wind distribution
        c[:] = 4.1667
        d[:] = 0.36191

    # 根据公式计算sigma_z和sigma_y，单位：m
    sig_z = a * (x / 1000)**b  # x单位转换为km
    sig_z[np.where(sig_z[:] > 5000)] = 5000
    theta = 0.017453293 * (c - d * np.log(np.abs(x + 1e-15) / 1000))
    sig_y = 465.11628 * x / 1000 * np.tan(theta)

    return sig_y, sig_z

if __name__ == '__main__':
    
    category=4
    x_wind=[500]