# -*- coding: utf-8 -*-
"""
Created on Mon Jun 17 13:09:41 2024

@author: EDY
"""

import os
import numpy as np
import transbigdata as tbd
import matplotlib
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER
from matplotlib.colors import ListedColormap
from math import cos, sin, atan2, sqrt, radians, degrees
from tqdm import tqdm
from Utils.config import cfg
from Utils.ordered_easydict import OrderedEasyDict as edict
from Module09.wrapped.gaussian_puff_function import gauss_puff_func
from multiprocessing import Pool
import multiprocessing

matplotlib.use('Agg')
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False


def center_geolocation(geolocations):
    '''
    多个经纬度点找中心点
    '''
    geolocations = geolocations.tolist()
    x = 0
    y = 0
    z = 0
    lenth = len(geolocations)
    for lon, lat in geolocations:
        lon = radians(float(lon))
        lat = radians(float(lat))
        x += cos(lat) * cos(lon)
        y += cos(lat) * sin(lon)
        z += sin(lat)

    x = float(x / lenth)
    y = float(y / lenth)
    z = float(z / lenth)

    center_lon = round(degrees(atan2(y, x)), 6)
    center_lat = round(degrees(atan2(z, sqrt(x * x + y * y))), 6)
    center_lonlat = [center_lon, center_lat]

    return center_lonlat


def generate_grid(lon, lat, dist, coors):
    '''
    根据中心经纬度点生成经纬度网格,和XY的index网格
    lon = 94.961285
    lat = 36.366595
    dist = 100 # 网格分辨率 m
    coors = 2500 # 两侧扩展的网格数量
    '''
    # n_coord = coors * 2 + 1
    # axis = np.linspace(-coors, coors, n_coord)
    # X, Y = np.meshgrid(axis, axis)
    axis = np.arange(-coors, coors + dist, dist)
    X, Y = np.meshgrid(axis, axis)
    R = 6378137
    dLat = (X / R) * dist
    dLon = (Y / (R * np.cos(np.pi * lat / 180))) * dist
    # lat_grid = np.flipud((lat + dLat * 180 / np.pi).T)
    lat_grid = (lat + dLat * 180 / np.pi).T  # 不用翻转，因为Y也是由小到大
    lon_grid = (lon + dLon * 180 / np.pi).T
    # output = np.concatenate((lon_grid[None],lat_grid[None]),axis=0)

    return X, Y, lon_grid, lat_grid


def find_nearest_point_index(target_point, grid_array):
    '''
    输出中心经纬度点在网格中最近的点的index
    target_point = np.array([94.961285, 36.366595])
    grid_array: shape(2,lon,lat)
    '''
    target_point = np.array(target_point)
    expanded_target = np.expand_dims(target_point, axis=(1, 2))
    distances = np.linalg.norm(grid_array - expanded_target, axis=0)
    nearest_idx = np.unravel_index(np.argmin(distances), distances.shape)

    return nearest_idx


def process_stability(args):
    """
    处理单个稳定度的计算，用于多进程
    """
    stab1, X, Y, z, num_stacks, Q, wind_speed, wind_d, stack_x, stack_y, H, t, delt_t_x = args
    # 确保使用float64类型
    result = np.zeros_like(X, dtype=np.float64)
    
    for j in range(num_stacks):
        n_steps = int(np.ceil(t / delt_t_x[j]))
        for i in range(n_steps):
            C = gauss_puff_func(
                Q=Q[j],
                u=wind_speed,
                dir1=wind_d,
                x=X,
                y=Y,
                z=z,
                xs=stack_x[j],
                ys=stack_y[j],
                H=H[j],
                STABILITY=stab1,
                t=t,
                delt_t=delt_t_x[j],
                i=i
            )
            result += C.astype(np.float64)  # 确保C的类型也是float64
    
    return result


