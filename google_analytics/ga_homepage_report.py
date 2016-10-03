from __future__ import division
import vertica_python
import numpy as np
from pandas import Series, DataFrame
import pandas as pd
from vertica_python import connect
import StringIO
from StringIO import StringIO
from datetime import date, timedelta as td
import xlsxwriter
import os
import json
import urllib2
import base64
import datetime
import re
import csv
import pandas as pd
from pandas import DataFrame, Series
import numpy as np


#pd.options.display.float_format = '{:.2f}%'.format


# In[2]:

d1 = date(2016, 9, 22) # Start Date
d2 = date(2016, 9, 23) # End Date
filepath="C:/Users/ochang/Desktop/Weekly Marketing Reports/HP Snapshots/"
#recipients = ["patrick@edx.org","snorkin@edx.org","rsacks@edx.org","ebottomy@edx.org","jzheng@edx.org","cvongsy@edx.org","junjie@edx.org"]
recipients = ["ojchang@edx.org"]

# In[3]:

"""A simple example of how to access the Google Analytics API."""

import argparse

# pip install --upgrade google-api-python-client
from apiclient.discovery import build
import httplib2
from oauth2client import client
from oauth2client import file
from oauth2client import tools

def get_service(api_name, api_version, scope, client_secrets_path):
  """Get a service that communicates to a Google API.

  Args:
    api_name: string The name of the api to connect to.
    api_version: string The api version to connect to.
    scope: A list of strings representing the auth scopes to authorize for the
      connection.
    client_secrets_path: string A path to a valid client secrets file.

  Returns:
    A service that is connected to the specified API.
  """
  # Parse command-line arguments.
  parser = argparse.ArgumentParser(
      formatter_class=argparse.RawDescriptionHelpFormatter,
      parents=[tools.argparser])
  flags = parser.parse_args([])

  # Set up a Flow object to be used if we need to authenticate.
  flow = client.flow_from_clientsecrets(
      client_secrets_path, scope=scope,
      message=tools.message_if_missing(client_secrets_path))

  # Prepare credentials, and authorize HTTP object with them.
  # If the credentials don't exist or are invalid run through the native client
  # flow. The Storage object will ensure that if successful the good
  # credentials will get written back to a file.
  storage = file.Storage(api_name + '.dat')
  credentials = storage.get()
  if credentials is None or credentials.invalid:
    credentials = tools.run_flow(flow, storage, flags)
  http = credentials.authorize(http=httplib2.Http())

  # Build the service object.
  service = build(api_name, api_version, http=http)

  return service


def get_hpEnrolls(service,date):
  # Use the Analytics Service Object to query the Core Reporting API
  # for the number of sessions in the past seven days.
  filters = [
    'ga:eventAction==edx.bi.user.course-details.enroll.header',
    'ga:eventAction==edx.bi.user.course-details.enroll.main',
    'ga:eventAction==edx.bi.user.xseries-details.enroll.discovery-card',
    'ga:eventAction==edx.bi.user.course-details.enroll.discovery-card',
  ]
  return service.data().ga().get(
      ids='ga:' + '86300562',
      start_date=str(date),
      end_date=str(date),
      max_results=10000,
      metrics='ga:totalEvents,ga:uniqueEvents',
      dimensions='ga:date,ga:pageTitle',
      filters=','.join(filters),
      segment='sessions::sequence::ga:pagePath==/;->ga:pagePath!~^/course/subject/;ga:pagePath=~^/course/,ga:pagePath=~^/xseries/,ga:pagePath=~^/micromasters/;->>ga:eventAction==edx.bi.user.course-details.enroll.header,ga:eventAction==edx.bi.user.course-details.enroll.main,ga:eventAction==edx.bi.user.xseries-details.enroll.discovery-card,ga:eventAction==edx.bi.user.course-details.enroll.discovery-card').execute()

