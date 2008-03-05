#!/usr/bin/env python
# 
# The MIT License
#
# Copyright (c) 2007-2008 Heikki Toivonen <hjtoi at comcast dot net>
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
#
# MultiListbox Copyright:
#   Brent Burley 2001
#   Pedro Werneck 2003
#   Heikki Toivonen 2007-2008

"""
Caltrain schedule for systems that have Python and Tkinter, for
example Windows Mobile. Alternatively can be imported to provide schedule
parsing etc.
"""

# Tested on Cingular 8525 running Windows Mobile 5 and Python 2.5+Tkinter.
#
# My installation:
# Download PythonCE 2.5 and Tkinter from:
#   http://pythonce.sourceforge.net/Wikka/HomePage
# Installed Python 2.5 onto storage card without a problem. Then
# downloaded Tkinter, unzipped on PC, and copied files as follows:
#   * DLLs from Windows directory to device's \Windows directory
#   * From tcl8.4.3 directory copied library and tk8.4 directories into
#     storage card's Program Files directory (siblings of Python25)
# Made CaltrainPy directory, a sibling of Python25 and placed caltrain.py
# there. Launched caltrain.py by clicking on it in Explorer.
#
# CaltrainPy 0.3
# - Update to schedules published March 3, 2008
# - fix AM/PM bugs
# CaltrainPy 0.2
# - AM/PM indicators
# - train types
# - can be used as a module to parse Caltrain schedule
# - MIT License
# - setup.py
# Caltrain 0.1
# - initial release
#
# BUGS/TODO
# * Weekend/Holiday, change From station to San Jose, click Northbound
#    => From-To reset
# * Fullscreen
# * Fit the screen ;)
# * Respond to OK on Windows Mobile
# * About
# * Show only trains that stop at selected stations
# * Map
# ...

import array
from urllib2 import urlopen

try:
    import _tkinter # Seems to help some with DLL load problems
    from Tkinter import *
    have_tkinter = True
except ImportError:
    class Frame: pass
    have_tkinter = False

try:
    from BeautifulSoup import BeautifulSoup
    have_beautifulsoup = True
except ImportError:
    have_beautifulsoup = False

FORMAT_PYTHON = 'python'
FORMAT_JSON   = 'json'
FORMAT_HTML   = 'html'

# Constant strings
weekday = "Mon-Fri"
weekend = "Weekend/Holiday"
northbound = "Northbound"
southbound = "Southbound"
trainNumber = "Train No."

service = {
    weekday: {northbound:None, southbound:None},
    weekend: {northbound:None, southbound:None},    
    }

stations = {
    weekday: {northbound:None, southbound:None},
    weekend: {northbound:None, southbound:None},
    }


def am_pm(table, row, cell):
    """
    Return cell + AM/PM value for cell.
    
    @param table: Table as filled so far.
    @param row:   Row as filled so far.
    @param cell:  Cell value (without AM/PM) that is about to be added to row.
    @return:      True if need to change AM/PM.
    """
    column = len(row)
    assert cell.find(':') > -1
    cell_hours = int(cell[:cell.find(':')])
    
    # Fix some bugs in the timetable
    if cell_hours > 12: 
        cell_hours -= 12
        cell = '%d%s' % (cell_hours, cell[cell.find(':'):])
        
    if cell == '10:01' and row[0] == 'San Francisco' and \
       table[0][column] == '195':
        cell = '11:01'
    
    # start from latest row, going up, first row has train numbers so skip
    for i in range(len(table) - 1, 1, -1):
        above = table[i][column]
        if above and '-' not in above:
            assert above.find(':') > -1
            above_hours = int(above[:above.find(':')])
            
            if above_hours != cell_hours and above_hours != 12 and \
               (above_hours > cell_hours or cell_hours == 12):
                if above[-2:] == 'AM':
                    return cell + ' PM'
                return cell + ' AM'

            return cell + above[-3:]
            
    # no values above, look to the left
    # start from latest column, go left, first column has stations so skip
    for i in range(column - 1, 1, -1):
        left = row[i]
        if left and '-' not in left:
            assert left.find(':') > -1
            left_hours = int(left[:left.find(':')])
            
            if left_hours != cell_hours and left_hours != 12 and \
               (left_hours > cell_hours or cell_hours == 12):
                if left[-2:] == 'AM':
                    return cell + ' PM'
                return cell + ' AM'

            return cell + left[-3:]
            
    # We rely on the fact that currently this always means AM
    return cell + ' AM'


def scrape_timetable(html=None, format=FORMAT_PYTHON):
    """
    Scrape timetables from HTML, and return them in machine readable format.

    @param html:   If None, fetch the timetable first, otherwise expected to be
                   the HTML string to parse.
    @param format: In what format should results be returns, default
                   FORMAT_PYTHON. Other legal values FORMAT_JSON, FORMAT_HTML.
    """
    # This is somewhat quick and dirty parsing, but given that it parses
    # ok now (as of 2008-3-4) and that the original format is subject to
    # change with the whims of Caltrain it does not seem to warrant too
    # many refinements. Bug fixes always welcome.
    
    if not have_beautifulsoup:
        raise Exception('Need BeautifulSoup')

    if html is None:
        html = urlopen('http://caltrain.com/timetable.html').read()

    # Sanitize the input a little, otherwise we'll miss some cells
    # 1. Sharks game, train departs at this time or later
    html = html.replace('<sup><a href="#note-sharks">#</a></sup>', '#')
    # 2. Six minute timed transfer in Redwood City
    html = html.replace('<sup><a href="#note-xfer">@</a></sup>', '@')
    # 3. May leave up to 5 minutes early
    html = html.replace('<sup><a href="#note-early">*</a></sup>', '*')
    # 4. Newlines to spaces
    html = html.replace('<br>', ' ')
    
    soup = BeautifulSoup(html)
    
    # assume 5 tables: legend, northbound, southbound, weekend n, weekend s
    tables = 0
    alltables = []
    # bgcolor attribute shows what kind of train, no color is normal train
    bgcolor = {'#F0B2A1': '(b)', # baby bullet
               '#F7E89D': '(x)'} # limited aka express
    
    for table in soup('table'):
        tables += 1
        if tables == 1:
            continue #legend
        
        rows = 0
        onetable = []
        for tr in table('tr'):
            onerow = []
            rows += 1

            # train numbers and types
            for th in tr('th'):
                if th.string is None:
                    th.string = ''
                t = th.string.replace('&nbsp;', ' ').strip()
                if t not in onerow:
                    # relying on station names to not have bgcolor same as
                    # train type legend
                    onerow.append(t + bgcolor.get(th.get('bgcolor', None), ''))

            # arrival and departure times
            for td in tr('td'):
                if td.string is None:
                    td.string = ''
                t = td.string.replace('&nbsp;', ' ').strip()

                if t and '-' not in t:
                    t = am_pm(onetable, onerow, t)
                onerow.append(t)

            onetable.append(onerow)
        assert rows == 30 or rows == 27, rows

        alltables.append(onetable)

    if format == FORMAT_PYTHON:
        return alltables
    elif format == FORMAT_HTML:
        ret = []
        for onetable in alltables:
            ret.append('<table border="1">')
            for row in onetable:
                ret.append('<tr>')
                for entry in row:
                    #great for debug:
                    if 'PM' in entry:
                        ret.append('<td bgcolor="red">%s</td>' % entry)
                    else:
                        ret.append('<td>%s</td>' % entry)
                ret.append('</tr>\n')
            ret.append('</table>\n')
        return ''.join(ret)
    else: # FORMAT_JSON
        import json
        return json.write(alltables)


# To get the service & stations:
#   Run the following script, and copy the output here.
# The reason we do this is so that everything is in one file; easy deployment.
"""
import caltrain

tables = caltrain.scrape_timetable(format=caltrain.FORMAT_PYTHON)

tt = {0: 'service[weekday][northbound] =',
      1: 'service[weekday][southbound] =',
      2: 'service[weekend][northbound] =',
      3: 'service[weekend][southbound] ='}

ss = {0: 'stations[weekday][northbound] =',
      1: 'stations[weekday][southbound] =',
      2: 'stations[weekend][northbound] =',
      3: 'stations[weekend][southbound] ='}

for i, table in enumerate(tables):
    stations = []
    timetable = {}
    station = ''

    for row in table:
        station = row[0]
        if row[0] != 'Train No.':
            stations.append(station)
        timetable[station] = row[1:]

    
    print tt[i], str(timetable).replace('], ', '],\n')
    print
    print ss[i], stations
    print
"""

