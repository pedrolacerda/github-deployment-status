from flask import Flask, render_template, request, redirect, session, flash, url_for, Markup
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
import plotly.express as px
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import chart_studio.plotly as py
import plotly.tools as plotly_tools
import plotly.graph_objs as go
import plotly.io as pio
import os
import tempfile
import configparser
os.environ['MPLCONFIGDIR'] = tempfile.mkdtemp()
from IPython.display import HTML


app = Flask(__name__)
config = configparser.ConfigParser()
config.read('env/app.config')
BEARER_TOKEN = config['SECRETS']['GITHUB_PAT']
print("GITHUB_TOKEN"+BEARER_TOKEN)

_transport = RequestsHTTPTransport(
    url='https://api.github.com/graphql',
    use_json=True,
    headers={"authorization": "Bearer "+ BEARER_TOKEN}
)

client = Client(
    transport=_transport,
    fetch_schema_from_transport=True
)

query = gql("""
  query listDeploymentStatus($owner: String!, $repo_name: String!, $environment: [String!]){
      repository(owner: $owner, name: $repo_name){
        deployments(last: 100, environments: $environment){
          totalCount
          nodes{
            latestStatus{
              state
              createdAt
              updatedAt
            } 
           # state
          }
          
          pageInfo{
            endCursor
            hasNextPage
            hasPreviousPage
          }
      
        }
      }
  }
""")

params = {
    'owner': 'poc-itau',
    'repo_name': 'ReadingTimeDemo',
    'environment': ['Review AWS', 'Review Azure', 'production']
    # "owner" : "octodemo",
    # "repo_name": "ReadingTimeDemo", 
    # "environment": ["development", "review", "github-pages", "production"]
}

repository = client.execute(query, variable_values=params)["repository"]
deployments_list = repository["deployments"]
total_deployments = deployments_list["totalCount"]
deployments = deployments_list["nodes"]

# Map of number of deployments per status
deployments_by_status = {}
deployments_normalized = []

# Increment number of deployments for each status
# [PENDING, SUCCESS, FAILURE, INACTIVE, ERROR, QUEUED, IN_PROGRESS]
for deploy in deployments:
    latestStatus = deploy['latestStatus']
    
    try:
        # Increment the existing status's count.
        deployments_by_status[latestStatus['state']] += 1
        deployments_normalized.append(latestStatus)
    except KeyError:
        # This status has not been seen. Set its count to 1.
        deployments_by_status[latestStatus['state']] = 1
        deployments_normalized.append(latestStatus)
    except (AttributeError, TypeError, NameError) as e:
        print("Null object found")


df = pd.DataFrame(deployments_normalized)
df['createdAt'] = pd.to_datetime(df['createdAt']).apply(lambda x: x.date())
df['updatedAt'] = pd.to_datetime(df['updatedAt']).apply(lambda x: x.date())

# Group the dataset and retransform it from Group object to DataFrame
df = pd.DataFrame({'count' : df.groupby(['state', 'updatedAt']).size()}).reset_index()

df_pending     = df['state'] == 'PENDING'
df_success     = df['state'] == 'SUCCESS'
df_failure     = df['state'] == 'FAILURE'
df_inactive    = df['state'] == 'INACTIVE'
df_error       = df['state'] == 'ERROR'
df_queued      = df['state'] == 'QUEUED'
df_in_progress = df['state'] == 'IN_PROGRESS'

fig = go.Figure()

fig.add_trace(go.Scatter(x=df[df_success]['updatedAt'], y=df[df_success]['count'], mode='lines+markers', name='SUCCESS'))
fig.add_trace(go.Scatter(x=df[df_pending]['updatedAt'], y=df[df_pending]['count'], mode='lines+markers', name='PENDING'))
fig.add_trace(go.Scatter(x=df[df_failure]['updatedAt'], y=df[df_failure]['count'], mode='lines+markers', name='FAILURE'))
fig.add_trace(go.Scatter(x=df[df_inactive]['updatedAt'], y=df[df_inactive]['count'], mode='lines+markers', name='INACTIVE'))
fig.add_trace(go.Scatter(x=df[df_error]['updatedAt'], y=df[df_error]['count'], mode='lines+markers', name='ERROR'))
fig.add_trace(go.Scatter(x=df[df_queued]['updatedAt'], y=df[df_queued]['count'], mode='lines+markers', name='QUEUED'))
fig.add_trace(go.Scatter(x=df[df_in_progress]['updatedAt'], y=df[df_in_progress]['count'], mode='lines+markers', name='IN PROGRESS'))
fig.update_layout(title='Deployments Timestamp')

pio.write_html(fig, file='templates/chart.html', auto_open=False)

summary_table = df.describe()
summary_table = summary_table\
    .to_html()\
    .replace('<table border="1" class="dataframe">','<table class="table table-striped">') # use bootstrap styling

@app.route("/")
def index():
    return render_template('template.html', title='Deployment Statuses', status=deployments_by_status, total_deployments=total_deployments, table=summary_table)
