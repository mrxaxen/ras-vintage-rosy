import PyInstaller.__main__
from pathlib import Path

cwd = Path(__file__).parent.absolute()
path_to_main = str(cwd/"main.py")

def install():
    PyInstaller.__main__.run([
        path_to_main,
        '--onefile',
        '-nvintage-rosy'
    ])