service[weekday][northbound] = {u'Santa Clara': [u'4:35 AM', u'5:10 AM', u'-', u'6:02 AM', u'-', u'6:27 AM', u'-', u'-', u'7:02 AM', u'-', u'7:25 AM', u'-', u'-', u'8:02 AM', u'-', u'8:27 AM', u'8:45 AM', u'9:15 AM', u'9:45 AM', u'10:15 AM', u'10:45 AM', u'11:15 AM', u'11:45 AM', u'12:15 PM', u'12:45 PM', u'1:15 PM', u'1:45 PM', u'2:15 PM', u'2:45 PM', u'3:12 PM', u'3:49 PM', u'4:10 PM', u'-', u'4:44 PM', u'-', u'5:10 PM', u'-', u'-', u'5:44 PM', u'-', u'6:10 PM', u'-', u'-', u'-', u'6:55 PM', u'7:35 PM', u'8:35 PM', u'9:35 PM', u'10:35 PM'],
u'Hayward Park': [u'5:22 AM', u'5:57 AM', u'-', u'-', u'-', u'7:05 AM', u'-', u'-', u'-', u'-', u'8:05 AM', u'-', u'-', u'-', u'-', u'9:05 AM', u'-', u'10:02 AM', u'-', u'11:02 AM', u'-', u'12:02 PM', u'-', u'1:02 PM', u'-', u'2:02 PM', u'-', u'3:02 PM', u'-', u'3:59 PM', u'-', u'4:45 PM', u'-', u'-', u'-', u'5:45 PM', u'-', u'-', u'-', u'-', u'6:45 PM', u'-', u'-', u'-', u'7:42 PM', u'8:22 PM', u'9:22 PM', u'10:22 PM', u'11:22 PM'],
u'San Francisco': [u'6:01 AM', u'6:36 AM', u'6:42 AM', u'7:19 AM', u'7:02 AM', u'7:48 AM', u'7:42 AM', u'7:57 AM', u'8:19 AM', u'8:02 AM', u'8:48 AM', u'8:42 AM', u'8:57 AM', u'9:19 AM', u'9:02 AM', u'9:45 AM', u'10:02 AM', u'10:41 AM', u'11:02 AM', u'11:41 AM', u'12:02 PM', u'12:41 PM', u'1:02 PM', u'1:41 PM', u'2:02 PM', u'2:41 PM', u'3:02 PM', u'3:41 PM', u'4:02 PM', u'4:38 PM', u'5:03 PM', u'5:29 PM', u'5:24 PM', u'6:02 PM', u'5:44 PM', u'6:29 PM', u'6:24 PM', u'6:39 PM', u'7:02 PM', u'6:44 PM', u'7:29 PM', u'7:24 PM', u'7:39 PM', u'8:00 PM', u'8:21 PM', u'9:01 PM', u'10:01 PM', u'11:01 PM', u'12:01 AM'],
u'San Martin': ['', '', '', '', '', '', '', '', u'6:16 AM', '', u'6:39 AM', '', '', u'7:14 AM', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', ''],
u'San Mateo': [u'5:25 AM', u'6:00 AM', u'-', u'-', u'6:39 AM', u'7:08 AM', u'-', u'7:32 AM', u'-', u'7:39 AM', u'8:08 AM', u'-', u'8:32 AM', u'-', u'8:39 AM', u'9:08 AM', u'9:33 AM', u'10:05 AM', u'10:33 AM', u'11:05 AM', u'11:33 AM', u'12:05 PM', u'12:33 PM', u'1:05 PM', u'1:33 PM', u'2:05 PM', u'2:33 PM', u'3:05 PM', u'3:33 PM', u'4:02 PM', u'4:36 PM', u'4:48 PM', u'-', u'5:36 PM', u'-', u'5:48 PM', u'-', u'6:12 PM', u'6:36 PM', u'-', u'6:48 PM', u'-', u'7:12 PM', u'7:32 PM', u'7:45 PM', u'8:25 PM', u'9:25 PM', u'10:25 PM', u'11:25 PM'],
u'Blossom Hill': ['', '', '', '', '', '', '', '', u'6:35 AM', '', u'6:58 AM', '', '', u'7:33 AM', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', ''],
u'College Park': [u'-', u'-', u'-', u'-', u'-', u'-', u'-', u'-', u'-', u'-', u'-', u'-', u'-', u'7:58 AM', u'-', u'-', u'-', u'-', u'-', u'-', u'-', u'-', u'-', u'-', u'-', u'-', u'-', u'-', u'-', u'3:08 PM', u'-', u'-', u'-', u'-', u'-', u'-', u'-', u'-', u'-', u'-', u'-', u'-', u'-', u'-', u'-', u'-', u'-', u'-', u'-'],
u'Lawrence': [u'4:40 AM', u'5:15 AM', u'-', u'6:12 AM', u'-', u'-', u'-', u'-', u'7:12 AM', u'-', u'7:30 AM', u'-', u'-', u'8:12 AM', u'-', u'-', u'8:50 AM', u'9:20 AM', u'9:50 AM', u'10:20 AM', u'10:50 AM', u'11:20 AM', u'11:50 AM', u'12:20 PM', u'12:50 PM', u'1:20 PM', u'1:50 PM', u'2:20 PM', u'2:50 PM', u'3:17 PM', u'3:54 PM', u'-', u'-', u'4:52 PM', u'-', u'-', u'-', u'5:39 PM', u'5:52 PM', u'-', u'-', u'-', u'6:39 PM', u'6:53 PM', u'7:00 PM', u'7:40 PM', u'8:40 PM', u'9:40 PM', u'10:40 PM'],
u'Burlingame': [u'5:28 AM', u'6:03 AM', u'-', u'-', u'-', u'7:11 AM', u'-', u'7:35 AM', u'-', u'-', u'8:11 AM', u'-', u'8:35 AM', u'-', u'-', u'9:11 AM', u'9:36 AM', u'10:08 AM', u'10:36 AM', u'11:08 AM', u'11:36 AM', u'12:08 PM', u'12:36 PM', u'1:08 PM', u'1:36 PM', u'2:08 PM', u'2:36 PM', u'3:08 PM', u'3:36 PM', u'4:05 PM', u'-', u'4:51 PM', u'-', u'-', u'-', u'5:51 PM', u'-', u'6:15 PM', u'-', u'-', u'6:51 PM', u'-', u'7:15 PM', u'7:35 PM', u'7:48 PM', u'8:28 PM', u'9:28 PM', u'10:28 PM', u'11:28 PM'],
u'Mountain View': [u'4:49 AM', u'5:24 AM', u'5:57 AM', u'6:23 AM', u'-', u'6:37 AM', u'6:57 AM', u'7:05 AM', u'7:23 AM', u'-', u'7:37 AM', u'7:57 AM', u'8:05 AM', u'8:23 AM', u'-', u'8:37 AM', u'8:59 AM', u'9:29 AM', u'9:59 AM', u'10:29 AM', u'10:59 AM', u'11:29 AM', u'11:59 AM', u'12:29 PM', u'12:59 PM', u'1:29 PM', u'1:59 PM', u'2:29 PM', u'2:59 PM', u'3:26 PM', u'4:03 PM', u'-', u'4:37 PM', u'5:03 PM', u'4:58 PM', u'-', u'5:37 PM', u'5:46 PM', u'6:03 PM', u'5:58 PM', u'-', u'6:37 PM', u'6:46 PM', u'7:00 PM', u'7:09 PM', u'7:49 PM', u'8:49 PM', u'9:49 PM', u'10:49 PM'],
u'22nd Street': [u'5:52 AM', u'6:27 AM', u'-', u'-', u'-', u'7:40* AM', u'-', u'-', u'-', u'-', u'8:40* AM', u'-', u'-', u'-', u'-', u'9:37 AM', u'-', u'10:32 AM', u'-', u'11:32 AM', u'-', u'12:32 PM', u'-', u'1:32 PM', u'-', u'2:32 PM', u'-', u'3:32 PM', u'-', u'4:29 PM', u'4:55 PM', u'5:21* PM', u'5:17 PM', u'5:55 PM', u'5:37 PM', u'6:21* PM', u'6:17 PM', u'-', u'6:55 PM', u'6:37 PM', u'7:21* PM', u'7:17 PM', u'-', u'7:53 PM', u'8:12 PM', u'8:52 PM', u'9:52 PM', u'10:52 PM', u'11:52 PM'],
u'Bayshore': [u'5:47 AM', u'6:22 AM', u'-', u'-', u'-', u'7:33* AM', u'-', u'-', u'-', u'-', u'8:33* AM', u'-', u'-', u'-', u'-', u'9:31 AM', u'-', u'10:27 AM', u'-', u'11:27 AM', u'-', u'12:27 PM', u'-', u'1:27 PM', u'-', u'2:27 PM', u'-', u'3:27 PM', u'-', u'4:24 PM', u'-', u'5:13* PM', u'-', u'-', u'-', u'6:13* PM', u'-', u'-', u'-', u'-', u'7:13* PM', u'-', u'-', u'-', u'8:07 PM', u'8:57 PM', u'9:47 PM', u'10:47 PM', u'11:47 PM'],
u'San Antonio': [u'4:53 AM', u'5:28 AM', u'-', u'6:27 AM', u'-', u'-', u'-', u'-', u'7:27 AM', u'-', u'-', u'-', u'-', u'8:27 AM', u'-', u'-', u'9:03 AM', u'9:33 AM', u'10:03 AM', u'10:33 AM', u'11:03 AM', u'11:33 AM', u'12:03 PM', u'12:33 PM', u'1:03 PM', u'1:33 PM', u'2:03 PM', u'2:33 PM', u'3:03 PM', u'3:30 PM', u'4:07 PM', u'-', u'-', u'5:07 PM', u'-', u'-', u'-', u'-', u'6:07 PM', u'-', u'-', u'-', u'-', u'-', u'7:13 PM', u'7:53 PM', u'8:53 PM', u'9:53 PM', u'10:53 PM'],
u'Millbrae': [u'5:33 AM', u'6:08 AM', u'6:24 AM', u'6:59 AM', u'6:45 AM', u'7:17 AM', u'7:24 AM', u'-', u'7:59 AM', u'7:45 AM', u'8:17 AM', u'8:24 AM', u'-', u'8:59 AM', u'8:45 AM', u'9:17 AM', u'9:41 AM', u'10:13 AM', u'10:41 AM', u'11:13 AM', u'11:41 AM', u'12:13 PM', u'12:41 PM', u'1:13 PM', u'1:41 PM', u'2:13 PM', u'2:41 PM', u'3:13 PM', u'3:41 PM', u'4:10 PM', u'4:43 PM', u'4:57 PM', u'5:05 PM', u'5:43 PM', u'5:25 PM', u'5:57 PM', u'6:05 PM', u'-', u'6:43 PM', u'6:25 PM', u'6:57 PM', u'7:05 PM', u'-', u'7:41 PM', u'7:53 PM', u'8:33 PM', u'9:33 PM', u'10:33 PM', u'11:33 PM'],
u'San Carlos': [u'5:13 AM', u'5:48 AM', u'-', u'-', u'-', u'6:55 AM', u'-', u'7:24 AM', u'-', u'-', u'7:55 AM', u'-', u'8:24 AM', u'-', u'-', u'8:55 AM', u'9:23 AM', u'9:53 AM', u'10:23 AM', u'10:53 AM', u'11:23 AM', u'11:53 AM', u'12:23 PM', u'12:53 PM', u'1:23 PM', u'1:53 PM', u'2:23 PM', u'2:53 PM', u'3:23 PM', u'3:50 PM', u'4:29 PM', u'4:35 PM', u'-', u'5:29 PM', u'-', u'5:35 PM', u'-', u'6:04 PM', u'6:29 PM', u'-', u'6:35 PM', u'-', u'7:04 PM', u'7:23 PM', u'7:33 PM', u'8:13 PM', u'9:13 PM', u'10:13 PM', u'11:13 PM'],
u'Train No.': [u'101', u'103', u'305(b)', u'207(x)', u'309(b)', u'211(x)', u'313(b)', u'215(x)', u'217(x)', u'319(b)', u'221(x)', u'323(b)', u'225(x)', u'227(x)', u'329(b)', u'231(x)', u'233(x)', u'135', u'237(x)', u'139', u'241(x)', u'143', u'245(x)', u'147', u'249(x)', u'151', u'253(x)', u'155', u'257(x)', u'159', u'261(x)', u'263(x)', u'365(b)', u'267(x)', u'369(b)', u'271(x)', u'373(b)', u'275(x)', u'277(x)', u'379(b)', u'281(x)', u'383(b)', u'285(x)', u'287(x)', u'189', u'191', u'193', u'195', u'197#'],
u'Menlo Park': [u'5:04 AM', u'5:39 AM', u'-', u'6:39 AM', u'-', u'6:45 AM', u'-', u'-', u'7:39 AM', u'-', u'7:45 AM', u'-', u'-', u'8:39 AM', u'-', u'8:45 AM', u'9:14 AM', u'9:44 AM', u'10:14 AM', u'10:44 AM', u'11:14 AM', u'11:44 AM', u'12:14 PM', u'12:44 PM', u'1:14 PM', u'1:44 PM', u'2:14 PM', u'2:44 PM', u'3:14 PM', u'3:41 PM', u'4:19 PM', u'-', u'4:46 PM', u'5:19 PM', u'-', u'-', u'5:46 PM', u'5:57 PM', u'6:19 PM', u'-', u'-', u'6:46 PM', u'6:57 PM', u'7:13 PM', u'7:24 PM', u'8:04 PM', u'9:04 PM', u'10:04 PM', u'11:04 PM'],
u'San Jose': [u'4:30 AM', u'5:05 AM', u'5:45 AM', u'5:57 AM', u'6:03 AM', u'6:22 AM', u'6:45 AM', u'6:50 AM', u'6:57 AM', u'7:03 AM', u'7:20 AM', u'7:45 AM', u'7:50 AM', u'7:55 AM', u'8:03 AM', u'8:22 AM', u'8:40 AM', u'9:10 AM', u'9:40 AM', u'10:10 AM', u'10:40 AM', u'11:10 AM', u'11:40 AM', u'12:10 PM', u'12:40 PM', u'1:10 PM', u'1:40 PM', u'2:10 PM', u'2:40 PM', u'3:05 PM', u'3:44 PM', u'4:05 PM', u'4:25 PM', u'4:39 PM', u'4:45 PM', u'5:05 PM', u'5:25 PM', u'5:31 PM', u'5:39 PM', u'5:45 PM', u'6:05 PM', u'6:25 PM', u'6:31 PM', u'6:45 PM', u'6:50 PM', u'7:30 PM', u'8:30 PM', u'9:30 PM', u'10:30 PM'],
u'Hillsdale': [u'5:19 AM', u'5:54 AM', u'6:16 AM', u'6:51 AM', u'-', u'7:02 AM', u'7:16 AM', u'7:28 AM', u'7:51 AM', u'-', u'8:02 AM', u'8:16 AM', u'8:28 AM', u'8:51 AM', u'-', u'9:02 AM', u'9:29 AM', u'9:59 AM', u'10:29 AM', u'10:59 AM', u'11:29 AM', u'11:59 AM', u'12:29 PM', u'12:59 PM', u'1:29 PM', u'1:59 PM', u'2:29 PM', u'2:59 PM', u'3:29 PM', u'3:56 PM', u'-', u'4:42 PM', u'-', u'-', u'5:17 PM', u'5:42 PM', u'-', u'6:08 PM', u'-', u'6:17 PM', u'6:42 PM', u'-', u'7:08 PM', u'7:28 PM', u'7:39 PM', u'8:19 PM', u'9:19 PM', u'10:19 PM', u'11:19 PM'],
u'Sunnyvale': [u'4:44 AM', u'5:19 AM', u'-', u'6:18 AM', u'6:13 AM', u'-', u'-', u'7:00 AM', u'7:18 AM', u'7:13 AM', u'-', u'-', u'8:00 AM', u'8:18 AM', u'8:13 AM', u'-', u'8:54 AM', u'9:24 AM', u'9:54 AM', u'10:24 AM', u'10:54 AM', u'11:24 AM', u'11:54 AM', u'12:24 PM', u'12:54 PM', u'1:24 PM', u'1:54 PM', u'2:24 PM', u'2:54 PM', u'3:21 PM', u'3:58 PM', u'-', u'-', u'4:58 PM', u'-', u'-', u'-', u'-', u'5:58 PM', u'-', u'-', u'-', u'-', u'-', u'7:04 PM', u'7:44 PM', u'8:44 PM', u'9:44 PM', u'10:44 PM'],
u'Palo Alto': [u'5:01 AM', u'5:36 AM', u'6:05 AM', u'6:36 AM', u'6:23 AM', u'-', u'7:05 AM', u'7:16 AM', u'7:36 AM', u'7:23 AM', u'-', u'8:05 AM', u'8:16 AM', u'8:36 AM', u'8:23 AM', u'-', u'9:11 AM', u'9:41 AM', u'10:11 AM', u'10:41 AM', u'11:11 AM', u'11:41 AM', u'12:11 PM', u'12:41 PM', u'1:11 PM', u'1:41 PM', u'2:11 PM', u'2:41 PM', u'3:11 PM', u'3:38 PM', u'4:16 PM', u'4:24 PM', u'-', u'5:16 PM', u'5:06 PM', u'5:24 PM', u'-', u'5:54 PM', u'6:16 PM', u'6:06 PM', u'6:24 PM', u'-', u'6:54 PM', u'7:10 PM', u'7:21 PM', u'8:01 PM', u'9:01 PM', u'10:01 PM', u'11:01 PM'],
u'Redwood City': [u'5:09 AM', u'5:44 AM', u'-', u'6:45@ AM', u'6:30 AM', u'6:51@ AM', u'-', u'-', u'7:45@ AM', u'7:30 AM', u'7:51@ AM', u'-', u'-', u'8:45@ AM', u'8:30 AM', u'8:51@ AM', u'9:19 AM', u'9:49 AM', u'10:19 AM', u'10:49 AM', u'11:19 AM', u'11:49 AM', u'12:19 PM', u'12:49 PM', u'1:19 PM', u'1:49 PM', u'2:19 PM', u'2:49 PM', u'3:19 PM', u'3:46 PM', u'4:25@ PM', u'4:31@ PM', u'4:52 PM', u'5:25@ PM', u'-', u'5:31@ PM', u'5:52 PM', u'-', u'6:25@ PM', u'-', u'6:31@ PM', u'6:52 PM', u'-', u'7:19 PM', u'7:29 PM', u'8:09 PM', u'9:09 PM', u'10:09 PM', u'11:09 PM'],
u'San Bruno': [u'5:37 AM', u'6:12 AM', u'-', u'-', u'-', u'7:21 AM', u'-', u'7:42 AM', u'-', u'-', u'8:21 AM', u'-', u'8:42 AM', u'-', u'-', u'9:21 AM', u'9:45 AM', u'10:17 AM', u'10:45 AM', u'11:17 AM', u'11:45 AM', u'12:17 PM', u'12:45 PM', u'1:17 PM', u'1:45 PM', u'2:17 PM', u'2:45 PM', u'3:17 PM', u'3:45 PM', u'4:14 PM', u'-', u'5:01 PM', u'-', u'-', u'-', u'6:01 PM', u'-', u'6:22 PM', u'-', u'-', u'7:01 PM', u'-', u'7:22 PM', u'-', u'7:57 PM', u'8:37 PM', u'9:37 PM', u'10:37 PM', u'11:37 PM'],
u'So. San Francisco': [u'5:41 AM', u'6:16 AM', u'-', u'7:05 AM', u'-', u'7:25 AM', u'-', u'-', u'8:05 AM', u'-', u'8:25 AM', u'-', u'-', u'9:05 AM', u'-', u'9:25 AM', u'-', u'10:21 AM', u'-', u'11:21 AM', u'-', u'12:21 PM', u'-', u'1:21 PM', u'-', u'2:21 PM', u'-', u'3:21 PM', u'-', u'4:18 PM', u'-', u'5:05 PM', u'-', u'-', u'-', u'6:05 PM', u'-', u'-', u'-', u'-', u'7:05 PM', u'-', u'-', u'-', u'8:01 PM', u'8:41 PM', u'9:41 PM', u'10:41 PM', u'11:41 PM'],
u'Capitol': ['', '', '', '', '', '', '', '', u'6:41 AM', '', u'7:04 AM', '', '', u'7:39 AM', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', ''],
u'Morgan Hill': ['', '', '', '', '', '', '', '', u'6:22 AM', '', u'6:45 AM', '', '', u'7:20 AM', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', ''],
u'Belmont': [u'5:16 AM', u'5:51 AM', u'-', u'-', u'-', u'6:58 AM', u'-', u'-', u'-', u'-', u'7:58 AM', u'-', u'-', u'-', u'-', u'8:58 AM', u'9:26 AM', u'9:56 AM', u'10:26 AM', u'10:56 AM', u'11:26 AM', u'11:56 AM', u'12:26 PM', u'12:56 PM', u'1:26 PM', u'1:56 PM', u'2:26 PM', u'2:56 PM', u'3:26 PM', u'3:53 PM', u'-', u'4:38 PM', u'-', u'-', u'-', u'5:38 PM', u'-', u'-', u'-', u'-', u'6:38 PM', u'-', u'-', u'-', u'7:36 PM', u'8:16 PM', u'9:16 PM', u'10:16 PM', u'11:16 PM'],
u'Tamien': ['', u'4:58 AM', '', u'5:50 AM', u'5:56 AM', '', '', '', u'6:49 AM', u'6:56 AM', u'7:12 AM', '', '', u'7:47 AM', u'7:56 AM', '', u'8:33 AM', '', u'9:33 AM', '', u'10:33 AM', '', u'11:33 AM', '', u'12:33 PM', '', u'1:33 PM', '', u'2:33 PM', '', u'3:37 PM', u'3:58 PM', '', u'4:32 PM', '', u'4:58 PM', '', '', u'5:32 PM', '', u'5:58 PM', '', u'6:24 PM', '', '', '', u'8:23 PM', u'9:23 PM', ''],
u'California Ave': [u'4:57 AM', u'5:32 AM', u'-', u'6:31 AM', u'-', u'-', u'-', u'7:11 AM', u'7:31 AM', u'-', u'-', u'-', u'8:11 AM', u'8:31 AM', u'-', u'-', u'9:07 AM', u'9:37 AM', u'10:07 AM', u'10:37 AM', u'11:07 AM', u'11:37 AM', u'12:07 PM', u'12:37 PM', u'1:07 PM', u'1:37 PM', u'2:07 PM', u'2:37 PM', u'3:07 PM', u'3:34 PM', u'4:11 PM', u'-', u'-', u'5:11 PM', u'-', u'-', u'-', u'-', u'6:11 PM', u'-', u'-', u'-', u'-', u'7:06 PM', u'7:17 PM', u'7:57 PM', u'8:57 PM', u'9:57 PM', u'10:57 PM'],
u'Gilroy': ['', '', '', '', '', '', '', '', u'6:07 AM', '', u'6:30 AM', '', '', u'7:05 AM', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '']}

stations[weekday][northbound] = [u'Gilroy', u'San Martin', u'Morgan Hill', u'Blossom Hill', u'Capitol', u'Tamien', u'San Jose', u'College Park', u'Santa Clara', u'Lawrence', u'Sunnyvale', u'Mountain View', u'San Antonio', u'California Ave', u'Palo Alto', u'Menlo Park', u'Redwood City', u'San Carlos', u'Belmont', u'Hillsdale', u'Hayward Park', u'San Mateo', u'Burlingame', u'Millbrae', u'San Bruno', u'So. San Francisco', u'Bayshore', u'22nd Street', u'San Francisco']

service[weekday][southbound] = {u'Santa Clara': [u'6:17 AM', u'6:47 AM', u'-', u'7:34 AM', u'7:56* AM', u'-', u'-', u'-', u'8:34 AM', u'8:56* AM', u'-', u'-', u'-', u'9:34 AM', u'9:56* AM', u'-', u'10:29 AM', u'10:51 AM', u'11:29 AM', u'11:51 AM', u'12:29 PM', u'12:51 PM', u'1:29 PM', u'1:51 PM', u'2:29 PM', u'2:51 PM', u'3:29 PM', u'3:51 PM', u'4:29 PM', u'4:51 PM', u'-', u'-', u'5:47 PM', u'-', u'6:08* PM', u'-', u'-', u'6:48 PM', u'-', u'7:08* PM', u'-', u'7:47 PM', u'-', u'8:04 PM', u'8:52 PM', u'9:52 PM', u'10:52 PM', u'11:52 PM', u'1:23 AM'],
u'Hayward Park': [u'5:29 AM', u'5:59 AM', u'-', u'6:58 AM', u'-', u'-', u'-', u'-', u'7:58 AM', u'-', u'-', u'-', u'-', u'8:58 AM', u'-', u'-', u'9:41 AM', u'-', u'10:41 AM', u'-', u'11:41 AM', u'-', u'12:41 PM', u'-', u'1:41 PM', u'-', u'2:41 PM', u'-', u'3:41 PM', u'-', u'-', u'-', u'5:07 PM', u'-', u'-', u'-', u'-', u'6:07 PM', u'-', u'-', u'-', u'7:07 PM', u'-', u'-', u'8:04 PM', u'9:04 PM', u'10:04 PM', u'11:04 PM', u'12:35 AM'],
u'San Martin': ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', u'5:17 PM', '', '', '', '', '', u'6:54 PM', '', '', u'7:34 PM', '', '', '', '', '', '', '', '', '', '', ''],
u'San Francisco': [u'4:55 AM', u'5:25 AM', u'6:11 AM', u'6:24 AM', u'6:44 AM', u'6:59 AM', u'7:14 AM', u'7:19 AM', u'7:24 AM', u'7:44 AM', u'7:59 AM', u'8:14 AM', u'8:19 AM', u'8:24 AM', u'8:44 AM', u'8:59 AM', u'9:07 AM', u'9:37 AM', u'10:07 AM', u'10:37 AM', u'11:07 AM', u'11:37 AM', u'12:07 PM', u'12:37 PM', u'1:07 PM', u'1:37 PM', u'2:07 PM', u'2:37 PM', u'3:07 PM', u'3:37 PM', u'4:09 PM', u'4:19 PM', u'4:27 PM', u'4:33 PM', u'4:56 PM', u'5:14 PM', u'5:20 PM', u'5:27 PM', u'5:33 PM', u'5:56 PM', u'6:14 PM', u'6:27 PM', u'6:33 PM', u'6:56 PM', u'7:30 PM', u'8:30 PM', u'9:30 PM', u'10:30 PM', u'12:01 AM'],
u'San Mateo': [u'5:26 AM', u'5:56 AM', u'6:36 AM', u'6:55 AM', u'7:07 AM', u'-', u'-', u'7:42 AM', u'7:55 AM', u'8:07 AM', u'-', u'-', u'8:42 AM', u'8:55 AM', u'9:07 AM', u'-', u'9:38 AM', u'10:02 AM', u'10:38 AM', u'11:02 AM', u'11:38 AM', u'12:02 PM', u'12:38 PM', u'1:02 PM', u'1:38 PM', u'2:02 PM', u'2:38 PM', u'3:02 PM', u'3:38 PM', u'4:02 PM', u'-', u'4:42 PM', u'5:04 PM', u'4:57 PM', u'-', u'-', u'5:43 PM', u'6:04 PM', u'5:57 PM', u'-', u'-', u'7:04 PM', u'6:57 PM', u'-', u'8:01 PM', u'9:01 PM', u'10:01 PM', u'11:01 PM', u'12:32 AM'],
u'San Carlos': [u'5:38 AM', u'6:08 AM', u'6:44 AM', u'7:07 AM', u'7:13 AM', u'-', u'-', u'7:50 AM', u'8:07 AM', u'8:13 AM', u'-', u'-', u'8:50 AM', u'9:07 AM', u'9:13 AM', u'-', u'9:50 AM', u'10:12 AM', u'10:50 AM', u'11:12 AM', u'11:50 AM', u'12:12 PM', u'12:50 PM', u'1:12 PM', u'1:50 PM', u'2:12 PM', u'2:50 PM', u'3:12 PM', u'3:50 PM', u'4:12 PM', u'-', u'4:51 PM', u'5:18 PM', u'-', u'-', u'-', u'5:52 PM', u'6:18 PM', u'-', u'-', u'-', u'7:18 PM', u'-', u'-', u'8:13 PM', u'9:13 PM', u'10:13 PM', u'11:13 PM', u'12:44 AM'],
u'College Park': [u'-', u'-', u'-', u'-', u'7:59* AM', u'-', u'-', u'-', u'-', u'-', u'-', u'-', u'-', u'-', u'-', u'-', u'-', u'-', u'-', u'-', u'-', u'-', u'-', u'-', u'-', u'-', u'-', u'-', u'4:32 PM', u'-', u'-', u'-', u'-', u'-', u'-', u'-', u'-', u'-', u'-', u'-', u'-', u'-', u'-', u'-', u'-', u'-', u'-', u'-', u'-'],
u'Lawrence': [u'6:12 AM', u'6:42 AM', u'7:12 AM', u'-', u'7:49* AM', u'-', u'-', u'8:16 AM', u'-', u'8:49* AM', u'-', u'-', u'9:16 AM', u'-', u'9:49* AM', u'-', u'10:24 AM', u'10:46 AM', u'11:24 AM', u'11:46 AM', u'12:24 PM', u'12:46 PM', u'1:24 PM', u'1:46 PM', u'2:24 PM', u'2:46 PM', u'3:24 PM', u'3:46 PM', u'4:24 PM', u'4:46 PM', u'-', u'-', u'-', u'-', u'6:01* PM', u'-', u'-', u'6:43 PM', u'-', u'7:01* PM', u'-', u'-', u'-', u'7:59 PM', u'8:47 PM', u'9:47 PM', u'10:47 PM', u'11:47 PM', u'1:18 AM'],
u'Burlingame': [u'5:23 AM', u'5:53 AM', u'6:33 AM', u'6:52 AM', u'-', u'-', u'-', u'7:38 AM', u'7:52 AM', u'-', u'-', u'-', u'8:38 AM', u'8:52 AM', u'-', u'-', u'9:35 AM', u'9:59 AM', u'10:35 AM', u'10:59 AM', u'11:35 AM', u'11:59 AM', u'12:35 PM', u'12:59 PM', u'1:35 PM', u'1:59 PM', u'2:35 PM', u'2:59 PM', u'3:35 PM', u'3:59 PM', u'-', u'4:38 PM', u'5:00 PM', u'-', u'-', u'-', u'5:39 PM', u'6:00 PM', u'-', u'-', u'-', u'7:00 PM', u'-', u'-', u'7:58 PM', u'8:58 PM', u'9:58 PM', u'10:58 PM', u'12:29 AM'],
u'Mountain View': [u'6:03 AM', u'6:33 AM', u'7:07 AM', u'-', u'7:38 AM', u'7:44 AM', u'7:58 AM', u'8:09 AM', u'-', u'8:38 AM', u'8:44 AM', u'8:58 AM', u'9:09 AM', u'-', u'9:38 AM', u'9:44 AM', u'10:15 AM', u'10:37 AM', u'11:15 AM', u'11:37 AM', u'12:15 PM', u'12:37 PM', u'1:15 PM', u'1:37 PM', u'2:15 PM', u'2:37 PM', u'3:15 PM', u'3:37 PM', u'4:15 PM', u'4:37 PM', u'4:51 PM', u'5:11 PM', u'5:36 PM', u'-', u'5:50 PM', u'5:56 PM', u'6:12 PM', u'6:36 PM', u'-', u'6:50 PM', u'6:56 PM', u'7:36 PM', u'-', u'7:50 PM', u'8:38 PM', u'9:38 PM', u'10:38 PM', u'11:38 PM', u'1:09 AM'],
u'22nd Street': [u'5:00 AM', u'5:30 AM', u'6:16 AM', u'6:29 AM', u'6:49 AM', u'7:04 AM', u'7:19 AM', u'-', u'7:29 AM', u'7:49 AM', u'8:04 AM', u'8:19 AM', u'-', u'8:29 AM', u'8:49 AM', u'9:04 AM', u'9:12 AM', u'-', u'10:12 AM', u'-', u'11:12 AM', u'-', u'12:12 PM', u'-', u'1:12 PM', u'-', u'2:12 PM', u'-', u'3:12 PM', u'-', u'-', u'-', u'4:32 PM', u'-', u'-', u'-', u'-', u'5:32 PM', u'-', u'-', u'-', u'6:32 PM', u'-', u'-', u'7:35 PM', u'8:35 PM', u'9:35 PM', u'10:35 PM', u'12:06 AM'],
u'Bayshore': [u'5:05 AM', u'5:35 AM', u'-', u'6:34 AM', u'-', u'-', u'-', u'-', u'7:34 AM', u'-', u'-', u'-', u'-', u'8:34 AM', u'-', u'-', u'9:17 AM', u'-', u'10:17 AM', u'-', u'11:17 AM', u'-', u'12:17 PM', u'-', u'1:17 PM', u'-', u'2:17 PM', u'-', u'3:17 PM', u'-', u'-', u'-', u'4:40 PM', u'-', u'-', u'-', u'-', u'5:40 PM', u'-', u'-', u'-', u'6:40 PM', u'-', u'-', u'7:40 PM', u'8:40 PM', u'9:40 PM', u'10:40 PM', u'12:11 AM'],
u'San Antonio': [u'5:59 AM', u'6:29 AM', u'-', u'-', u'7:34 AM', u'-', u'-', u'-', u'-', u'8:34 AM', u'-', u'-', u'-', u'-', u'9:34 AM', u'-', u'10:11 AM', u'10:33 AM', u'11:11 AM', u'11:33 AM', u'12:11 PM', u'12:33 PM', u'1:11 PM', u'1:33 PM', u'2:11 PM', u'2:33 PM', u'3:11 PM', u'3:33 PM', u'4:11 PM', u'4:33 PM', u'-', u'-', u'-', u'-', u'5:46 PM', u'-', u'-', u'-', u'-', u'6:46 PM', u'-', u'-', u'-', u'7:46 PM', u'8:34 PM', u'9:34 PM', u'10:34 PM', u'11:34 PM', u'1:05 AM'],
u'Millbrae': [u'5:19 AM', u'5:49 AM', u'6:29 AM', u'6:48 AM', u'7:01 AM', u'7:17 AM', u'7:32 AM', u'-', u'7:48 AM', u'8:01 AM', u'8:17 AM', u'8:32 AM', u'-', u'8:48 AM', u'9:01 AM', u'9:17 AM', u'9:31 AM', u'9:55 AM', u'10:31 AM', u'10:55 AM', u'11:31 AM', u'11:55 AM', u'12:31 PM', u'12:55 PM', u'1:31 PM', u'1:55 PM', u'2:31 PM', u'2:55 PM', u'3:31 PM', u'3:55 PM', u'4:25 PM', u'-', u'4:56 PM', u'4:49 PM', u'5:14 PM', u'5:30 PM', u'-', u'5:56 PM', u'5:49 PM', u'6:14 PM', u'6:30 PM', u'6:56 PM', u'6:49 PM', u'7:14 PM', u'7:54 PM', u'8:54 PM', u'9:54 PM', u'10:54 PM', u'12:25 AM'],
u'Blossom Hill': ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', u'4:58 PM', '', '', '', '', '', u'6:35 PM', '', '', u'7:15 PM', '', '', '', '', '', '', '', '', '', '', ''],
u'Train No.': [u'102', u'104', u'206(x)', u'208(x)', u'210(x)', u'312(b)', u'314(b)', u'216(x)', u'218(x)', u'220(x)', u'322(b)', u'324(b)', u'226(x)', u'228(x)', u'230(x)', u'332(b)', u'134', u'236(x)', u'138', u'240(x)', u'142', u'244(x)', u'146', u'248(x)', u'150', u'252(x)', u'154', u'256(x)', u'158', u'260(x)', u'362(b)', u'264(x)', u'266(x)', u'368(b)', u'270(x)', u'372(b)', u'274(x)', u'276(x)', u'378(b)', u'280(x)', u'382(b)', u'284(x)', u'386(b)', u'288(x)', u'190', u'192', u'194', u'196', u'198'],
u'Menlo Park': [u'5:48 AM', u'6:18 AM', u'6:54 AM', u'-', u'7:23 AM', u'7:35 AM', u'-', u'7:58 AM', u'-', u'8:23 AM', u'8:35 AM', u'-', u'8:58 AM', u'-', u'9:23 AM', u'9:35 AM', u'10:00 AM', u'10:22 AM', u'11:00 AM', u'11:22 AM', u'12:00 PM', u'12:22 PM', u'1:00 PM', u'1:22 PM', u'2:00 PM', u'2:22 PM', u'3:00 PM', u'3:22 PM', u'4:00 PM', u'4:22 PM', u'-', u'-', u'5:28 PM', u'-', u'5:34 PM', u'-', u'-', u'6:28 PM', u'-', u'6:34 PM', u'-', u'7:28 PM', u'-', u'7:34 PM', u'8:23 PM', u'9:23 PM', u'10:23 PM', u'11:23 PM', u'12:54 AM'],
u'San Jose': [u'6:26 AM', u'6:56 AM', u'7:24 AM', u'7:43 AM', u'8:06 AM', u'7:58 AM', u'8:13 AM', u'8:28 AM', u'8:43 AM', u'9:05 AM', u'8:58 AM', u'9:13 AM', u'9:28 AM', u'9:43 AM', u'10:05 AM', u'9:58 AM', u'10:38 AM', u'11:00 AM', u'11:38 AM', u'12:00 PM', u'12:38 PM', u'1:00 PM', u'1:38 PM', u'2:00 PM', u'2:38 PM', u'3:00 PM', u'3:38 PM', u'4:00 PM', u'4:39 PM', u'5:00 PM', u'5:06 PM', u'5:27 PM', u'5:55 PM', u'5:32 PM', u'6:16 PM', u'6:11 PM', u'6:28 PM', u'6:56 PM', u'6:32 PM', u'7:16 PM', u'7:11 PM', u'7:55 PM', u'7:32 PM', u'8:12 PM', u'9:01 PM', u'10:01 PM', u'11:01 PM', u'12:01 AM', u'1:32 AM'],
u'Hillsdale': [u'5:32 AM', u'6:02 AM', u'6:40 AM', u'7:01 AM', u'-', u'-', u'7:40 AM', u'7:46 AM', u'8:01 AM', u'-', u'-', u'8:40 AM', u'8:46 AM', u'9:01 AM', u'-', u'-', u'9:44 AM', u'10:06 AM', u'10:44 AM', u'11:06 AM', u'11:44 AM', u'12:06 PM', u'12:44 PM', u'1:06 PM', u'1:44 PM', u'2:06 PM', u'2:44 PM', u'3:06 PM', u'3:44 PM', u'4:06 PM', u'4:33 PM', u'4:47 PM', u'5:11 PM', u'-', u'5:22 PM', u'5:38 PM', u'5:48 PM', u'6:11 PM', u'-', u'6:22 PM', u'6:38 PM', u'7:11 PM', u'-', u'7:22 PM', u'8:07 PM', u'9:07 PM', u'10:07 PM', u'11:07 PM', u'12:38 AM'],
u'Sunnyvale': [u'6:08 AM', u'6:38 AM', u'-', u'-', u'7:43 AM', u'-', u'-', u'-', u'-', u'8:43 AM', u'-', u'-', u'-', u'-', u'9:43 AM', u'-', u'10:20 AM', u'10:42 AM', u'11:20 AM', u'11:42 AM', u'12:20 PM', u'12:42 PM', u'1:20 PM', u'1:42 PM', u'2:20 PM', u'2:42 PM', u'3:20 PM', u'3:42 PM', u'4:20 PM', u'4:42 PM', u'-', u'5:16 PM', u'-', u'5:21 PM', u'5:55 PM', u'-', u'6:17 PM', u'-', u'6:21 PM', u'6:55 PM', u'-', u'-', u'7:21 PM', u'7:55 PM', u'8:43 PM', u'9:43 PM', u'10:43 PM', u'11:43 PM', u'1:14 AM'],
u'Palo Alto': [u'5:51 AM', u'6:21 AM', u'6:57 AM', u'7:18 AM', u'7:26 AM', u'-', u'7:51 AM', u'8:01 AM', u'8:18 AM', u'8:26 AM', u'-', u'8:51 AM', u'9:01 AM', u'9:18 AM', u'9:26 AM', u'-', u'10:03 AM', u'10:25 AM', u'11:03 AM', u'11:25 AM', u'12:03 PM', u'12:25 PM', u'1:03 PM', u'1:25 PM', u'2:03 PM', u'2:25 PM', u'3:03 PM', u'3:25 PM', u'4:03 PM', u'4:25 PM', u'4:44 PM', u'5:01 PM', u'-', u'5:12 PM', u'5:38 PM', u'5:49 PM', u'6:02 PM', u'-', u'6:12 PM', u'6:38 PM', u'6:49 PM', u'-', u'7:12 PM', u'7:38 PM', u'8:26 PM', u'9:26 PM', u'10:26 PM', u'11:26 PM', u'12:57 AM'],
u'Redwood City': [u'5:43 AM', u'6:13 AM', u'6:49 AM', u'7:12@ AM', u'7:18@ AM', u'7:30 AM', u'-', u'-', u'8:12@ AM', u'8:18@ AM', u'8:30 AM', u'-', u'-', u'9:12@ AM', u'9:18@ AM', u'9:30 AM', u'9:55 AM', u'10:17 AM', u'10:55 AM', u'11:17 AM', u'11:55 AM', u'12:17 PM', u'12:55 PM', u'1:17 PM', u'1:55 PM', u'2:17 PM', u'2:55 PM', u'3:17 PM', u'3:55 PM', u'4:17 PM', u'-', u'-', u'5:22@ PM', u'5:06 PM', u'5:28@ PM', u'-', u'-', u'6:22@ PM', u'6:06 PM', u'6:28@ PM', u'-', u'7:22@ PM', u'7:06 PM', u'7:28@ PM', u'8:18 PM', u'9:18 PM', u'10:18 PM', u'11:18 PM', u'12:49 AM'],
u'San Bruno': [u'5:15 AM', u'5:45 AM', u'-', u'6:44 AM', u'-', u'-', u'-', u'7:33 AM', u'7:44 AM', u'-', u'-', u'-', u'8:33 AM', u'8:44 AM', u'-', u'-', u'9:27 AM', u'9:51 AM', u'10:27 AM', u'10:51 AM', u'11:27 AM', u'11:51 AM', u'12:27 PM', u'12:51 PM', u'1:27 PM', u'1:51 PM', u'2:27 PM', u'2:51 PM', u'3:27 PM', u'3:51 PM', u'-', u'4:33 PM', u'4:52 PM', u'-', u'-', u'-', u'5:34 PM', u'5:52 PM', u'-', u'-', u'-', u'6:52 PM', u'-', u'-', u'7:50 PM', u'8:50 PM', u'9:50 PM', u'10:50 PM', u'12:21 AM'],
u'So. San Francisco': [u'5:11 AM', u'5:41 AM', u'-', u'6:40 AM', u'-', u'-', u'-', u'-', u'7:40 AM', u'-', u'-', u'-', u'-', u'8:40 AM', u'-', u'-', u'9:23 AM', u'-', u'10:23 AM', u'-', u'11:23 AM', u'-', u'12:23 PM', u'-', u'1:23 PM', u'-', u'2:23 PM', u'-', u'3:23 PM', u'-', u'-', u'-', u'4:48 PM', u'-', u'5:08 PM', u'-', u'-', u'5:48 PM', u'-', u'6:08 PM', u'-', u'6:48 PM', u'-', u'7:08 PM', u'7:46 PM', u'8:46 PM', u'9:46 PM', u'10:46 PM', u'12:17 AM'],
u'Capitol': ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', u'4:52 PM', '', '', '', '', '', u'6:29 PM', '', '', u'7:09 PM', '', '', '', '', '', '', '', '', '', '', ''],
u'Morgan Hill': ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', u'5:11 PM', '', '', '', '', '', u'6:48 PM', '', '', u'7:28 PM', '', '', '', '', '', '', '', '', '', '', ''],
u'Belmont': [u'5:35 AM', u'6:05 AM', u'-', u'7:04 AM', u'-', u'-', u'-', u'-', u'8:04 AM', u'-', u'-', u'-', u'-', u'9:04 AM', u'-', u'-', u'9:47 AM', u'10:09 AM', u'10:47 AM', u'11:09 AM', u'11:47 AM', u'12:09 PM', u'12:47 PM', u'1:09 PM', u'1:47 PM', u'2:09 PM', u'2:47 PM', u'3:09 PM', u'3:47 PM', u'4:09 PM', u'-', u'-', u'5:14 PM', u'-', u'-', u'-', u'-', u'6:14 PM', u'-', u'-', u'-', u'7:14 PM', u'-', u'-', u'8:10 PM', u'9:10 PM', u'10:10 PM', u'11:10 PM', u'12:41 AM'],
u'Tamien': ['', u'7:03 AM', '', u'7:50 AM', u'8:13 AM', '', '', '', u'8:50 AM', u'9:12 AM', '', '', '', u'9:50 AM', u'10:12 AM', '', '', u'11:07 AM', '', u'12:07 PM', '', u'1:07 PM', '', u'2:07 PM', '', u'3:07 PM', '', u'4:07 PM', u'4:45 PM', u'5:07 PM', '', '', '', u'5:39 PM', u'6:22 PM', '', '', u'7:02 PM', u'6:39 PM', u'7:23 PM', '', '', u'7:39 PM', u'8:19 PM', '', u'10:08 PM', u'11:08 PM', '', ''],
u'California Ave': [u'5:55 AM', u'6:25 AM', u'7:01 AM', u'-', u'7:30 AM', u'-', u'-', u'-', u'-', u'8:30 AM', u'-', u'-', u'-', u'-', u'9:30 AM', u'-', u'10:07 AM', u'10:29 AM', u'11:07 AM', u'11:29 AM', u'12:07 PM', u'12:29 PM', u'1:07 PM', u'1:29 PM', u'2:07 PM', u'2:29 PM', u'3:07 PM', u'3:29 PM', u'4:07 PM', u'4:29 PM', u'-', u'5:05 PM', u'-', u'-', u'5:42 PM', u'-', u'6:06 PM', u'-', u'-', u'6:42 PM', u'-', u'-', u'-', u'7:42 PM', u'8:30 PM', u'9:30 PM', u'10:30 PM', u'11:30 PM', u'1:01 AM'],
u'Gilroy': ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', u'5:30 PM', '', '', '', '', '', u'7:07 PM', '', '', u'7:47 PM', '', '', '', '', '', '', '', '', '', '', '']}

stations[weekday][southbound] = [u'San Francisco', u'22nd Street', u'Bayshore', u'So. San Francisco', u'San Bruno', u'Millbrae', u'Burlingame', u'San Mateo', u'Hayward Park', u'Hillsdale', u'Belmont', u'San Carlos', u'Redwood City', u'Menlo Park', u'Palo Alto', u'California Ave', u'San Antonio', u'Mountain View', u'Sunnyvale', u'Lawrence', u'Santa Clara', u'College Park', u'San Jose', u'Tamien', u'Capitol', u'Blossom Hill', u'Morgan Hill', u'San Martin', u'Gilroy']

service[weekend][northbound] = {u'Shuttle Bus arr. S.J.': [u'', u'7:45 AM', u'8:45 AM', u'9:45 AM', u'10:45 AM', u'11:45 AM', u'12:45 PM', u'1:45 PM', u'2:45 PM', u'3:45 PM', u'4:45 PM', u'5:45 PM', u'6:45 PM', u'7:45 PM', u'', u''],
u'Santa Clara': [u'7:05 AM', u'8:05 AM', u'9:05 AM', u'10:05 AM', u'11:05 AM', u'12:05 PM', u'1:05 PM', u'2:05 PM', u'3:05 PM', u'4:05 PM', u'5:05 PM', u'6:05 PM', u'7:05 PM', u'8:05 PM', u'9:05 PM', u'10:35 PM'],
u'Hayward Park': [u'7:54 AM', u'8:54 AM', u'9:54 AM', u'10:54 AM', u'11:54 AM', u'12:54 PM', u'1:54 PM', u'2:54 PM', u'3:54 PM', u'4:54 PM', u'5:54 PM', u'6:54 PM', u'7:54 PM', u'8:54 PM', u'9:54 PM', u'11:24 PM'],
u'San Francisco': [u'8:36 AM', u'9:36 AM', u'10:36 AM', u'11:36 AM', u'12:36 PM', u'1:36 PM', u'2:36 PM', u'3:36 PM', u'4:36 PM', u'5:36 PM', u'6:36 PM', u'7:36 PM', u'8:36 PM', u'9:36 PM', u'10:36 PM', u'12:06 AM'],
u'San Mateo': [u'7:57 AM', u'8:57 AM', u'9:57 AM', u'10:57 AM', u'11:57 AM', u'12:57 PM', u'1:57 PM', u'2:57 PM', u'3:57 PM', u'4:57 PM', u'5:57 PM', u'6:57 PM', u'7:57 PM', u'8:57 PM', u'9:57 PM', u'11:27 PM'],
u'San Carlos': [u'7:45 AM', u'8:45 AM', u'9:45 AM', u'10:45 AM', u'11:45 AM', u'12:45 PM', u'1:45 PM', u'2:45 PM', u'3:45 PM', u'4:45 PM', u'5:45 PM', u'6:45 PM', u'7:45 PM', u'8:45 PM', u'9:45 PM', u'11:15 PM'],
u'Atherton': [u'7:37 AM', u'8:37 AM', u'9:37 AM', u'10:37 AM', u'11:37 AM', u'12:37 PM', u'1:37 PM', u'2:37 PM', u'3:37 PM', u'4:37 PM', u'5:37 PM', u'6:37 PM', u'7:37 PM', u'8:37 PM', u'9:37 PM', u'11:07 PM'],
u'Lawrence': [u'7:10 AM', u'8:10 AM', u'9:10 AM', u'10:10 AM', u'11:10 AM', u'12:10 PM', u'1:10 PM', u'2:10 PM', u'3:10 PM', u'4:10 PM', u'5:10 PM', u'6:10 PM', u'7:10 PM', u'8:10 PM', u'9:10 PM', u'10:40 PM'],
u'Burlingame': [u'8:00 AM', u'9:00 AM', u'10:00 AM', u'11:00 AM', u'12:00 PM', u'1:00 PM', u'2:00 PM', u'3:00 PM', u'4:00 PM', u'5:00 PM', u'6:00 PM', u'7:00 PM', u'8:00 PM', u'9:00 PM', u'10:00 PM', u'11:30 PM'],
u'Mountain View': [u'7:19 AM', u'8:19 AM', u'9:19 AM', u'10:19 AM', u'11:19 AM', u'12:19 PM', u'1:19 PM', u'2:19 PM', u'3:19 PM', u'4:19 PM', u'5:19 PM', u'6:19 PM', u'7:19 PM', u'8:19 PM', u'9:19 PM', u'10:49 PM'],
u'22nd Street': [u'8:28 AM', u'9:28 AM', u'10:28 AM', u'11:28 AM', u'12:28 PM', u'1:28 PM', u'2:28 PM', u'3:28 PM', u'4:28 PM', u'5:28 PM', u'6:28 PM', u'7:28 PM', u'8:28 PM', u'9:28 PM', u'10:28 PM', u'11:58 PM'],
u'Shuttle dep. Tamien': [u'', u'7:31 AM', u'8:31 AM', u'9:31 AM', u'10:31 AM', u'11:31 AM', u'12:31 PM', u'1:31 PM', u'2:31 PM', u'3:31 PM', u'4:31 PM', u'5:31 PM', u'6:31 PM', u'7:31 PM', u'', u''],
u'San Antonio': [u'7:23 AM', u'8:23 AM', u'9:23 AM', u'10:23 AM', u'11:23 AM', u'12:23 PM', u'1:23 PM', u'2:23 PM', u'3:23 PM', u'4:23 PM', u'5:23 PM', u'6:23 PM', u'7:23 PM', u'8:23 PM', u'9:23 PM', u'10:53 PM'],
u'Millbrae': [u'8:08 AM', u'9:08 AM', u'10:08 AM', u'11:08 AM', u'12:08 PM', u'1:08 PM', u'2:08 PM', u'3:08 PM', u'4:08 PM', u'5:08 PM', u'6:08 PM', u'7:08 PM', u'8:08 PM', u'9:08 PM', u'10:08 PM', u'11:38 PM'],
u'Bayshore': [u'8:23 AM', u'9:23 AM', u'10:23 AM', u'11:23 AM', u'12:23 PM', u'1:23 PM', u'2:23 PM', u'3:23 PM', u'4:23 PM', u'5:23 PM', u'6:23 PM', u'7:23 PM', u'8:23 PM', u'9:23 PM', u'10:23 PM', u'11:53 PM'],
u'Train No.': [u'421 SAT. only', u'423', u'425', u'427', u'429', u'431', u'433', u'435', u'437', u'439', u'441', u'443', u'445', u'447', u'449', u'451# SAT. only'],
u'Menlo Park': [u'7:34 AM', u'8:34 AM', u'9:34 AM', u'10:34 AM', u'11:34 AM', u'12:34 PM', u'1:34 PM', u'2:34 PM', u'3:34 PM', u'4:34 PM', u'5:34 PM', u'6:34 PM', u'7:34 PM', u'8:34 PM', u'9:34 PM', u'11:04 PM'],
u'San Jose': [u'7:00 AM', u'8:00 AM', u'9:00 AM', u'10:00 AM', u'11:00 AM', u'12:00 PM', u'1:00 PM', u'2:00 PM', u'3:00 PM', u'4:00 PM', u'5:00 PM', u'6:00 PM', u'7:00 PM', u'8:00 PM', u'9:00 PM', u'10:30 PM'],
u'Hillsdale': [u'7:51 AM', u'8:51 AM', u'9:51 AM', u'10:51 AM', u'11:51 AM', u'12:51 PM', u'1:51 PM', u'2:51 PM', u'3:51 PM', u'4:51 PM', u'5:51 PM', u'6:51 PM', u'7:51 PM', u'8:51 PM', u'9:51 PM', u'11:21 PM'],
u'Sunnyvale': [u'7:14 AM', u'8:14 AM', u'9:14 AM', u'10:14 AM', u'11:14 AM', u'12:14 PM', u'1:14 PM', u'2:14 PM', u'3:14 PM', u'4:14 PM', u'5:14 PM', u'6:14 PM', u'7:14 PM', u'8:14 PM', u'9:14 PM', u'10:44 PM'],
u'Palo Alto': [u'7:31 AM', u'8:31 AM', u'9:31 AM', u'10:31 AM', u'11:31 AM', u'12:31 PM', u'1:31 PM', u'2:31 PM', u'3:31 PM', u'4:31 PM', u'5:31 PM', u'6:31 PM', u'7:31 PM', u'8:31 PM', u'9:31 PM', u'11:01 PM'],
u'Redwood City': [u'7:41 AM', u'8:41 AM', u'9:41 AM', u'10:41 AM', u'11:41 AM', u'12:41 PM', u'1:41 PM', u'2:41 PM', u'3:41 PM', u'4:41 PM', u'5:41 PM', u'6:41 PM', u'7:41 PM', u'8:41 PM', u'9:41 PM', u'11:11 PM'],
u'San Bruno': [u'8:12 AM', u'9:12 AM', u'10:12 AM', u'11:12 AM', u'12:12 PM', u'1:12 PM', u'2:12 PM', u'3:12 PM', u'4:12 PM', u'5:12 PM', u'6:12 PM', u'7:12 PM', u'8:12 PM', u'9:12 PM', u'10:12 PM', u'11:42 PM'],
u'So. San Francisco': [u'8:17 AM', u'9:17 AM', u'10:17 AM', u'11:17 AM', u'12:17 PM', u'1:17 PM', u'2:17 PM', u'3:17 PM', u'4:17 PM', u'5:17 PM', u'6:17 PM', u'7:17 PM', u'8:17 PM', u'9:17 PM', u'10:17 PM', u'11:47 PM'],
u'Belmont': [u'7:48 AM', u'8:48 AM', u'9:48 AM', u'10:48 AM', u'11:48 AM', u'12:48 PM', u'1:48 PM', u'2:48 PM', u'3:48 PM', u'4:48 PM', u'5:48 PM', u'6:48 PM', u'7:48 PM', u'8:48 PM', u'9:48 PM', u'11:18 PM'],
u'Broadway': [u'8:03 AM', u'9:03 AM', u'10:03 AM', u'11:03 AM', u'12:03 PM', u'1:03 PM', u'2:03 PM', u'3:03 PM', u'4:03 PM', u'5:03 PM', u'6:03 PM', u'7:03 PM', u'8:03 PM', u'9:03 PM', u'10:03 PM', u'11:33 PM'],
u'California Ave': [u'7:27 AM', u'8:27 AM', u'9:27 AM', u'10:27 AM', u'11:27 AM', u'12:27 PM', u'1:27 PM', u'2:27 PM', u'3:27 PM', u'4:27 PM', u'5:27 PM', u'6:27 PM', u'7:27 PM', u'8:27 PM', u'9:27 PM', u'10:57 PM']}

stations[weekend][northbound] = [u'Shuttle dep. Tamien', u'Shuttle Bus arr. S.J.', u'San Jose', u'Santa Clara', u'Lawrence', u'Sunnyvale', u'Mountain View', u'San Antonio', u'California Ave', u'Palo Alto', u'Menlo Park', u'Atherton', u'Redwood City', u'San Carlos', u'Belmont', u'Hillsdale', u'Hayward Park', u'San Mateo', u'Burlingame', u'Broadway', u'Millbrae', u'San Bruno', u'So. San Francisco', u'Bayshore', u'22nd Street', u'San Francisco']

service[weekend][southbound] = {u'Santa Clara': [u'9:28 AM', u'10:28 AM', u'11:28 AM', u'12:28 PM', u'1:28 PM', u'2:28 PM', u'3:28 PM', u'4:28 PM', u'5:28 PM', u'6:28 PM', u'7:28 PM', u'8:28 PM', u'9:28 PM', u'10:28 PM', u'11:28 PM', u'1:29 AM'],
u'Hayward Park': [u'8:37 AM', u'9:37 AM', u'10:37 AM', u'11:37 AM', u'12:37 PM', u'1:37 PM', u'2:37 PM', u'3:37 PM', u'4:37 PM', u'5:37 PM', u'6:37 PM', u'7:37 PM', u'8:37 PM', u'9:37 PM', u'10:37 PM', u'12:38 AM'],
u'San Francisco': [u'8:00 AM', u'9:00 AM', u'10:00 AM', u'11:00 AM', u'12:00 PM', u'1:00 PM', u'2:00 PM', u'3:00 PM', u'4:00 PM', u'5:00 PM', u'6:00 PM', u'7:00 PM', u'8:00 PM', u'9:00 PM', u'10:00 PM', u'12:01 AM'],
u'San Mateo': [u'8:34 AM', u'9:34 AM', u'10:34 AM', u'11:34 AM', u'12:34 PM', u'1:34 PM', u'2:34 PM', u'3:34 PM', u'4:34 PM', u'5:34 PM', u'6:34 PM', u'7:34 PM', u'8:34 PM', u'9:34 PM', u'10:34 PM', u'12:35 AM'],
u'San Carlos': [u'8:46 AM', u'9:46 AM', u'10:46 AM', u'11:46 AM', u'12:46 PM', u'1:46 PM', u'2:46 PM', u'3:46 PM', u'4:46 PM', u'5:46 PM', u'6:46 PM', u'7:46 PM', u'8:46 PM', u'9:46 PM', u'10:46 PM', u'12:47 AM'],
u'Atherton': [u'8:56 AM', u'9:56 AM', u'10:56 AM', u'11:56 AM', u'12:56 PM', u'1:56 PM', u'2:56 PM', u'3:56 PM', u'4:56 PM', u'5:56 PM', u'6:56 PM', u'7:56 PM', u'8:56 PM', u'9:56 PM', u'10:56 PM', u'12:57 AM'],
u'Lawrence': [u'9:23 AM', u'10:23 AM', u'11:23 AM', u'12:23 PM', u'1:23 PM', u'2:23 PM', u'3:23 PM', u'4:23 PM', u'5:23 PM', u'6:23 PM', u'7:23 PM', u'8:23 PM', u'9:23 PM', u'10:23 PM', u'11:23 PM', u'1:24 AM'],
u'Burlingame': [u'8:30 AM', u'9:30 AM', u'10:30 AM', u'11:30 AM', u'12:30 PM', u'1:30 PM', u'2:30 PM', u'3:30 PM', u'4:30 PM', u'5:30 PM', u'6:30 PM', u'7:30 PM', u'8:30 PM', u'9:30 PM', u'10:30 PM', u'12:31 AM'],
u'Mountain View': [u'9:14 AM', u'10:14 AM', u'11:14 AM', u'12:14 PM', u'1:14 PM', u'2:14 PM', u'3:14 PM', u'4:14 PM', u'5:14 PM', u'6:14 PM', u'7:14 PM', u'8:14 PM', u'9:14 PM', u'10:14 PM', u'11:14 PM', u'1:15 AM'],
u'22nd Street': [u'8:05 AM', u'9:05 AM', u'10:05 AM', u'11:05 AM', u'12:05 PM', u'1:05 PM', u'2:05 PM', u'3:05 PM', u'4:05 PM', u'5:05 PM', u'6:05 PM', u'7:05 PM', u'8:05 PM', u'9:05 PM', u'10:05 PM', u'12:06 AM'],
u'Bayshore': [u'8:10 AM', u'9:10 AM', u'10:10 AM', u'11:10 AM', u'12:10 PM', u'1:10 PM', u'2:10 PM', u'3:10 PM', u'4:10 PM', u'5:10 PM', u'6:10 PM', u'7:10 PM', u'8:10 PM', u'9:10 PM', u'10:10 PM', u'12:11 AM'],
u'San Antonio': [u'9:10 AM', u'10:10 AM', u'11:10 AM', u'12:10 PM', u'1:10 PM', u'2:10 PM', u'3:10 PM', u'4:10 PM', u'5:10 PM', u'6:10 PM', u'7:10 PM', u'8:10 PM', u'9:10 PM', u'10:10 PM', u'11:10 PM', u'1:11 AM'],
u'Millbrae': [u'8:24 AM', u'9:24 AM', u'10:24 AM', u'11:24 AM', u'12:24 PM', u'1:24 PM', u'2:24 PM', u'3:24 PM', u'4:24 PM', u'5:24 PM', u'6:24 PM', u'7:24 PM', u'8:24 PM', u'9:24 PM', u'10:24 PM', u'12:25 AM'],
u'Train No.': [u'422', u'424', u'426', u'428', u'430', u'432', u'434', u'436', u'438', u'440', u'442', u'444', u'446', u'448', u'450 SAT. only', u'454 SAT. only'],
u'Menlo Park': [u'8:59 AM', u'9:59 AM', u'10:59 AM', u'11:59 AM', u'12:59 PM', u'1:59 PM', u'2:59 PM', u'3:59 PM', u'4:59 PM', u'5:59 PM', u'6:59 PM', u'7:59 PM', u'8:59 PM', u'9:59 PM', u'10:59 PM', u'1:00 AM'],
u'San Jose': [u'9:36 AM', u'10:36 AM', u'11:36 AM', u'12:36 PM', u'1:36 PM', u'2:36 PM', u'3:36 PM', u'4:36 PM', u'5:36 PM', u'6:36 PM', u'7:36 PM', u'8:36 PM', u'9:36 PM', u'10:36 PM', u'11:36 PM', u'1:37 AM'],
u'Hillsdale': [u'8:40 AM', u'9:40 AM', u'10:40 AM', u'11:40 AM', u'12:40 PM', u'1:40 PM', u'2:40 PM', u'3:40 PM', u'4:40 PM', u'5:40 PM', u'6:40 PM', u'7:40 PM', u'8:40 PM', u'9:40 PM', u'10:40 PM', u'12:41 AM'],
u'Shuttle arr. Tamien': [u'10:03 AM', u'11:03 AM', u'12:03 PM', u'1:03 PM', u'2:03 PM', u'3:03 PM', u'4:03 PM', u'5:03 PM', u'6:03 PM', u'7:03 PM', u'8:03 PM', u'9:03 PM', u'10:03 PM', u'', u'', u''],
u'Sunnyvale': [u'9:19 AM', u'10:19 AM', u'11:19 AM', u'12:19 PM', u'1:19 PM', u'2:19 PM', u'3:19 PM', u'4:19 PM', u'5:19 PM', u'6:19 PM', u'7:19 PM', u'8:19 PM', u'9:19 PM', u'10:19 PM', u'11:19 PM', u'1:20 AM'],
u'Palo Alto': [u'9:02 AM', u'10:02 AM', u'11:02 AM', u'12:02 PM', u'1:02 PM', u'2:02 PM', u'3:02 PM', u'4:02 PM', u'5:02 PM', u'6:02 PM', u'7:02 PM', u'8:02 PM', u'9:02 PM', u'10:02 PM', u'11:02 PM', u'1:03 AM'],
u'Shuttle Bus dep. SJ': [u'9:55 AM', u'10:55 AM', u'11:55 AM', u'12:55 PM', u'1:55 PM', u'2:55 PM', u'3:55 PM', u'4:55 PM', u'5:55 PM', u'6:55 PM', u'7:55 PM', u'8:55 PM', u'9:55 PM', u'', u'', u''],
u'Redwood City': [u'8:52 AM', u'9:52 AM', u'10:52 AM', u'11:52 AM', u'12:52 PM', u'1:52 PM', u'2:52 PM', u'3:52 PM', u'4:52 PM', u'5:52 PM', u'6:52 PM', u'7:52 PM', u'8:52 PM', u'9:52 PM', u'10:52 PM', u'12:53 AM'],
u'San Bruno': [u'8:20 AM', u'9:20 AM', u'10:20 AM', u'11:20 AM', u'12:20 PM', u'1:20 PM', u'2:20 PM', u'3:20 PM', u'4:20 PM', u'5:20 PM', u'6:20 PM', u'7:20 PM', u'8:20 PM', u'9:20 PM', u'10:20 PM', u'12:21 AM'],
u'So. San Francisco': [u'8:16 AM', u'9:16 AM', u'10:16 AM', u'11:16 AM', u'12:16 PM', u'1:16 PM', u'2:16 PM', u'3:16 PM', u'4:16 PM', u'5:16 PM', u'6:16 PM', u'7:16 PM', u'8:16 PM', u'9:16 PM', u'10:16 PM', u'12:17 AM'],
u'Belmont': [u'8:43 AM', u'9:43 AM', u'10:43 AM', u'11:43 AM', u'12:43 PM', u'1:43 PM', u'2:43 PM', u'3:43 PM', u'4:43 PM', u'5:43 PM', u'6:43 PM', u'7:43 PM', u'8:43 PM', u'9:43 PM', u'10:43 PM', u'12:44 AM'],
u'Broadway': [u'8:28 AM', u'9:28 AM', u'10:28 AM', u'11:28 AM', u'12:28 PM', u'1:28 PM', u'2:28 PM', u'3:28 PM', u'4:28 PM', u'5:28 PM', u'6:28 PM', u'7:28 PM', u'8:28 PM', u'9:28 PM', u'10:28 PM', u'12:29 AM'],
u'California Ave': [u'9:06 AM', u'10:06 AM', u'11:06 AM', u'12:06 PM', u'1:06 PM', u'2:06 PM', u'3:06 PM', u'4:06 PM', u'5:06 PM', u'6:06 PM', u'7:06 PM', u'8:06 PM', u'9:06 PM', u'10:06 PM', u'11:06 PM', u'1:07 AM']}

stations[weekend][southbound] = [u'San Francisco', u'22nd Street', u'Bayshore', u'So. San Francisco', u'San Bruno', u'Millbrae', u'Broadway', u'Burlingame', u'San Mateo', u'Hayward Park', u'Hillsdale', u'Belmont', u'San Carlos', u'Redwood City', u'Atherton', u'Menlo Park', u'Palo Alto', u'California Ave', u'San Antonio', u'Mountain View', u'Sunnyvale', u'Lawrence', u'Santa Clara', u'San Jose', u'Shuttle Bus dep. SJ', u'Shuttle arr. Tamien']

###
# http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/52266
class MultiListbox(Frame):
    def __init__(self, master, lists):
        if not have_tkinter:
            raise Exception('Need Tkinter')
        
	Frame.__init__(self, master)
	self.lists = []
	for l,w in lists:
	    frame = Frame(self); frame.pack(side=LEFT, expand=YES, fill=BOTH)
	    Label(frame, text=l, borderwidth=1, relief=RAISED).pack(fill=X)
	    lb = Listbox(frame, width=w, borderwidth=0, selectborderwidth=0,
			 relief=FLAT, exportselection=FALSE)
	    lb.pack(expand=YES, fill=BOTH)
	    self.lists.append(lb)
	    lb.bind('<B1-Motion>', lambda e, s=self: s._select(e.y))
	    lb.bind('<Button-1>', lambda e, s=self: s._select(e.y))
	    lb.bind('<Leave>', lambda e: 'break')
	    lb.bind('<B2-Motion>', lambda e, s=self: s._b2motion(e.x, e.y))
	    lb.bind('<Button-2>', lambda e, s=self: s._button2(e.x, e.y))
            lb.bind('<Button-4>',lambda e,s=self: s._scroll(SCROLL, -1, UNITS))
            lb.bind('<Button-5>',lambda e,s=self: s._scroll(SCROLL, 1, UNITS)) 
            lb.bind('<Up>',lambda e,s=self: s._scroll(SCROLL, -1, UNITS))
            lb.bind('<Down>',lambda e,s=self: s._scroll(SCROLL, 1, UNITS)) 
	frame = Frame(self); frame.pack(side=LEFT, fill=Y)
	Label(frame, borderwidth=1, relief=RAISED).pack(fill=X)
	sb = Scrollbar(frame, orient=VERTICAL, command=self._scroll)
	sb.pack(expand=YES, fill=Y)
	self.lists[0]['yscrollcommand']=sb.set

    def _select(self, y):
	row = self.lists[0].nearest(y)
        self.lists[0].focus_set()
	self.selection_clear(0, END)
	self.selection_set(row)
	return 'break'

    def _button2(self, x, y):
	for l in self.lists: l.scan_mark(x, y)
	return 'break'

    def _b2motion(self, x, y):
	for l in self.lists: l.scan_dragto(x, y)
	return 'break'

    def _scroll(self, *args):
	for l in self.lists:
	    apply(l.yview, args)
        return 'break'

    def curselection(self):
	return self.lists[0].curselection()

    def delete(self, first, last=None):
	for l in self.lists:
	    l.delete(first, last)

    def get(self, first, last=None):
	result = []
	for l in self.lists:
	    result.append(l.get(first,last))
	if last: return apply(map, [None] + result)
	return result
	    
    def index(self, index):
	self.lists[0].index(index)

    def insert(self, index, *elements):
	for e in elements:
	    i = 0
	    for l in self.lists:
		l.insert(index, e[i])
		i = i + 1

    def size(self):
	return self.lists[0].size()

    def see(self, index):
	for l in self.lists:
	    l.see(index)

    def selection_anchor(self, index):
	for l in self.lists:
	    l.selection_anchor(index)

    def selection_clear(self, first, last=None):
	for l in self.lists:
	    l.selection_clear(first, last)

    def selection_includes(self, index):
	return self.lists[0].selection_includes(index)

    def selection_set(self, first, last=None):
	for l in self.lists:
	    l.selection_set(first, last)
#
###


class Caltrain(object):
    def __init__(self):
        self.root = Tk()
        self.root.title("CaltrainPy")

        # This makes it full screen, but for some reason controls don't fill
        # It also makes OptionMenus hard to use (seems like a bug)
        #w, h = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        #self.root.geometry("%dx%d+0+0" % (w, h))

        self.init()

    def onDays(self):
        text = self.days['text']
        if text == weekday:
            self.days['text'] = weekend
        else:
            self.days['text'] = weekday

        self.updateFromTo()

    def onDirection(self):
        if self.direction['text'] == northbound:
            self.direction['text'] = southbound
        else:
            self.direction['text'] = northbound

        fromStation = self.fromDefault.get()
        self.fromDefault.set(self.toDefault.get())
        self.toDefault.set(fromStation)
        
        self.updateTable()

    def updateFromTo(self, _a=None, _b=None, _c=None):
        fromStation = self.fromDefault.get()
        toStation = self.toDefault.get()
        day = self.days['text']
        direction = self.direction['text']
        s = stations[day][direction]

        if fromStation not in s or toStation not in s:
            self.fromDefault.set(s[0])
            self.toDefault.set(s[-1])

        self.fromMenu.destroy()
        self.fromMenu = OptionMenu(self.root, self.fromDefault, *s)
        self.fromMenu.grid(row=1, column=1)

        self.toMenu.destroy()
        self.toMenu = OptionMenu(self.root, self.toDefault, *s)
        self.toMenu.grid(row=1, column=2, sticky=E)

        self.updateTable()
        
    def updateTable(self, _a=None):
        fromStation = self.fromDefault.get()
        toStation = self.toDefault.get()
        day = self.days['text']
        direction = self.direction['text']
        
        self.trains = MultiListbox(self.root, (("Train", 1), (fromStation, 2),
                                               (toStation, 3)))
        for train, fromTime, toTime in zip(service[day][direction][trainNumber],
                                           service[day][direction][fromStation],
                                           service[day][direction][toStation]):
            self.trains.insert(END, (train, fromTime, toTime))
        self.trains.grid(row=2, columnspan=3, sticky=W+E)

    def init(self):
        # top row buttons
        self.days = Button(self.root, text=weekday, command=self.onDays)
        self.direction = Button(self.root, text=northbound,
                                command=self.onDirection)
        self.days.grid(row=0, columnspan=2, sticky=W)
        self.direction.grid(row=0, column=2, sticky=E)

        # Second row label and OptionsMenus
        Label(self.root, text="From-To").grid(row=1, sticky=W)

        self.fromDefault = StringVar(self.root)
        self.fromDefault.set(stations[weekday][northbound][0])
        self.fromMenu = OptionMenu(self.root, self.fromDefault, *stations[weekday][northbound])
        self.fromMenu.grid(row=1, column=1)
        self.fromDefault.trace_variable('w', self.updateFromTo)

        self.toDefault = StringVar(self.root)
        self.toDefault.set(stations[weekday][northbound][-1])
        self.toMenu = OptionMenu(self.root, self.toDefault, *stations[weekday][northbound])
        self.toMenu.grid(row=1, column=2, sticky=E)
        self.toDefault.trace_variable('w', self.updateFromTo)
        
        # Timetable
        self.updateTable()

if __name__ == "__main__":
    caltrain = Caltrain()
    caltrain.root.mainloop()