def get_X(service,date):
  # Use the Analytics Service Object to query the Core Reporting API
  # for the number of sessions in the past seven days.
  return service.data().ga().get(
      ids='ga:' + '86300562',
      start_date=str(date),
      end_date=str(date),
      max_results=10000,
      metrics='ga:pageviews',
      dimensions='ga:date,ga:pageTitle',
      filters='ga:landingPagePath=~^/xseries/;ga:secondPagePath=~^/course/;,ga:pagePath=~^/micromasters/').execute()


def get_hpCourseViews(service,date):
  # Use the Analytics Service Object to query the Core Reporting API
  # for the number of sessions in the past seven days.
  return service.data().ga().get(
      ids='ga:' + '86300562',
      start_date=str(date),
      end_date=str(date),
      max_results=10000,
      metrics='ga:pageviews,ga:uniquePageviews',
      dimensions='ga:date,ga:pageTitle',
      filters='ga:previousPagePath==/;ga:pagePath!~^/course/subject/;ga:pagePath=~^/course/,ga:pagePath=~^/xseries/,ga:pagePath=~^/micromasters/').execute()

def get_hpSubjectViews(service,date):
  # Use the Analytics Service Object to query the Core Reporting API
  # for the number of sessions in the past seven days.
  return service.data().ga().get(
      ids='ga:' + '86300562',
      start_date=str(date),
      end_date=str(date),
      max_results=10000,
      metrics='ga:pageviews,ga:uniquePageviews',
      dimensions='ga:date,ga:pageTitle',
      filters='ga:previousPagePath==/;ga:pagePath=~^/course/subject/').execute()

def get_hpViews(service,date):
  # Use the Analytics Service Object to query the Core Reporting API
  # for the number of sessions in the past seven days.
  return service.data().ga().get(
      ids='ga:' + '86300562',
      start_date=str(date),
      end_date=str(date),
      max_results=10000,
      metrics='ga:pageviews,ga:uniquePageviews',
      dimensions='ga:date',
      filters='ga:pagePath==/').execute()


def main_hpEnrolls(date):
  # Define the auth scopes to request.
  scope = ['https://www.googleapis.com/auth/analytics.readonly']

  # Authenticate and construct service.
  service = get_service('analytics', 'v3', scope, 'client_secrets.json')

  return get_hpEnrolls(service,str(date))['rows']


def main_hpViews(date):
  # Define the auth scopes to request.
  scope = ['https://www.googleapis.com/auth/analytics.readonly']

  # Authenticate and construct service.
  service = get_service('analytics', 'v3', scope, 'client_secrets.json')

  return get_hpCourseViews(service,str(date))['rows']

def main_hpSubjectViews(date):
  # Define the auth scopes to request.
  scope = ['https://www.googleapis.com/auth/analytics.readonly']

  # Authenticate and construct service.
  service = get_service('analytics', 'v3', scope, 'client_secrets.json')

  return get_hpSubjectViews(service,str(date))['rows']

def main_hpViewsTot(date):
  # Define the auth scopes to request.
  scope = ['https://www.googleapis.com/auth/analytics.readonly']

  # Authenticate and construct service.
  service = get_service('analytics', 'v3', scope, 'client_secrets.json')

  return get_hpViews(service,str(date))['rows']


def substring(x):
    z=len(x)
    y=(z-6)
    temp=x[:y]
    return temp
substring('IELTS Academic Test Preparation | edX')


# In[4]:

delta = d2 - d1

t=0

for i in range(delta.days + 1):
    t=t+1
    dt=d1 + td(days=i)
    print dt
    print t
    if t==1:
        hpData=main_hpEnrolls(dt)
        hpData2=main_hpViews(dt)
        hpDataSubj=main_hpSubjectViews(dt)
        hpDataViews=main_hpViewsTot(dt)
    if t>1:
        hpData=hpData+main_hpEnrolls(dt)
        hpData2=hpData2+main_hpViews(dt)
        hpDataSubj=hpDataSubj+main_hpSubjectViews(dt)
        hpDataViews=hpDataViews+main_hpViewsTot(dt)



# In[5]:

