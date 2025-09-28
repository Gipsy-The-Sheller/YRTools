# YRTools

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

[![License](https://img.shields.io/badge/license-GPL-green.svg)](LICENSE)

[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)]()

<img src="https://github.com/Gipsy-The-Sheller/YRTools/blob/main/icons/badge.svg" width="auto" height="50"/>

YiRan Tools (abbr. YRTools) is a one-for-all plugin-based desktop platform. The aim of YRTools is to shape the outline of the next-generation bioinformatic desktop platform, but actually, it can be applied to any area you can imagine.

亦然 (Chinese pinyin. yì rán) is a classical and formal adverb that means ​​"also thus," "similarly," or "likewise", which is a highly-refined abstract of the plugin-based architecture of YRTools.

The main program of YRTools acts as a GUI wrapper for all its plugins, while plugin is the basic function unit of YRTools, ensuring that all functions are loosely coupled, and the platform itself is highly scalable.

If you are interested in the plugin development of YRTools, you may go to its Github Wiki for more information.

## What's new on v0.0.2-pre?

In v0.0.2-pre, there are several changes of the main program and the basic plugin set:

- YRTools has now become Anglicized.
- From now on, YRTools supports a lightweight runtime environment management by **YR Runtime Manager**. You may create environments lighter than conda and use them to manage not only python site-packages, but also any scripts or binaries which are needed to be reused.
- Several small changes of art design and icons.

## Installation

The source code of YRTools can be directly run on any platform with several site-package dependancies. If you want a portable solution, you can download its PyInstaller-packaged binary from **Release** page (Note: priority supply to Windows users) and place it into your mobile storage device.

## Bug Report

You can report bugs at Github Issue or send an email to zjxmolls@outlook.com

## Citation

YRTools hasn't had any publications or preprints. So if you use YRTools' plugins, please cite the Github repository of YRTools itself and the corresponding plugin / plugin set.