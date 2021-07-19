import re
import time
import requests
from lxml import etree
import os

# 解析源代码中引用的其他的项目文件
def pageFn(context):
    global pool
    res = []
    xPathStrs = [
        ("//script/@src", 'js'),
        ("//img/@src", 'img'),
        ("//link/@href", 'css'),
        ("//a/@href", 'html')
    ]
    for xPathStr in xPathStrs:
        html = etree.HTML(context)
        if html is not None:
            for i in html.xpath(xPathStr[0]):
                if i not in pool:
                    pool.add(i)
                    temp = {
                        "type": xPathStr[1],
                        "url": i
                    }
                    res.append(temp)
    # print(re.findall(r'url\(".*"/\*tpa=(.*)\*/\)', context))
    # print(re.findall(r'url\("([^"]*)"/\*tpa=(.*)\*/\)', context))
    for i in re.findall(r'url\(".*"/\*tpa=(.*)\*/\)',context):
        if i not in pool:
            pool.add(i)
            temp = {
                "type": "fontFiles",
                "url": i
            }
            res.append(temp)

    for i in re.findall(r'url\("([^"]*)"', context):
        if not re.findall(r'-t=',context) and i not in pool:
            pool.add(i)
            temp = {
                "type": "urlFile",
                "url": i
            }
            res.append(temp)
    return res


# 将路径中的特殊字符，解析为可用的链接
def srcFN(srcPath, loadPath, nextPath,type=''):

    res = {
        "load": True
    }

    if re.findall(r'\\', loadPath):
        loadPath = loadPath.replace("\\", "/")
    if re.findall(r'/$', loadPath):
        loadPath = loadPath[:-1]
    if re.findall(r'/$', srcPath):
        srcPath = srcPath[:-1]

    if re.match(r'^\./', nextPath):
        res["srcPath"] = srcPath
        res["loadPath"] = loadPath
        res["nextPath"] = nextPath[1:]
        return res

    elif re.match(r'^\.\./', nextPath):
        nextPath = nextPath[nextPath.find('/') + 1:]
        loadPath = loadPath[:loadPath.rfind('/')]
        srcPath = srcPath[:srcPath.rfind('/')]
        return srcFN(srcPath, loadPath, nextPath)

    elif re.match(r'^(http://)|(https://)', nextPath):
        if type == "fontFiles":
            res["srcPath"] = nextPath[:nextPath.rfind('/')]
            res["loadPath"] = loadPath
            res["nextPath"] = nextPath[nextPath.rfind('/'):]
            return res
        res["load"] = False
        res["srcPath"] = srcPath
        res["loadPath"] = loadPath
        res["nextPath"] = nextPath
        return res

    elif re.match(r'^\w+', nextPath):
        res["srcPath"] = srcPath
        res["loadPath"] = loadPath
        res["nextPath"] = "/" + nextPath
        return res

    elif re.match(r'^/', nextPath):
        res["srcPath"] = srcPath
        res["loadPath"] = loadPath
        res["nextPath"] = nextPath
        return res

    else:
        res["load"] = False
        res["srcPath"] = srcPath
        res["loadPath"] = loadPath
        res["nextPath"] = nextPath
        print("------------------匹配失败------------------------------------------")
        print("--   srcPath = " + srcPath)
        print("--   loadPath = " + loadPath)
        print("--   nextPath = " + nextPath)
        print("-------------------------------------------------------------------")
        print()
        return res


# 标准化路径，使nextPath只有一层结构
def srcResFN(res):
    srcPath = res["srcPath"]
    loadPath = res["loadPath"]
    nextPath = res["nextPath"]
    count = nextPath.count('/', 1)
    if count:
        change = nextPath[:nextPath.rfind('/')]
        res["nextPath"] = nextPath[nextPath.rfind('/'):]
        res["loadPath"] = loadPath + change
        res["srcPath"] = srcPath + change
    if re.findall(r"[+';#]", res["nextPath"]):
        res["load"] = False
    return res


# 保存文件
def saveFileFn(url, file, type, content=''):

    if re.findall(r'\\', file):
        file = file.replace("\\", "/")
    if re.findall(r'[?]', file):
        file = file[:file.rfind('?')]
    if re.findall(r'[#]', file):
        file = file[:file.rfind('#')]
    if re.findall('-t=', file):
        file = file[:file.rfind('-t=')]
    if file.find("?", 0, 1) != -1:
        file = file[:file.find("?", 0, 1)]
    if file.find("&", 0, 1) != -1:
        file = file[:file.find("&", 0, 1)]

    dir = file[:file.rfind('/')]
    if not os.path.exists(dir):
        os.makedirs(dir)

    print("保存文件   -->   " + file)
    global error
    error = error + "保存文件   -->   " + file + "\n"

    if type in notTextFile:
        res = requests.get(url)
        res.encoding = res.apparent_encoding
        with open(file, "wb") as file_obj:
            file_obj.write(res.content)

    elif len(content) > 1:
        with open(file, "w", encoding=encode) as file_obj:
            file_obj.write(content)

    else:
        res = requests.get(url)
        res.encoding = res.apparent_encoding
        with open(file, "w", encoding=encode) as file_obj:
            file_obj.write(res.text)


# 源代码类
class Page:
    def __init__(self, srcPath, loadPath, nextPath, type="url"):
        self.srcPath = srcPath
        self.loadPath = loadPath
        self.nextPath = nextPath
        self.type = type

    def load(self):
        global error
        try:
            url = self.srcPath + self.nextPath
            file = self.loadPath + self.nextPath
            error = error + "读取url   -->   " + url + "\n"
            res = requests.get(url=url)
            res.encoding = res.apparent_encoding
            content = res.text
            saveFileFn(url, file, self.type, content=content)
            for nextPath in pageFn(content):
                self.type = nextPath["type"]
                res = srcResFN(srcFN(self.srcPath, self.loadPath, nextPath["url"],self.type))
                if res["load"]:
                    Page(res["srcPath"], res["loadPath"], res["nextPath"]).load()
                    url = res["srcPath"] + res["nextPath"]
                    file = res["loadPath"] + res["nextPath"]
                    saveFileFn(url, file, self.type)
        except NotADirectoryError:
            print("==============错误================")
            print("==   " + self.srcPath + self.nextPath)
            print("=================================")
            error = error + "=============错误====================\n"
            error = error + "==   " + str(self.srcPath) + "\n"
            error = error + "==   " + str(self.nextPath) + "\n"
            error = error + "==   " + str(self.srcPath + self.nextPath) + "\n"
            error = error + "====================================\n"


def start():
    global indexUrl
    global fileHome
    srcPath = indexUrl
    loadPath = fileHome
    nextPath = srcPath[srcPath.rfind('/'):]
    srcPath = srcPath[:srcPath.rfind('/')]
    Page(srcPath, loadPath, nextPath).load()


encode = 'utf-8'

# 访问的链接的集合，避免重复访问，闭环重复
pool = set()
# 需要用二进制保存的文件类型
notTextFile = ('img', 'mp3')



struct_time = time.localtime(time.time())
timeStr = time.strftime("%Y-%m-%d %H:%M:%S", struct_time)
error = "log    " + timeStr + "\n"


indexUrl = "http://demo.uu2018.com/962/index.html"

fileHome = "D:/desktop/runtime/pythonLoader/txt/editor2"

start()

# 日志保存，可注释
print(error, file=open("log.txt", "w"))
