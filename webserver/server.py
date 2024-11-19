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

  query = text(f"SELECT user_name FROM App_User WHERE applicant_id = '{id}'")
  result = g.conn.execute(query)
  name = result.fetchone()[0]
  result.close()

  cursor1 = g.conn.execute(
  text("""SELECT * FROM Role_Posts
  JOIN Applies ON Applies.role_id = Role_Posts.role_id
  JOIN App_User ON App_User.company_id = Role_Posts.company_id
  WHERE Applies.applicant_id = :applicant_id"""),
  {'applicant_id': int(id)}
  )
  role = [row for row in cursor1]
  cursor1.close()
  context_apps = dict(data_apps = role)

  cursor2 = g.conn.execute(text("SELECT * FROM Event_Holds,Attends WHERE Event_Holds.event_id = Attends.event_id AND Attends.applicant_id = :applicant_id"),{"applicant_id": int(id)})
  event = []
  for result in cursor2:
    event.append(result)
  cursor2.close()
  context_events = dict(data_events = event)

  cursor3 = g.conn.execute(
  text("""SELECT * FROM Role_Posts
  JOIN Interviews ON Interviews.role_id = Role_Posts.role_id
  JOIN App_User ON App_User.company_id = Role_Posts.company_id
  WHERE Interviews.applicant_id = :applicant_id"""),
  {'applicant_id': int(id)}
  )
  interview = [row for row in cursor3]
  cursor3.close()
  context_interviews = dict(data_interviews=interview)
  return render_template('applicant.html', id=id, name=name, **context_apps, **context_events, **context_interviews)

@app.route('/applicant/<id>/<role_id>/update_status', methods=['POST'])
def update_status(id=None, role_id=None):
    if not session.get('logged_in'):
      return home()
    status = request.form.get('status')

    query = text("""
        UPDATE Applies 
        SET status = :status 
        WHERE role_id = :role_id AND applicant_id = :applicant_id
    """)
    g.conn.execute(query, {'status': status, 'role_id': role_id, 'applicant_id': id})
    g.conn.commit()
    return redirect(url_for('applicant_home', id=id))


@app.route('/applicant/<applicant_id>/<role_id>/interviews', methods=['GET', 'POST'])
def interviews(applicant_id=None, role_id=None):
  if not session.get('logged_in'):
    return home()
  with engine.connect() as conn:
    if request.method == 'POST':
      interview_types = request.form.get('interview_types')
      interview_dates = request.form.get('interview_dates')
      interview_dates = datetime.strptime(interview_dates, '%Y-%m-%d').date()
      notes = request.form.get('notes') or ""
      
      # Check if an interview record already exists for this role and applicant
      select_query = """
      SELECT * FROM interviews 
      WHERE role_id = :role_id AND applicant_id = :applicant_id
      """
      existing_interview = conn.execute(
        text(select_query), 
        {'role_id': role_id, 'applicant_id': applicant_id}
        ).fetchone()
      
      # Update the existing record by appending to arrays
      if existing_interview is not None:
        update_query = """
        UPDATE interviews 
        SET interview_types = array_append(interview_types, :interview_types),
        interview_dates = array_append(interview_dates, :interview_dates),
        interview_notes = array_append(interview_notes, :notes)
        WHERE role_id = :role_id AND applicant_id = :applicant_id
        """
        conn.execute(text(update_query), {
          'role_id': role_id,
          'applicant_id': applicant_id,
          'interview_types': interview_types,
          'interview_dates': interview_dates,
          'notes': notes,
          })
        conn.commit()
      else:
        insert_query = """
        INSERT INTO interviews VALUES (:role_id, :applicant_id, ARRAY[:interview_dates]::date[], ARRAY[:notes], ARRAY[:interview_types])
        """
        conn.execute(text(insert_query),{
            'role_id': role_id,
            'applicant_id': applicant_id,
            'interview_dates': interview_dates,
            'notes': notes,
            'interview_types': interview_types,
        })
        conn.commit()
      # Redirect to the interview history page after adding or updating an interview
      return redirect(url_for('interviews', applicant_id=applicant_id, role_id=role_id))
    # Fetch all existing interviews for this applicant and role
    select_query = """
    SELECT * FROM interviews
    WHERE role_id = :role_id AND applicant_id = :applicant_id
    """
    result = conn.execute(text(select_query), {'role_id': role_id, 'applicant_id': applicant_id})
    interviews = result.fetchall()
    
    interviews_list = [{
      'role_id': row.role_id,
      'interview_types': row.interview_types,
      'interview_dates': row.interview_dates,
      'interview_notes': row.interview_notes,
      } for row in interviews]
    print("Fetched interviews:", interviews_list)
  # Render the interviews page with the fetched interview data
  return render_template('interviews.html', id=applicant_id, role_id=role_id, interviews=interviews_list)
  
