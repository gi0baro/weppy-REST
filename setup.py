# -*- coding: utf-8 -*-
"""
weppy-REST
----------

Rest extension for weppy framework.

"""

from setuptools import setup

setup(
    name='weppy-REST',
    version='0.4',
    url='https://github.com/gi0baro/weppy-rest',
    license='BSD',
    author='Giovanni Barillari',
    author_email='gi0baro@d4net.org',
    description='REST extension for weppy framework',
    long_description=__doc__,
    packages=['weppy_rest'],
    install_requires=[
        'weppy>=1.0'
    ],
    zip_safe=False,
    platforms='any',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Text Processing :: Markup :: HTML'
    ],
)
