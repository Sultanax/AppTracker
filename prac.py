import os
from sqlalchemy import *
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.pool import NullPool
from sqlalchemy import create_engine, text
from flask import Flask, flash, request, render_template, g, redirect, Response, session, abort, url_for
import os
import re
from datetime import datetime

DB_USER = "sy3196"
DB_PASSWORD = "hotdogs123"
DB_SERVER = "w4111.cisxo09blonu.us-east-1.rds.amazonaws.com"
DATABASEURI = "postgresql://"+DB_USER+":"+DB_PASSWORD+"@"+DB_SERVER+"/w4111"

engine = create_engine(DATABASEURI)

with engine.connect() as conn:
    query = "SELECT * FROM event_holds"
    result = conn.execute(text(query))
    for row in result:
        print(row)
