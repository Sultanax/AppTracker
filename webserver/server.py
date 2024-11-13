#!/usr/bin/env python3

"""
Columbia W4111 Intro to databases
Example webserver

To run locally

    python server.py

Go to http://localhost:8111 in your browser


A debugger such as "pdb" may be helpful for debugging.
Read about it online.
"""

import os
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from sqlalchemy import create_engine, text
from flask import Flask, flash, request, render_template, g, redirect, Response, session, abort, url_for
import os
from datetime import datetime

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)



# XXX: The Database URI should be in the format of: 
#
#     postgresql://USER:PASSWORD@<IP_OF_POSTGRE_SQL_SERVER>/<DB_NAME>
#
# For example, if you had username ewu2493, password foobar, then the following line would be:
#
#     DATABASEURI = "postgresql://ewu2493:foobar@<IP_OF_POSTGRE_SQL_SERVER>/postgres"
#
# For your convenience, we already set it to the class database

# Use the DB credentials you received by e-mail
DB_USER = "sy3196"
DB_PASSWORD = "hotdogs123"

DB_SERVER = "w4111.cisxo09blonu.us-east-1.rds.amazonaws.com"

DATABASEURI = "postgresql://"+DB_USER+":"+DB_PASSWORD+"@"+DB_SERVER+"/w4111"

#
# This line creates a database engine that knows how to connect to the URI above
#
engine = create_engine(DATABASEURI)

@app.before_request
def before_request():
  """
  This function is run at the beginning of every web request 
  (every time you enter an address in the web browser).
  We use it to setup a database connection that can be used throughout the request

  The variable g is globally accessible
  """
  try:
    g.conn = engine.connect()
  except:
    print("uh oh, problem connecting to database")
    import traceback; traceback.print_exc()
    g.conn = None

@app.teardown_request
def teardown_request(exception):
  """
  At the end of the web request, this makes sure to close the database connection.
  If you don't the database could run out of memory!
  """
  try:
    g.conn.close()
  except Exception as e:
    pass


@app.route('/applicant')

@app.route('/applicant/<id>')
def applicant_home(id=None):
  if not session.get('logged_in'):
    return home()
  return render_template('applicant.html', person=id)

@app.route('/company')

@app.route('/company/<id>')
def company_home(id=None):
  if not session.get('logged_in'):
    return home()
  
  query = f"SELECT user_name FROM App_User WHERE company_id = '{id}'"
  result = engine.execute(query)
  name = result.fetchone()[0]
  result.close()

  cursor = g.conn.execute("SELECT * FROM Role_Posts WHERE company_id = %s", (int(id),))
  role = []
  for result in cursor:
    role.append(result)
  cursor.close()
  context_posts = dict(data_posts = role)

  cursor = g.conn.execute("SELECT * FROM Event_Holds WHERE company_id = %s", (int(id),))
  event = []
  for result in cursor:
    event.append(result)
  cursor.close()
  context_events = dict(data_events = role)

  return render_template("company.html", id=id, name = name, **context_posts, **context_events)


@app.route('/company/<id>/event')
def create_event(id=None):
  if not session.get('logged_in'):
    return home()
  return "create event"

@app.route('/company/<id>/post', methods=['GET','CREATE'])
def create_post(id=None):
  if not session.get('logged_in'):
    return home()
  if request.method == 'CREATE':
    print("created")
    position = request.form['position']
    print("1")
    description = request.form['description']
    print("1")
    location = request.form['location']
    print("1")
    salary = request.form['salary']
    print("1")
    role_type = request.form['role_type']
    print("1")

    if not position or not role_type:
      return render_template('create-post.html',id=id, error='Missing Information')
    if salary and not salary.isdigit():
      return render_template('create-post.html',id=id, error='Salary should be a number')
    print("correct values")
    query = f"SELECT MAX(role_id) FROM Role_Posts"
    result = engine.execute(query)
    role_id = result.fetchone()[0] + 1
    result.close()
    print(role_id)
    cmd = 'INSERT INTO Role_Posts VALUES (:id,:position,:description,:location,:salary,:role_type,:date,:company_id)'
    g.conn.execute(text(cmd), id=role_id,position=position,description=description,location=locationn,salary=salary,role_type=role_type,date=datetime.now(),company_id=id)
    print("added")
    return redirect(url_for('company_home',id=id))

  return render_template('create-post.html',id=id)


@app.route('/')
def home():
  if not session.get('logged_in'):
    return render_template('login.html')
  else:
    session['logged_in'] = False
    return render_template('login.html')

