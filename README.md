# YRTools

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-GPL-green.svg)](LICENSE)
[![License](https://img.shields.io/badge/license-CC--BY--SA-green.svg)](LICENSE.icon)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)]()
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/Gipsy-The-Sheller/YRTools)

<img src="https://github.com/Gipsy-The-Sheller/YRTools/blob/main/icons/badge.svg" width="auto" height="50"/>

YiRan Tools (abbr. YRTools) is a one-for-all plugin-based desktop platform. The aim of YRTools is to shape the outline of the next-generation bioinformatic desktop platform, but actually, it can be applied to any area you can imagine.

**亦然** (Chinese pinyin. yì rán) is a classical and formal adverb that means ​​"also thus," "similarly," or "likewise", which is a highly-refined abstract of the plugin-based architecture of YRTools:

The main program of YRTools acts as a GUI wrapper for all its plugins, while plugin is the basic function unit of YRTools, ensuring that all functions are loosely coupled, and the platform itself is highly scalable. The integration of any function is fast, easy and simple.

If you are interested in the plugin development of YRTools, you may go to its Github Wiki for more information.

## What's new in v0.1.0

v0.0.3 has several changes in the software's distribution.

- YRTools is now portable via embedded Python, not pyinstaller packaging.
- A new official plugin **YR-MPE**, for the discipline *Molecular Phylogenetics and Evolution*, set is now formally supported.
- Scipy is removed from rigid dependencies, to reduce the size of the binary.
- I am considering incoporating a volume-reduced **MSYS2** environment for Windows version, as YRTools will soon suppoer running **SPAdes** directly on Windows **MSYYS2** environment (but not via **WSL2**). Also, many biotools are relatively easy to compile and run with MSYS.

## Installation

The source code of YRTools can be directly run on any platform with several site-package dependancies. If you want a portable solution, you can download its binary from **Release** page (Note: priority supply to Windows users) and place it into your mobile storage device.

## Licenses

[![License](https://img.shields.io/badge/license-GPL-green.svg)](LICENSE)
[![License](https://mirrors.creativecommons.org/presskit/buttons/80x15/svg/by-sa.svg)](LICENSE.icon)

All codes in this repository are distributed under the [**GNU General Public License 3.0 (GPL v3)** License](LICENSE). The core icons are distributed under the [**Creative Commons Attribution-ShareAlike (CC BY-SA) 4.0 International License**](LICENSE.icon)

## The YRTools Biosoftware Ecosystem

Below is a list of all the plugins and plugin sets currently planned or supported by YRTools. The planning plugin sets are shown as their dependencies are already successfully transplanted to Windows, and only need to implement the plugin interfaces and workflows.

|Area|Plugin set|Functions|Status|
|:--|:--|:--|:--|
|**Molecular Phylogenetics and Evolution**|[YR-MPE](https://github.com/Gipsy-The-Sheller/YR-MPE)|16+ softwares covering sequence alignment (4), trimming (2), distance methods (1), maximum likelihood method (1), Bayesian inference (2), phylogenetic dating (1)|**Officially Supported**|
|**Parametric Transcriptomics**|[YR-Trans](https://github.com/Gipsy-The-Sheller/YR-Trans)|HISAT2, FeatureCounts, PyDESeq2, Viz.|**On Development**|
|**General HTS Data Analysis**|YR-HTS|HTSLib, bwa & bowtie, Samtools, bcftools, vcftools, freebayes, fastp & cutadapt|**Planning**|
|**Genomics**|YR-Genomics|Genome Survey (Jellyfish), Genome Assembly (SPAdes, SKESA, Velvet), Organelle Genome Pipeline (GetOrganelle), tRNA Annotations (ARWEN, ARAGORN, tRNAScan-SE)|**Planning**|
|**Comparative Genomics**|YR-CompGen|SNP Calling (Snippy), Reduced-Representation Genomics (ipyrad), Aligners (BLAST, LAST, BLAT, Mummer), Collinear Alignment (SibeliaZ, ProgressiveMauve), Alignment viz (JCVI, GBdraw), Ortholog Finder (Orthofinder), Phylogenomics (TreeMix, WASTER)|**Planning**|
|**More features**| ...... | ...... |**Looking forward to your ideas and contributions.**|

## Bug Report

You can report bugs at Github Issue or send an email to zjxmolls@outlook.com.

## Citation

YRTools hasn't had any publications or preprints. So if you use YRTools' plugins, please cite the Github repository of YRTools itself and the corresponding plugin / plugin set.

You may cite specified literature when using some plugins.