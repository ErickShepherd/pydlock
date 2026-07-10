API reference
=============

The everyday API is the :func:`~pydlock.lock` / :func:`~pydlock.unlock` pair,
which encrypt and decrypt a file in place. The lower-level
:func:`~pydlock.encrypt` / :func:`~pydlock.decrypt` functions return the
envelope or plaintext bytes without touching the file, and the prompt helpers
read a password from the terminal. Everything below is imported directly from
the top-level ``pydlock`` package.

Locking and unlocking files
---------------------------

.. autofunction:: pydlock.lock

.. autofunction:: pydlock.unlock

Byte-level encryption
---------------------

.. autofunction:: pydlock.encrypt

.. autofunction:: pydlock.decrypt

Password prompts
----------------

.. autofunction:: pydlock.password_prompt

.. autofunction:: pydlock.double_password_prompt