@app.route('/applicant/<id>/events', methods=['GET', 'POST'])
def signup_events(id=None):
  if not session.get('logged_in'):
    return home()
  query = text("""
        SELECT DISTINCT *
        FROM Event_Holds
        JOIN App_User ON App_User.company_id = Event_Holds.company_id
        WHERE Event_Holds.event_id NOT IN (
            SELECT event_id
            FROM Attends
            WHERE applicant_id = :applicant_id
        ) AND Event_Holds.event_date >= CURRENT_DATE
    """)
  cursor1 = g.conn.execute(query, {'applicant_id': id})
  event = [result for result in cursor1]
  cursor1.close()
  context_events = dict(data_events = event)
  
  if request.method == 'POST':
    event_id = request.form.get('event')
    cursor2 = g.conn.execute(text("SELECT * FROM Attends WHERE event_id =:event_id AND applicant_id =:applicant_id"),{'event_id':event_id,'applicant_id':id})
    user_data = cursor2.fetchone()
    cursor2.close()
    if user_data and user_data[0]:
      return render_template('signup-events.html',id=id,**context_events,error='Already signed-up to attend')
    cmd = 'INSERT INTO Attends VALUES (:id,:event_id)'
    g.conn.execute(text(cmd), {'id':int(id),'event_id':int(event_id)})
    g.conn.commit()
  return render_template('signup-events.html',id=id,**context_events)


@app.route('/applicant/<id>/roles', methods=['GET', 'POST'])
def signup_roles(id=None):
  if not session.get('logged_in'):
    return home()
  query = text("""
        SELECT DISTINCT
            App_User.user_name,
            Role_Posts.role_id,
            Role_Posts.role_position,
            Role_Posts.role_description,
            Role_Posts.role_location,
            Role_Posts.role_salary,
            Role_Posts.role_type
        FROM Role_Posts
        JOIN App_User ON App_User.company_id = Role_Posts.company_id
        WHERE Role_Posts.role_id NOT IN (
            SELECT role_id
            FROM Applies
            WHERE applicant_id = :applicant_id
        )
    """)
  cursor1 = g.conn.execute(query, {'applicant_id': id})
  role = [result for result in cursor1]
  cursor1.close()
  context_roles = dict(data_roles = role)
  if request.method == 'POST':
    role_id = request.form.get('role')
    cursor2 = g.conn.execute(text("SELECT * FROM Applies WHERE role_id =:role_id AND applicant_id =:applicant_id"),{'role_id':role_id,'applicant_id':id})
    user_data = cursor2.fetchone()
    cursor2.close()
    if user_data and user_data[0]:
      return render_template('signup-roles.html',id=id,**context_roles,error='Already applied')
    cmd = 'INSERT INTO Applies VALUES (:role_id,:id,:date,:status)'
    g.conn.execute(text(cmd), {'role_id':int(role_id),'id':int(id),'date':datetime.now(),'status':'Applied'})
    g.conn.commit()
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
  name = result.fetchone()[0]
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

  cursor3 = g.conn.execute(text("SELECT * FROM Event_Holds,Leads,Organizer WHERE Leads.event_id=Event_Holds.event_id AND Organizer.org_id=Leads.org_id AND company_id = :company_id"), {'company_id': int(id)})
  org = []
  for result in cursor3:
    org.append(result)
  cursor3.close()
  context_orgs = dict(data_orgs = org)

  return render_template("company.html", id=id, name = name, **context_posts, **context_events,**context_orgs)


