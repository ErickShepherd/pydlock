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
<https://pypi.org/project/pydlock/>. To install **pydlock**, simply use the
Python :code:`pip` installer:

.. code-block:: console
   
    pip install pydlock


=====
Usage
=====

From the command line
---------------------

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

    user@computer:~$ cat secret.txt
    Shh! It's a secret!

    user@computer:~$ python -m pydlock lock secret.txt
    Enter password:
    Re-enter password:

    user@computer:~$ cat secret.txt
    gAAAAABeqx971nHtXHi4dJYw8A_m_1mRYT8V2Sy4XPLqdg0t4mp9ooN-aTU1fuPQwEpwnuFiAfbJ6oPaN9IB1gzFT5-Tb4gFXQMw5uQUXDYV2Pvso6E5lXQ=user@computer:~$ python -m pydlock unlock secret.txt
    Enter password:

    user@computer:~$ cat secret.txt
    Shh! It's a secret!


In other Python modules
-----------------------

.. code-block:: python
   
    import pydlock

    filename = "example.txt"

    with open(filename, "w+") as file:

        print("Shh! It's a secret!", file = file)

    pydlock.lock(filename)


=====================
Copyright and License
=====================

Copyright
---------

Pydlock - A Python file encryption tool.

Copyright (C) 2020 of Erick Edward Shepherd, all rights reserved.


License
-------
    
Pydlock is free software: you can redistribute it and/or modify it under the
terms of the GNU Affero General Public License as published by the Free
Software Foundation, either version 3 of the License, or (at your option) any
later version.

Pydlock is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along
with Pydlock. If not, see <https://www.gnu.org/licenses/>.
