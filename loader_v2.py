import re
import requests
from lxml import etree
import os


class Log:
    logTxt = ""
    logFile = "log.txt"

    def __init__(self, logFile="log.txt"):
        self.logFile = logFile
        self.logTime()

    # 日志
    def logError(self, title='标题', *strArg):
        self.logTxt = self.logTxt + "=============" + title + "====================\n"
        for i in strArg:
            self.logTxt = self.logTxt + "==   " + i + "\n"
        self.logTxt = self.logTxt + "====================================\n"

    def logWarn(self, title='标题', *strArg):
        self.dbLog("------------------" + title + "------------------------------------------")
        for i in strArg:
            self.dbLog("--   " + i)
        self.dbLog("-------------------------------------------------------------------")

    def log(self, strArg):
        print(strArg)

    def dbLog(self, strArg):
        strArg = str(strArg)
        print(strArg)
        self.logTxt = self.logTxt + strArg + "\n"

    def dbPrint(self, strArg):
        print(strArg)
        self.logTxt = self.logTxt + "==   " + strArg + "\n"

    def logRead(self, url):
        self.dbLog("读取链接   -->   " + url)

    def logSave(self, file, url='', type="default", fn="undefined"):
        if url == '':
            self.dbLog("保存文件(" + fn + ")   " + type + "   " + file)
        else:
            self.dbLog("保存文件(" + fn + ")   " + type + "   " + url + "   ==》   " + file)

    def logTime(self):
        import time
        struct_time = time.localtime(time.time())
        timeStr = time.strftime("%Y-%m-%d %H:%M:%S", struct_time)
        self.logTxt = "log    " + timeStr + "\n"

    def logEnd(self):
        print(self.logTxt, file=open(self.logFile, "w"))


log = Log()


class LoadPool:
    def __init__(self, maxUrlLength=400):
        self.links = set()
        self.files = set()
        self.maxUrlLength = maxUrlLength

    def checkLink(self, link):
        return link not in self.links

    def loadedLink(self, link):
        self.links.add(link)

    def checkFile(self, file):
        return file not in self.files

    def loadedFile(self, file):
        self.files.add(file)


pool = LoadPool()


