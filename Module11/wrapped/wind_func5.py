import os
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.pyplot import MultipleLocator
from scipy.stats import weibull_min
from Utils.config import cfg
from Utils.ordered_easydict import OrderedEasyDict as edict
from Module11.wrapped.wind_dataloader import get_data_postgresql, wind_tower_processing

matplotlib.use('agg')
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False
    
def wind_stats5(data_dict, img_path):
    '''
    风频曲线计算
    1.weibull分布参数
    2.weibull pdf图
    '''
    result = edict()
    x = np.linspace(0, 25, 1000)
    fig, ax = plt.subplots(figsize=(7, 5))
    
    for sta, sub_dict in data_dict.items():
        result[sta] = edict()
        result[sta]['img_save_path'] = edict()

        ws_df = sub_dict['ws_10'].filter(like='m_hour_ws')
        ws_df.dropna(axis=1,how='all',inplace=True) # 删除全是nan的列(未进行高度赋值)
 
        df = pd.DataFrame(columns=['尺度参数C(m/s)','形状参数k'])
        for col in ws_df.columns:
            data = ws_df[col].dropna()
            k, loc, c = weibull_min.fit(data, floc=0)
            
            # 画图
            weibull_pdf = weibull_min.pdf(x, k, loc, c)
            samples = weibull_min.rvs(k, loc, c, size=1000)
            ax.hist(samples, bins=25, density=True, alpha=0.5, label='Histogram', rwidth=0.8)
            ax.plot(x, weibull_pdf, label='Weibull PDF')
            ax.set_xlabel('Wind Speed (m/s)')
            ax.set_ylabel('Probability Density')
            ax.set_ylim(0, 0.225)
            ax.xaxis.set_major_locator(MultipleLocator(2))
            ax.yaxis.set_major_locator(MultipleLocator(0.025))
            ax.text(0.85, 0.75, 'Weibull Distribution '+col.split('_')[0], transform=ax.transAxes, ha='right', va='top', fontsize=12, color='red')
            ax.text(0.85, 0.68, 'C='+str(round(c,2)), transform=ax.transAxes, ha='right', va='top', fontsize=12, color='red')
            ax.text(0.85, 0.61, 'K='+str(round(k,2)), transform=ax.transAxes, ha='right', va='top', fontsize=12, color='red')
            ax.grid(True)
            save_path = img_path+'/weibull_'+col.split('_')[0]+'.png'
            plt.savefig(save_path, dpi=200, format='png', bbox_inches='tight')
            plt.cla()
            result[sta]['img_save_path'][col.split('_')[0]] = save_path
            
            # 输出结果表
            df.loc[len(df)] = [round(k,2),round(c,2)]
        df.insert(loc=0, column='高度', value=[h.split('_')[0] for h in ws_df.columns])
        result[sta]['weibull_params'] = df.to_dict(orient='records')
        plt.close('all')
        
    return result


if __name__ == '__main__':
    df = get_data_postgresql(sta_id='QH001', time_range='20230801,20240831')
    after_process = wind_tower_processing(df)
    save_path = r'C:/Users/MJY/Desktop/result'
    result = wind_stats5(after_process, save_path)