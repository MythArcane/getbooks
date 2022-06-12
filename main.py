from io import BufferedWriter
from typing import List, Tuple
import requests, time, os, threading, json
from bs4 import BeautifulSoup

'''
当天时间为2022/5/17, 网址目前可用。
TODO 实现updateNovel函数(已完成，但没试验过)。
    搭建小型网页服务端, 将下载好的小说放在上面。
    添加ip代理池, 将获取网站目录的速度加快。
    实现updateWebsiteCatalog函数。
    添加交互界面, 最好为图形界面。
    添加过滤重复章节，重复章节指的是当前章和上一张相同，则当前章为重复章节。
    添加功能，当下载小说时查找不到小说的名字，可以根据相似度提示其他小说名字。
    将下载章节改为一个章节一个txt，当有失败章节的时候能将其记录，下载完毕后对失败章节进行5次重下，如果还不成功就作罢，最后由主线程将所有章节合并。
'''

headers = {
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

url = 'http://www.biququ.com/'
# targetUrl = 'http://www.biququ.com/html/50050/'
startUrl = 'http://www.biququ.com/html/50050/625621.html'

# 线程锁
threadLock = threading.Lock()
# 参数，第一个为'http://www.biququ.com/html/50050/'中的50050，可变
#       第二个为leaveCount，遇到404时加1
#       第三个为allCount，总计爬了多少本小说
#       第四个为时间参数，可计算总耗时
parameters = [1, 0, 0, time.perf_counter()]

chapters = []
links = []
failList = []
chapterParamters = [0, 0]

# 根据当前页面返回下一章的url
# 如果爬不到，可以采用模拟点击下一章按钮规避
def getNextUrl(content: str):
    pass

# 获取小说目录
def getCatalog(targetUrl: str, name: str, mode='download') -> Tuple[List[str], List[str]]:
    if mode not in ['download', 'update']:
        raise ValueError

    response = requests.get(targetUrl, headers=headers)
    if response.status_code != 200:
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
def getChapter(name: str, threadNum=10, mode='wb'):
    # 使用二进制模式防止编码错误
    f = open('./books/{}.txt'.format(name), mode)
    threadList = [threading.Thread(target=getChapterThread, args=(f, time.perf_counter())) for _ in range(threadNum)]
    for each in threadList:
        each.start()
    while chapterParamters[1] < len(links):
        pass
    time.sleep(1)
    f.close()
    print('\n成功下载{}章，失败{}章，章节名为：'.format(len(chapters) - len(failList), len(failList)))
    for each in failList:
        print(each)

def getChapterThread(*args):
    f: BufferedWriter = args[0]
    t: float = args[1]
    while True:
        with threadLock:
            if chapterParamters[0] >= len(chapters):
                return
            index = chapterParamters[0]
            chapterParamters[0] += 1
        try:
            response = requests.get(url + links[index], headers)
        except:
            while chapterParamters[1] != index:
                pass
            print('爬取{}章节失败，已留空！'.format(chapters[index]))
            with threadLock:
                f.write((chapters[index] + '\n\n').encode())
            failList.append(chapters[index])
            chapterParamters[1] += 1
            continue
        if response.status_code != 200:
            while chapterParamters[1] != index:
                pass
            print('爬取{}章节失败，已留空！'.format(chapters[index]))
            with threadLock:
                f.write((chapters[index] + '\n\n').encode())
            failList.append(chapters[index])
            chapterParamters[1] += 1
            continue
        
        soup = BeautifulSoup(response.text, "html.parser")
        data = soup.find_all('p')
        while chapterParamters[1] != index:
            pass
        # with threadLock:
        f.write((chapters[index] + '\n').encode())
        for each in data:
            if each.a is None and each.parent.attrs.get('id', None) == 'content':
                # print(each.text)
                f.write((each.text + '\n').encode())
        f.write('\n'.encode())
        print('爬取 {} 成功，还剩{}章，总计耗时{:.2f}秒。'.format(chapters[index], len(links)-index-1, time.perf_counter()-t))
        chapterParamters[1] += 1

        time.sleep(0.1)

def getWebsiteCatalogThread():
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
        threadLock.acquire()
        tmpUrl = url + str(parameters[0])
        now_page = parameters[0]
        parameters[0] += 1
        threadLock.release()
        response = requests.get(tmpUrl, headers=headers)
        if response.status_code == 404:
            parameters[1] += 1
            # parameters[2] -= 1
            if parameters[1] > 100:
                break
            continue
        parameters[1] = 0
        parameters[2] += 1
        print('爬到第{}本小说，目前序号为：{}，总耗时{:.2f}分钟'.format(parameters[2], now_page, (time.perf_counter()-parameters[3])/60))
        data = response.text
        soup = BeautifulSoup(data, "html.parser")
        for each in soup.find_all('meta'):
            if each.attrs.get('name', None) == 'keywords':
                threadLock.acquire()
                f.write('{}、{}\n'.format(now_page, each.attrs['content']))
                f.flush()
                threadLock.release()
                break
        time.sleep(0.1)

def test():
    del headers['Referer']
    response = requests.get(url + 'html/1', headers=headers)
    with open('test.txt', 'w') as f:
        f.write(response.text)

def getWebsiteCatalog():
    threadList = [threading.Thread(target=getWebsiteCatalogThread) for _ in range(10)]
    for each in threadList:
        each.start()

# 更新小说
def updateNovel(name: str):
    global chapters, links

    targetUrl = None
    t = time.perf_counter()
    with open('catalogThread.txt') as f:
        while True:
            data = f.readline().strip()
            if not data:
                break
            if data.split('、')[-1] == name:
                targetUrl = url + 'html/{}/'.format(data.split('、')[0])
                break
    print('查找完毕，共耗时{:.2f}秒'.format(time.perf_counter() - t))

    tmp1, tmp2 = getCatalog(targetUrl, name, 'update')
    if tmp1 is None:
        print('没能成功获取章节目录！')
        return
    chapters.extend(tmp1)
    links.extend(tmp2)
    # print(len(links))

    if os.path.exists('./updateSettings.json') and os.path.getsize('./updateSettings.json') != 0:
        with open('./updateSettings.json') as f:
            updateSettings = json.loads(f.read())
        for each in updateSettings.keys():
            if updateSettings[each]['name'] == name:
                if len(links) == updateSettings[each]['chapterNumber']:
                    print('这本小说暂时没有更新！')
                    return
                chapterName = updateSettings[each]['chapterName']
                chapterNumber = updateSettings[each]['chapterNumber']
                print('需要更新{}章节'.format(len(links) - chapterNumber))
                break
        chapters = chapters[chapterNumber:]
        links = links[chapterNumber:]
        if len(links) < 10:
            getChapter(name, 1, 'ab')
        else:
            getChapter(name, 10, 'ab')
    else:
        print('检测到未下载过小说，请先下载小说！')

# 更新网站目录
def WebsiteCatalog():
    pass

def main(name: str):
    # 判断是否有下载过
    for each in os.listdir('./books'):
        if '{}.txt'.format(name) == each:
            updateNovel(name)
            return
            # print('当前目录下已有该本小说，是否重新下载(y/n)?')
            # if input().lower() == 'y':
            #     break
            # else:
            #     return
    # 查找目录
    targetUrl = None
    t = time.perf_counter()
    with open('catalogThread.txt') as f:
        while True:
            data = f.readline().strip()
            if not data:
                break
            if data.split('、')[-1] == name:
                targetUrl = url + 'html/{}/'.format(data.split('、')[0])
                break
    print('查找完毕，共耗时{:.2f}秒'.format(time.perf_counter() - t))
    if targetUrl is None:
        print('没有找到这本书！请检查拼写是否有错误！')
        return
    
    # 开始下载
    tmp1, tmp2 = getCatalog(targetUrl, name)
    if tmp1 is None:
        print('没能成功获取章节目录！')
        return
    chapters.extend(tmp1)
    links.extend(tmp2)
    getChapter(name)

if __name__ == '__main__':
    main('舌尖上的霍格沃茨')
    # getWebsiteCatalog()