@app.route('/company/<id>/event', methods=['GET', 'POST'])
def create_event(id=None):
  if not session.get('logged_in'):
    return home()
  if request.method == 'POST':
    notes = request.form['notes']
    date = datetime.fromisoformat(request.form['date'])
    attendees = request.form['attendees']
    event_type = request.form['event_type']
    org_name=request.form['organizer-name']
    org_email=request.form['organizer-email']
    org_role=request.form['organizer-role']
    org_linkedin=request.form['organizer-linkedin']

    if not date or not event_type or not notes or not attendees:
      return render_template('create-event.html',id=id, error='Missing Information')
    if attendees and not attendees.isdigit():
      return render_template('create-event.html',id=id, error='Attendees should be a number')
    if (org_name and not org_email) or (not org_name and org_email):
      return render_template('create-event.html',id=id, error='Organizers should have a name and email')
    if(org_email and not is_valid_email(org_email)):
      return render_template('create-event.html',id=id, error='Invalid email')
    if(org_linkedin and not is_valid_linkedin(org_linkedin)):
      return render_template('create-event.html',id=id, error='Invalid linkedin, must begin with "http://linkedin.com/in/"')

    query = text(f"SELECT MAX(event_id) FROM Event_Holds")
    result = g.conn.execute(query)
    event_id = result.fetchone()[0] + 1
    result.close()
    cmd = text("""INSERT INTO Event_Holds 
               VALUES (:event_id,:company_id,:event_notes,:attendees,:event_date,:info_session,:coffee_chat)""")
    
    g.conn.execute(cmd, {
      'event_id': event_id,
      'company_id': id,
      'event_notes': notes,
      'attendees': int(attendees),
      'event_date': date,
      'info_session': True if event_type == 'Info_session' else False,
      'coffee_chat': True if event_type == 'Coffee_chat' else False
      })
    g.conn.commit()

    if org_name and org_email:
      query = text(f"""SELECT MAX(org_id) FROM Organizer""")
      result = g.conn.execute(query)
      org_id = result.fetchone()[0] + 1
      result.close()
      cmd = text("""INSERT INTO Organizer VALUES (:org_id,:org_name,:org_email,:org_role,:org_linkedin)""")
    
      g.conn.execute(cmd, {
        'org_id': org_id,
        'org_name': org_name,
        'org_email': org_email,
        'org_role': org_role,
        'org_linkedin': org_linkedin,
        })
      g.conn.commit()

      cmd = text("""INSERT INTO Leads VALUES (:org_id,:event_id)""")
      g.conn.execute(cmd, {
        'org_id': org_id,
        'event_id': event_id
        })
      g.conn.commit()

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
    query = text(f"""SELECT MAX(role_id) FROM Role_Posts""")
    result = g.conn.execute(query)
    role_id = result.fetchone()[0] + 1
    result.close()
    cmd = text("""
               INSERT INTO Role_Posts(role_id, role_position, role_description, role_location, role_salary, role_type, date_posted, company_id)
               VALUES (:role_id, :position, :description, :location, :salary, :role_type, :date, :company_id)
               """)
    g.conn.execute(cmd, {
      'role_id': role_id,
      'position': position,
      'description': description,
      'location': location,
      'salary': int(salary) if salary else None,
      'role_type': role_type,
      'date': datetime.now().date(),
      'company_id': id
      })
    g.conn.commit()
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
        session['logged_in'] = True
        query = text(f"SELECT company_id,applicant_id FROM App_User WHERE user_email = '{email}'")
        result = g.conn.execute(query)
        user_data = result.fetchone()
        result.close()
        if user_data:
          if user_data[0]:
            return redirect(url_for('company_home', id=user_data[0]))
          elif user_data[1]:
            return redirect(url_for('applicant_home', id=user_data[1]))
      else:
        return render_template('login.html',error='Username or password not found. Try again.')
    else:
      return render_template('login.html',error='Username or password not found. Try again.')
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
      return render_template('create-account-applicant.html',error='Passwords do not match')
    query = text(f"SELECT * FROM App_Password WHERE user_email = '{new_email}'")
    result = g.conn.execute(query)
    user_data = result.fetchone()
    result.close()
    if user_data and user_data[0]:
      return render_template('create-account-applicant.html',error='Email already exists')

    cmd = 'INSERT INTO App_Password VALUES (:email,:password)'
    g.conn.execute(text(cmd), {'email':new_email, 'password':new_password})
    g.conn.commit()

    query = text(f"SELECT MAX(applicant_id) FROM Applicant")
    result = g.conn.execute(query)
    applicant_id = result.fetchone()[0] + 1
    result.close()

    cmd = 'INSERT INTO Applicant VALUES (:id,:occupation)'
    g.conn.execute(text(cmd), {'id':applicant_id,'occupation':new_occupation})
    g.conn.commit()
    cmd = 'INSERT INTO App_User VALUES (:email,:name,null,:id)'
    g.conn.execute(text(cmd), {'email':new_email, 'name':new_name,'id':applicant_id})
    g.conn.commit()

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
    if not is_strong_password(new_password):
      return render_template('create-account-company.html',error='Password must have 8 characters minumum, at least one uppercase, one lowercase, and one speacial character.')
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
    g.conn.commit()
    query = text(f"SELECT MAX(company_id) FROM Company")
    result = g.conn.execute(query)
    company_id = result.fetchone()[0] + 1
    result.close()

    cmd = text('INSERT INTO Company VALUES (:id,:size,:field)')
    g.conn.execute(cmd, {'id': company_id, 'size': new_size, 'field': new_field})
    g.conn.commit()
    cmd = text('INSERT INTO App_User VALUES (:email,:name,:id,null)')
    g.conn.execute(cmd, {'email': new_email, 'name': new_name, 'id': company_id})
    g.conn.commit()
    
    session['logged_in'] = True
    return redirect(url_for('company_home',id=company_id))

  return render_template('create-account-company.html')

