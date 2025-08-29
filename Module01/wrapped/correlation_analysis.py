import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from Utils.config import cfg
from Utils.ordered_easydict import OrderedEasyDict as edict
from Utils.data_processing import daily_data_processing
import os
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde
import matplotlib

matplotlib.use('Agg')
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

def linear_regression(x, y, intercept=1):

    if intercept == 1:
        flag = True
    else:
        flag = False

    x = np.array(x).reshape(-1, 1)
    y = np.array(y).reshape(-1, 1)
    model = LinearRegression(fit_intercept=flag).fit(x, y)
    weight = model.coef_[0][0].round(3)
    r_square = model.score(x, y)
    r_square = round(r_square, 3)

    if flag == True:
        bias = model.intercept_[0].round(3)
        return weight, bias, r_square
    elif flag == False:
        return weight, 0, r_square


def correlation_analysis(data_df, elements, main_st, sub_st, method,data_dir):
    '''
    相关性分析接口
    主站和对比站都是天擎站
    '''
    # 生成elements对应的中文列表
    replace_dict = {'PRS_Avg': '平均气压', 
                    'PRS_Max': '最高气压', 
                    'PRS_Min': '最低气压', 
                    'TEM_Avg': '平均气温', 
                    'TEM_Min': '最低气温', 
                    'TEM_Max': '最高气温', 
                    'RHU_Avg': '平均湿度', 
                    'PRE_Time_2020': '降水量', 
                    'WIN_S_2mi_Avg': '平均风速', 
                    'WIN_S_Max': '最大风速'}

    data_scale=dict()
    data_scale['平均气压']=5
    data_scale['最高气压']=5
    data_scale['最低气压']=5
    data_scale['平均气温']=5
    data_scale['最低气温']=5
    data_scale['最高气温']=5
    data_scale['平均湿度']=5
    data_scale['降水量']=5
    data_scale['平均风速']=1
    data_scale['最大风速']=1
    
    data_unit=dict()
    data_unit['平均气压']='(平均气压:hPa)'
    data_unit['最高气压']='(最高气压:hPa)'
    data_unit['最低气压']='(最低气压:hPa)'
    data_unit['平均气温']='(平均气温:℃)'
    data_unit['最低气温']='(最低气温:℃)'
    data_unit['最高气温']='(最高气温:℃)'
    data_unit['平均湿度']='(平均湿度:%)'
    data_unit['降水量']='(降水量:mm)'
    data_unit['平均风速']='(平均风速:m/s)'
    data_unit['最大风速']='(最大风速:m/s)'

    # elements_ch和elements顺序相同
    elements_ch = [replace_dict[ele] if ele in replace_dict else ele for ele in elements]

    all_result = edict()
    all_result['day'] = edict()
    all_result['picture'] = edict()

    for num, ele in enumerate(elements):
        ele_ch = replace_dict[ele]
        all_result['picture'][ele_ch] = edict()
        all_result['day'][ele_ch] = edict()
        all_result['day'][ele_ch]['data'] = edict()

        if 'regression' in method:
            all_result['day'][ele_ch]['regression'] = edict()
            day_result_reg = pd.DataFrame(columns=['气象要素', '对比站X', '参证站Y', '样本数', '回归方程', '权重', '偏差', '确定系数', '样本X均值', '样本Y均值'])

        if 'ratio' in method:
            all_result['day'][ele_ch]['ratio'] = edict()
            day_result_rat = pd.DataFrame(columns=['气象要素', '对比站X', '参证站Y', '样本数', '回归方程', '权重', '确定系数', '样本X均值', '样本Y均值'])

        # 计算
        x_train = data_df[data_df['Station_Id_C'] == main_st][ele].to_frame()
        for j in range(len(sub_st)):
            y_train = data_df[data_df['Station_Id_C'] == sub_st[j]][ele].to_frame()
            train = pd.concat([x_train, y_train], axis=1)
            train = train.dropna(how='any', axis=0)  # 删除任何包含nan的行

            try:
                all_result['day'][ele_ch]['data'][sub_st[j]] = edict()
                train_data = train.values

                if 'ratio' in method:
                    weight, _, r_square = linear_regression(train_data[:, 0], train_data[:, 1], intercept=0)  # 计算线性回归
                    formula = 'y = ' + str(weight) + 'x'
                    num_data = len(train_data)
                    df_row = day_result_rat.shape[0]
                    day_result_rat.loc[df_row] = [elements_ch[num], main_st, sub_st[j], num_data, formula, weight, r_square, round(float(x_train.mean()),1), round(float(y_train.mean()),1)]
                    all_result['day'][ele_ch]['data'][sub_st[j]]['ratio'] = [weight, 0]

                if 'regression' in method:
                    weight, bias, r_square = linear_regression(train_data[:, 0], train_data[:, 1])  # 计算线性回归
                    formula = 'y = ' + str(weight) + 'x + ' + str(bias)
                    num_data = len(train_data)
                    df_row = day_result_reg.shape[0]
                    day_result_reg.loc[df_row] = [elements_ch[num], main_st, sub_st[j], num_data, formula, weight, bias, r_square, round(float(x_train.mean()),1), round(float(y_train.mean()),1)]
                    all_result['day'][ele_ch]['data'][sub_st[j]]['regression'] = [weight, bias]
                
                    # 图片绘制
                    xy = train.T
                    z = gaussian_kde(xy)(xy)
                    idx = z.argsort()

                    z=(z-z.min())/(z.max()-z.min())
                    fig, ax = plt.subplots(figsize=(5,5))
                    scatter = ax.scatter(xy.iloc[0,:], xy.iloc[1,:], marker='o', c=z, edgecolors=None, s=15, cmap='RdBu_r',  alpha=0.8)
                    # cbar = plt.colorbar(scatter, shrink=1, orientation='vertical', extend='both', pad=0.015, aspect=30, label='frequency')

                    if 'regression' in method:
                        regression_data=all_result['day'][ele_ch]['data'][sub_st[j]]['regression'][0]*xy.values.flatten()+all_result['day'][ele_ch]['data'][sub_st[j]]['regression'][1]
                        plt.plot(xy.values.flatten(), regression_data, 'red', lw=1.5, label=f"回归方程: y={all_result['day'][ele_ch]['data'][sub_st[j]]['regression'][0]}*x+{all_result['day'][ele_ch]['data'][sub_st[j]]['regression'][1]}") 

                    # if 'ratio' in method:
                    #     ratio_data=all_result['day'][ele_ch]['data'][sub_st[j]]['ratio'][0]*xy.values.flatten()
                    #     plt.plot(xy.values.flatten(), ratio_data, 'red', lw=1.5, label=f"比值法: y={all_result['day'][ele_ch]['data'][sub_st[j]]['ratio'][0]}*x") 

                    plt.xlim(xy.min().min()-data_scale[ele_ch],xy.max().max()+data_scale[ele_ch])
                    plt.ylim(xy.min().min()-data_scale[ele_ch],xy.max().max()+data_scale[ele_ch])
                    plt.xlabel(data_df[data_df['Station_Id_C']==main_st]['Station_Name'][0]+data_unit[ele_ch])
                    plt.ylabel(data_df[data_df['Station_Id_C']==sub_st[j]]['Station_Name'][0]+data_unit[ele_ch])

                    ax.grid(True, linestyle='--', alpha=0.3)
                    ax.legend(loc='best', frameon = False)

                    picture=os.path.join(data_dir,f'{str(main_st)}_{str(sub_st[j])}_{ele}.png')
                    plt.savefig(picture, bbox_inches='tight', dpi=200)
                    plt.cla()
                    
                    all_result['picture'][ele_ch][main_st+'-'+sub_st[j]] = picture
                
            except:
                all_result['day'][ele]['data'][sub_st[j]] = None

        plt.close('all')

        # 保存计算结果
        if 'regression' in method:
            day_result_reg = day_result_reg
            all_result['day'][ele_ch]['regression'] = day_result_reg.to_dict(orient='records')

        if 'ratio' in method:
            day_result_rat = day_result_rat
            all_result['day'][ele_ch]['ratio'] = day_result_rat.to_dict(orient='records')

    return all_result


