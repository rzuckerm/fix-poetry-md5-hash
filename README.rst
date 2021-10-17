fix-poetry-md5-hash
===================

Quick and dirty script to fix MD5 hashes in ``poetry.lock`` file.

Usage::

    poetry run fix-poetry-md5-hash <project_dir>

where:

* ``<project_dir>`` is path to project directory

This is a work-around for `poetry issue #4523`_

.. _poetry issue #4523: https://github.com/python-poetry/poetry/issues/4523
