#!/bin/python

from flask import Flask, render_template, json, request
from flaskext.mysql import MySQL

mysql = MySQL()

app = Flask(__name__)

# MySQL configurations
app.config['MYSQL_DATABASE_USER'] = 'gm2_reader'
app.config['MYSQL_DATABASE_PASSWORD'] = 'gm2_4_reader'
app.config['MYSQL_DATABASE_DB'] = 'gm2_calorimeter_db'
app.config['MYSQL_DATABASE_HOST'] = 'fnalmysqldev.fnal.gov'
app.config['MYSQL_DATABASE_PORT'] = 3313

#app.config['MYSQL_DATABASE_USER'] = 'root'
#app.config['MYSQL_DATABASE_PASSWORD'] = ''
#app.config['MYSQL_DATABASE_DB'] = 'gm2_calorimeter_db'
#app.config['MYSQL_DATABASE_HOST'] = 'localhost'


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
        #print "Welcome!"
        return json.dumps({'html':'<span>All fields good !!</span>'})
    else:
        return json.dumps({'html':'<span>Enter the required fields</span>'})

@app.route('/calorimeter')
def calorimeter():

    cursor.execute("SELECT calorimeter_id FROM calorimeter")

    rows = cursor.fetchall()
    return render_template('calorimeter.html', rows = rows)

@app.route('/sipm')
def sipm():

    cursor.execute("SELECT sipm_id, package_id FROM sipm ORDER by sipm_id")

    rows = cursor.fetchall()
    return render_template('sipm.html', rows = rows)


@app.route('/crystalQC')
def crystalQC():
    cursor.execute("SELECT qc_id, serial_number, location, width_left, width_right, height_left, height_right, length, longitudinal_trans_avg_value from crystal_qc")

    rows = cursor.fetchall()
    return render_template('crystal_qc.html', rows = rows)


@app.route('/gluingProgress')
def gluingProgress():

    cursor.execute("SELECT calo_id, glued, crystal_serial_num, sipm_id, height, width, reserved, calo_row, calo_xtal_num, start_time, stop_time FROM gluing_progress")
    col_names = [i[0] for i in cursor.description]

    rows = cursor.fetchall()
    return render_template('gluing_progress.html', rows = rows, col_names = col_names)

@app.route('/beaglebone')
def beaglebone():

    cursor.execute("SELECT beaglebone_id, ip_address FROM beaglebone")

    rows = cursor.fetchall()
    return render_template('beaglebone.html', rows = rows)

@app.route('/bkprecision')
def bkprecision():

    cursor.execute("SELECT bkprecision_id, serial_number, calorimeter_id FROM bkprecision")

    rows = cursor.fetchall()
    return render_template('bkprecision.html', rows = rows)

@app.route('/amc13')
def amc13():

    cursor.execute("SELECT serial_number, vendor, model, location, owner, deployment, spartan_t2, kintex_t1, status, notes FROM amc13")

    rows = cursor.fetchall()
    return render_template('amc13.html', rows = rows)

@app.route('/microtca')
def microtca():

    cursor.execute("SELECT serial_number, vendor, model, location, owner, version, deployment, notes FROM utca_crate")

    rows = cursor.fetchall()
    return render_template('microtca.html', rows = rows)

@app.route('/wfd5')
def wfd5():

    cursor.execute("SELECT serial_number, wfdps_sn, afe_sn, deployment, mmc_fwv, golden_fwv, master_fwv, channel_fwv, location, owner, status FROM wfd5")

    rows = cursor.fetchall()
    return render_template('wfd5.html', rows = rows)


@app.route('/gbrew')
def gbrew():

    cursor.execute("SELECT name, cups, current_credit FROM g_brew")

    rows = cursor.fetchall()
    return render_template('gbrew.html', rows = rows)

@app.route('/fiber')
def fiber():

    cursor.execute("SELECT bundle_id, fiber_id, p_out, prism_id FROM fiber")

    rows = cursor.fetchall()
    return render_template('fiber.html', rows = rows)

@app.route('/panel')
def panel():

    cursor.execute("SELECT panel_id, bundle_id, bending_close, bending_far FROM front_panel")

    rows = cursor.fetchall()
    return render_template('panel.html', rows = rows)


@app.route('/calo_vis/<caloNum>')
def calo_vis(caloNum):

    cursor.execute("SELECT crystal_serial_num, sipm_id, calo_xtal_num, reserved FROM gluing_progress WHERE calo_id = {0} ORDER BY calo_xtal_num DESC".format(caloNum))

    col_names = [i[0] for i in cursor.description]

    rows = cursor.fetchall()
    return render_template('calo_vis.html', rows = rows, col_names = col_names, caloNum = caloNum)

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
