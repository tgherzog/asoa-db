
import flask
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_assets import Environment, Bundle
import markupsafe
from datetime import datetime
from markdown import markdown
import os
import re

import openpyxl as xl

config = {
  'db_path': 'data/asoa-roster.xlsx'
}

config['db_lastmod'] = xl.load_workbook(filename=config['db_path']).properties.modified

app = flask.Flask(__name__)
# if being run via gunicorn, make us proxy-aware (assume Apache)
if os.environ.get('_', '').endswith('gunicorn'):
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_prefix=1)
assets = Environment(app)
assets.url = app.static_url_path
assets.append_path('assets/scss')
assets.url_expire = False   # disable dynamic CSS loading
scss = Bundle('custom.scss', filters='pyscss', output='css/custom.css')
assets.register('scss_site', scss)


@app.template_filter('markdown')
def app_markdown_filter(s):
    
    return markupsafe.Markup(markdown(s))

@app.context_processor
def context_processor():
    email = 'seabreezeowners@gmail.com'

    def email_link(title=None):
        if not title:
            title = email

        return markupsafe.Markup('<a href="mailto:{}">{}</a>'.format(email, title))

    return {
      # global variables
      'asoa_email': email,
      'db_datestamp': config['db_lastmod'].strftime('%m/%d/%Y %I:%M%p UTC'),
      'db_update_form': 'https://forms.gle/usB89vY9sc5U6adG8',

      # custom functions
      'contact_asoa': email_link
    }


@app.route('/')
def app_start():

  return flask.render_template('start.html')

@app.route('/list')
def app_list():

    return flask.render_template('list.html', page_title='List of All Known Seabreezes', boats=db_load())

@app.route('/detail/<hull>')
def app_detail(hull):

    boat = db_load(hull)
    if boat:
        # we also pass the original hull number in case of error
        return flask.render_template('detail.html', hull=hull, boat=db_load(hull))

    flask.abort(404, 'Hull {} is not a known Seabreeze'.format(hull))

@app.route('/search')
def app_search():
    
    q = flask.request.args.get('q')
    if q:
        try:
            q = int(q)
        except:
            pass

        if type(q) is int:
            return flask.redirect('/detail/{}'.format(q))
        else:
            return flask.render_template('list.html', search_term=q, page_title='Search Results', boats=db_load(q=q))

    return flask.redirect(flask.url_for('app_list'))

def db_load(id=None, q=None):
    '''Loads the database from a spreadsheet.
      
       id:      hull number. If defined, the function returns a single record (dict), otherwise
                a list of records (dicts)

       q:       search text to filter results. Else return all boats

    '''

    def filter_boats(item):
        '''Crude search functionality: search on boat name, berth, and owners
        '''

        (k,boat) = item
        s = ' '.join([boat['boat_name'], boat['berth']] + list(map(lambda x: x['owner_name'], boat['owners'])))
        return q in s.lower()

    def fmt_date(date):
        if type(date) is datetime:
            # 7/1 is a special date signifying that only the year has any confidence
            # mm/1 means that only month and year have confidence so we omit the date
            if date.month == 7 and date.day == 1:
                return date.strftime('%Y')
            elif date.day == 1:
                return date.strftime('%-m/%Y')

            return date.strftime('%-m/%-d/%Y')

        return ''    

    wb = xl.load_workbook(filename=config['db_path'], read_only=True, data_only=True)
    boats = wb['boats']
    boat_db = {}
    keys = {}
    i = 0
    for col in boats[1]:
        keys[col.value] = i
        i += 1

    for row in boats.iter_rows(2):
        boat = {}
        for key in ['hull', 'date', 'status', 'boat_name', 'sale_link', 'rig', 'serial', 'color', 'engine_type', 'engine_desc', 'berth', 'epitaph', 'latest_info']:
            boat[key] = row[keys[key]].value or ''

        boat['hull'] = str(boat['hull'])

        if not boat['hull']:
            continue

        owner = {'hull': boat['hull'], 'acquired': fmt_date(boat['date'])}

        for key in ['owner_name']:
            owner[key] = row[keys[key]].value or ''

        boat['date'] = fmt_date(boat['date'])

        hull = boat['hull']
        if boat_db.get(hull):
            # Prior record exists: append owner to front and merge more recent fields
            if boat['status'] in ['GOOD', 'RENO']:    
                boat_db[hull]['owners'].insert(0, owner)

            for k,v in boat.items():
                if v:
                    boat_db[hull][k] = v
        else:
            boat['owners'] = []
            if boat['status'] in ['GOOD', 'RENO']:
                boat['owners'].append(owner)

            boat_db[hull] = boat

    if id:
        return boat_db.get(id, {})
    elif q:
        q = q.lower()
        return dict(filter(filter_boats, boat_db.items()))

    return boat_db
