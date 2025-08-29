# -*- coding: utf-8 -*-
"""
Created on Thu May 30 15:24:02 2024

@author: EDY
"""

import os
from docx import Document
from docxcompose.composer import Composer

original_docx_path = "D:\\Project\\3_项目\\2_气候评估和气候可行性论证\\qhkxxlz\\Report\\report\\Module02\\"
new_docx_path = "D:\\Project\\3_项目\\2_气候评估和气候可行性论证\\qhkxxlz\\Report\\report\\merged1_doc.docx"

# 过滤出所有Word文档
all_word = [file for file in os.listdir(original_docx_path) if file.endswith('.docx')]
all_file_path = [os.path.join(original_docx_path, file) for file in all_word]

try:
    master = Document(all_file_path[0])
    middle_new_docx = Composer(master)
    for word in all_file_path[1:]:  # 从第二个文档开始追加
        word_document = Document(word)
        # 删除手动添加分页符的代码
        middle_new_docx.append(word_document)
    middle_new_docx.save(new_docx_path)
except Exception as e:
    print(f"发生错误：{e}")
