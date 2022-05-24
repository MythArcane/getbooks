from bs4 import BeautifulSoup
import os

data = ''
url = 'http://www.biququ.com/'

# with open('test.txt', 'ab') as f:
#     data = f.read()

# soup = BeautifulSoup(data, "html.parser")

# # for each in soup.find_all('meta'):
# #     if each.attrs.get('name', None) == 'keywords':
# #         print(each.attrs['content'])

# for each in os.listdir():
#     print(each)

import os, json

with open('updateSettings.json') as f:
    updateSettings = json.loads(f.read())
    print(updateSettings['1']['chapterNumber'])