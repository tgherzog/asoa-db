
import flask
import jinja2
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_assets import Environment, Bundle
import markupsafe
from datetime import datetime
from markdown import markdown
import os
import re

import openpyxl as xl

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

    wb = xl.load_workbook(filename='data/asoa-roster.xlsx', read_only=True, data_only=True)
    boats = wb['boats']
    owners = wb['owners']
    for ws in (boats,owners):
        ws.keys_ = {}
        i = 0
        for col in ws[1]:
            ws.keys_[col.value] = i
            i += 1

    def get_value(ws, row, key):
        if key not in ws.keys_:
            raise KeyError('{} is not a column in {}'.format(key, ws.title))

        return row[ws.keys_[key]].value or ''

    def filter_boats(item):
        '''Crude search functionality: search on boat name, berth, and owners
        '''

        (k,boat) = item
        s = ' '.join([boat['name'], boat['berth']] + list(map(lambda x: x['owner_name'], boat['owners'])))
        return q in s.lower()

    boat_db = {}
    for row in boats.iter_rows(2):
        boat = {'owners': []}
        for key in ['hull', 'name', 'status', 'rig', 'serial', 'color', 'engine_type', 'engine_desc', 'berth', 'epitaph', 'notes']:
            boat[key] = get_value(boats, row, key)

        boat['hull'] = str(boat['hull'])
        if boat['hull'] in boat_db:
            raise KeyError('Hull {} is listed multiple times in the database'.format(boat['hull']))

        if id is None or id == boat['hull']:
            boat_db[boat['hull']] = boat

    for row in owners.iter_rows(2):
        owner = {}
        for key in ['hull', 'acquired', 'owner_name']:
            owner[key] = get_value(owners, row, key)

        owner['hull'] = str(owner['hull'])
        if type(owner['acquired']) is datetime:
            owner['acquired'] = owner['acquired'].strftime('%m/%d/%Y')

        if owner['hull'] in boat_db:
            boat_db[owner['hull']]['owners'].insert(0, owner)

    if id:
        return boat_db.get(id, {})
    elif q:
        q = q.lower()
        return dict(filter(filter_boats, boat_db.items()))

    return boat_db
