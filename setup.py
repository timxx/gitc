import sys
import os
import codecs

from setuptools import (setup, find_packages)
from distutils.core import Command
from distutils.command.build import build
from distutils.spawn import find_executable, spawn
from distutils.errors import DistutilsExecError
from glob import glob

from qgitc.version import VERSION


class CustomBuild(build):

    def get_sub_commands(self):
        subCommands = super(CustomBuild, self).get_sub_commands()
        subCommands.insert(0, "build_qt")
        return subCommands


class BuildQt(Command):
    description = "Build Qt files"
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        methos = ("ui", "ts")
        for m in methos:
            getattr(self, "compile_" + m)()

    def compile_ui(self):
        return  # tempory disabled
        uic_bin = find_executable("pyside2-uic") or find_executable("uic")
        if not uic_bin:
            raise DistutilsExecError("Missing uic")

        for uiFile in glob("qgitc/*.ui"):
            name = os.path.basename(uiFile)
            pyFile = "qgitc/ui_" + name[:-3] + ".py"
            # "--from-imports" seems no use at all
            spawn([uic_bin, "-g", "python", "-o", pyFile, uiFile])

    def compile_ts(self):
        lrelease = find_executable(
            "lrelease-qt5") or find_executable("lrelease")
        if not lrelease:
            raise DistutilsExecError("Missing lrelease")

        path = os.path.realpath("qgitc/data/translations/qgitc.pro")
        spawn([lrelease, path])


class UpdateTs(Command):
    description = "Update *.ts files"
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        lupdate = find_executable("pyside2-lupdate")
        if not lupdate:
            raise DistutilsExecError("Missing pyside2-lupdate")

        path = os.path.realpath("qgitc/data/translations/qgitc.pro")
        spawn([lupdate, path])


with open("README.md", "r") as f:
    long_description = f.read()


setup(name="qgitc",
      version=VERSION,
      author="Weitian Leung",
      author_email="weitianleung@gmail.com",
      description='A file conflict viewer for git',
      long_description_content_type="text/markdown",
      long_description=long_description,
      keywords="git conflict viewer",
      url="https://github.com/timxx/qgitc",
      packages=find_packages(),
      package_data={"qgitc": ["data/icons/qgitc.*",
                              "data/licenses/Apache-2.0.html",
                              "data/translations/*.qm"
                              ]},
      license="Apache",
      python_requires='>=3.0',
      entry_points={
          "console_scripts": [
              "qgitc=qgitc.main:main",
              "imgdiff=mergetool.imgdiff:main"
          ]
      },
      install_requires=["PySide2", "pygit2"],
      classifiers=[
          "License :: OSI Approved :: Apache Software License",
          "Operating System :: POSIX",
          "Operating System :: POSIX :: BSD",
          "Operating System :: POSIX :: Linux",
          "Operating System :: Microsoft :: Windows",
          "Programming Language :: Python :: 3",
      ],
      cmdclass=dict(build=CustomBuild,
                    build_qt=BuildQt,
                    update_ts=UpdateTs
                    )
      )
