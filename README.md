
This repository contains the source code for the online member database
for the [Allied Seabreeze Owners Association](http://alliedseabreeze35.org) (ASOA).

It is built using python, [Flask][flask], [Jinja][jinja] (for templating) and
[Bootstrap][bootstrap] (theming and responsive design).
The database (not included in the repo for privacy) is a simple Excel spreadsheet
read using [openpyxl][openpyxl].

The python component simply defines endpoints, loads the spreadsheet
and provides rudimentary search. Most of the "guts" of the program are
implemented through [jinja templates](tree/master/templates).

If your unfamiliar with Flask, the key thing to understand in `app.py` is that it mostly
just loads the spreadsheet and uses `render_template` to load one of the Jinja
templates. The extra parameters passed through `render_template` define the names and
values of variables in the template.

[flask]: https://flask.palletsprojects.com/
[jinja]: https://jinja.palletsprojects.com/
[bootstrap]: https://getbootstrap.com/
[openpyxl]: https://openpyxl.readthedocs.io/