hpDataViews=DataFrame(hpDataViews,columns=['date','views','uniqueViews'])
hpDataViews=hpDataViews.convert_objects(convert_numeric=True)
hpTotal=int(hpDataViews['uniqueViews'].sum())
hpTotal


# In[6]:

hpSubjData=DataFrame(hpDataSubj,columns=['date','page_title','views','uniqueViews'])
hpSubjData=hpSubjData.convert_objects(convert_numeric=True)
hpSubjData.drop('date', axis=1, inplace=True)
hpSubjData2=hpSubjData.groupby(['page_title']).sum().sort(['uniqueViews'],ascending=0)
hpSubjData2.reset_index(inplace=True)
hpSubjData2['subject']=hpSubjData2['page_title'].apply(lambda x: substring(x))
hpSubjData2['totViews'] = hpSubjData2['uniqueViews'].sum()
hpSubjData2['Pct'] =(hpSubjData2['uniqueViews'] /hpSubjData2['totViews'])
hpSubjData2=hpSubjData2[(hpSubjData2['Pct']>0.0001)]
hpSubjData2.to_clipboard(excel=True,encoding='utf-8')
hpSubjDataFinal=hpSubjData2[['subject','uniqueViews','Pct']]
#hpSubjDataFinal['Pct'] = hpSubjDataFinal['Pct'].astype(int)
hpSubjDataFinal


# In[7]:

hpViewData=DataFrame(hpData2,columns=['date','page_title','views','uniqueViews'])
hpViewData=hpViewData.convert_objects(convert_numeric=True)
hpViewData.drop('date', axis=1, inplace=True)
hpViewData2=hpViewData.groupby(['page_title']).sum().sort(['uniqueViews'],ascending=0)
hpViewData2.reset_index(inplace=True)
#hpViewData2['course_name']=hpViewData2['course_title'].apply(lambda x: substring(x))
hpViewData2.to_clipboard(excel=True,encoding='utf-8')
hpViewData2.head()


# In[8]:

hpData2=DataFrame(hpData,columns=['date','page_title','totalEnrolls','uniqueEnrolls'])
hpData2=hpData2.convert_objects(convert_numeric=True)
hpData2.drop('date', axis=1, inplace=True)
hpData3=hpData2.groupby(['page_title']).sum().sort(['uniqueEnrolls'],ascending=0)
hpData3.reset_index(inplace=True)
#hpData4=pd.merge(hpData3,courseCat,on='course_id',how='left')[['course_name','org','start_date','course_id','uniqueEnrolls','page']]
#hpData4.sort(['uniqueEnrolls'],ascending=0,inplace=True)
hpData3.to_clipboard(excel=True,encoding='utf-8')
hpData3.head()
courseEnrolls=hpData3[['page_title','uniqueEnrolls']]
courseEnrolls['course_name']=courseEnrolls['page_title'].apply(lambda x: substring(x))
courseEnrolls.drop('page_title', axis=1, inplace=True)
courseEnrolls[['course_name','uniqueEnrolls']].head()


# In[9]:

pd.merge(hpViewData2,hpData3,on='page_title',how='outer').to_clipboard(excel=True,encoding='utf-8')
hpTop12=pd.merge(hpViewData2,hpData3,on='page_title',how='outer').head(14)
hpTop12['totViews'] = hpTop12['uniqueViews'].sum()
hpTop12['CR'] =(hpTop12['uniqueEnrolls'] /hpTop12['uniqueViews'])
hpTop12['CTR'] =(hpTop12['uniqueViews'] /hpTotal)
hpTop12['clickShare'] =(hpTop12['uniqueViews'] /hpTop12['totViews'])
hpTop12['enrollsPerImp'] =(hpTop12['uniqueEnrolls'] /hpTop12['totViews'])
hpTop12['course_name']=hpTop12['page_title'].apply(lambda x: substring(x))
final12=hpTop12[['course_name','uniqueViews','CTR','clickShare','uniqueEnrolls','CR','enrollsPerImp']]
final12


# In[10]:

