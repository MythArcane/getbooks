from io import BufferedWriter
from math import ceil
from typing import List, Tuple
import requests, time, os, threading, json
from bs4 import BeautifulSoup

class GetBooks():
    def __init__(self) -> None:
        self.headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Cache-Control': 'max-age=0',
            'Cookie': 'fontcolor=%23000; Hm_lvt_de8213d0318263e9f4609fc88082f6e5=1652520319; Hm_lpvt_de8213d0318263e9f4609fc88082f6e5=1652707254',
            'Host': 'www.biququ.com',
            'Proxy-Connection': 'keep-alive',
            'Referer': 'http://www.biququ.com/html/50050/',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.54 Safari/537.36'
        }
        self.url = 'http://www.biququ.com/'

        # 章节分隔符
        self.splitChapter = '\n\n'

        # 线程锁
        self.threadLock = threading.Lock()

        # 参数，第一个为'http://www.biququ.com/html/50050/'中的50050，可变
        #       第二个为leaveCount，遇到404时加1
        #       第三个为allCount，总计爬了多少本小说
        #       第四个为时间参数，可计算总耗时
        self.parameters = [1, 0, 0, time.perf_counter()]

        self.chapters = []
        self.links = []
        self.failList = []
        self.failListIndex = []

        # 第一个参数为下载章节数量，不论失败与否。
        # 第二个参数只有当处于下载失败章节的时候，此参数代表失败章节数量，否则无意义
        # 第三个参数为线程结束任务数
        self.chapterParamters = [0, 0, 0]

        # 获取章节目录失败时变为True
        self.getCatalogFail: bool = False
        self.finish: bool = True
        self.processBar: int = 100
        self.allChapterNum: int = 0

    # 根据当前页面返回下一章的url
    # 如果爬不到，可以采用模拟点击下一章按钮规避
    def getNextUrl(self, content: str):
        pass

    # 获取小说目录
    def getCatalog(self, targetUrl: str, name: str, mode='download') -> Tuple[List[str], List[str]]:
        if mode not in ['download', 'update']:
            raise ValueError

        response = requests.get(targetUrl, headers=self.headers)
        if response.status_code != 200:
            self.getCatalogFail = True
            return None, None
        
        chapters = []
        links = []
        data = response.text
        soup = BeautifulSoup(data, "html.parser")
        each = soup.dd
        chapters.append(each.text)
        links.append(each.a['href'])
        while True:
            each = each.next_sibling.next_sibling
            if each is None:
                break
            chapters.append(each.text)
            links.append(each.a['href'])
        assert(len(chapters) == len(links))

        # 封装下载小说的目录信息，以便更新方便
        if mode == 'download':
            print('需要爬取{}章'.format(len(chapters)))
            if os.path.exists('./updateSettings.json') and os.path.getsize('./updateSettings.json') != 0:
                with open('updateSettings.json') as f:
                    updateSettings: dict = json.loads(f.read())
                flag = False
                for each in updateSettings.keys():
                    if updateSettings[each]['name'] == name:
                        updateSettings[each]['chapterNumber'] = len(links)
                        flag = True
                        break
                if not flag:
                    updateSettings[max([int(i) for i in updateSettings.keys()])+1] = {'name': name, 'chapterName': chapters[-1], 'chapterNumber': len(chapters)}
                with open('updateSettings.json', 'w') as f:
                    json.dump(updateSettings, f)
            else:
                with open('updateSettings.json', 'w') as f:
                    updateSettings = {1: {'name': name, 'chapterName': chapters[-1], 'chapterNumber': len(chapters)}}
                    json.dump(updateSettings, f)

        return chapters, links

    # 获取小说章节内容
    # 没有使用代理池，所以设置了间隔时间
    def getChapter(self, name: str, threadNum=10, maxtry=5):
        self.allChapterNum: int = len(self.chapters)
        os.mkdir('./tmp/{}'.format(name))
        if maxtry < 5:
            threadList = [threading.Thread(target=self.getChapterThread, args=(time.perf_counter(), name, True)) for _ in range(threadNum)]
        else:
            threadList = [threading.Thread(target=self.getChapterThread, args=(time.perf_counter(), name, False)) for _ in range(threadNum)]
        for each in threadList:
            each.start()
        while self.chapterParamters[2] != threadNum:
            pass
        time.sleep(1)
        
        if len(self.failList) > 0 and maxtry > 0:
            self.processFail()
            self.getChapter(name, threadNum if len(self.links) > 10 else len(self.links), maxtry-1)
        if maxtry != 5:
            return
        
        if len(self.failList) == 0:
            print('\n成功下载{}章，失败0章'.format(self.allChapterNum))
        else:
            print('\n成功下载{}章，失败{}章，章节名为：'.format(self.allChapterNum - len(self.failList), len(self.failList)))
            for each in self.failList:
                print(each)

    def getChapterThread(self, *args):
        f: BufferedWriter = None
        t: float = args[0]
        filename: str = args[1]
        hasFailListIndex = args[2]

        while True:
            # 处于有爬取失败章节的状态
            if hasFailListIndex:
                with self.threadLock:
                    # 通过processFail预设了在 一次重新下载失败章节 的时候的数量，不会将在这一次重新下载失败章节的再次失败的章节再次下载。
                    # 同时通过每次取index时使用pop将原本的失败章节给移出列表
                    if self.chapterParamters[0] >= self.chapterParamters[1]:
                        self.chapterParamters[2] += 1
                        return
                    index = self.failListIndex.pop(0)
                    self.failList.pop()
                    self.chapterParamters[0] += 1
                f = open('./tmp/{}/{}.txt'.format(filename, index), 'wb')
            else:
                with self.threadLock:
                    if self.chapterParamters[0] >= len(self.chapters):
                        self.chapterParamters[2] += 1
                        return
                    index = self.chapterParamters[0]
                    self.chapterParamters[0] += 1
                f = open('./tmp/{}/{}.txt'.format(filename, index), 'wb')
            try:
                response = requests.get(self.url + self.links[index], self.headers)
            except:
                print('爬取{}章节失败，已留空！'.format(self.chapters[index]))
                f.write((self.chapters[index] + self.splitChapter).encode())
                self.failList.append(self.chapters[index])
                self.failListIndex.append(index)
                f.close()
                continue
            if response.status_code != 200:
                print('爬取{}章节失败，已留空！'.format(self.chapters[index]))
                f.write((self.chapters[index] + self.splitChapter).encode())
                self.failList.append(self.chapters[index])
                f.close()
                continue
            
            soup = BeautifulSoup(response.text, "html.parser")
            data = soup.find_all('p')

            f.write((self.chapters[index] + '\n').encode())
            for each in data:
                if each.a is None and each.parent.attrs.get('id', None) == 'content':
                    # print(each.text)
                    f.write((each.text + '\n').encode())
            f.write(self.splitChapter.encode())
            print('爬取 {} 成功，还剩{}章，总计耗时{:.2f}秒。'.format(self.chapters[index], len(self.links)-index-1, time.perf_counter()-t))
            with self.threadLock:
                self.processBar = max(self.processBar, ceil(((len(self.links)-index-1)/self.allChapterNum)*100))
            f.close()

            time.sleep(0.1)

    def mergePart(self, name: str):
        print('Start merge!')
        path = './tmp/{}/'.format(name)
        if not os.path.exists(path):
            print('未能成功下载小说')
            return
        f = open('./books/{}.txt'.format(name), 'ab')
        for i in range(len(self.chapters)):
            tmpPath = path + str(i) + '.txt'
            with open(tmpPath, 'rb') as f1:
                data = f1.read()
            f.write(data)
            f.flush()
        f.close()
        print('Finish merge!')

    def removePart(self, name: str):
        path = './tmp/{}/'.format(name)
        if not os.path.exists(path):
            return
        for i in range(len(self.chapters)):
            tmpPath = path + str(i) + '.txt'
            os.remove(tmpPath)
        os.rmdir(path)

    def processFail(self):
        self.chapterParamters = [0, len(self.failList), 0]

    def getWebsiteCatalogThread(self):
        url = 'http://www.biququ.com/'
        url = url + 'html/'
        headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Cache-Control': 'max-age=0',
        'Cookie': 'fontcolor=%23000; Hm_lvt_de8213d0318263e9f4609fc88082f6e5=1652520319; Hm_lpvt_de8213d0318263e9f4609fc88082f6e5=1652707254',
        'Host': 'www.biququ.com',
        'Proxy-Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.54 Safari/537.36'
        }
        f = open('catalogThread.txt', 'a')
        while True:
            self.threadLock.acquire()
            tmpUrl = url + str(self.parameters[0])
            now_page = self.parameters[0]
            self.parameters[0] += 1
            self.threadLock.release()
            response = requests.get(tmpUrl, headers=headers)
            if response.status_code == 404:
                self.parameters[1] += 1
                # parameters[2] -= 1
                if self.parameters[1] > 100:
                    break
                continue
            self.parameters[1] = 0
            self.parameters[2] += 1
            print('爬到第{}本小说，目前序号为：{}，总耗时{:.2f}分钟'.format(self.parameters[2], now_page, (time.perf_counter()-self.parameters[3])/60))
            data = response.text
            soup = BeautifulSoup(data, "html.parser")
            for each in soup.find_all('meta'):
                if each.attrs.get('name', None) == 'keywords':
                    self.threadLock.acquire()
                    f.write('{}、{}\n'.format(now_page, each.attrs['content']))
                    f.flush()
                    self.threadLock.release()
                    break
            time.sleep(0.1)

    def test(self):
        del self.headers['Referer']
        response = requests.get(self.url + 'html/1', headers=self.headers)
        with open('test.txt', 'w') as f:
            f.write(response.text)

    def getWebsiteCatalog(self):
        threadList = [threading.Thread(target=self.getWebsiteCatalogThread) for _ in range(10)]
        for each in threadList:
            each.start()

    # 更新小说
    def updateNovel(self, name: str):
        targetUrl = None
        t = time.perf_counter()
        with open('catalogThread.txt') as f:
            while True:
                data = f.readline().strip()
                if not data:
                    break
                if data.split('、')[-1] == name:
                    targetUrl = self.url + 'html/{}/'.format(data.split('、')[0])
                    break
        print('查找完毕，共耗时{:.2f}秒'.format(time.perf_counter() - t))

        tmp1, tmp2 = self.getCatalog(targetUrl, name, 'update')
        if tmp1 is None:
            print('没能成功获取章节目录！')
            return
        self.chapters.extend(tmp1)
        self.links.extend(tmp2)
        # print(len(links))

        if os.path.exists('./updateSettings.json') and os.path.getsize('./updateSettings.json') != 0:
            with open('./updateSettings.json') as f:
                updateSettings = json.loads(f.read())
            for each in updateSettings.keys():
                # print(updateSettings[each]['name'])
                if updateSettings[each]['name'] == name:
                    if len(self.links) == updateSettings[each]['chapterNumber']:
                        print('这本小说暂时没有更新！')
                        return
                    chapterName = updateSettings[each]['chapterName']
                    chapterNumber = updateSettings[each]['chapterNumber']
                    print('需要更新{}章节'.format(len(self.links) - chapterNumber))
                    break
            self.chapters = self.chapters[chapterNumber:]
            self.links = self.links[chapterNumber:]
            if len(self.links) < 10:
                self.getChapter(name, 1)
            else:
                self.getChapter(name, 10)
        else:
            print('检测到未下载过小说，请先下载小说！')

    # 更新网站目录
    def WebsiteCatalog(self):
        pass

    def mainInit(self):
        self.getCatalogFail = False
        self.finish = False
        self.processBar = 0

    def mainEnd(self):
        self.finish = True

    def main(self, name: str):
        self.mainInit()
        # 判断是否有下载过
        try:
            for each in os.listdir('./books'):
                if '{}.txt'.format(name) == each:
                    self.updateNovel(name)
                    self.mergePart(name)
                    self.removePart(name)
                    self.mainEnd()
                    return
            # 查找目录
            targetUrl = None
            t = time.perf_counter()
            with open('catalogThread.txt') as f:
                while True:
                    data = f.readline().strip()
                    if not data:
                        break
                    if data.split('、')[-1] == name:
                        targetUrl = self.url + 'html/{}/'.format(data.split('、')[0])
                        break
            print('查找完毕，共耗时{:.2f}秒'.format(time.perf_counter() - t))
            if targetUrl is None:
                print('没有找到这本书！请检查拼写是否有错误！')
                self.mainEnd()
                return
            
            # 开始下载
            tmp1, tmp2 = self.getCatalog(targetUrl, name)
            if tmp1 is None:
                print('没能成功获取章节目录！')
            else:
                self.chapters.extend(tmp1)
                self.links.extend(tmp2)
                self.getChapter(name)
                self.mergePart(name)
                self.removePart(name)
        finally:
            self.mainEnd()
            return