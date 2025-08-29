import numpy as np
import pandas as pd
from scipy.optimize import fsolve, root, least_squares
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from Utils.ordered_easydict import OrderedEasyDict as edict
import matplotlib.pyplot as plt
from matplotlib.pyplot import MultipleLocator


# 1.分公式
def part_func(p, x):
    '''
    构建暴雨强度分公式，包含参数A/b/n
    '''
    t = x
    A, b, n = p
    return A / ((t + b)**n)


def part_error_func(p, x, y):
    '''
    构建暴雨强度分公式的残差约束，用于找到最佳参数
    '''
    return y - part_func(p, x)


def part_func_fitting(data_x, data_y):
    '''
    暴雨强度分公式A/b/n参数迭代计算
    '''
    p0 = np.array([0.1, 0.1, 0.1])
    fit_res = least_squares(part_error_func, p0, args=(data_x, data_y))

    return fit_res


# 2.总公式
def total_func(p, x, y):
    '''
    构建暴雨强度总公式的残差约束，包含参数A/b/C/n
    '''
    A, b, C, n = p[0], p[1], p[2], p[3]
    t = x

    formula_1 = (y[0, :] - A * (1 + C * np.log10(2)) / ((t + b)**n))**2
    formula_2 = (y[1, :] - A * (1 + C * np.log10(3)) / ((t + b)**n))**2
    formula_3 = (y[2, :] - A * (1 + C * np.log10(5)) / ((t + b)**n))**2
    formula_4 = (y[3, :] - A * (1 + C * np.log10(10)) / ((t + b)**n))**2
    formula_5 = (y[4, :] - A * (1 + C * np.log10(20)) / ((t + b)**n))**2
    formula_6 = (y[5, :] - A * (1 + C * np.log10(30)) / ((t + b)**n))**2
    formula_7 = (y[6, :] - A * (1 + C * np.log10(50)) / ((t + b)**n))**2
    formula_8 = (y[7, :] - A * (1 + C * np.log10(100)) / ((t + b)**n))**2

    return formula_1 + formula_2 + formula_3 + formula_4 + formula_5 + formula_6 + formula_7 + formula_8


def total_func_fitting(data_x, data_y):
    '''
    暴雨强度总公式A/b/n参数迭代计算
    '''
    p0 = [0.1, 0.1, 0.1, 0.1]
    fit_res = least_squares(total_func, p0, args=(data_x, data_y))

    return fit_res


