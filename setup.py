#!/usr/bin/env python
#
# The MIT License
#
# Copyright (c) 2008-2009 Heikki Toivonen <My first name at heikkitoivonen.net>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.


setup_args = {
    "name": "caltrain",
    "version": "0.5.1",
    "platforms": ["any"],
    "description": "GUI and library for Caltrain schedules",
    "author": "Heikki Toivonen",
    "author_email": "My first name at heikkitoivonen.net",
    "url": 'http://www.heikkitoivonen.net/caltrain',
    "license": "The MIT License",
    "py_modules": ["caltrain"],
    "classifiers": [
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ], 
}

try:
    from setuptools import setup
    
    setup_args["zip_safe"] = True
    setup_args["entry_points"] = {
        "gui_scripts": [
            "caltrain = caltrain:gui",
        ]
    }
    setup_args["extras_require"] = {
        "JSON": ["python-json >=3.4", "BeautifulSoup >=3.0.4"],
        "parser": ["BeautifulSoup >=3.0.4"],
    }
except ImportError:
    from distutils.core import setup

setup(**setup_args)
