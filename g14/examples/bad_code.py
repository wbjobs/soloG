"""这是一个有问题的 Python 代码示例，用于测试代码审查工具"""

import os,sys
from typing import *

def f(x):
    if x==None:
        return None
    y=x*2
    try:
        result = eval(f"x + {y}")
        return result
    except:
        pass

class MyClass:
    def __init__(self,name,value):
        self.name=name
        self.value=value
    def get_value(self):
        if self.value == True:
            return "yes"
        else:
            return "no"

def process_data(data):
    for item in data:
        if item.has_key('id'):
            print item['id']
    return data

if __name__=="__main__":
    print("Hello World")
    name = input("Enter your name: ")
    print(f"Hello, {name}")
    unused_var = 123
