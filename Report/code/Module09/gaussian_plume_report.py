# -*- coding: utf-8 -*-
"""
Created on Mon Jul 29 14:33:02 2024

@author: EDY
"""


import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from docxtpl import DocxTemplate, InlineImage
import os
from Utils.config import cfg
from docx.shared import Mm
plt.rcParams['font.sans-serif'] = ['SimHei'] 
plt.rcParams['axes.unicode_minus'] = False 


# data_dir=r'D:\Project\3_项目\2_气候评估和气候可行性论证\qhkxxlz\Report\report\Module09'

def gaussian_plume_report(result_dict,result_dict_3d, lon, lat, q, h, wind_s, wind_d, z1, data_dir):

    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        
    doc_path=os.path.join(cfg['report']['template'],'Module09','gaussian_plume_report.docx')
    doc=DocxTemplate(doc_path)
    
    dic=dict()
    dic['lon']=lon
    dic['lat']=lat
    dic['h']= h
    dic['Q']=q
    dic['uv']=wind_s
    dic['uvdir']=wind_d
    dic['h_u']=z1
    
    dic['d1_picture'] = InlineImage(doc, result_dict['A强不稳定'], width=Mm(70))
    dic['d2_picture'] = InlineImage(doc, result_dict['B不稳定'], width=Mm(70))
    dic['d3_picture'] = InlineImage(doc, result_dict['C弱不稳定'], width=Mm(70))
    dic['d4_picture'] = InlineImage(doc, result_dict['D中性'], width=Mm(70))
    dic['d5_picture'] = InlineImage(doc, result_dict['E较稳定'], width=Mm(70))
    dic['d6_picture'] = InlineImage(doc, result_dict['F稳定'], width=Mm(70))

    dic['d11_picture'] = InlineImage(doc, result_dict_3d['A_3D强不稳定'], width=Mm(70))
    dic['d12_picture'] = InlineImage(doc, result_dict_3d['B_3D不稳定'], width=Mm(70))
    dic['d13_picture'] = InlineImage(doc, result_dict_3d['C_3D弱不稳定'], width=Mm(70))
    dic['d14_picture'] = InlineImage(doc, result_dict_3d['D_3D中性'], width=Mm(70))
    dic['d15_picture'] = InlineImage(doc, result_dict_3d['E_3D较稳定'], width=Mm(70))
    dic['d16_picture'] = InlineImage(doc, result_dict_3d['F_3D稳定'], width=Mm(70))


    # 模版文件读取写入字典
    doc.render(dic)
    # 保存结果到新的docx文件
    report=os.path.join(data_dir,'gaussian_plume_report.docx')
    doc.save(report)
    
    return report
