*********
Changelog
*********

==========================
2020-04-12 - Version 1.0.0
==========================

* Initial build developed and released.

  - Created :code:`pydlock.py`.


==========================
2020-04-13 - Version 1.1.0
==========================

* Added a "re-enter password" prompt when encrypting to avoid lock-out due to
  typos.

* Patched functions emptying files after invalid password entries.


==========================
2020-04-30 - Version 1.2.0
==========================

* Converted pydlock from a :code:`pydlock.py` module to a :code:`pydlock`
  package.

  - Created :code:`setup.py`.

  - Renamed :code:`pydlock.py` to :code:`__init__.py`.

  - Created :code:`__main__.py`.

  - Moved relevant :code:`__main__` namespace code into the new
    :code:`__main__.py` module.

* Single-sourced the :code:`__author__` and :code:`__version__` dunders.

* Changed the README file from Markdown to reStructuredText.

* Changed the package versioning system to include a build number for PyPI
  package management.
