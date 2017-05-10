import sqlite3
import pandas
from flask import Flask, request, session, g, redirect, url_for, \
     abort, render_template, flash
from contextlib import closing
from bokeh.embed import file_html, Resources
from bokeh.charts import Bar, Histogram, Line, TimeSeries

import gspread


CDN = Resources(mode="cdn")
# List of pages
NUM_PER_YEAR = "surgeries_per_year"
AGE_DISTRIBUTION = "age_distribution"
RECOVERY_TIMES = "recovery_times"

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


@app.route('/age', methods=['GET'])
def show_surgeries():
    """
    This page provides a histogram of surgeries according to pitcher age at time of surgery
    """
    error = None
    return render_template(
        "chart.html",
        error=error,
        chart_title="Major League Surgeries",
        chart_subtitle="Distribution by Age (histogram)",
        chart_file=AGE_DISTRIBUTION)

@app.route('/surgeries-by-year', methods=['GET'])
def show_surgeries_by_year():
    """
    This page provides a bar graph of the number of surgeries each year
    """
    error = None
    return render_template(
        "chart.html",
        error=error,
        chart_title="surgeries_per_year",
        chart_subtitle="",
        chart_file=NUM_PER_YEAR
    )

@app.route('/recovery-times', methods=['GET'])
def show_recovery_times():
    """
    This chart looks at the time to recovery, which is defined as the amount of time passed until
    the next non-rehab start (er, I think)
    """
    return render_template(
        "chart.html",
        error=None,
        chart_title="Recovery Times",
        chart_subtitle="",
        chart_file=RECOVERY_TIMES
    )


def build_charts():
    df = pandas.DataFrame.from_csv('devstuff/TJList.csv', index_col='mlbamid')
    chart_recovery_time(recov_df=df)
    chart_surgeries_per_year(surgeries_df0=df)
    chart_age_distribution(age_df=df)


def chart_surgeries_per_year(surgeries_df0):
    """
    Creates an embedded chart with the number of surgeries per year, broken out by major and minor leaguers
    """
    surgeries_df = pandas.DataFrame.from_csv('devstuff/TJList.csv', index_col='mlbamid')
    surgeries_df['TJ Surgery Date'] = surgeries_df['TJ Surgery Date'].apply(lambda x: int(str(x)[-4:]))

    majors_only = surgeries_df[(surgeries_df.Majors == 'Y')]
    minors_only = surgeries_df[(surgeries_df.Majors == 'N')]
    majors_only_counts = pandas.DataFrame(majors_only['TJ Surgery Date'].value_counts(sort=False))
    minors_only_counts = pandas.DataFrame(minors_only['TJ Surgery Date'].value_counts(sort=False))

    years_df = majors_only_counts.join(minors_only_counts, lsuffix='_majors', rsuffix='_minors')
    years_df.fillna(0, inplace=True)
    years_df.rename(columns={u'0_majors': u'majors', u'0_minors': u'minors'}, inplace=True)

    per_year_bar_chart = Bar(years_df, stacked=True, legend=True)
    html = file_html(per_year_bar_chart, CDN, NUM_PER_YEAR)
    with open("templates/" + NUM_PER_YEAR, "w") as f:
        f.write(html)


def chart_age_distribution(age_df):
    """
    Creates a histogram that charts the age distribution for major leaguers
    """
    age_df = age_df[(age_df.Majors == 'Y')]
    all_ages = list(age_df['Age'])
    age_histogram = Histogram(all_ages, bins=25)
    html = file_html(age_histogram, CDN, AGE_DISTRIBUTION)
    with open("templates/" + AGE_DISTRIBUTION, "w") as f:
        f.write(html)


def chart_recovery_time(recov_df):
    """
    Line graph that depicts the recovery times of pitchers. It is broken out by year.
    """
    recov_df['TJ Surgery Date'] = pandas.to_datetime(recov_df['TJ Surgery Date'], format='%m/%d/%Y')
    recov_df = recov_df[(recov_df.Majors == 'Y')]
    recovery_times = recov_df[['Recovery Time (months)', 'TJ Surgery Date']]
    recovery_times.dropna(0, inplace=True)

    data = dict(Recovery=recovery_times['Recovery Time (months)'], Date=recovery_times['TJ Surgery Date'])
    recovery_graph = TimeSeries(data, index='Date', xlabel="year", ylabel='months')
    html = file_html(recovery_graph, CDN, "recovery_times")
    with open("templates/recovery_times", "w") as f:
        f.write(html)


def get_spreadsheet():
    """
    Loads entire worksheet and writes to the file referenced by graphs. It will only
    overwrite the existing file if it is larger than the previous file.
    """
    gspread_session = gspread.login(app.config['GOOGLE_USER'], app.config['GOOGLE_PASS'])
    tj_spreadsheet = gspread_session.open_by_key(app.config['GOOGLE_SHEET_KEY'])
    tj_worksheet = tj_spreadsheet.worksheet("TJ List")
    all_stuff = tj_worksheet.get_all_values()
    # write out all_stuff as a csv file


if __name__ == '__main__':
    init_db()
    build_charts()
    app.run()
