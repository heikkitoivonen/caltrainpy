# Caltrain Schedules in Python and Javascript: Public Transportation Made Easy

**Note: This project is no longer active.**

Caltrain offers schedules online, but not in a usable format for Windows Mobile, Apple iPhone or other mobile devices. CaltrainPy is an option for devices for which the Python runtime is available. Another option is CaltrainJS, which is a free online Caltrain schedule application optimized for small devices. I also have a third port of this software: Caltrain Schedules for Google Android devices.

## CaltrainPY

I started on the Python version since I wanted a schedule for my Cingular 8525 PDA/smart phone running Microsoft Windows Mobile device after I had migrated away from a great PalmOS Caltrain schedule application. It was the inspiration for me starting this project.

The GUI is done using the Tkinter package. Unfortunately Python doesn't run very well on Windows Mobile, which lead me to start working on the Javascript version (see below).

Current release is 0.6, which supports the August 31, 2009 schedules.

It would be interesting to see if the Python versions works well on OpenMoko. PyGTK might be a better option than Tkinter in that case, at least if I am reading the OpenMoko Python page right.

Guido van Rossum expressed interest in a port to the Nokia S60 platform. The Nokia Python for S60 and Python for Series 60 tutorial seem like good resources to get started. But please note that the online Javascript version already works in Nokia phones using the more capable WebKit-based browser (see below).

The Python version can also work as a library to screen scrape the online Caltrain schedules and provide output in various formats, including JSON.

## License

The source code is available under the MIT License.

## CaltrainJS

I used the JSON output from CaltrainPY as basis for the Javascript version. The main targeted platform is Microsoft Windows Mobile 6, but it works in many other devices and browsers.

Tested/reported to be working in:

    Cingular 8525 - Windows Mobile 6 - Internet Explorer Mobile
    Apple iPhone from AT&T - Safari
    Nokia N75 from AT&T - WebKit based browser (go to: Tools > Web)
    Mozilla Firefox 2.x & 3.x
    Internet Explorer 7

The Javascript Caltrain Schedules for Windows Mobile, iPhone and other small devices is available [online](http://caltrain.heikkitoivonen.net/).
