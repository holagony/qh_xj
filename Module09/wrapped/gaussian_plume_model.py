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

# matplotlib.use('Agg')
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
    # axis = np.linspace(-coors, coors, n_coord) #* dist
    
    axis=np.arange(-coors,coors+dist,dist)
    X, Y = np.meshgrid(axis, axis)
    R = 6378137
    dLat = (X / R)# * dist
    dLon = (Y / (R * np.cos(np.pi * lat / 180))) #* dist
    # lat_grid = np.flipud((lat + dLat * 180 / np.pi).T)
    lat_grid = (lat + dLat * 180 / np.pi).T # 不用翻转，因为Y也是由小到大
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


def gaussianPlumeModel(lon, lat, q, h, wind_s, wind_d, z1, save_path, humidify, acid, rh):
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
    grid_array = np.concatenate((lon_grid[None], lat_grid[None]), axis=0)

    for i in range(num_stacks):
        nearest_index = find_nearest_point_index(lonlat[i], grid_array)
        stack_x[i] = X[nearest_index]
        stack_y[i] = Y[nearest_index]

    # Main loop
    wind_speed = wind_s  # m/s
    wind_dir = wind_d
    C1 = np.zeros((X.shape[0], X.shape[1], len(stability_str1)))
    print(C1.shape)

    z_grid = np.zeros(np.shape(X)) + z1
    for stab1 in tqdm(np.arange(len(stability_str1))):
        for j in range(num_stacks):  # 不同的污染中心
            C = gauss_plume_func(
                Q=Q[j],
                u=wind_speed,
                dir1=wind_dir,
                x=X,  # 二维区域的x坐标
                y=Y,  # 二维区域的y坐标
                z=z_grid,  # 2d-array 对应(x,y)的高度z，地面为0
                xs=stack_x[j],  # 起始x位置
                ys=stack_y[j],  # 起始y位置
                H=H[j],  # 起始污染塔的高度
                STABILITY=stab1)  # 大气稳定度等级
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
    
    # 将 C1 从 g/m³ 转换为 mg/m³
    C1 = C1 * 1000  # 转换为 mg/m³
    C1 = np.where(C1 < 1e-2, np.nan, C1)  # 阈值也相应调整

    # Plot
    result_dict = dict()
    for i in range(6):
        contour_data = C1[:, :, i]
        
        fig = plt.figure(figsize=(10, 10))
        ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())
        contourf_obj=ax.contourf(lon_grid, lat_grid, contour_data,transform=ccrs.PlateCarree(), cmap='magma_r', alpha=0.7) 
        cb = fig.colorbar(contourf_obj, ax=ax,shrink=0.65)
        cb.ax.text(0.5, 1.02, '污染物浓度 mg/m$^3$', ha='center', va='bottom', transform=cb.ax.transAxes)  # 修改单位显示
        ax.scatter(lon_x, lat_y, color='red', s=50, marker='*', transform=ccrs.PlateCarree(), alpha=0.85)

        if z1 == 0:
            title = '大气污染扩散模拟: 地面高度处浓度分布'
        else:
            title = f'大气污染扩散模拟: 离地{z1}米高度处浓度分布'
        
        ax.set_title(title, fontsize=13)
        ax.text(0.02, 0.98, '目标经度: ' + lon, transform=ax.transAxes, ha='left', va='top', fontsize=12, color='red')
        ax.text(0.02, 0.94, '目标纬度: ' + lat, transform=ax.transAxes, ha='left', va='top', fontsize=12, color='red')
        ax.text(0.02, 0.90, '排放速率: ' + str(q) + ' g/s', transform=ax.transAxes, ha='left', va='top', fontsize=12, color='red')
        ax.text(0.02, 0.86, '排放高度: ' + str(h) + ' m', transform=ax.transAxes, ha='left', va='top', fontsize=12, color='red')
        ax.text(0.02, 0.82, '风速: ' + str(wind_s) + ' m/s', transform=ax.transAxes, ha='left', va='top', fontsize=12, color='red')
        ax.text(0.02, 0.78, '风向: ' + str(wind_dir) + '°', transform=ax.transAxes, ha='left', va='top', fontsize=12, color='red')
        ax.text(0.98, 0.98, 'Pasquill大气稳定度等级: ' + stability_str1[i], transform=ax.transAxes, ha='right', va='top', fontsize=12, color='blue')

        grid = ax.gridlines(draw_labels=True, linewidth=0.8, color='grey', alpha=0.5, linestyle='--')
        grid.top_labels = False
        grid.right_labels = False
        grid.xformatter = LONGITUDE_FORMATTER
        grid.yformatter = LATITUDE_FORMATTER

        bounds = [np.min(lon_grid), np.min(lat_grid), np.max(lon_grid), np.max(lat_grid)]
        tbd.plot_map(plt, bounds, zoom=12, style=4)
        ax.set_extent([np.min(lon_grid), np.max(lon_grid), np.min(lat_grid), np.max(lat_grid)], crs=ccrs.PlateCarree())

        result_picture = os.path.join(save_path, 'plume_大气稳定度' + stability_str1[i][0] +  '.png')
        fig.savefig(result_picture, dpi=200, bbox_inches='tight')
        plt.cla()

        result_dict[stability_str1[i]] = result_picture

    plt.close('all')

    return result_dict


if __name__ == '__main__':
    lon = '94.961285,94.980918'
    lat = '36.366595,36.387004'
    q = '300,300'
    h = '13,23'
    wind_s = 20
    wind_d = 130
    z1 = 0
    humidify = None
    acid = 'SODIUM_CHLORIDE'
    rh = 0.9
    save_path = r'C:/Users/MJY/Desktop/result'
    result_dict= gaussianPlumeModel(lon, lat, q, h, wind_s, wind_d, z1, save_path, humidify= None, acid= 'SODIUM_CHLORIDE', rh= 0.9)
