import subprocess
import locale
import tempfile
import os
import shutil

encoding = locale.getdefaultlocale()[1]

class PackageInfo():
    name = None
    repo = None
    version = None
    description = None
    author = None
    maintainer = None
    infourl = None
    copyright = None
    dependencies = list()
    capabilities = list()

    @staticmethod
    def read_package(path):
        process = subprocess.Popen(['kpack', '-i', path], stdout=subprocess.PIPE)
        output = process.communicate()[0].decode(encoding)
        result = PackageInfo()
        for line in output.splitlines():
            if not "=" in line: continue
            eq = line.index('=')
            key = line[:eq]
            value = line[eq + 1:]
            if key == 'name':
                result.name = value
            elif key == 'repo':
                result.repo = value
            elif key == 'version':
                s = value.split('.')
                result.version = (int(s[0]), int(s[1]), int(s[2]))
            elif key == 'description':
                result.description = value
            elif key == 'author':
                result.author = value
            elif key == 'maintainer':
                result.maintainer = value
            elif key == 'infourl':
                result.infourl = value
            elif key == 'copyright':
                result.copyright = value
            elif key == 'dependencies':
                result.dependencies = [v.split(':')[0] for v in value.split(' ')]
            elif key == 'capabilities':
                result.capabilities = value.split(' ')
        return result

    @staticmethod
    def get_package_contents(path):
        tempFolder = tempfile.mkdtemp()
        fullTempPath = os.path.join(tempFolder, 'package.pkg')
        shutil.copyfile(path, fullTempPath)
        extractedDir = os.path.join(tempFolder, 'pkgroot/')
        subprocess.call(['kpack', '-e', path, extractedDir])
        return PackageInfo.walkdir(extractedDir, 0)

    @staticmethod
    def walkdir(dirname, level):
        prefix = ""
        packageList = []
        for x in range(0, level):
            prefix = prefix + "---"
        for item in os.listdir(dirname):
            if os.path.isfile(os.path.join(dirname, item)):
                packageList.append(prefix + item)
            else:
                packageList.append(prefix + "/" + item)
                packageList.extend(PackageInfo.walkdir(os.path.join(dirname, item), level + 1))
        return packageList


