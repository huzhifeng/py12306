Windows下打包生成exe可执行文件
======

本项目提供的 py12306.exe 是使用[PyInstaller-2.1](https://pypi.python.org/packages/source/P/PyInstaller/PyInstaller-2.1.zip)打包生成的，步骤如下：  
1. 下载[PyInstaller-2.1](https://pypi.python.org/packages/source/P/PyInstaller/PyInstaller-2.1.zip)并解压（本项目已经提供)  
2. 下载[pywin32](http://sourceforge.net/projects/pywin32/files/pywin32/)并安装 (注意选对版本，目前最新版本是发布于2014-05-04的Build 219，我当时使用的是Build 218中的[pywin32-218.win32-py2.7.exe](http://sourceforge.net/projects/pywin32/files/pywin32/Build%20218/pywin32-218.win32-py2.7.exe/download))  
3. 进入PyInstaller-2.1根目录，执行`python pyinstaller.py -F ..\..\py12306.py`将创建py12306目录，生成的exe文件位于`py12306\dist\py12306.exe`<pre>
E:\Github\py12306>cd exe\PyInstaller-2.1

E:\Github\py12306\exe\PyInstaller-2.1>python pyinstaller.py -F ..\..\py12306.py
59 INFO: wrote E:\Github\py12306\exe\PyInstaller-2.1\py12306\py12306.spec
78 INFO: Testing for ability to set icons, version resources...
136 INFO: ... resource update available
139 INFO: UPX is not available.
165 INFO: Processing hook hook-os
271 INFO: Processing hook hook-time
308 INFO: Processing hook hook-_sre
327 INFO: Processing hook hook-cStringIO
337 INFO: Processing hook hook-codecs
351 INFO: Processing hook hook-encodings
805 INFO: Processing hook hook-cPickle
917 INFO: Extending PYTHONPATH with E:\Github\py12306
918 INFO: checking Analysis
918 INFO: building Analysis because out00-Analysis.toc non existent
918 INFO: running Analysis out00-Analysis.toc
919 INFO: Adding Microsoft.VC90.CRT to dependent assemblies of final executable
1001 INFO: Searching for assembly x86_Microsoft.VC90.CRT_1fc8b3b9a1e18e3b_9.0.21022.8_none ...
1002 INFO: Found manifest C:\Windows\WinSxS\Manifests\x86_microsoft.vc90.crt_1fc8b3b9a1e18e3b_9.0.21022.8_none_bcb86ed6ac711f91.manifest
1004 INFO: Searching for file msvcr90.dll
1004 INFO: Found file C:\Windows\WinSxS\x86_microsoft.vc90.crt_1fc8b3b9a1e18e3b_9.0.21022.8_none_bcb86ed6ac711f91\msvcr90.dll
1005 INFO: Searching for file msvcp90.dll
1005 INFO: Found file C:\Windows\WinSxS\x86_microsoft.vc90.crt_1fc8b3b9a1e18e3b_9.0.21022.8_none_bcb86ed6ac711f91\msvcp90.dll
1005 INFO: Searching for file msvcm90.dll
1006 INFO: Found file C:\Windows\WinSxS\x86_microsoft.vc90.crt_1fc8b3b9a1e18e3b_9.0.21022.8_none_bcb86ed6ac711f91\msvcm90.dll
1092 INFO: Analyzing E:\Github\py12306\exe\PyInstaller-2.1\PyInstaller\loader\_pyi_bootstrap.py
1108 INFO: Processing hook hook-os
1118 INFO: Processing hook hook-site
1138 INFO: Processing hook hook-encodings
1244 INFO: Processing hook hook-time
1281 INFO: Processing hook hook-_sre
1302 INFO: Processing hook hook-cStringIO
1311 INFO: Processing hook hook-codecs
1797 INFO: Processing hook hook-cPickle
1937 INFO: Processing hook hook-pydoc
2068 INFO: Processing hook hook-email
2125 INFO: Processing hook hook-httplib
2159 INFO: Processing hook hook-email.message
2224 INFO: Analyzing E:\Github\py12306\exe\PyInstaller-2.1\PyInstaller\loader\pyi_importers.py
2285 INFO: Analyzing E:\Github\py12306\exe\PyInstaller-2.1\PyInstaller\loader\pyi_archive.py
2338 INFO: Analyzing E:\Github\py12306\exe\PyInstaller-2.1\PyInstaller\loader\pyi_carchive.py
2391 INFO: Analyzing E:\Github\py12306\exe\PyInstaller-2.1\PyInstaller\loader\pyi_os_path.py
2401 INFO: Analyzing ..\..\py12306.py
2623 INFO: Hidden import 'codecs' has been found otherwise
2623 INFO: Hidden import 'encodings' has been found otherwise
2624 INFO: Looking for run-time hooks
2763 INFO: Using Python library C:\Windows\system32\python27.dll
2833 INFO: Warnings written to E:\Github\py12306\exe\PyInstaller-2.1\py12306\build\py12306\warnpy12306.txt
2838 INFO: checking PYZ
2840 INFO: rebuilding out00-PYZ.toc because out00-PYZ.pyz is missing
2840 INFO: building PYZ (ZlibArchive) out00-PYZ.toc
3816 INFO: checking PKG
3816 INFO: rebuilding out00-PKG.toc because out00-PKG.pkg is missing
3817 INFO: building PKG (CArchive) out00-PKG.pkg
4979 INFO: checking EXE
4979 INFO: rebuilding out00-EXE.toc because py12306.exe missing
4980 INFO: building EXE from out00-EXE.toc
4982 INFO: Appending archive to EXE E:\Github\py12306\exe\PyInstaller-2.1\py12306\dist\py12306.exe

E:\Github\py12306\exe\PyInstaller-2.1>
</pre>
4. 参考[[Python]项目打包：5步将py文件打包成exe文件](http://blog.csdn.net/pleasecallmewhy/article/details/8935135)