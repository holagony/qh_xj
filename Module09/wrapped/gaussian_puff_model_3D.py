# -*- coding: utf-8 -*-
"""
Created on Thu Jul  4 13:47:42 2024

@author: EDY
"""
import warnings
warnings.filterwarnings("ignore")

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
from matplotlib.ticker import MultipleLocator
from mpl_toolkits.mplot3d import Axes3D
import multiprocessing
from multiprocessing import Pool

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
    stab1, XX, YY, z, num_stacks, Q, wind_speed, wind_d, stack_x, stack_y, H, t, delt_t_x = args
    # 确保使用float64类型
    result = np.zeros_like(XX, dtype=np.float64)
    
    for j in range(num_stacks):
        n_steps = int(np.ceil(t / delt_t_x[j]))
        for i in range(n_steps):
            C = gauss_puff_func(
                Q=Q[j],
                u=wind_speed,
                dir1=wind_d,
                x=XX,
                y=YY,
                z=z,
                xs=stack_x[j],
                ys=stack_y[j],
                H=H[j],
                STABILITY=stab1,
                t=t,
                delt_t=delt_t_x[j],
                i=i
            )
            result += C.astype(np.float64)
    
    return result


def gaussianPuffModel3D(lon, lat, q, h, wind_s, wind_d, z1, save_path, t, delt_t, acid, humidify, rh):
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
    t: 模拟时长
    delt_t：排放间隔
    '''
  
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
    stability_str1 = ['A_3D强不稳定', 'B_3D不稳定', 'C_3D弱不稳定', 'D_3D中性', 'E_3D较稳定', 'F_3D稳定']  # 大气状态

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
    stack_x = np.zeros(num_stacks)
    stack_y = np.zeros(num_stacks)
    stack_xx = np.zeros(num_stacks)
    stack_yy = np.zeros(num_stacks)
    grid_array = np.concatenate((lon_grid[None], lat_grid[None]), axis=0)

    for i in range(num_stacks):
        nearest_index = find_nearest_point_index(lonlat[i], grid_array)
        stack_x[i] = X[nearest_index]
        stack_y[i] = Y[nearest_index]

        stack_xx[i] = nearest_index[0]
        stack_yy[i] = nearest_index[1]
        
    # Main loop
    wind_speed = wind_s  # m/s
    wind_dir = wind_d
    
    x_center_min=np.min(stack_xx)
    y_center_min=np.min(stack_yy)
    y_center_max=np.max(stack_yy)
    
    XX=X[int(y_center_min-1000/res):int(y_center_max+1000/res+1):,int(x_center_min):int(8000/res+1):]
    YY=Y[int(y_center_min-1000/res):int(y_center_max+1000/res+1):,int(x_center_min):int(8000/res+1):]

    C1 = np.zeros((XX.shape[0], XX.shape[1], len(stability_str1)))
    print(C1.shape)

    z = np.zeros(np.shape(XX)) + z1
    for stab1 in tqdm(np.arange(len(stability_str1))):
        for j in range(num_stacks):  # 不同的污染中心
            for i in np.arange(np.ceil(t / delt_t_x[j])):
                C = gauss_puff_func(
                    Q=Q[j],
                    u=wind_speed,
                    dir1=wind_dir,  # 某个时间点的风向，可以是逐日/小时/10min...
                    x=XX,  # 二维区域的x坐标
                    y=YY,  # 二维区域的y坐标
                    z=z,  # 2d-array 对应(x,y)的高度z，地面为0
                    xs=stack_x[j],  # 起始x位置
                    ys=stack_y[j],  # 起始y位置
                    H=H[j],  # 起始污染塔的高度
                    STABILITY=stab1,  # 大气稳定度等级，每个时间点一个稳定度
                    t=t,
                    delt_t=delt_t_x[j],
                    i=i)

                C1[:, :, stab1] = C1[:, :, stab1] + C

    if humidify is not None:
        aerosol_type = params_dict[acid] - 1
        nu = params_dict['nu']
        rho_s = params_dict['rho_s']
        Ms = params_dict['Ms']
        Mw = 18e-3
        dry_size = 60e-9
        mass = np.pi / 6 * rho_s[aerosol_type] * dry_size**3
        moles = mass / Ms[aerosol_type]
        nw = rh * nu[aerosol_type] * moles / (1 - rh)
        mass2 = nw * Mw + moles * Ms[aerosol_type]
        C1 = C1 * mass2 / mass

    # 使用多进程计算不同稳定度
    stability_args = []
    for stab1 in range(len(stability_str1)):
        args = (stab1, XX, YY, z, num_stacks, Q, wind_speed, wind_dir, 
               stack_x, stack_y, H, t, delt_t_x)
        stability_args.append(args)

    # 使用多进程计算不同稳定度
    # n_cores = multiprocessing.cpu_count() - 1  # 保留一个核心给系统
    n_cores = 6
    with Pool(processes=n_cores) as pool:
        results = pool.map(process_stability, stability_args)
    
    # 将结果组装到C1中
    C1 = np.stack(results, axis=-1)

    # Plot
    result_dict = dict()
    for i in range(6):
        contour_data = C1[:, :, i] * 1000  # 将 g/m³ 转换为 mg/m³
        fig = plt.figure(figsize=(12,8))
        # 设置图形背景为白色
        fig.patch.set_facecolor('white')
        
        # 设置3D坐标系背景为白色
        ax = fig.add_subplot(111, projection='3d', facecolor='white')
        
        # 调整图形整体布局，为标签留出更多空间
        plt.subplots_adjust(left=0.1, right=0.9, bottom=0.1, top=0.9)
        
        # 设置3D坐标系的坐标轴面板为白色
        ax.xaxis.pane.fill = False
        ax.yaxis.pane.fill = False
        ax.zaxis.pane.fill = False
        
        # 设置网格线
        ax.grid(True, linestyle='--', alpha=0.3, color='gray')
        
        # 使用magma_r配色方案
        custom_cmap = plt.cm.magma_r
        
        # 计算颜色条的范围和刻度
        vmin = 0  # 强制最小值为0
        vmax = np.max(contour_data)
        ticks = np.linspace(vmin, vmax, 10)  # 固定10个刻度
        
        surf = ax.plot_surface(XX, YY, contour_data, cmap=custom_cmap, 
                             rstride=4, cstride=4, vmin=vmin, vmax=vmax)

        ax.set_xlim(np.min(XX[0,:]), np.max(XX[0,:]))
        ax.set_ylim(np.min(YY[:,0]), np.max(YY[:,0]))
        ax.set_zlim(vmin, vmax)  # 设置Z轴范围与colorbar一致
        
        # 设置Z轴刻度为与colorbar相同的刻度
        ax.set_zticks(ticks)
        
        # 格式化刻度标签
        tick_labels = []
        for tick in ticks:
            if tick == 0:
                tick_labels.append('0')
            elif tick < 0.01:
                exp = int(np.floor(np.log10(tick)))
                mantissa = tick / (10**exp)
                tick_labels.append(f'{mantissa:.1f}e{exp:+d}')
            else:
                tick_labels.append(f'{tick:.2f}')
        
        # 设置Z轴刻度标签
        ax.set_zticklabels(tick_labels, fontsize=8)

        if len(stack_x)==1:
            # 单源情况下的视角优化
            ax.view_init(elev=25, azim=-135)  # 调整仰角和方位角
            cbar = fig.colorbar(surf, shrink=.65, ticks=ticks, pad=0.05)  # 使用相同的ticks
            cbar.ax.set_yticklabels(tick_labels, fontsize=8)  # 使用相同的tick_labels
            cbar.ax.set_title('浓度(mg/m$^3$)', fontsize=8, pad=5)
        else:
            # 多源情况下的视角优化
            ax.view_init(elev=25, azim=-135)
            cax = plt.axes([0.85, 0.3, 0.02, 0.4])  # [左, 下, 宽度, 高度]
            cbar = fig.colorbar(surf, cax=cax, shrink=.65, ticks=ticks)  # 使用相同的ticks
            cbar.ax.set_yticklabels(tick_labels, fontsize=8)  # 使用相同的tick_labels
            cbar.ax.set_title('浓度(mg/m$^3$)', fontsize=8, pad=5)
        
        # 设置轴标签和刻度
        ax.set_xlabel('水平下风向距离(m)', fontsize=8, labelpad=0.3)
        ax.set_ylabel('垂直方向距离(m)', fontsize=8, labelpad=0.3)
        ax.set_zlabel('气体扩散浓度(mg/m$^3$)', fontsize=8, labelpad=0.1)
        
        # 设置主刻度间隔
        x_major_locator = MultipleLocator(500)
        ax.xaxis.set_major_locator(x_major_locator)
        
        y_major_locator = MultipleLocator(250)
        ax.yaxis.set_major_locator(y_major_locator)
        
        # 设置刻度标签
        xticks = ax.get_xticks()
        yticks = ax.get_yticks()
        xticklabels = [f'{int(tick)}' for tick in xticks]
        yticklabels = [f'{int(tick)}' for tick in yticks]
        
        ax.set_xticklabels(xticklabels, fontsize=8)
        ax.set_yticklabels(yticklabels, fontsize=8)
        
        # 添加文本信息
        if z1 == 0:
            title = '大气污染扩散模拟: 地面高度处浓度分布'
        else:
            title = f'大气污染扩散模拟: 离地{z1}米高度处浓度分布'
        
        info_text = (
            f'{title}\n'
            f'目标经度: {lon}\n'
            f'目标纬度: {lat}\n'
            f'排放量: {q} kg\n'
            f'排放高度: {h} m\n'
            f'风速: {wind_s} m/s\n'
            f'风向: {wind_d}°\n'
            f'排放时间: {t}s\n'
            f'排放间隔: {delt_t}s\n'
            f'Pasquill大气稳定度等级: {stability_str1[i]}')
        
        ax.text2D(0.02, 0.99, info_text,
                 transform=ax.transAxes,
                 fontsize=10,
                 verticalalignment='top',
                 bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))

        result_picture = os.path.join(save_path, 'puff_大气稳定度_3D_' + stability_str1[i][0] + '.png')
        fig.savefig(result_picture, dpi=200, bbox_inches='tight', pad_inches=0.3)
        plt.cla()

        result_dict[stability_str1[i]] = result_picture

    plt.close('all')

    return result_dict


if __name__ == '__main__':

    lon = '94.990519'
    lat = '36.349942'
    q = '7500'
    h = '210'
    wind_s = 25
    wind_d = 270
    z1 = 0
    humidify = 0
    acid = 'SODIUM_CHLORIDE'
    rh = 0.9
    save_path = r'C:/Users/MJY/Desktop/result'
    t = 300
    delt_t = '20,20'
    result_dict = gaussianPuffModel3D(lon, lat, q, h, wind_s, wind_d, z1, save_path, t, delt_t, acid= 'SODIUM_CHLORIDE', humidify= None, rh= 0.9)
