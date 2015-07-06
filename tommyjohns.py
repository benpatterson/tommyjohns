# all the imports
import sqlite3
import pandas
from flask import Flask, request, session, g, redirect, url_for, \
     abort, render_template, flash
from contextlib import closing
from bokeh.embed import file_html, Resources
from bokeh.charts import Bar


app = Flask(__name__)
app.config.from_envvar('TOMMYJOHNS_SETTINGS_FILE', silent=True)


def connect_db():
    return sqlite3.connect(app.config['DATABASE'])


def init_db():
    with closing(connect_db()) as db:
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

@app.before_request
def before_request():
    g.db = connect_db()

@app.teardown_request
def teardown_request(exception):
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()


@app.route('/')
def show_entries():
    cur = g.db.execute('select googleuid, title from spreadsheets order by id desc')
    entries = [dict(title=row[0], text=row[1]) for row in cur.fetchall()]
    return render_template('show_entries.html', entries=entries)

@app.route('/surgeries', methods=['GET'])
def show_surgeries():
    error = None
    return render_template('surgeries.html', error=error)

@app.route('/surgeries-by-year', methods=['GET'])
def show_surgeries_by_year():
    error = None
    return render_template('surgery_dates.html', error=error)


def build_charts():
    # from bokeh.charts import Histogram, show, output_file
    surgeries_df = pandas.DataFrame.from_csv('devstuff/TJList.csv', index_col='mlbamid')
    # change surgery date strings to just years
    surgeries_df['TJ Surgery Date'] = surgeries_df['TJ Surgery Date'].apply(lambda x: int(str(x)[-4:]))
    # zup = pandas.DataFrame(surgeries_df['TJ Surgery Date'].value_counts(sort=False))
    majors_only = surgeries_df[(surgeries_df.Majors == 'Y')]
    minors_only = surgeries_df[(surgeries_df.Majors == 'N')]
    majors_only_counts = pandas.DataFrame(majors_only['TJ Surgery Date'].value_counts(sort=False))
    minors_only_counts = pandas.DataFrame(minors_only['TJ Surgery Date'].value_counts(sort=False))
    years_df = majors_only_counts.join(minors_only_counts, lsuffix='_majors', rsuffix='_minors')
    years_df.fillna(0, inplace=True)
    years_df.rename(columns={u'0_majors': u'majors', u'0_minors': u'minors'}, inplace=True)
    per_year_bar_chart = Bar(years_df, stacked=True, legend=True)
    CDN = Resources(mode="cdn")
    html = file_html(per_year_bar_chart, CDN, "surg_dates_0")
    with open("templates/surg_dates_1", "w") as f:
        f.write(html)


# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     error = None
#     if request.method == 'POST':
#         if request.form['username'] != app.config['USERNAME']:
#             error = 'Invalid username'
#         elif request.form['password'] != app.config['PASSWORD']:
#             error = 'Invalid password'
#         else:
#             session['logged_in'] = True
#             flash('You were logged in')
#             return redirect(url_for('show_entries'))
#     return render_template('login.html', error=error)

# @app.route('/logout')
# def logout():
#     session.pop('logged_in', None)
#     flash('You were logged out')
#     return redirect(url_for('show_entries'))

# @app.route('/add', methods=['POST'])
# def add_entry():
#     if not session.get('logged_in'):
#         abort(401)
#     g.db.execute('insert into spreadsheets (googleuid, spreadsheettitle) values (?, ?)',
#                  [request.form['googleuid'], request.form['spreadsheettitle']])
#     # g.db.execute('insert into entries (title, text) values (?, ?)',
#     #              [request.form['title'], request.form['text']])
#     g.db.commit()
#     flash('New entry was successfully posted')
#     return redirect(url_for('show_entries'))

# @app.route('/add', methods=['POST'])
# def add_entry():
#     if not session.get('logged_in'):
#         abort(401)
#     g.db.execute('insert into spreadsheets (googleuid, spreadsheettitle) values (?, ?)',
#                  [request.form['googleuid'], request.form['spreadsheet title']])
#     g.db.commit()
#     flash('New entry was successfully posted')
#     return redirect(url_for('show_entries'))

if __name__ == '__main__':
    init_db()
    app.run()
