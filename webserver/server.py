#!/usr/bin/env python3

import os
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from sqlalchemy import create_engine, text
from flask import Flask, flash, request, render_template, g, redirect, Response, session, abort, url_for
import os
import re
from datetime import datetime

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)


DB_USER = "sy3196"
DB_PASSWORD = "hotdogs123"
DB_SERVER = "w4111.cisxo09blonu.us-east-1.rds.amazonaws.com"
DATABASEURI = "postgresql://"+DB_USER+":"+DB_PASSWORD+"@"+DB_SERVER+"/w4111"

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

  query = f"SELECT user_name FROM App_User WHERE applicant_id = '{id}'"
  result = engine.execute(query)
  name = result.fetchone()[0]
  result.close()

  cursor1 = g.conn.execute("SELECT * FROM Role_Posts, Applies,App_User WHERE App_User.company_id = Role_Posts.company_id AND Applies.role_id = Role_Posts.role_id AND Applies.applicant_id = %s", (int(id),))
  role = []
  for result in cursor1:
    role.append(result)
  cursor1.close()
  context_apps = dict(data_apps = role)

  cursor2 = g.conn.execute("SELECT * FROM Event_Holds,Attends WHERE Event_Holds.event_id = Attends.event_id AND Attends.applicant_id = %s", (int(id),))
  event = []
  for result in cursor2:
    event.append(result)
  cursor2.close()
  context_events = dict(data_events = event)

  cursor3 = g.conn.execute("SELECT * FROM Role_Posts, Interviews ,App_User WHERE App_User.company_id = Role_Posts.company_id AND Interviews.role_id = Role_Posts.role_id AND Interviews.applicant_id = %s", (int(id),))
  interview = []
  for result in cursor3:
    interview.append(result)
  cursor3.close()
  context_interviews = dict(data_interviews = interview)

  return render_template('applicant.html', id=id, name = name, **context_apps, **context_events, **context_interviews)


@app.route('/applicant/<id>/events', methods=['GET', 'POST'])
def signup_events(id=None):
  if not session.get('logged_in'):
    return home()
  return render_template('signup-events.html',id=id)

@app.route('/applicant/<id>/roles', methods=['GET', 'POST'])
def signup_roles(id=None):
  if not session.get('logged_in'):
    return home()
  cursor1 = g.conn.execute("SELECT DISTINCT App_User.user_name, Role_Posts.role_id,  Role_Posts.role_position, Role_Posts.role_description,Role_Posts.role_location,Role_Posts.role_salary,Role_Posts.role_type FROM Role_Posts, App_User WHERE App_User.company_id = Role_Posts.company_id")
  role = []
  for result in cursor1:
    role.append(result)
  cursor1.close()
  context_roles = dict(data_roles = role)
  return render_template('signup-roles.html',id=id,**context_roles)

@app.route('/applicant/<id>/interviews', methods=['GET', 'POST'])
def signup_interviews(id=None):
  if not session.get('logged_in'):
    return home()
  return render_template('signup-interviews.html',id=id)

  
  
@app.route('/company')

@app.route('/company/<id>')
def company_home(id=None):
  if not session.get('logged_in'):
    return home()
  
  query = text("SELECT user_name FROM App_User WHERE company_id = :company_id")
  result = g.conn.execute(query, {'company_id': id})
  name = result.fetchone()
  print(name)
  result.close()

  cursor1 = g.conn.execute(text("SELECT * FROM Role_Posts WHERE company_id = :company_id"), {'company_id': int(id)})
  role = []
  for result in cursor1:
    role.append(result)
  cursor1.close()
  context_posts = dict(data_posts = role)

  cursor2 = g.conn.execute(text("SELECT * FROM Event_Holds WHERE company_id = :company_id"), {'company_id': int(id)})
  event = []
  for result in cursor2:
    event.append(result)
  cursor2.close()
  context_events = dict(data_events = event)

  return render_template("company.html", id=id, name = name, **context_posts, **context_events)


@app.route('/company/<id>/event', methods=['GET', 'POST'])
def create_event(id=None):
  if not session.get('logged_in'):
    return home()
  if request.method == 'POST':
    notes = request.form['notes']
    date = datetime.fromisoformat(request.form['date'])
    attendees = request.form['attendees']
    event_type = request.form['event_type']

    if not date or not event_type:
      return render_template('create-event.html',id=id, error='Missing Information')
    if attendees and not attendees.isdigit():
      return render_template('create-event.html',id=id, error='Attendees should be a number')

    query = f"SELECT MAX(event_id) FROM Event_Holds"
    result = engine.execute(query)
    event_id = result.fetchone()[0] + 1
    result.close()
    
      
    cmd = 'INSERT INTO Event_Holds VALUES (:event_id,:company_id,:event_notes,:attendees,:event_date,:info_session,:coffee_chat)'
    if event_type=='Info_session':
      g.conn.execute(text(cmd), event_id=event_id,company_id=id,event_notes=notes,attendees=attendees,event_date=date,info_session=True,coffee_chat=False)
    if event_type=='Coffee_chat':
      g.conn.execute(text(cmd), event_id=event_id,company_id=id,event_notes=notes,attendees=attendees,event_date=date,info_session=False,coffee_chat=True)
      
    return redirect(url_for('company_home',id=id))

  return render_template('create-event.html',id=id)