#from pandas import ExcelWriter
#writer = ExcelWriter(str(filepath)+'HP Data '+str(d1)+' to '+str(d2)+'.xlsx')
#hpTop12[['course_name','uniqueViews','CR','clickShare','uniqueEnrolls','enrollsPerImp']].to_excel(writer,'HomepageCourses',index=False)
#hpSubjDataFinal.to_excel(writer,'HomepageSubjects',index=False)
#writer.save()
int(final12['uniqueViews'].sum())/hpTotal


# In[11]:

excelFile=str(filepath)+'HP Data '+str(d1)+' to '+str(d2)+'.xlsx'
from pandas import ExcelWriter
writer = pd.ExcelWriter(excelFile,engine='xlsxwriter')
final12.to_excel(writer, index=False, sheet_name='HomepageCourses', startrow=8)
hpSubjDataFinal.to_excel(writer, index=False, sheet_name='HomepageSubjects', startrow=2)
courseEnrolls[['course_name','uniqueEnrolls']].to_excel(writer, index=False, sheet_name='CourseEnrolls', startrow=2)


# Get access to the workbook and sheet
workbook = writer.book
worksheet = writer.sheets['HomepageCourses']

money_fmt = workbook.add_format({'num_format': '$#,##0', 'bold': True})
percent_fmt = workbook.add_format({'num_format': '0.0%', 'bold': False})
comma_fmt = workbook.add_format({'num_format': '#,##0', 'bold': False})
date_fmt = workbook.add_format({'num_format': 'dd/mm/yy'})
cell_format = workbook.add_format({'bold': True, 'italic': False})

worksheet.conditional_format('F1:F1000', {'type': '3_color_scale'})
worksheet.conditional_format('D1:D1000', {'type': '3_color_scale'})
worksheet.conditional_format('C1:C1000', {'type': '3_color_scale'})
worksheet.conditional_format('G1:G1000', {'type': '3_color_scale'})

worksheet.set_column('A:A', 60)
worksheet.set_column('B:B', 15, comma_fmt)
worksheet.set_column('E:E', 15, comma_fmt)
worksheet.set_column('C:D', 15, percent_fmt)
worksheet.set_column('F:G', 15, percent_fmt)
worksheet.write('A1', 'Homepage Course Enrollments, Data from '+str(d1)+' to '+str(d2) , cell_format)
worksheet.write('A3', 'Total Homepage Views:', cell_format)
worksheet.write('A4', 'Total Click-Throughs to Courses Below:', cell_format)
worksheet.write('A5', 'Total CTR:', cell_format)
worksheet.write('A6', 'Total Enrollments:', cell_format)
worksheet.write('A7', 'Total Enrollments per Homepage View:', cell_format)

worksheet.write('B3', hpTotal, comma_fmt)
worksheet.write('B4', int(final12['uniqueViews'].sum()), comma_fmt)
worksheet.write('B5', int(final12['uniqueViews'].sum())/hpTotal, percent_fmt)
worksheet.write('B6', int(final12['uniqueEnrolls'].sum()), comma_fmt)
worksheet.write('B7', int(final12['uniqueEnrolls'].sum())/hpTotal, percent_fmt)


worksheet = writer.sheets['HomepageSubjects']

worksheet.conditional_format('C1:C1000', {'type': '3_color_scale'})

worksheet.set_column('A:A', 27)
worksheet.set_column('B:B', 15, comma_fmt)
worksheet.set_column('C:S', 15, percent_fmt)
worksheet.write('A1', 'Top Subject Pages from the Homepage, Data from '+str(d1)+' to '+str(d2) , cell_format)

worksheet = writer.sheets['CourseEnrolls']

worksheet.conditional_format('B1:B1000', {'type': '3_color_scale'})

worksheet.set_column('A:A', 100)
worksheet.set_column('B:B', 20, comma_fmt)
worksheet.write('A1', 'Course Enrollments from the Homepage, Data from '+str(d1)+' to '+str(d2) , cell_format)
worksheet.autofilter('A3:B3')

writer.save()
