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
from sqlalchemy import create_engine
from flask import Flask, flash, request, render_template, g, redirect, Response, session, abort, url_for
import os

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

result = engine.execute("SELECT * FROM Company")
for row in result:
  print(row)


result = engine.execute("SELECT * FROM Applicant")
for row in result:
  print(row)

result = engine.execute("SELECT * FROM App_User")
for row in result:
  print(row)

result = engine.execute("SELECT * FROM App_Password")
for row in result:
  print(row)


# Here we create a test table and insert some values in it
engine.execute("""DROP TABLE IF EXISTS test;""")
engine.execute("""CREATE TABLE IF NOT EXISTS test (
  id serial,
  name text
);""")
engine.execute("""INSERT INTO test(name) VALUES ('grace hopper'), ('alan turing'), ('ada lovelace');""")



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


#
# @app.route is a decorator around index() that means:
#   run index() whenever the user tries to access the "/" path using a GET request
#
# If you wanted the user to go to e.g., localhost:8111/foobar/ with POST or GET then you could use
#
#       @app.route("/foobar/", methods=["POST", "GET"])
#
# PROTIP: (the trailing / in the path is important)
# 
# see for routing: http://flask.pocoo.org/docs/0.10/quickstart/#routing
# see for decorators: http://simeonfranklin.com/blog/2012/jul/1/python-decorators-in-12-steps/
#
@app.route('/index')
def index():
  """
  request is a special object that Flask provides to access web request information:

  request.method:   "GET" or "POST"
  request.form:     if the browser submitted a form, this contains the data in the form
  request.args:     dictionary of URL arguments e.g., {a:1, b:2} for http://localhost?a=1&b=2

  See its API: http://flask.pocoo.org/docs/0.10/api/#incoming-request-data
  """

  # DEBUG: this is debugging code to see what request looks like
  print(request.args)

  #
  # example of a database query
  #
  cursor = g.conn.execute("SELECT name FROM test")
  names = []
  for result in cursor:
    names.append(result['name'])  # can also be accessed using result[0]
  cursor.close()

  #
  # Flask uses Jinja templates, which is an extension to HTML where you can
  # pass data to a template and dynamically generate HTML based on the data
  # (you can think of it as simple PHP)
  # documentation: https://realpython.com/blog/python/primer-on-jinja-templating/
  #
  # You can see an example template in templates/index.html
  #
  # context are the variables that are passed to the template.
  # for example, "data" key in the context variable defined below will be 
  # accessible as a variable in index.html:
  #
  #     # will print: [u'grace hopper', u'alan turing', u'ada lovelace']
  #     <div>{{data}}</div>
  #     
  #     # creates a <div> tag for each element in data
  #     # will print: 
  #     #
  #     #   <div>grace hopper</div>
  #     #   <div>alan turing</div>
  #     #   <div>ada lovelace</div>
  #     #
  #     {% for n in data %}
  #     <div>{{n}}</div>
  #     {% endfor %}
  #
  context = dict(data = names)

  #
  # render_template looks in the templates/ folder for files.
  # for example, the below file reads template/index.html
  #
  return render_template("index.html", **context)

#
# This is an example of a different path.  You can see it at
# 
#     localhost:8111/another
#
# notice that the functio name is another() rather than index()
# the functions for each app.route needs to have different names
#
@app.route('/another')
def another():
  return render_template("anotherfile.html")

@app.route('/test')

@app.route('/test/<name>')
def hello(name=None):
    return render_template('test.html', person=name)

@app.route('/applicant')

@app.route('/applicant/<id>')
def applicant_home(id=None):
  if not session.get('logged_in'):
    return home()
  return render_template('applicant.html', person=id)

@app.route('/company')

@app.route('/company/<id>')
def company_home(id=None):
  print("in company user home")
  if not session.get('logged_in'):
    return home()
  return render_template('company.html', person=id)


@app.route('/')
def home():
  if not session.get('logged_in'):
    return render_template('login.html')
  else:
    return "Hello Boss!  <a href='/logout'>Logout</a>"

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
    user_type = request.form.get('user_type')
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
      print("missing")
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
      print("email exists")
      return render_template('create-account-applicant.html',error='Email already exists')

    print('adding user')

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