@app.route('/company/<id>/delete_role/<role_id>', methods=['POST'])
def delete_role(id,role_id):
  if not session.get('logged_in'):
    return home()
  g.conn.execute(text('DELETE FROM Applies WHERE role_id = :role_id'), {"role_id": int(role_id)})
  g.conn.commit()
  g.conn.execute(text('DELETE FROM Interviews WHERE role_id = :role_id'), {"role_id": int(role_id)})
  g.conn.commit()
  g.conn.execute(text('DELETE FROM Role_Posts WHERE role_id = :role_id'), {"role_id": int(role_id)})
  g.conn.commit()

  return redirect(url_for('company_home',id=id))

@app.route('/company/<id>/delete_event/<event_id>', methods=['POST'])
def delete_event(id,event_id):
  if not session.get('logged_in'):
    return home()
  g.conn.execute(text('DELETE FROM Attends WHERE event_id = :event_id'), {"event_id": int(event_id)})
  g.conn.commit()
  g.conn.execute(text('DELETE FROM Leads WHERE event_id = :event_id'), {"event_id": int(event_id)})
  g.conn.commit()
  g.conn.execute(text('DELETE FROM Event_Holds WHERE event_id = :event_id'), {"event_id": int(event_id)})
  g.conn.commit()
  return redirect(url_for('company_home',id=id))

def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def is_valid_linkedin(link):
    pattern = r'^http://linkedin\.com/in/[\w-]+$'
    return re.match(pattern, link) is not None

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
