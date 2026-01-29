import numpy as np
import pandas as pd
from scipy import stats
from Utils.config import cfg


def _to_finite_1d(values):
    if isinstance(values, pd.Series):
        arr = values.to_numpy(dtype=float, copy=False)
    else:
        arr = np.asarray(values, dtype=float)
    arr = np.ravel(arr)
    return arr[np.isfinite(arr)]


def estimate_parameters_gumbel(data, method='normal'):
    '''
    将观测数据拟合入Gumbel分布，得到数据在Gumbel分布下的偏移和缩放参数

    Args:
        data: 输入的气象要素时间序列，如: 2020.1-2020.2的逐小时温度；类型: list/array/dataframe
        method: 估计参数的方法，填写normal为scipy包自动进行MLE估计，填写其他为MM估计；类型: str

    Returns:
        loc: 输入数据在Gumbel分布下的偏移参数；类型: float
        scale: 输入数据在Gumbel分布下的缩放参数；类型: float
    '''
    data = _to_finite_1d(data)
    if data.size < 1:
        raise ValueError('输入数据为空或包含非有限值')

    if method == 'normal':  # MLE
        loc, scale = stats.gumbel_r.fit(data)

    else:  # method of moments
        scale = np.sqrt(6) / np.pi * np.std(data)  # beta
        loc = np.mean(data) - np.euler_gamma * scale  # mu

    loc = round(loc, 3)
    scale = round(scale, 3)

    return loc, scale


def get_max_values_gumbel(years, param1, param2):
    '''
    根据输入的重现期(年)和已知的偏移和缩放参数，得到服从Gumbel分布的对应极值计算结果

    Args:
        years: 重现期(年)或重现期(年)列表，如：50/80/100年；类型: int/list
        param1: 已知的Gumbel偏移系数loc；类型: float
        param2: 已知的Gumbel缩放系数scale；类型: float

    Returns:
        max_values: 极值计算结果；类型: float/array
    '''
    years = np.array(years)
    prob = 1 - 1 / years
    max_values = stats.gumbel_r.ppf(prob, loc=param1, scale=param2)
    max_values = max_values.round(3)

    return max_values


def estimate_parameters_pearson3(data, method):
    '''
    将观测数据拟合入pearson type3分布，得到数据在p3分布下的相关参数

    Args:
        data: 输入的气象要素时间序列，如: 2020.1-2020.2的逐小时温度；类型: list/array/dataframe
        method: 估计参数的方法，填写normal得到skew/loc/scale，填写其他得到Ex/Cv/Cs；类型: str

    Returns:
        skew: 输入数据在p3分布下的偏态参数；类型: float
        loc: 输入数据在p3分布下的偏移参数；类型: float
        scale: 输入数据在p3分布下的缩放参数；类型: float

        Ex: 输入数据的数学期望；类型: float
        Cv: 输入数据的变差系数；类型: float
        Cs: 输入数据的偏态系数；类型: float
        注: Cs等价于skew，使用Cv/Cs参数时，loc=0/scale=1
    '''
    data = _to_finite_1d(data)
    if data.size < 1:
        raise ValueError('输入数据为空或包含非有限值')

    if method == 'normal':  # MLE
        skew, loc, scale = stats.pearson3.fit(data)
        skew = round(skew, 3)
        loc = round(loc, 3)
        scale = round(scale, 3)

        return skew, loc, scale

    else:  # method of moments
        if data.size < 3:
            raise ValueError('样本量不足，无法计算偏态系数')
        Ex = np.mean(data)  # 均值
        K = data / Ex  # 模比系数
        Cv = np.sqrt(np.sum((K - 1)**2) / (len(data) - 1))  # 变差系数
        Cs = stats.skew(data, bias=False)  # 偏态系数

        Ex = round(Ex, 3)
        Cv = round(Cv, 3)
        Cs = round(Cs, 3)

        return Ex, Cv, Cs


