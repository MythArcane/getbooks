from typing import Optional
from flask import Flask, render_template, send_from_directory, request, redirect, url_for
import os, json, time, threading
from getBook import GetBooks

'''
官网例程误我，写了大半才想起来可以用class来更好的集成，也不用那么多的global了
有空改
'''

DOWNLOAD_PATH = r'C:\workspace\getbooks\books'

isUpdating = False
updateStatus = []

app = Flask(__name__)
getbook = GetBooks()

# 工具函数
def getCatalogMaxLength() -> int:
    max1 = 0
    for each in os.listdir('./books'):
            each = each.split('.')[0]
            max1 = max(len(each), max1)
    return max1*22 + 68

def getBookTime(books: list) -> list:
    path = './books/'
    bookTime = []
    for each in books:
        tmpPath = path + each
        bookTime.append(os.path.getmtime(tmpPath))
    return bookTime

def getBookStatus(books: list) -> list:
    ls = []
    data = getFinishedBook()
    for each in books:
        ls.append(int(data[each]))
    return ls

def getFinishedBook() -> Optional[dict]:
    if os.path.exists('bookStatus.json'):
        with open('bookStatus.json', encoding='utf-8') as f:
            data = json.loads(f.read())
        return data
    else:
        return None

def writeFinishedBook(fileDict: dict) -> None:
    with open('bookStatus.json', 'w', encoding='utf-8') as f:
        json.dump(fileDict, f)

def addOneBookStatus(bookName: str, status: int):
    data = getFinishedBook()
    if not bookName.endswith('.txt'):
        bookName += '.txt'
    data[bookName] = str(status)
    writeFinishedBook(data)

def removeOneBookStatus(bookName: str):
    data = getFinishedBook()
    if not bookName.endswith('.txt'):
        bookName += '.txt'
    if data.get(bookName, None) is None:
        return
    del data[bookName]
    writeFinishedBook(data)

def checkUpdateStatus():
    global isUpdating, getbook

    if isUpdating:
        if getbook.finish:
            isUpdating = False
            initUpdateStatus()
        else:
            pass
    else:
        initUpdateStatus()

def pureUpdate(filename):
    global updateStatus, isUpdating, getbook

    message = []
    for each in os.listdir('./books'):
        message.append(each)
    index = message.index(filename + '.txt')
    updateStatus[index] = 1
    isUpdating = True

    t1 = threading.Thread(target=getbook.main, args=(filename,))
    t1.start()

def initUpdateStatus():
    global updateStatus

    updateStatus.clear()

    message = []
    for each in os.listdir('./books'):
        message.append(each)
    
    updateStatus.extend([0] * len(message))

def initIndex():
    message = []
    for each in os.listdir('./books'):
        message.append(each)
    data = getFinishedBook()
    if len(message) < len(data.keys()):
        for each in list(data.keys())[:]:
            if each not in message:
                del data[each]
    elif len(message) > len(data.keys()):
        for each in message:
            if each not in data.keys():
                data[each] = '0'

def init():
    initUpdateStatus()
# 工具函数

@app.route('/about/')
def about():
    return render_template('about.html')

@app.route('/')
def index():
    global getbook

    initIndex()
    checkUpdateStatus()
    message = []
    prelink = '/books/'
    maxLength = 0
    for each in os.listdir('./books'):
        message.append(each)
        maxLength = max(len(each), maxLength)

    indexDict = {
        'message': message, 
        'prelink': prelink, 
        'maxCatalogLength': getCatalogMaxLength(), 
        'bookLength': len(message),
        'bookTime': getBookTime(message),
        'bookStatus': getBookStatus(message),
        'updateStatus': updateStatus,
        'progressBar': getbook.processBar
    }
    return render_template('index.html', **indexDict)

@app.route('/books/<filename>')
# 在目录页面下，用户点击对应的a标签，调用download函数，filename作为参数
# 使用send_from_directory方法返回对应目录下的对应文件，直接下载即可
def download(filename):
    return send_from_directory(DOWNLOAD_PATH, filename, as_attachment=True)

@app.route('/downloadFullBook', methods=['POST'])
def downloadFullBook():
    global getbook

    form = request.form
    bookName = form.get('bookname')
    if getbook.searchBook(bookName):
        with open('./books/{}.txt'.format(bookName), 'w') as f:
            pass
        addOneBookStatus(bookName, 0)
        pureUpdate(bookName)
        return redirect(url_for('.index'))
    else:
        return '没有找到该小说，请注意拼写！'

@app.route('/update/<filename>')
def update(filename):
    pureUpdate(filename)

    return redirect(url_for('.index'))

@app.route('/controlStatus')
def controlStatus():
    message = []
    prelink = '/books/'
    maxLength = 0
    for each in os.listdir('./books'):
        message.append(each)
        maxLength = max(len(each), maxLength)

    indexDict = {
        'message': message, 
        'prelink': prelink, 
        'maxCatalogLength': getCatalogMaxLength(), 
        'bookLength': len(message),
        'bookStatus': getBookStatus(message)
    }

    # return indexDict
    return render_template('controlStatus.html', **indexDict)

@app.route('/modify', methods=['POST'])
def modifyBookStatus():
    form = request.form
    length = len(os.listdir('./books'))
    message = []
    for each in os.listdir('./books'):
        message.append(each)
    data = getFinishedBook()
    for index in range(length):
        data[message[index]] = form['bookStatus'+str(index)]
    writeFinishedBook(data)

    return redirect(url_for('.controlStatus'))

@app.route('/test1')
def test1():
    global isUpdating
    return {isUpdating:1}

count = 0
@app.route('/test2')
def test2():
    global count
    if count == 0:
        time.sleep(10)
        count += 1
    return {count: count}

if __name__ == "__main__":
    init()

    app.debug = True
    app.run(port=9877, host='192.168.2.107')