import numpy as np
import pandas as pd


def calc_membership_degree(type, x, level_points=None):
    '''
    计算隶属度 输入因子数值和相应的分级，输出因子的隶属度
    type 因子类型 0数值型 or 1类别型
    x 因子数值
    level_points 因子的分级阈值点 list
    '''
    if type == 0:
        v1 = level_points[0]
        v2 = level_points[1]
        v3 = level_points[2]
        v4 = level_points[3]
        v5 = level_points[4]


        decreasing = np.diff([v1, v2, v3, v4, v5]).min() < 0

        # 初始化隶属度函数列表
        degree = []

        if not decreasing:
            u_1 = np.select([x<=v1, v1<x<=v2, x>=v2], [1, (v2-x)/(v2-v1), 0]).round(2)
            u_2 = np.select([x<=v1 or x>v3, v1<x<=v2, v2<x<=v3], [0, (x-v1)/(v2-v1), (v3-x)/(v3-v2)]).round(2)
            u_3 = np.select([x<=v2 or x>v4, v2<x<=v3, v3<x<=v4], [0, (x-v2)/(v3-v2), (v4-x)/(v4-v3)]).round(2)
            u_4 = np.select([x<=v3 or x>v5, v3<x<=v4, v4<x<=v5], [0, (x-v3)/(v4-v3), (v5-x)/(v5-v4)]).round(2)
            u_5 = np.select([x<=v4, v4<x<=v5, x>v5], [0, (x-v4)/(v5-v4), 1]).round(2)
        else:
            u_5 = np.select([x<=v5, v5<x<=v4, x>=v4], [1, (v4-x)/(v4-v5), 0]).round(2)
            u_4 = np.select([x<=v5 or x>v3, v5<x<=v4, v4<x<=v3], [0, (x-v5)/(v4-v5), (v3-x)/(v3-v4)]).round(2)
            u_3 = np.select([x<=v4 or x>v2, v4<x<=v3, v3<x<=v2], [0, (x-v4)/(v3-v4), (v2-x)/(v2-v3)]).round(2)
            u_2 = np.select([x<=v3 or x>v1, v3<x<=v2, v2<x<=v5], [0, (x-v3)/(v2-v3), (v1-x)/(v1-v2)]).round(2)
            u_1 = np.select([x<=v2, v2<x<=v1, x>v1], [0, (x-v2)/(v1-v2), 1]).round(2)

    
        degree = [u_1,u_2,u_3,u_4,u_5]

    elif type == 1:
        
        if x == 1:
            degree = [1,0,0,0,0]

        elif x == 2:
            degree = [0,1,0,0,0]
        
        elif x == 3:
            degree = [0,0,1,0,0]
        
        elif x == 4:
            degree = [0,0,0,1,0]
        
        elif x == 5:
            degree = [0,0,0,0,1]

    return np.array(degree).reshape(1,-1)