class FN:
    fontFileSuffix = (
        "eot", "woff2", "woff", "ttf"
    )

    imgFileSuffix = {
        "ico", "gif", "cur", "png", "jpg", "jpeg", "webp"
    }

    binaryFileSuffix = (
        "eot", "woff2", "woff", "ttf",
        "ico", "gif", "cur", "png", "jpg", "jpeg", "webp"
    )

    commonFileSuffix = ("svg", "html", "js", "css")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    def __init__(self, maxSize=300):
        self.maxSize = maxSize

    def xpathMatch(self, context, xPathStr):
        matches = []
        html = etree.HTML(context)
        if html is not None:
            for match in html.xpath(xPathStr):
                if self.isUrl(match) and pool.checkLink(match):
                    matches.append(match)
        return matches

    def unionUrl(self, home="", prefix="", suffix="", fileType="default"):
        # 规范化路径，\\变为/
        if re.match(r'\\', home):
            home = home.replace("\\", "/")
        if re.match(r'\\', prefix):
            prefix = prefix.replace("\\", "/")
        if re.match(r'\\', suffix):
            suffix = suffix.replace("\\", "/")

        # 路径前缀不以/结尾
        while re.match(r'/$', prefix):
            prefix = prefix[:-1]

        res = {
            "fileType": fileType
        }

        if re.match(r'^tpa', fileType):
            res["suffix"] = suffix
            if re.match(r'^\./', prefix):
                res["prefix"] = prefix[1:]
                res["home"] = home
                return res

            elif re.match(r'^\.\./', prefix):
                prefix = prefix[prefix.find('/') + 1:]
                home = home[:home.rfind('/')]
                return self.unionUrl(prefix=prefix, home=home, suffix=suffix, fileType=fileType)

            elif re.match(r'^\w+', prefix):
                res["prefix"] = "/" + prefix
                res["home"] = home
                return res

            elif re.match(r'^/[^/]+', prefix):
                res["prefix"] = prefix
                res["home"] = home
                return res

            else:
                res["prefix"] = prefix
                res["home"] = home
                res["fileType"] = "false"
                log.logWarn("tpa匹配失败(prefix, home, suffix, fileType)", prefix, home, suffix, fileType)
                return res
        else:
            if re.match(r'^\./', suffix):
                res["prefix"] = prefix
                res["home"] = home
                res["suffix"] = suffix[1:]
                return res

            elif re.match(r'^\.\./', suffix):
                suffix = suffix[suffix.find('/') + 1:]
                home = home[:home.rfind('/')]
                prefix = prefix[:prefix.rfind('/')]
                return self.unionUrl(prefix=prefix, home=home, suffix=suffix, fileType=fileType)

            elif re.match(r'^(http://)|(https://)', suffix):
                res["prefix"] = prefix
                res["home"] = home
                res["suffix"] = suffix
                res["fileType"] = "false"
                log.logWarn("网络链接,无需下载(prefix, home, suffix, fileType)", prefix, home, suffix, fileType)
                return res

            elif re.match(r'^\w+', suffix):
                res["prefix"] = prefix
                res["home"] = home
                res["suffix"] = "/" + suffix
                return res

            elif re.match(r'^/[^/]+', suffix):
                res["prefix"] = prefix
                res["home"] = home
                res["suffix"] = suffix
                return res

            else:
                res["prefix"] = prefix
                res["home"] = home
                res["suffix"] = suffix
                res["fileType"] = "false"
                log.logWarn("匹配失败(prefix, home, suffix, fileType)", prefix, home, suffix, fileType)
                return res

    def simpleUrl(self, res):
        home = res["home"]
        prefix = res["prefix"]
        suffix = res["suffix"]
        fileType = res["fileType"]

        if fileType == "false":
            return res
        if re.match(r'^tpa', fileType):
            if prefix.find("/", 1) > 0:
                change = prefix[:prefix.rfind('/')]
                res["prefix"] = prefix[prefix.rfind('/'):]
                res["home"] = home + change
        else:
            if suffix.find("/", 1) > 0:
                change = suffix[:suffix.rfind('/')]
                res["suffix"] = suffix[suffix.rfind('/'):]
                res["home"] = home + change
                res["prefix"] = prefix + change

        # if re.match(r"[+';#]", res["suffix"]) or re.match(r"[+';#]", res["prefix"]):
        #     res["fileType"] = "false"
        #     log.logError("链接中含有+';#特殊字符,链接被忽略")

        return res

    def unionFilePath(self, file):
        if (not 0 < len(file) <= self.maxSize) or file.find(fileHome) == -1:
            return ""
        if re.match(r'\\', file):
            file = file.replace("\\", "/")

        specialStrs = ("?", "-t=", "-#iefix")
        for specialStr in specialStrs:
            if file.find(specialStr) != -1:
                file = file[:file.rfind(specialStr)]

        return file

    def isUrl(self, url):
        return 0 < len(url) <= self.maxSize

    def isNetUrl(self, url):
        return re.match(r'^(http://)|(https://)', url)

    def saveBinaryFile(self, url, file, type="default"):
        self.mkdirByFilePath(file)

        file = self.unionFilePath(file=file)
        if file == "":
            return

        file_suffix = file[file.rfind('.') + 1:]

        if file_suffix in self.commonFileSuffix:
            self.saveCommonFile(url=url, file=file, type=type)

        elif file_suffix in self.binaryFileSuffix:
            log.logSave(file, url, type=type, fn="saveBinaryFile")
            res = self.get(url)
            if res:
                res.encoding = res.apparent_encoding
                with open(file, "wb") as file_obj:
                    file_obj.write(res.content)
            else:
                log.logError("保存文件失败(url, file, type, fn)", url, file, type, "saveBinaryFile")
        else:
            log.logWarn("类型无法识别,强制保存(url, file, type, fn)", url, file, type, "saveBinaryFile")
            res = self.get(url)
            if res:
                res.encoding = res.apparent_encoding
                with open(file, "wb") as file_obj:
                    file_obj.write(res.content)
            else:
                log.logError("保存文件失败(url, file, type, fn)", url, file, type, "saveBinaryFile")

    def saveCommonFile(self, url, file, type="default"):
        self.mkdirByFilePath(file)
        file = self.unionFilePath(file=file)
        if file == "":
            return

        file_suffix = file[file.rfind('.') + 1:]
        if file_suffix in self.commonFileSuffix:
            log.logSave(file, url, type=type, fn="saveCommonFile")
            res = self.get(url)
            if res:
                with open(file, "w", encoding=encode) as file_obj:
                    file_obj.write(res.text)
            else:
                log.logError("保存文件失败(url, file, type, fn)", url, file, type, "saveCommonFile")
        elif file_suffix in self.binaryFileSuffix:
            self.saveBinaryFile(url=url, file=file, type=type)

        else:
            log.logWarn("类型无法识别,强制保存(url, file, type, fn)", url, file, type, "saveCommonFile")
            res = self.get(url)
            if res:
                with open(file, "w", encoding=encode) as file_obj:
                    file_obj.write(res.text)
            else:
                log.logError("保存文件失败(url, file, type, fn)", url, file, type, "saveCommonFile")

    def saveCommonFileWithContext(self, file="", context="", url="", type="default"):
        self.mkdirByFilePath(file)
        file = self.unionFilePath(file=file)
        if file == "":
            return
        file_suffix = file[file.rfind('.') + 1:]
        if file_suffix in self.commonFileSuffix:
            log.logSave(file, type=type, fn="saveCommonFileWithContext")
            with open(file, "w", encoding=encode) as file_obj:
                file_obj.write(context)
        elif file_suffix in self.binaryFileSuffix:
            self.saveBinaryFile(url=url, file=file, type=type)
        else:
            log.logWarn("类型无法识别,强制保存(url, file, type, fn)", url, file, type, "saveCommonFileWithContext")
            log.logSave(file, type=type, fn="saveCommonFileWithContext")
            with open(file, "w", encoding=encode) as file_obj:
                file_obj.write(context)

    def get(self, url):
        log.logRead(url)
        res = requests.get(url=url, headers=self.headers)
        if res.status_code == 404:
            log.logError("404", url)
            return False
        return res

    def mkdirByFilePath(self, file):
        dir = file[:file.rfind('/')]
        try:
            if not os.path.exists(dir):
                os.makedirs(dir)
        except NotADirectoryError:
            log.logError("NotADirectoryError(dir)", dir)
        except FileNotFoundError:
            log.logError("FileNotFoundError(dir)", dir)