def step4_run(table):
    '''
    计算暴雨公式流程 分公式加总公式
    支持分别计算长短历时(0~180/0~1440min)暴雨公式
    table 来自step3算出来的不同重现期各个历时的雨强表
    '''
    result = edict()
    result['full'] = edict()

    table = np.array(table)
    return_years = [2, 3, 5, 10, 20, 30, 50, 100]
    x_long = np.array([5, 10, 15, 20, 30, 45, 60, 90, 120, 150, 180, 240, 360, 720, 1440])
    x_short = np.array([5, 10, 15, 20, 30, 45, 60, 90, 120, 150, 180])

    if table.shape[1] == 15:
        table_dict = {'result': [x_long, table]}
        result['type'] = '长历时'

    elif table.shape[1] == 11:
        table_dict = {'result': [x_short, table]}
        result['type'] = '短历时'

    for _, vals in table_dict.items():
        x = vals[0]
        table = vals[1]

        # 分公式计算
        for i, year in enumerate(return_years):
            result[str(year) + 'a'] = edict()
            y = table[i, :]  # 某个重现期的所有历时雨强结果

            # 计算拟合参数
            fit_res = part_func_fitting(x, y)
            A, b, n = fit_res.x
            A = round(A, 3)
            b = round(b, 3)
            n = round(n, 3)
            result[str(year) + 'a']['params'] = {'A': A, 'b': b, 'n': n}

            # 计算拟合误差
            y_pred = part_func(fit_res.x, x)
            rmse = np.sqrt(mean_squared_error(y, y_pred))
            mae = mean_absolute_error(y, y_pred)
            error = (mae / np.mean(y)) * 100  # 相对误差，使用mae
            rmse = round(rmse, 5)
            mae = round(mae, 5)
            error = round(error, 2)
            result[str(year) + 'a']['error'] = {'mae': mae, 'rmse': rmse, 'rel_error': error}

        # 总公式计算
        # 计算拟合参数 todo 短历时公式查算表
        fit_res_full = total_func_fitting(x, table)
        A, b, C, n = fit_res_full.x
        A = round(A, 3)
        b = round(b, 3)
        C = round(C, 3)
        n = round(n, 3)
        result['full']['params'] = {'A': A, 'b': b, 'C': C, 'n': n}

        # 计算拟合误差
        for num, year in enumerate(return_years):
            arr = A * (1 + C * np.log10(year)) / ((x + b)**n)
            arr = arr.reshape(1, -1)

            if num == 0:
                y_pred = arr
            else:
                y_pred = np.concatenate((y_pred, arr), axis=0)

        rmse = np.sqrt(mean_squared_error(table, y_pred))
        mae = mean_absolute_error(table, y_pred)
        error = (mae / np.mean(table)) * 100  # 相对误差
        rmse = round(rmse, 5)
        mae = round(mae, 5)
        error = round(error, 2)
        result['full']['error'] = {'mae': mae, 'rmse': rmse, 'rel_error': error}

        # 增加查算表 0-180min各重现期的雨强i(mm/min)
        if table.shape[1] == 15:
            input_t = np.arange(1, 1441).reshape(-1, 1)
        elif table.shape[1] == 11:
            input_t = np.arange(1, 181).reshape(-1, 1)

        input_years = np.array(return_years).reshape(1, -1)
        output_i = A * (1 + C * np.log10(input_years)) / ((input_t + b)**n)
        output_i = pd.DataFrame(output_i)
        output_i.columns = [str(year) + 'a' for year in return_years]
        output_i.insert(loc=0, column='分钟', value=input_t)
        output_i = output_i.round(3)
        
        if table.shape[1] == 11:
            result['table'] = output_i.to_dict(orient='records')

    return result


if __name__ == '__main__':
    # 上一步输出的不同历时的P3重现期结果 return_table
    # table = np.array([[0.781, 0.596, 0.474, 0.393, 0.297, 0.226, 0.19, 0.152, 0.13, 0.117, 0.106, 0.089, 0.068, 0.039, 0.022], 
    #                   [0.992, 0.749, 0.606, 0.51, 0.39, 0.296, 0.246, 0.191, 0.159, 0.14, 0.127, 0.106, 0.08, 0.046, 0.025],
    #                   [1.255, 0.936, 0.772, 0.659, 0.51, 0.385, 0.32, 0.238, 0.194, 0.168, 0.15, 0.124, 0.093, 0.053, 0.029], 
    #                   [1.609, 1.185, 0.997, 0.863, 0.676, 0.509, 0.42, 0.302, 0.24, 0.203, 0.179, 0.148, 0.11, 0.063, 0.034],
    #                   [1.961, 1.432, 1.223, 1.069, 0.845, 0.635, 0.522, 0.365, 0.284, 0.237, 0.208, 0.17, 0.126, 0.071, 0.038], 
    #                   [2.166, 1.575, 1.354, 1.19, 0.944, 0.709, 0.582, 0.401, 0.309, 0.256, 0.224, 0.183, 0.135, 0.076, 0.041],
    #                   [2.425, 1.754, 1.52, 1.343, 1.07, 0.803, 0.657, 0.447, 0.341, 0.28, 0.244, 0.199, 0.146, 0.082, 0.044], 
    #                   [2.774, 1.996, 1.745, 1.551, 1.242, 0.93, 0.76, 0.509, 0.384, 0.312, 0.27, 0.22, 0.161, 0.09, 0.048]])
    table=np.array(table)
    result_formula = step4_run(table)