def calc_lightning_risk(factors, weights):
    '''
    每层隶属度组成的矩阵结合权重，得到雷电风险评估结果
    factors 因子字典 [类型, 数值]
    weights 因子权重字典
    '''
    # 从左往右，从下往上
    level3_2 = calc_membership_degree(factors['雷击密度']['type'],factors['雷击密度']['value'],level_points=[0.5,1.5,2.5,3.5,4.5]) # 雷击密度隶属度
    level3_3 = calc_membership_degree(factors['雷电流强度']['type'],factors['雷电流强度']['value'],level_points=[5,15,30,50,80]) # 雷电流强度隶属度

    level2_1 = np.matmul(np.array([weights['雷击密度'],weights['雷电流强度']]).reshape(1,-1), np.concatenate([level3_2,level3_3],axis=0)) # 雷击风险隶属度

    #################################
    level4_1 = calc_membership_degree(factors['土壤电阻率']['type'],factors['土壤电阻率']['value'],level_points=[4350,2000,650,200,50]) # 土壤电阻率隶属度
    level4_2 = calc_membership_degree(factors['土壤垂直分层']['type'],factors['土壤垂直分层']['value'],level_points=[435,200,65,20,5]) # 土壤垂直分层隶属度
    level4_3 = calc_membership_degree(factors['土壤水平分层']['type'],factors['土壤水平分层']['value'],level_points=[435,200,65,20,5]) # 土壤水平分层隶属度
    level4_4 = calc_membership_degree(factors['安全距离']['type'],factors['安全距离']['value']) # 安全距离隶属度
    level4_5 = calc_membership_degree(factors['相对高度']['type'],factors['相对高度']['value']) # 相对高度隶属度
    level4_6 = calc_membership_degree(factors['电磁环境']['type'],factors['电磁环境']['value'],level_points=[0.035,0.41,1.575,6.2,14.625]) # 电磁环境隶属度

    level3_4 = np.matmul(np.array([weights['土壤电阻率'],weights['土壤垂直分层'],weights['土壤水平分层']]).reshape(1,-1), np.concatenate([level4_1,level4_2,level4_3],axis=0)) # 土壤结构隶属度
    level3_5 = calc_membership_degree(factors['地形地貌']['type'],factors['地形地貌']['value']) # 地形地貌隶属度
    level3_6 = np.matmul(np.array([weights['安全距离'],weights['相对高度'],weights['电磁环境']]).reshape(1,-1), np.concatenate([level4_4,level4_5,level4_6],axis=0)) # 周边环境隶属度

    level2_2 = np.matmul(np.array([weights['土壤结构'],weights['地形地貌'],weights['周边环境']]).reshape(1,-1), np.concatenate([level3_4,level3_5,level3_6],axis=0)) # 地域风险隶属度

    #################################
    level4_7 = calc_membership_degree(factors['使用性质']['type'],factors['使用性质']['value']) # 使用性质隶属度
    level4_8 = calc_membership_degree(factors['人员数量']['type'],factors['人员数量']['value'],level_points=[50,200,650,2000,4350]) # 人员数量隶属度
    level4_9 = calc_membership_degree(factors['影响程度']['type'],factors['影响程度']['value']) # 影响程度隶属度
    level4_10 = calc_membership_degree(factors['占地面积']['type'],factors['占地面积']['value'],level_points=[1250,3750,6250,8750,12500]) # 占地面积隶属度
    level4_11 = calc_membership_degree(factors['材料结构']['type'],factors['材料结构']['value']) # 材料结构隶属度
    level4_12 = calc_membership_degree(factors['等效高度']['type'],factors['等效高度']['value'],level_points=[15,37.5,52.5,80,127.5]) # 等效高度隶属度
    level4_13 = calc_membership_degree(factors['电子系统']['type'],factors['电子系统']['value']) # 电子系统隶属度
    level4_14 = calc_membership_degree(factors['电气系统']['type'],factors['电气系统']['value']) # 电气系统隶属度

    level3_7 = np.matmul(np.array([weights['使用性质'],weights['人员数量'],weights['影响程度']]).reshape(1,-1), np.concatenate([level4_7,level4_8,level4_9],axis=0)) # 项目属性隶属度
    level3_8 = np.matmul(np.array([weights['占地面积'],weights['材料结构'],weights['等效高度']]).reshape(1,-1), np.concatenate([level4_10,level4_11,level4_12],axis=0)) # 建筑特征隶属度
    level3_9 = np.matmul(np.array([weights['电子系统'],weights['电气系统']]).reshape(1,-1), np.concatenate([level4_13,level4_14],axis=0)) # 电子电气系统隶属度

    level2_3 = np.matmul(np.array([weights['项目属性'],weights['建筑特征'],weights['电子电气系统']]).reshape(1,-1), np.concatenate([level3_7,level3_8,level3_9],axis=0)) # 承载体风险隶属度

    ################################
    level1 = np.matmul(np.array([weights['雷电风险'],weights['地域风险'],weights['承载体风险']]).reshape(1,-1), np.concatenate([level2_1,level2_2,level2_3],axis=0)) # 区域雷电灾害风险隶属度
    level1_norm = level1/np.sum(level1)
    level1_norm = level1_norm.round(3)

    g = (level1_norm[:,0] + level1_norm[:,1]*3 + level1_norm[:,2]*5 + level1_norm[:,3]*7 + level1_norm[:,4]*9).round(2)

    if 0<=g<2:
        risk = '低风险'

    elif 2<=g<4:
        risk = '较低风险'

    elif 4<=g<6:
        risk = '中等风险'
    
    elif 6<=g<8:
        risk = '较高风险'
    
    elif 8<=g<=10:
        risk = '高风险'
    
    # 隶属度结果输出df
    degree = np.concatenate([level1_norm,level2_1,level2_2,level2_3,
                             level3_2,level3_3,level3_4,level3_5,level3_6,level3_7,level3_8,level3_9,
                             level4_1,level4_2,level4_3,level4_4,level4_5,level4_6,level4_7,level4_8,level4_9,level4_10,level4_11,level4_12,
                             level4_13,level4_14],axis=0)
    degree = degree.round(3)
    degree_df = pd.DataFrame(degree)
    degree_df.index = ['区域雷电灾害风险','雷电风险','地域风险','承载体风险',
                       '雷击密度','雷电流强度','土壤结构','地形地貌','周边环境','项目属性','建筑特征','电子电气系统',
                       '土壤电阻率','土壤垂直分层','土壤水平分层','安全距离','相对高度','电磁环境','使用性质','人员数量','影响程度','占地面积','材料结构','等效高度','电子系统','电气系统']
    
    level1_norm=pd.DataFrame(level1_norm)
    level1_norm.columns=['I级','Ⅱ级','Ⅲ级','Ⅳ级','Ⅴ级']
    
    return g, risk, degree_df, level1_norm

# risk = calc_lightning_risk(factors, weights)