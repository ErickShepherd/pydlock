*******************
Prospective Updates
*******************

===================
Version 1.3.0 Goals
===================

* Create platform independent scripts to run Pydlock using only a "pydlock"
  command.
  
  - This could be accomplished by checking the installing operating system in
    the :code:`setup.py` file and populating the :code:`list` passed to the
    :code:`scripts` argument of the :code:`setup` function with the path to
    a batch or bash script respectively.
  
* Add "encrypt" and "decrypt" as synonymous command line :code:`operation`
  options to "lock" and "unlock".


========================
Version 2.0.0 Milestones
========================

* Add support for some function chains for naive source code protection.

  - Obsfucation -> compression -> encoding -> encryption
  
    + Obsfucation may be able to be substituded for minification. Multiple
      third party packages exist for this purpose. :code:`Opy` is one such
      obsfucation package, and :code:`python-minifier` and :code:`pyminifier`
      are capable of minifying Python modules. It may be worth investigating
      whether combining an obsfucator with a minifier affords any special
      advantage.
      
    + Compression can be accomplished through the native :code:`zlib` package.
    
    + Encoding can be accomplished through the native :code:`base64` package.
  
  - Obsfucation -> compilation -> encryption
  
    + Compilation can be accomplished through either the native
      :code:`compileall` package or the third party :code:`Cython` package.
