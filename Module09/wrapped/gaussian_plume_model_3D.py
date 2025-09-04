# -*- coding: utf-8 -*-
"""
Created on Thu Jul  4 09:34:52 2024

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
from Module09.wrapped.gaussian_plume_function import gauss_plume_func
from matplotlib.ticker import MultipleLocator
from mpl_toolkits.mplot3d import Axes3D
import multiprocessing
from multiprocessing import Pool
from functools import lru_cache


matplotlib.use('Agg')
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False


@lru_cache(maxsize=128)
def center_geolocation(geolocations_tuple):
    '''
    多个经纬度点找中心点 - 优化版本
    '''
    geolocations = np.array(geolocations_tuple)
    
    # 向量化计算
    lon_rad = np.radians(geolocations[:, 0])
    lat_rad = np.radians(geolocations[:, 1])
    
    x = np.mean(np.cos(lat_rad) * np.cos(lon_rad))
    y = np.mean(np.cos(lat_rad) * np.sin(lon_rad))
    z = np.mean(np.sin(lat_rad))

    center_lon = round(degrees(atan2(y, x)), 6)
    center_lat = round(degrees(atan2(z, sqrt(x * x + y * y))), 6)
    
    return [center_lon, center_lat]


@lru_cache(maxsize=32)
def generate_grid(lon, lat, dist, coors):
    '''
    根据中心经纬度点生成经纬度网格,和XY的index网格 - 优化版本
    '''
    axis = np.arange(-coors, coors + dist, dist, dtype=np.float32)
    X, Y = np.meshgrid(axis, axis)
    
    # 预计算常量
    R = 6378137
    lat_rad = np.pi * lat / 180
    cos_lat = np.cos(lat_rad)
    
    # 向量化计算
    dLat = X / R
    dLon = Y / (R * cos_lat)
    
    lat_grid = (lat + dLat * 180 / np.pi).T.astype(np.float32)
    lon_grid = (lon + dLon * 180 / np.pi).T.astype(np.float32)

    return X.astype(np.float32), Y.astype(np.float32), lon_grid, lat_grid


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


def compute_stability_3d(args):
    '''
    计算单个稳定度等级的污染物浓度分布 - 用于多进程
    '''
    stab1 = args['stab1']
    XX_shape = args['XX_shape']
    num_stacks = args['num_stacks']
    Q = args['Q']
    wind_speed = args['wind_speed']
    wind_dir = args['wind_dir']
    XX = args['XX']
    YY = args['YY']
    z_grid = args['z_grid']
    stack_x = args['stack_x']
    stack_y = args['stack_y']
    H = args['H']
    
    C_stab = np.zeros(XX_shape, dtype=np.float32)
    for j in range(num_stacks):  # 不同的污染中心
        C = gauss_plume_func(
            Q=Q[j],
            u=wind_speed,
            dir1=wind_dir,
            x=XX,  # 二维区域的x坐标
            y=YY,  # 二维区域的y坐标
            z=z_grid,  # 2d-array 对应(x,y)的高度z，地面为0
            xs=stack_x[j],  # 起始x位置
            ys=stack_y[j],  # 起始y位置
            H=H[j],  # 起始污染塔的高度
            STABILITY=stab1)  # 大气稳定度等级
        C_stab += C
    return stab1, C_stab


def gaussianPlumeModel3D(lon, lat, q, h, wind_s, wind_d, z1, save_path, humidify, acid, rh):
    '''
    lon: 污染源经度 str
    lat: 污染源纬度 str
    q: 烟囱排放速率 str
    h: 烟囱高度 str
    
    wind_s:风速 m/s float
    wind_d:风向 0-360° int
    z1: 模拟高度 float
    
    humidify: 干/湿气溶胶 如果传值，说明是湿气溶胶，对结果进行修正
    acid: 气溶胶类型：SODIUM_CHLORIDE，SULPHURIC_ACID，ORGANIC_ACID，AMMONIUM_NITRATE 氯化钠 硫酸 有机酸 硝胺酸
    rh: 相对湿度 float
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

    # 根据烟囱位置得到中心经纬度
    lon_x = np.array(lon.split(','), dtype=float).tolist()
    lat_y = np.array(lat.split(','), dtype=float).tolist()
    lonlat = np.array(list(zip(lon_x, lat_y)))

    if lonlat.shape[0] != 1:  # 如果多个经纬度点，计算中心经纬度点，用于图像定位
        center_lonlat = center_geolocation(tuple(map(tuple, lonlat)))
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
    
    XX=X[int(y_center_min-1000/res):int(y_center_max+1000/res+1):,int(x_center_min):int(11000/res+1):]
    YY=Y[int(y_center_min-1000/res):int(y_center_max+1000/res+1):,int(x_center_min):int(11000/res+1):]

    C1 = np.zeros((XX.shape[0], XX.shape[1], len(stability_str1)), dtype=np.float32)
    print(C1.shape)

    z_grid = np.full(np.shape(XX), z1, dtype=np.float32)
    
    # 准备多进程计算参数
    compute_args = []
    for stab1 in range(len(stability_str1)):
        args = {
            'stab1': stab1,
            'XX_shape': XX.shape,
            'num_stacks': num_stacks,
            'Q': Q,
            'wind_speed': wind_speed,
            'wind_dir': wind_dir,
            'XX': XX,
            'YY': YY,
            'z_grid': z_grid,
            'stack_x': stack_x,
            'stack_y': stack_y,
            'H': H
        }
        compute_args.append(args)
    
    # 使用多进程计算
    num_cores = min(multiprocessing.cpu_count(), len(stability_str1))
    if num_cores > 1:
        with Pool(processes=num_cores) as pool:
            results = pool.map(compute_stability_3d, compute_args)
    else:
        # 单核处理
        results = [compute_stability_3d(args) for args in compute_args]
    
    # 将结果合并
    for stab1, C_stab in results:
        C1[:, :, stab1] = C_stab

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
    

    # Plot - 优化绘图性能
    result_dict = dict()
    
    # 预计算通用参数
    conversion_factor = 1000  # g/m³ 转换为 mg/m³
    
    for i in range(6):
        contour_data = C1[:, :, i] * conversion_factor
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
        
        # 方案2：使用内置的YlOrRd（从黄到橙到红），也很适合表示污染物浓度
        custom_cmap = plt.cm.magma_r
        
        # 计算颜色条的范围和刻度
        vmin = 0  # 强制最小值为0
        vmax = np.max(contour_data)
        ticks = np.linspace(vmin, vmax, 10)  # 固定10个刻度
        
        # 优化绘图性能：减少数据点
        stride = max(1, min(XX.shape[0] // 50, XX.shape[1] // 50))
        surf = ax.plot_surface(XX[::stride, ::stride], YY[::stride, ::stride], 
                             contour_data[::stride, ::stride], cmap=custom_cmap, 
                             rstride=1, cstride=1, vmin=vmin, vmax=vmax, 
                             antialiased=False, shade=True)

        ax.set_xlim(np.min(XX[0,:]),np.max(XX[0,:]))
        ax.set_ylim(np.min(YY[:,0]),np.max(YY[:,0]))
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

        if len(stack_x)==1:
            # 单源情况下的视角优化
            ax.view_init(elev=25, azim=-135)  # 调整仰角和方位角
            cbar = fig.colorbar(surf, shrink=.65, ticks=ticks, pad=0.05)  # 减小pad值使colorbar更靠近图形
            cbar.ax.set_yticklabels(tick_labels, fontsize=8)
            cbar.ax.set_title('浓度(mg/m$^3$)', fontsize=8, pad=5)
        else:
            # 多源情况下的视角优化
            ax.view_init(elev=25, azim=-135)  # 调整仰角和方位角
            cax = plt.axes([0.85, 0.3, 0.02, 0.4])  # [左, 下, 宽度, 高度]
            cbar = fig.colorbar(surf, cax=cax, shrink=.65, ticks=ticks)
            cbar.ax.set_yticklabels(tick_labels, fontsize=8)
            cbar.ax.set_title('浓度(mg/m$^3$)', fontsize=8, pad=5)
        
        # 设置Z轴刻度标签
        ax.set_zticklabels(tick_labels, fontsize=6)
        ax.set_xlabel('水平下风向距离(m)', fontsize=8, labelpad=0.3)
        ax.set_ylabel('垂直方向距离(m)', fontsize=8, labelpad=0.3)
        ax.set_zlabel('气体扩散浓度(mg/m$^3$)', fontsize=8, labelpad=0.1)
        
        x_major_locator = MultipleLocator(500)
        ax.xaxis.set_major_locator(x_major_locator)
        
        y_major_locator = MultipleLocator(250)
        ax.yaxis.set_major_locator(y_major_locator)
        
        # 设置X、Y轴刻度标签
        xticks = ax.get_xticks()
        yticks = ax.get_yticks()
        xticklabels = [f'{int(tick)}' for tick in xticks]
        yticklabels = [f'{int(tick)}' for tick in yticks]
        
        # 减小X、Y轴刻度的字体大小
        ax.set_xticklabels(xticklabels, fontsize=8)
        ax.set_yticklabels(yticklabels, fontsize=8)
        
        # 添加文本信息
        if z1 == 0:
            title = '大气污染扩散模拟: 地面高度处浓度分布'
        else:
            title = f'大气污染扩散模拟: 离地{z1}米高度处浓度分布'
        
        # 在图形上添加参数信息
        info_text = (
            f'{title}\n'
            f'目标经度: {lon}\n'
            f'目标纬度: {lat}\n'
            f'排放速率: {q} g/s\n'
            f'排放高度: {h} m\n'
            f'风速: {wind_s} m/s\n'
            f'Pasquill大气稳定度等级: {stability_str1[i]}')
        
        # 在3D图的左上角添加文本框
        ax.text2D(0.02, 0.99, info_text,
                 transform=ax.transAxes,
                 fontsize=10,
                 verticalalignment='top',
                 bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))
        
        result_picture = os.path.join(save_path, 'plume_大气稳定度_3D_' + stability_str1[i][0] +  '.png')
        fig.savefig(result_picture, dpi=150, bbox_inches='tight', pad_inches=0.3, 
                   facecolor='white', edgecolor='none')
        plt.cla()
        plt.close(fig)  # 显式关闭图形以释放内存

        result_dict[stability_str1[i]] = result_picture

    plt.close('all')

    return result_dict


if __name__ == '__main__':
    lon = '87'
    lat = '43'
    q = '3000'
    h = '210'
    wind_s = 20
    wind_d = 270
    z1 = 10
    humidify = None
    acid = 'SODIUM_CHLORIDE'
    rh = 0.9
    save_path = r'C:/Users/mjynj/Desktop/result'
    result_dict_3d = gaussianPlumeModel3D(lon, lat, q, h, wind_s, wind_d, z1, save_path, humidify= None, acid= 'SODIUM_CHLORIDE', rh= 0.9)
