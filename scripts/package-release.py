"""Prepare release sources, corresponding Qt sources and checksums on CI."""
from pathlib import Path
import hashlib,subprocess,urllib.request,zipfile,concurrent.futures
from sentinel.product import PRODUCT
VERSION=PRODUCT.version
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'dist'
def main():
    subprocess.run(['git','archive','--format=zip','--prefix=CodexLoop-source/','-o',str(OUT/f'CodexLoop-{VERSION}-source.zip'),'HEAD'],cwd=ROOT,check=True)
    urls=[
      'https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.12.0-src/pyside-setup-everywhere-src-6.12.0.tar.xz',
      'https://download.qt.io/official_releases/qt/6.12/6.12.0/submodules/qtbase-everywhere-src-6.12.0.tar.xz',
      'https://download.qt.io/official_releases/qt/6.12/6.12.0/submodules/qtsvg-everywhere-src-6.12.0.tar.xz',
    ]
    def fetch(url):
        target=OUT/url.rsplit('/',1)[1]
        with urllib.request.urlopen(url,timeout=90) as response,target.open('wb') as output:
            while chunk:=response.read(1024*1024):output.write(chunk)
        return target
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:archives=list(pool.map(fetch,urls))
    with zipfile.ZipFile(OUT/f'CodexLoop-{VERSION}-dependency-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for path in archives:z.write(path,'dependency-sources/'+path.name)
        z.writestr('dependency-sources/ORIGINS.txt','\n'.join(urls)+'\n')
    names=['CodexLoop-Setup.exe','CodexLoop-Setup.exe.sha256',f'CodexLoop-{VERSION}-windows-x64.zip',f'CodexLoop-{VERSION}-source.zip',f'CodexLoop-{VERSION}-dependency-sources.zip']
    (OUT/'SHA256SUMS.txt').write_text(''.join(hashlib.sha256((OUT/name).read_bytes()).hexdigest()+'  '+name+'\n' for name in names),encoding='ascii')
if __name__=='__main__':main()
