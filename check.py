import configparser
import requests
import sqlite3
import time
import smtplib
from email.mime.text import MIMEText
# import pdb

class App:

    def __init__(self):
        config = configparser.ConfigParser()
        config.read('config.ini')
        self.smtp_host = config['email']['smtp_host']
        self.smtp_username = config['email']['smtp_username']
        self.smtp_password = config['email']['smtp_password']
        self.email_from = config['email']['email_from']
        self.email_to = config['email']['email_to']

        self.local_db_connection_string = 'site-checker.db'
        self.sqlite_conn = None
        self.test_sites = (
            ('classic_catalog', 'https://classic.cincinnatilibrary.org/'),
            ('encore', 'https://catalog.cincinnatilibrary.org/iii/encore/')
            #,
            # here are some other test sites we can use
            # ('status_500', 'https://httpstat.us/500'),
            # ('status_200', 'https://httpstat.us/200'),
            # ('site_not_exists', 'https://blakdjfkjdkajfdklfjkdsjfghghadkjklerjerjekfjdfkjd.com'),
            #('expired_ssl', 'https://expired.badssl.com/')
        )

        # open the local database, and create tables if we need to
        # sets self.sqlite_conn
        self.open_db_connections()

        for site in self.test_sites:
            try:
                r = None
                message = None
               
                # send the request to get the page
                r = requests.get(site[1])
                
                # debug
                # pdb.set_trace()
                # if we got a page back, regardless of status, it will be addressed in the function: send_status
                self.send_status(site[0], site[1], r.status_code, r.elapsed.total_seconds(), message)

            # deal with more specific / serious issues related to the HTTP request here
            except requests.exceptions.SSLError:
                message = 'SSL error'
                self.send_status(site[0], site[1], None, None, message)

            except requests.exceptions.ConnectionError:
                message = 'failed to connect'
                self.send_status(site[0], site[1], None, None, message)
                
            except requests.exceptions.RequestException as e:
                message = 'other failure: {}'.format(e)
                self.send_status(site[0], site[1], None, None, message)


    #~ the destructor
    def __del__(self):
        if self.sqlite_conn:
            if hasattr(self.sqlite_conn, 'commit'):
                self.sqlite_conn.commit()

        if hasattr(self.sqlite_conn, 'close'):
            print("closing sqlite_conn")
            self.sqlite_conn.close()

        self.sqlite_conn = None
		
        print("done.")
                

    def send_status(self, site_name=None, site_url=None, status_code=None, elapsed=None, message=None):
        # create a new cursor to use
        cursor = self.sqlite_conn.cursor()

        # if status code is not set, or it's set and is above 200, consider check a failure
        if (status_code == None) or (status_code > 200):
            success = False
            # send our message .. problem with site
            subject = 'site: {} is down!'.format(site_name)
            message = '{} : {}\nhas status: {}\nmessage: {}'.format(site_name, site_url, status_code, message)
            self.send_message(subject, message)
        else:
            success = True

        timestamp = int(time.time())

        values = (timestamp, site_name, site_url, status_code, elapsed, message, success)
        
        # print(values)
        # print('timestamep : {}'.format(timestamp))
        # print('site_name  : {}'.format(site_name))
        # print('site_url   : {}'.format(site_url))
        # print('status_code: {}'.format(status_code))
        # print('message    : {}'.format(message))
        # print('success    : {}'.format(success))
        # print('---')

        sql = """
        INSERT INTO
        status (
            'checked_date', 'site_name', 'site_url', 'status_code', 'elapsed', 'message', 'success'
        )

        VALUES 
        (?, ?, ?, ?, ?, ?, ?)
        """

        cursor.execute(sql, values)
        self.sqlite_conn.commit()
        cursor.close()
        cursor = None


    def open_db_connections(self):
        try:
            self.sqlite_conn = sqlite3.connect(self.local_db_connection_string)
        except sqlite3.Error as e:
            print("unable to connect to local database: %s" % e)

        # create a new cursor to use
        cursor = self.sqlite_conn.cursor()

        sql = """
        CREATE TABLE IF NOT EXISTS 'status' ( 
            'checked_date' INTEGER, -- stored as unix epoch time
            'site_name' TEXT,
            'site_url' TEXT,
            'status_code' INTEGER,
            'elapsed' REAL,
            'message' TEXT,
            'success' INTEGER -- true on success, false on fail or bad status)
        );
        """

        cursor.execute(sql)
        self.sqlite_conn.commit()

        sql = None
        sql = """
        CREATE TABLE IF NOT EXISTS 'message_sent' ( 
            'sent_date' INTEGER, -- stored as unix epoch time
            'to' TEXT,
            'from' TEXT,
            'subject' TEXT,
            'message' TEXT
        );
        """
        cursor.execute(sql)
        self.sqlite_conn.commit()

        cursor.close()
        cursor = None


    def send_message(self, subject, message):

        # create a new cursor to use
        cursor = self.sqlite_conn.cursor()

        # TODO: query the database for last similar or same message sent, so that we don't spam ourselves when the site is down

        msg = MIMEText(message)
        msg['Subject'] = subject
        msg['From'] = self.email_from
        msg['To'] = self.email_to
        
        mailserver = smtplib.SMTP(self.smtp_host, 587)
        # identify ourselves to smtp client
        mailserver.ehlo()
        # secure our email with tls encryption
        mailserver.starttls()
        # re-identify ourselves as an encrypted connection
        mailserver.ehlo()
        mailserver.login(self.smtp_username, self.smtp_password)
        mailserver.sendmail(self.email_from, self.email_to, msg.as_string())
        mailserver.quit()
        mailserver = None

        # push the last message into the database
        sql = """
        INSERT INTO
        message_sent (
            'sent_date', 'to', 'from', 'subject', 'message'
        )

        VALUES 
        (?, ?, ?, ?, ?)
        """

        values = (int(time.time()), self.email_to, self.email_from, subject, message)

        cursor.execute(sql, values)
        self.sqlite_conn.commit()
        cursor.close()
        cursor = None

# run the app
app = App()