def get_max_values_pearson3(years, pattern, param0, param1, param2):
    '''
    根据输入的重现期(年)和参数skew/loc/scale，或参数Ex/Cv/Cs，得到服从p3分布的对应极值计算结果

    Args:
        years: 重现期(年)或重现期(年)列表，如：50/80/100年；类型: int/list
        pattern: 计算模式，等于0时配合第一组参数计算；等于1时配合第二组参数计算；类型: int
        param0: skew or Ex；类型: float
        param1: loc or Cv；类型: float
        param2: scale or Cs；类型: float

    Returns:
        max_values: 极值计算结果；类型: float/array
    '''
    years = np.array(years)
    prob = 1 - 1 / years

    if pattern == 0:
        max_values = stats.pearson3.ppf(prob, skew=param0, loc=param1, scale=param2)
        max_values = max_values.round(3)

    elif pattern == 1:
        max_values = (stats.pearson3.ppf(prob, param2) * param1 + 1) * param0
        max_values = max_values.round(3)

    return max_values


def kolmogorov_smirnov_test(data, cdf_func, distr_params=None):
    '''
    KS检验，比较一组样本的频率分布与特定理论分布，是否为同一分布
    或比较两组样本之间的频率分布，是否为同一分布

    一般的使用场景：通过年最大值序列拟合出分布，如P3，得到相应的PDF、CDF；
    在此基础上通过微调分布的参数后(如Cv/Cs)，计算得到一组x年一遇的最大值序列；
    所以比较的是：A最大值序列 vs B原始数据得到的P3_distr，是否同为P3分布；
    即检验的是微调参数后生成的序列A还服不服从一开始拟合出来的P3分布。

    Args:
        data: 可以是时序数组、生成数组的函数；类型: array
        cdf_func: 一个调用的CDF函数，或为一组时序数据；类型: array/function
        distr_params: 当cdf_func指定为调用的函数时，该参数为调用函数的参数；类型: list/tuple

    Returns:
        ks_statistic: KS检验的计算结果(D值)；类型: float
        p_val: 计算得到的p值，p大于0.05说明无差异；类型: float
    '''
    data = _to_finite_1d(data)
    if data.size < 1:
        raise ValueError('输入数据为空或包含非有限值')

    if distr_params is not None:
        ks_statistic, p_val = stats.kstest(data, cdf=cdf_func, args=distr_params)
    else:
        if callable(cdf_func) or isinstance(cdf_func, str):
            ks_statistic, p_val = stats.kstest(data, cdf=cdf_func)
        else:
            other = _to_finite_1d(cdf_func)
            if other.size < 1:
                raise ValueError('对比样本为空或包含非有限值')
            ks_statistic, p_val = stats.ks_2samp(data, other)

    ks_statistic = round(ks_statistic, 5)
    p_val = round(p_val, 5)

    return ks_statistic, p_val


def apply_prob_scale(ax, axis='x', percent=True, eps=1e-6, ticks=None):
    def forward(values):
        values = np.asarray(values, dtype=float)
        if percent:
            values = values / 100.0
        values = np.clip(values, eps, 1 - eps)
        return stats.norm.ppf(values)

    def inverse(values):
        values = np.asarray(values, dtype=float)
        values = stats.norm.cdf(values)
        if percent:
            values = values * 100.0
        return values

    if axis == 'x':
        ax.set_xscale('function', functions=(forward, inverse))
    elif axis == 'y':
        ax.set_yscale('function', functions=(forward, inverse))
    else:
        raise ValueError("axis must be 'x' or 'y'")

    if ticks is None:
        ticks = [0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50, 80, 90, 95, 98, 99, 99.5]

    if axis == 'x':
        ax.set_xticks(ticks)
        ax.set_xticklabels([str(t) for t in ticks])
    else:
        ax.set_yticks(ticks)
        ax.set_yticklabels([str(t) for t in ticks])
