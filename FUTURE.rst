*******************
Prospective Updates
*******************

=================
Version 1.3 Goals
=================

* Create platform independent scripts to run Pydlock using only a "pydlock"
  command.
  
  - This could be accomplished by checking the installing operating system in
    the :code:`setup.py` file and populating the :code:`list` passed to the
    :code:`scripts` argument of the :code:`setup` function with the path to
    a batch or bash script respectively.
  
* Add "encrypt" and "decrypt" as synonymous command line :code:`operation`
  options to "lock" and "unlock".
  

=================
Version 1.4 Goals
=================

* Add support to lock or unlock multiple files at once.

* Add support to temporarily unlock a file to read and return the contents as
  a variable.
  

=================
Version 1.5 Goals
=================

* Add seeding to the encryption.


======================
Version 2.0 Milestones
======================

* Add the ability to encrypt an entire directory as a single file.

  - This could be accomplished by zipping a directory into a single file using
    the zipfile module to compress the file into a .tar.gz for Unix/POSIX/MacOS
    or .zip for Windows.
    
      + See https://docs.python.org/3/library/zipfile.html

  - This could be accomplished by converting each file in the directory into a
    JSON-like object in a new text file and saving the directory structure in a
    similar JSON-like object in the same file, then encrypting that text file.
    Decrypting the resulting file can be accomplished by restoring the
    JSON-like objects to files according to the stored directory schema.

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
