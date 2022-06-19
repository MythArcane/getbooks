from typing import Optional
from flask import Flask, render_template, send_from_directory, request, redirect, url_for
import os, json

DOWNLOAD_PATH = r'C:\workspace\getbooks\books'

app = Flask(__name__)

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
# 工具函数

@app.route('/about/')
def about():
    return render_template('about.html')

@app.route('/')
def index():
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
        'bookStatus': getBookStatus(message)
    }
    return render_template('index.html', **indexDict)

@app.route('/books/<filename>')
# 在目录页面下，用户点击对应的a标签，调用download函数，filename作为参数
# 使用send_from_directory方法返回对应目录下的对应文件，直接下载即可
def download(filename):
    return send_from_directory(DOWNLOAD_PATH, filename, as_attachment=True)

@app.route('/update/<filename>')
def update(filename):
    return 'Not done!'

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

if __name__ == "__main__":
    app.debug = True
    app.run(port=9877, host='192.168.2.107')