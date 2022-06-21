import ctypes
import os
import time
import datetime as dt
import json
import threading

def getFinishedBook():
    if os.path.exists('bookStatus.json'):
        with open('bookStatus.json', encoding='utf-8') as f:
            data = json.loads(f.read())
        return data
    else:
        return None

def writeFinishedBook(fileDict):
    with open('bookStatus.json', 'w', encoding='utf-8') as f:
        json.dump(fileDict, f)

data = {
    '仙子很凶.txt': 1,
    '太监能有什么坏心思.txt': 0,
    '废土种田就是要攒.txt': 1,
    '我在修仙界长生不死.txt': 0,
    '我的卡牌无限强化.txt': 0,
    '我被迫挖了邪神的墙角.txt': 1,
    '星门.txt': 1,
    '精灵：我转生成了百变怪.txt': 0,
    '舌尖上的霍格沃茨.txt': 0
}

# with open('bookStatus.json', 'w', encoding='utf-8') as f:
#     data = json.dump(data, f, ensure_ascii=False)

# data = getFinishedBook()
# print(data)

# writeFinishedBook(data)

def getBookTime(books: list) -> list:
    path = './books/'
    bookTime = []
    for each in books:
        tmpPath = path + each
        bookTime.append(os.path.getmtime(tmpPath))
    return bookTime

# message = []
# for each in os.listdir('./books'):
#     message.append(each)

# updateStatus = []
# updateStatus.extend([0] * len(message))
# print(updateStatus)

from getBook import GetBooks

a = GetBooks()

a.main('我的法术没有攻击力')
# each = '我的法术没有攻击力'
# print(os.path.getsize('./books/{}.txt'.format(each)))