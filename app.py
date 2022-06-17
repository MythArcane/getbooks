from flask import Flask, render_template, send_from_directory
import os

DOWNLOAD_PATH = r'C:\workspace\getbooks\books'

app = Flask(__name__)

# 工具函数
def getCatalogMaxLength():
    max1 = 0
    for each in os.listdir('./books'):
            each = each.split('.')[0]
            max1 = max(len(each), max1)
    return max1*22 + 24
# 工具函数

@app.route('/about/')
def about():
    return render_template('about.html')

@app.route('/')
def index():
    message = []
    prelink = '/books/'
    for each in os.listdir('./books'):
        message.append(each)
    return render_template('index.html', message=message, prelink=prelink, maxCatalogLength=getCatalogMaxLength())

@app.route('/books/<filename>')
# 在目录页面下，用户点击对应的a标签，调用download函数，filename作为参数
# 使用send_from_directory方法返回对应目录下的对应文件，直接下载即可
def download(filename):
    return send_from_directory(DOWNLOAD_PATH, filename, as_attachment=True)

@app.route('/update/<filename>')
def update(filename):
    pass

if __name__ == "__main__":
    app.debug = True
    app.run(port=9877, host='192.168.2.107')