fn = FN()

'''
需要解析的文件类型：
1,普通的上下级关系（html文件）
    下级文件类型：html、css、img
2,html引用类型（img）
    下级文件类型：none
3,html引用类型（css）
    下级文件类型：font文件：css文件
4,font文件类型
    下级文件类型：无
-------------------路径要求-------------------
目录没有\\
前缀目录不以/结束
后缀目录以/开始
-------------------ImgFile-----------------
fileType:(net,local)
1.net 
(base:64)
(http)
2.local(default)
(正常前后缀关系)
------------------------------------
tpa文件
prefix：目录的后置路劲
home:目录的前置路径 
suffix：网络连接


其他文件
prefix：网络连接的前置路劲
home:目录的前置路径 
suffix：目录的后置路劲
    
'''


class JsFile:
    context = ''

    def __init__(self, home="", prefix="", suffix="", fileType="js"):
        if fileType == "false":
            return
        res = fn.simpleUrl(fn.unionUrl(home=home, prefix=prefix, suffix=suffix, fileType=fileType))
        if res["fileType"] == "false":
            return
        self.prefix = res["prefix"]
        self.suffix = res["suffix"]
        self.home = res["home"]
        self.fileType = res["fileType"]
        self.load()

    def load(self):
        self.save()
        self.loadchildren()

    def save(self):
        url = self.prefix + self.suffix
        file = self.home + self.suffix
        if pool.checkLink(url) and pool.checkFile(file):
            res = fn.get(url)
            if res:
                self.context = res.text
                fn.saveCommonFileWithContext(context=self.context, file=file, type=self.fileType, url=url)
                pool.loadedLink(url)
                pool.loadedFile(file)

    def loadchildren(self):
        # img文件
        self.context = str(self.context)
        for imgLink in re.findall(r'url\("([^"]*)"', self.context):
            ImgFile(self.home, self.prefix, imgLink, fileType="js_img")