@app.route('/company/<id>/post', methods=['GET', 'POST'])
def create_post(id=None):
  if not session.get('logged_in'):
    return home()
  if request.method == 'POST':  
    position = request.form['position']
    description = request.form['description']
    location = request.form['location']
    salary = request.form['salary']
    role_type = request.form['role_type']

    if not position or not role_type:
      return render_template('create-post.html',id=id, error='Missing Information')
    if salary and not salary.isdigit():
      return render_template('create-post.html',id=id, error='Salary should be a number')
    query = text(f"SELECT MAX(role_id) FROM Role_Posts")
    result = g.conn.execute(query)
    role_id = result.fetchone()[0] + 1
    result.close()
    cmd = text('INSERT INTO Role_Posts VALUES (:id,:position,:description,:location,:salary,:role_type,:date,:company_id)')
    g.conn.execute(text(cmd), id=role_id,position=position,description=description,location=location,salary=salary,role_type=role_type,date=datetime.now(),company_id=id)
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
  # TODO 
  # Here if a user is logged in, we don't want to redirect
  # them to the login page. Rather, we should be able to 
  # show up the dashboard, depending on whether they are 
  # a company or applicant.

@app.route('/login', methods=['GET','POST'])
def do_admin_login():
  if request.method == 'POST':
    email = request.form['email']
    password = request.form['password']
    if email and password:
      query = text(f"SELECT password FROM App_Password WHERE user_email = '{email}'")
      result = g.conn.execute(query)
      user_data = result.fetchone()
      result.close()
      if user_data and password == user_data[0]:
        flash('Logged in successfully!', 'success')
        session['logged_in'] = True
      
        query = text(f"SELECT company_id,applicant_id FROM App_User WHERE user_email = '{email}'")
        result = g.conn.execute(query)
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
    query = text(f"SELECT * FROM App_Password WHERE user_email = '{new_email}'")
    result = engine.execute(query)
    user_data = result.fetchone()
    result.close()
    if user_data and user_data[0]:
      return render_template('create-account-applicant.html',error='Email already exists')

    cmd = 'INSERT INTO App_Password VALUES (:email1,:password1)'
    g.conn.execute(text(cmd), email1 = new_email, password1 = new_password)

    query = text(f"SELECT MAX(applicant_id) FROM Applicant")
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

    if not new_email or not new_password or not confirm_password or not new_name or not new_size or not new_field:
      return render_template('create-account-company.html',error='Missing Information')
    if new_size and not new_size.isdigit():
      return render_template('create-account-company.html',error='Company size must be a number')
    #if not is_strong_password(new_password):
    #  return render_template('create-account-company.html',error='Password must have 8 characters minumum, at least one uppercase, one lowercase, and one speacial character.')
    if new_password != confirm_password:
      return render_template('create-account-company.html',error='Passwords do not match')
    if not is_valid_email(new_email):
      return render_template('create-account-company.html',error='Must enter proper email.')

    query = text(f"SELECT * FROM App_Password WHERE user_email = '{new_email}'")
    result = g.conn.execute(query, {'email': new_email})
    #result = g.conn.execute(query)
    user_data = result.fetchone()
    result.close()
    if user_data and user_data[0]:
      return render_template('create-account-company.html',error='Email already exists')

    cmd = text('INSERT INTO App_Password VALUES (:email,:password)')
    g.conn.execute(cmd, {'email': new_email, 'password': new_password})
    ## g.conn.execute(text(cmd), email1 = new_email, password1 = new_password)
    query = text(f"SELECT MAX(company_id) FROM Company")
    result = g.conn.execute(query)
    company_id = result.fetchone()[0] + 1
    result.close()

    cmd = text('INSERT INTO Company VALUES (:id,:size,:field)')
    g.conn.execute(cmd, {'id': company_id, 'size': new_size, 'field': new_field})
    #g.conn.execute(text(cmd), id1 = company_id,size1=new_size,field1=new_field )
    cmd = text('INSERT INTO App_User VALUES (:email,:name,:id,null)')
    g.conn.execute(cmd, {'email': new_email, 'name': new_name, 'id': company_id})
    #g.conn.execute(text(cmd), email1 = new_email, name1 = new_name,id1 = company_id)
    
    session['logged_in'] = True
    print(f"Redirecting to /company/{company_id}")
    return redirect(url_for('company_home',id=company_id))

  return render_template('create-account-company.html')

@app.route('/delete/<int:role_id>', methods=['POST'])
def delete_role(role_id):
    g.conn.execute('DELETE FROM roles WHERE role_id = ?', (role_id,))
    query = text(f"SELECT MAX(company_id) FROM Company")
    result = g.conn.execute(query)
    company_id = result.fetchone()[0] + 1
    return redirect(url_for('company_home',id=company_id))

def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def is_strong_password(password):
    # must have 8 chars, at least one uppercase, one lowercase, and one special char
    pattern = r'^(?=.*[A-Z])(?=.*[a-z])(?=.*[@$!%*?&])[A-Za-z@$!%*?&]{8,}$'
    return re.match(pattern, password) is not None

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
