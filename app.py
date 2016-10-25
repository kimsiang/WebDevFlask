#!/bin/python

from flask import Flask, render_template, json, request
from flaskext.mysql import MySQL
mysql = MySQL()

app = Flask(__name__)

# MySQL configurations
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = ''
app.config['MYSQL_DATABASE_DB'] = 'gm2calorimeter'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
mysql.init_app(app)

conn = mysql.connect()
cursor = conn.cursor()

#@app.route("/")
#def main():
#    return "Welcome!"
#    return render_template('index.html')

@app.route('/showSignUp')
def showSignUp():
    return render_template('signup.html')

@app.route('/signUp',methods=['POST'])
def signUp():
    # read the posted values from the UI
    _name = request.form['inputName']
    _email = request.form['inputEmail']
    _password = request.form['inputPassword']

    # validate the received values
    if _name and _email and _password:
        print "Welcome!"
        return json.dumps({'html':'<span>All fields good !!</span>'})
    else:
        return json.dumps({'html':'<span>Enter the required fields</span>'})


@app.route('/xtalQC')
def xtalQC():
    cursor.execute("SELECT xtal_qc_id, xtal_serial_num, location, width_left, width_right, height_left, height_right, length, longitudinal_trans_avg_value from xtal_qc")

    rows = cursor.fetchall()
    return render_template('xtal_qc.html', rows = rows)


@app.route('/gluingProgress')
def gluingProgress():
    cursor.execute("SELECT calo_num, glued, xtal_serial_num, sipm_num, height, width, reserved, calo_row, calo_xtal_num, start_time, stop_time FROM gluing_progress")

    rows = cursor.fetchall()
    return render_template('gluing_progress.html', rows = rows)

import numpy as np
from bokeh.plotting import figure
from bokeh.resources import CDN
from bokeh.embed import components

@app.route('/histogram')
def show_histogram():
    cursor.execute("SELECT height FROM gluing_progress")
    rows = cursor.fetchall()

    height = [row[0] for row in rows]
    # use numpy to calculate histogram
    # bins and values
    heights,edges = np.histogram(height)
    # create a bokeh figure object
    p = figure(title='SiPM Number')
    # add the rectangles
    p.quad(top=heights,bottom=0,
            left=edges[:-1],right=edges[1:],
            fill_color="orange",line_color="black")

    figJS,figDiv = components(p,CDN)

    rendered = render_template('histogram.html',
        height=height,figJS=figJS,figDiv=figDiv)
    return(rendered)

@app.route('/')
def main():
    return render_template('index.html')


if __name__ == "__main__":
    app.debug=True
    app.run(host='0.0.0.0')