def gaussianPuffModel(lon, lat, q, h, wind_s, wind_d, z1, save_path, t, delt_t, acid, humidify, rh):
    '''
    lon: 污染源经度
    lat: 污染源纬度
    q: 泄漏源瞬时泄漏的泄漏量，kg
    h: 烟囱高度
    
    acid:气溶胶类型：SODIUM_CHLORIDE，SULPHURIC_ACID，ORGANIC_ACID，AMMONIUM_NITRATE
    humidify: 干/湿气溶胶 如果传值，说明是湿气溶胶，对结果进行修正
    rh: 相对湿度
    wind_s:风速 m/s
    wind_d:风向 0-360°
    z:模拟高度
    area: 模拟区域，长款为area的正边形
    t: 模拟时长 s
    delt_t：排放间隔 s
    '''
    tbd.set_mapboxtoken(cfg.INFO.MAPBOX_TOKEN)
    tbd.set_imgsavepath(cfg.INFO.TILE_PATH)

    # 默认预设参数
    area = 6000  # 中心四周500个格点
    res = 5  # 格点分辨率

    params_dict = dict()
    params_dict['SODIUM_CHLORIDE'] = 1
    params_dict['SULPHURIC_ACID'] = 2
    params_dict['ORGANIC_ACID'] = 3
    params_dict['AMMONIUM_NITRATE'] = 4
    params_dict['nu'] = [2, 2.5, 1, 2]  # 比面积
    params_dict['rho_s'] = [2160, 1840, 1500, 1725]  # 气溶胶密度
    params_dict['Ms'] = [58.44e-3, 98e-3, 200e-3, 80e-3]  # 摩尔质量

    # 气溶胶参数
    stability_str1 = ['A强不稳定', 'B不稳定', 'C弱不稳定', 'D中性', 'E较稳定', 'F稳定']  # 大气状态
    
    # 烟囱高度和排放参数
    Q = np.array(q.split(','), dtype=float).tolist()
    H = np.array(h.split(','), dtype=float).tolist()
    delt_t_x = np.array(delt_t.split(','), dtype=float).tolist()

    # 根据烟囱位置得到中心经纬度
    lon_x = np.array(lon.split(','), dtype=float).tolist()
    lat_y = np.array(lat.split(','), dtype=float).tolist()
    lonlat = np.array(list(zip(lon_x, lat_y)))

    if lonlat.shape[0] != 1:  # 如果多个经纬度点，计算中心经纬度点，用于图像定位
        center_lonlat = center_geolocation(lonlat)
    else:
        center_lonlat = [lon_x[0], lat_y[0]]

    # 根据中心经纬度，创建经纬度网格和index网格
    X, Y, lon_grid, lat_grid = generate_grid(center_lonlat[0], center_lonlat[1], res, area)

    # 找到烟囱经纬度最近的网格点的index
    num_stacks = lonlat.shape[0]
    stack_x = np.zeros(num_stacks, dtype=np.float64)
    stack_y = np.zeros(num_stacks, dtype=np.float64)
    grid_array = np.concatenate((lon_grid[None], lat_grid[None]), axis=0)

    for i in range(num_stacks):
        nearest_index = find_nearest_point_index(lonlat[i], grid_array)
        stack_x[i] = X[nearest_index]
        stack_y[i] = Y[nearest_index]

    # Main loop
    wind_speed = wind_s  # m/s
    wind_dir = wind_d
    C1 = np.zeros((X.shape[0], X.shape[1], len(stability_str1)), dtype=np.float64)
    print(C1.shape)

    z = np.full_like(X, z1, dtype=np.float64)
    
    # 准备多进程参数
    stability_args = []
    for stab1 in range(len(stability_str1)):
        args = (stab1, X, Y, z, num_stacks, Q, wind_speed, wind_dir, 
               stack_x, stack_y, H, t, delt_t_x)
        stability_args.append(args)

    # 使用多进程计算不同稳定度
    n_cores = 6  # 固定使用6个核心，与3D版本保持一致
    with Pool(processes=n_cores) as pool:
        results = pool.map(process_stability, stability_args)
    
    # 将结果组装到C1中
    C1 = np.stack(results, axis=-1)

    if humidify is not None:
        aerosol_type = params_dict[acid] - 1
        nu = params_dict['nu'][aerosol_type]
        rho_s = params_dict['rho_s'][aerosol_type]
        Ms = params_dict['Ms'][aerosol_type]
        Mw = 18e-3
        dry_size = 60e-9
        
        # 向量化计算
        mass = np.pi / 6 * rho_s * dry_size**3
        moles = mass / Ms
        nw = rh * nu * moles / (1 - rh)
        mass2 = nw * Mw + moles * Ms
        C1 *= mass2 / mass

    C1 = np.where(C1 < 1e-5, np.nan, C1)

    # Plot
    # 定义cmaps
    # rgb_colors = [[20, 157, 241], [55, 230, 216], [129, 255, 180], [200, 230, 136], [255, 157, 83], [255, 56, 28]]
    # colors = [(0, 0, 0, 0)] + [(r / 255, g / 255, b / 255, 1) for r, g, b in rgb_colors]
    # cmap = ListedColormap(colors)

    result_dict = dict()
    for i in range(6):
        contour_data = C1[:, :, i]
        fig = plt.figure(figsize=(10, 10))
        ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())
        contourf_obj = ax.contourf(lon_grid, lat_grid, contour_data, transform=ccrs.PlateCarree(), cmap='hot_r', alpha=0.7)
        cb = fig.colorbar(contourf_obj, ax=ax, shrink=.65)
        cb.ax.text(0.5, 1.02, '污染物浓度 g/m$^3$', ha='center', va='bottom', transform=cb.ax.transAxes)
        ax.scatter(lon_x, lat_y, color='red', s=50, marker='*', transform=ccrs.PlateCarree(), alpha=0.85)
        ax.set_title('大气污染扩散(烟团): 离地' + str(z1) + '米高度处分布', fontsize=13)
        ax.text(0.02, 0.98, '目标经度: ' + lon, transform=ax.transAxes, ha='left', va='top', fontsize=12, color='red')
        ax.text(0.02, 0.94, '目标纬度: ' + lat, transform=ax.transAxes, ha='left', va='top', fontsize=12, color='red')
        ax.text(0.02, 0.90, '排放速率: ' + str(q) + ' g/s', transform=ax.transAxes, ha='left', va='top', fontsize=12, color='red')
        ax.text(0.02, 0.86, '排放高度: ' + str(h) + ' m', transform=ax.transAxes, ha='left', va='top', fontsize=12, color='red')
        ax.text(0.02, 0.82, '风速: ' + str(wind_s) + ' m/s', transform=ax.transAxes, ha='left', va='top', fontsize=12, color='red')
        ax.text(0.02, 0.78, '风向: ' + str(wind_dir) + '°', transform=ax.transAxes, ha='left', va='top', fontsize=12, color='red')
        ax.text(0.02, 0.74, '排放时间: ' + str(t) + 's', transform=ax.transAxes, ha='left', va='top', fontsize=12, color='red')
        ax.text(0.02, 0.70, '排放间隔: ' + delt_t + 's', transform=ax.transAxes, ha='left', va='top', fontsize=12, color='red')
        ax.text(0.98, 0.98, 'Pasquill大气稳定度等级: ' + stability_str1[i], transform=ax.transAxes, ha='right', va='top', fontsize=12, color='blue')

        grid = ax.gridlines(draw_labels=True, linewidth=0.8, color='grey', alpha=0.5, linestyle='--')
        grid.top_labels = False
        grid.right_labels = False
        grid.xformatter = LONGITUDE_FORMATTER
        grid.yformatter = LATITUDE_FORMATTER

        bounds = [np.min(lon_grid), np.min(lat_grid), np.max(lon_grid), np.max(lat_grid)]
        tbd.plot_map(plt, bounds, zoom=12, style=4)
        ax.set_extent([np.min(lon_grid), np.max(lon_grid), np.min(lat_grid), np.max(lat_grid)], crs=ccrs.PlateCarree())

        result_picture = os.path.join(save_path, 'puff_大气稳定度_' + stability_str1[i][0] + '.png')
        fig.savefig(result_picture, dpi=200, bbox_inches='tight')
        plt.cla()

        result_dict[stability_str1[i]] = result_picture

    plt.close('all')

    return result_dict


if __name__ == '__main__':

    lon = '94.961285'
    lat = '36.366595'
    q = '7500'
    h = '13'
    wind_s = 15.8
    wind_d = 270
    z1 = 20
    humidify = None
    acid = 'SODIUM_CHLORIDE'
    rh = 0.9
    save_path = r'C:/Users/MJY/Desktop/result'
    t = 300
    delt_t = '20'
    result_dict = gaussianPuffModel(lon, lat, q, h, wind_s, wind_d, z1, save_path, t, delt_t, acid= 'SODIUM_CHLORIDE', humidify= None, rh= 0.9)