@app.route('/login', methods=['GET','POST'])
def do_admin_login():
  if request.method == 'POST':
    email = request.form['email']
    password = request.form['password']
    if email and password:
      query = f"SELECT password FROM App_Password WHERE user_email = '{email}'"
      result = engine.execute(query)
      user_data = result.fetchone()
      result.close()
      if user_data and password == user_data[0]:
        flash('Logged in successfully!', 'success')
        session['logged_in'] = True
      
        query = f"SELECT company_id,applicant_id FROM App_User WHERE user_email = '{email}'"
        result = engine.execute(query)
        user_data = result.fetchone()
        result.close()
        if user_data and user_data[0]:
          return redirect(url_for('company_home', id=user_data[0]))
        if user_data and user_data[1]:
          return redirect(url_for('applicant_home', id=user_data[1]))
      else:
        flash('Incorrect login/password', 'danger')
    else:
      flash('Incorrect login/password', 'danger')
    return home()
  return render_template('login.html')

@app.route("/logout")
def logout():
  session['logged_in'] = False
  return home()

@app.route('/create-account', methods=['GET','POST'])
def create_account():
  if request.method == 'POST':
    user_type = request.form['user_type']
    if user_type=="Applicant":
      return redirect(url_for('create_account_applicant'))
    if user_type=="Company":
      return redirect(url_for('create_account_company'))

    return home()
  return render_template('create-account.html')


@app.route('/create-account-applicant', methods=['GET','POST'])
def create_account_applicant():
  if request.method == 'POST':
    new_email = request.form['email']
    new_password = request.form['password']
    confirm_password = request.form['confirm_password']
    new_name = request.form['name']
    new_occupation = request.form['occupation']

    if not new_email or not new_password or not confirm_password or not new_name:
      return render_template('create-account-applicant.html',error='Missing Information')
    if new_password != confirm_password:
      print("password dont match")
      return render_template('create-account-applicant.html',error='Passwords do not match')
    print("query")
    query = f"SELECT * FROM App_Password WHERE user_email = '{new_email}'"
    result = engine.execute(query)
    user_data = result.fetchone()
    result.close()
    if user_data and user_data[0]:
      return render_template('create-account-applicant.html',error='Email already exists')

    cmd = 'INSERT INTO App_Password VALUES (:email1,:password1)';
    g.conn.execute(text(cmd), email1 = new_email, password1 = new_password);

    query = f"SELECT MAX(applicant_id) FROM Applicant"
    result = engine.execute(query)
    applicant_id = result.fetchone()[0] + 1
    result.close()

    cmd = 'INSERT INTO Applicant VALUES (:id1,:occupation1)'
    g.conn.execute(text(cmd), id1 = applicant_id,occupation1 = new_occupation)
    cmd = 'INSERT INTO App_User VALUES (:email1,:name1,null,:id1)'
    g.conn.execute(text(cmd), email1 = new_email, name1 = new_name,id1 = applicant_id)

    session['logged_in'] = True
    return redirect(url_for('applicant_home',id=applicant_id))

  return render_template('create-account-applicant.html')


@app.route('/create-account-company', methods=['GET','POST'])
def create_account_company():
  if request.method == 'POST':
    new_email = request.form['email']
    new_password = request.form['password']
    confirm_password = request.form['confirm_password']
    new_name = request.form['name']
    new_field = request.form['field']
    new_size = request.form['size']

    if not new_email or not new_password or not confirm_password or not new_name:
      return render_template('create-account-company.html',error='Missing Information')
    if new_size and not new_size.isdigit():
      return render_template('create-account-company.html',error='Company size must be a number')
    if new_password != confirm_password:
      return render_template('create-account-company.html',error='Passwords do not match')

    query = f"SELECT * FROM App_Password WHERE user_email = '{new_email}'"
    result = engine.execute(query)
    user_data = result.fetchone()
    result.close()
    if user_data and user_data[0]:
      return render_template('create-account-company.html',error='Email already exists')

    cmd = 'INSERT INTO App_Password VALUES (:email1,:password1)';
    g.conn.execute(text(cmd), email1 = new_email, password1 = new_password);
    query = f"SELECT MAX(company_id) FROM Company"
    result = engine.execute(query)
    company_id = result.fetchone()[0] + 1
    result.close()

    cmd = 'INSERT INTO Company VALUES (:id1,:size1,:field1)'
    g.conn.execute(text(cmd), id1 = company_id,size1=new_size,field1=new_field )
    cmd = 'INSERT INTO App_User VALUES (:email1,:name1,:id1,null)'
    g.conn.execute(text(cmd), email1 = new_email, name1 = new_name,id1 = company_id)
    
    session['logged_in'] = True
    return redirect(url_for('company_home',id=company_id))

  return render_template('create-account-company.html')


if __name__ == "__main__":
  import click

  @click.command()
  @click.option('--debug', is_flag=True)
  @click.option('--threaded', is_flag=True)
  @click.argument('HOST', default='0.0.0.0')
  @click.argument('PORT', default=8111, type=int)
  def run(debug, threaded, host, port):
    """
    This function handles command line parameters.
    Run the server using

        python server.py

    Show the help text using

        python server.py --help

    """

    HOST, PORT = host, port
    print("running on %s:%d" % (HOST, PORT))
    app.secret_key = os.urandom(12)
    app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)

  run()
