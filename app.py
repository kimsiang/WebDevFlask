#!/bin/python

from flask import Flask, render_template, json, request
from flaskext.mysql import MySQL
mysql = MySQL()

app = Flask(__name__)

# MySQL configurations
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'precess116592089'
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

@app.route('/')
def main():
    cursor.execute("SELECT * from xtal_qc")

    rows = []

#    for row in cursor:
#        rows.append(row)
#        print(row)
#
#    return rows
    data = cursor.fetchall()    
    return render_template('index.html', data = data)


if __name__ == "__main__":
    app.run(host='0.0.0.0')