if __name__ == '__main__':
    method = ['regression','ratio']
    elements = ['TEM_Avg','PRS_Avg','RHU_Avg','WIN_S_2mi_Avg','TEM_Max','PRS_Max','WIN_S_Max','TEM_Min','PRS_Min','PRE_Time_2020']
    daily_elements = ','.join(elements)
    day_eles = ('Station_Name,Station_Id_C,Lat,Lon,Datetime,Year,Mon,Day,' + daily_elements).split(',')
    main_sta_ids = '56033'
    sub_sta_ids = '56151,52818,52602'
    sta_ids = main_sta_ids + ',' + sub_sta_ids
    sta_ids1 = [int(ids) for ids in sta_ids.split(',')]
    daily_df = pd.read_csv(cfg.FILES.QH_DATA_DAY)
    daily_df = daily_df.loc[daily_df['Station_Id_C'].isin(sta_ids1), day_eles]
    daily_df = daily_data_processing(daily_df)
    data_dir=r'D:\Project\3_项目\2_气候评估和气候可行性论证\qhkxxlz\Report\report\Module01\2'
    sub_sta_ids = sub_sta_ids.split(',')
    result_dict = correlation_analysis(daily_df, elements, main_sta_ids, sub_sta_ids, method,data_dir)

    #%%
    # data_df=daily_df
    # elements=elements
    # main_st=main_sta_ids
    # sub_st=sub_sta_ids
    # method=method
    