class ImgFile:
    def __init__(self, home="", prefix="", suffix="", fileType="img"):
        if fileType == "false":
            return
        res = fn.simpleUrl(fn.unionUrl(home=home, prefix=prefix, suffix=suffix, fileType=fileType))
        if res["fileType"] == "false":
            return
        self.prefix = res["prefix"]
        self.suffix = res["suffix"]
        self.home = res["home"]
        self.fileType = res["fileType"]
        self.load()

    def load(self):
        self.save()
        self.loadchildren()

    def save(self):
        url = self.prefix + self.suffix
        file = self.home + self.suffix
        if re.match(r'^tpa', self.fileType):
            file = self.home + self.prefix
            url = self.suffix
        if pool.checkLink(url) and pool.checkFile(file):
            fn.saveBinaryFile(url=url, file=file, type=self.fileType)
            pool.loadedLink(url)
            pool.loadedFile(file)

    def loadchildren(self):
        return


class CssFile:
    context = ""

    def __init__(self, home="", prefix="", suffix="", fileType="css"):
        if fileType == "false":
            return
        res = fn.simpleUrl(fn.unionUrl(home=home, prefix=prefix, suffix=suffix, fileType=fileType))
        if res["fileType"] == "false":
            return
        self.prefix = res["prefix"]
        self.suffix = res["suffix"]
        self.home = res["home"]
        self.fileType = res["fileType"]
        self.load()

    def load(self):
        self.save()
        self.loadchildren()

    def save(self):
        url = self.prefix + self.suffix
        file = self.home + self.suffix
        if re.match(r'^tpa', self.fileType):
            file = self.home + self.prefix
            url = self.suffix
        if pool.checkLink(url) and pool.checkFile(file):
            res = fn.get(url)
            if res:
                self.context = res.text
                fn.saveCommonFileWithContext(context=self.context, file=file, type=self.fileType, url=url)
                pool.loadedLink(url)
                pool.loadedFile(file)

    def loadchildren(self):
        if self.context == "":
            return

        # img文件
        self.context = str(self.context)
        for imgLink in re.findall(r'background: url\("([^"]*)"[^/]+', self.context):
            ImgFile(self.home, self.prefix, imgLink, fileType="img")

        for imgLink in re.findall(r'background-image: url\("([^"]*)"[^/]+', self.context):
            ImgFile(self.home, self.prefix, imgLink, fileType="img")

        for imgLink in re.findall(r'content: url\("([^"]*)"[^/]+', self.context):
            ImgFile(self.home, self.prefix, imgLink, fileType="img")

        # css文件
        for imgLink in re.findall(r'@import url\("([^"]*)"[^/]+', self.context):
            CssFile(self.home, self.prefix, imgLink, fileType="css")

        for imgMatch in re.findall(r'@import url\("([^"]*)"/\*tpa=([^"]*?)\*/\)', self.context):
            prefix = imgMatch[0]
            suffix = imgMatch[1]
            CssFile(self.home, prefix, suffix, fileType="tpa_img")

        # font文件
        for fontMatch in re.findall(r'url\("([^"]*)"/\*tpa=([^"]*?)\*/\)', self.context):
            prefix = fontMatch[0]
            suffix = fontMatch[1]
            for fileSuffix in fn.fontFileSuffix:
                if suffix.find("." + fileSuffix) != -1:
                    FontFile(self.home, prefix, suffix, fileType="tpa_font")
                    break


