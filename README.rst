*******
Pydlock
*******

===========
Description
===========

**pydlock** is a simple Python package for encrypting and decrypting files. It
can be used either as a package imported into other Python modules or as a
command line script.


============
Installation
============

**pydlock** is available on the Python Package Index (PyPI) at
https://pypi.org/project/pydlock. To install **pydlock**, simply use the
Python :code:`pip` installer:

.. code-block:: console
   
    pip install pydlock


=====
Usage
=====

From the command line
---------------------

To access the :code:`help` method of the script:

.. code-block:: console

    user@computer:~$ python -m pydlock -h
    usage: __main__.py [-h] [--arguments ARGUMENTS] [--encoding ENCODING]
                       {lock,unlock,python,run} file

    positional arguments:
        {lock,unlock,python,run}
        file

    optional arguments:
        -h, --help            show this help message and exit
        --arguments ARGUMENTS
        --encoding ENCODING

To encrypt a file, use :code:`python -m pydlock lock [file]`:

.. code-block:: console

    user@computer:~$ cat secret.txt
    Shh! It's a secret!

    user@computer:~$ python -m pydlock lock secret.txt
    Enter password:
    Re-enter password:

    user@computer:~$ cat secret.txt
    gAAAAABeqx971nHtXHi4dJYw8A_m_1mRYT8V2Sy4XPLqdg0t4mp9ooN-aTU1fuPQwEpwnuFiAfbJ6oPaN9IB1gzFT5-Tb4gFXQMw5uQUXDYV2Pvso6E5lXQ=

To decrypt a file, use :code:`python -m pydlock unlock [file]`:

.. code-block:: console
    
    user@computer:~$ python -m pydlock unlock secret.txt
    Enter password:

    user@computer:~$ cat secret.txt
    Shh! It's a secret!


In other Python modules
-----------------------

.. code-block:: python
   
    import pydlock

    filename = "secret.txt"

    with open(filename, "w+") as file:

        print("Shh! It's a secret!", file = file)

    pydlock.lock(filename)


=====================
Copyright and License
=====================

Copyright
---------

Pydlock - A Python file encryption tool.
    
Copyright (c) 2020 of Erick Edward Shepherd, all rights reserved.


License
-------
    
MIT License

Copyright (c) 2020 Erick Edward Shepherd

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
