import ctypes
import os
def isadmin():
	return ctypes.windll.shell32.IsUserAnAdmin()

print(isadmin())