class FontFile:
    def __init__(self, home="", prefix="", suffix="", fileType="font"):
        if fileType == "false":
            return
        res = fn.simpleUrl(fn.unionUrl(home=home, prefix=prefix, suffix=suffix, fileType=fileType))
        if res["fileType"] == "false":
            return
        self.prefix = res["prefix"]
        self.suffix = res["suffix"]
        self.home = res["home"]
        self.fileType = res["fileType"]
        self.load()

    def load(self):
        self.save()
        self.loadchildren()

    def save(self):
        url = self.prefix + self.suffix
        file = self.home + self.suffix
        if re.match(r'^tpa', self.fileType):
            file = self.home + self.prefix
            url = self.suffix
        if pool.checkLink(url) and pool.checkFile(file):
            fn.saveBinaryFile(url=url, file=file, type=self.fileType)
            pool.loadedLink(url)
            pool.loadedFile(file)

    def loadchildren(self):
        return


class HtmlFile:
    context = ''

    def __init__(self, home="", prefix="", suffix="", fileType="html"):
        if fileType == "false":
            return
        res = fn.simpleUrl(fn.unionUrl(home=home, prefix=prefix, suffix=suffix, fileType=fileType))
        if res["fileType"] == "false":
            return
        self.prefix = res["prefix"]
        self.suffix = res["suffix"]
        self.home = res["home"]
        self.fileType = res["fileType"]
        self.load()

    def load(self):
        self.save()
        self.loadchildren()

    def save(self):
        url = self.prefix + self.suffix
        file = self.home + self.suffix
        if not (pool.checkLink(url) and pool.checkFile(file)):
            return False
        self.context = fn.get(url).text
        pool.loadedLink(url)
        fn.saveCommonFile(url=url, file=file, type=self.fileType)
        pool.loadedFile(file)

    def loadchildren(self):

        if self.context == '':
            return

        cssXpaths = ("//link/@href",)
        htmlXpaths = ("//a/@href",)
        jsXpaths = ("//script/@src",)

        for cssXpath in cssXpaths:
            for cssLink in fn.xpathMatch(self.context, cssXpath):
                if cssLink.find("favicon.ico") != -1:
                    ImgFile(self.home, self.prefix, cssLink, fileType="img")
                else:
                    CssFile(self.home, self.prefix, cssLink, fileType="css")

        for jsXpath in jsXpaths:
            for jsLink in fn.xpathMatch(self.context, jsXpath):
                JsFile(self.home, self.prefix, jsLink, fileType="js")

        for htmlXpath in htmlXpaths:
            for htmlLink in fn.xpathMatch(self.context, htmlXpath):
                HtmlFile(self.home, self.prefix, htmlLink, fileType="html")

        imgXpaths = ("//img/@src",)

        for imgXpath in imgXpaths:
            for imgLink in fn.xpathMatch(self.context, imgXpath):
                ImgFile(self.home, self.prefix, imgLink, fileType="img")

        for imgMatch in re.findall(r'url\("([^"]*)"/\*tpa=([^"]*?)\*/\)', self.context):
            prefix = imgMatch[0]
            suffix = imgMatch[1]
            ImgFile(self.home, prefix, suffix, fileType="tpa_html_img")

        for imgLink in re.findall(r'url\("([^"]*)"[^/]+', self.context):
            ImgFile(self.home, self.prefix, imgLink, fileType="img")

    def start(self, fileHome="D:/desktop/runtime/pythonLoader/test/test", indexUrl=""):
        self.prefix = indexUrl[:indexUrl.rfind('/')]
        self.suffix = indexUrl[indexUrl.rfind('/'):]
        self.home = fileHome
        self.fileType = "html"
        self.load()


encode = 'utf-8'

indexUrl = "http://demo.uu2018.com/962/index.html"

fileHome = "D:/desktop/runtime/pythonLoader/txt/editor2"

HtmlFile(fileType='html').start(fileHome=fileHome, indexUrl=indexUrl)

# HtmlFile(fileType='false').start(indexUrl=indexUrl)

log.logEnd()
