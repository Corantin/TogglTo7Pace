# %% [markdown]
# This script is used to convert toggl time entries to 7pace
#
# # Requirements
# - Create the .env file starting from the .env.template file
# - Toggl entries should be the result of the work item copy button
# - Configurate the #Constants block

# %% [markdown]
# Set variables from environment variables

# %%
from datetime import datetime, timezone, timedelta
import json
from datetime import datetime, timedelta
import requests
import os
import sys
from dotenv import load_dotenv

load_dotenv(override=True)

# Constants

TOGGL_API_KEY = os.getenv('TOGGL_API_KEY')
TOGGL_WORKSPACE_ID = os.getenv('TOGGL_WORKSPACE_ID')
TOGGL_PROJECT_ID = os.getenv('TOGGL_PROJECT_ID')
SEVENPACE_API_KEY = os.getenv('SEVENPACE_API_KEY')
SEVENPACE_API_VERSION = os.getenv('SEVENPACE_API_VERSION')
DEVOPS_PERSONAL_ACCESS_TOKEN = os.getenv('DEVOPS_PERSONAL_ACCESS_TOKEN')

# If True, will only consider work items that were updated in the last week (vs current week)
LAST_WEEK = eval(os.getenv('LAST_WEEK'))

# Will be considered a TFS work item (not Azure Devops) if the work item id is greater than this number
TFS_7PACE_WORK_ITEM_THRESHOLD_START = int(
    os.getenv('TFS_7PACE_WORK_ITEM_THRESHOLD_START'))


# %%

# HTTP GET request to Toggl API


def TogglHttpGet(url, params):
    response = requests.get(url, auth=(
        TOGGL_API_KEY, 'api_token'), params=params)
    return response.json()


# %%
# Load the start and end dates of the current day week
day = datetime.now().strftime('%d/%b/%Y')
dt = datetime.strptime(day, '%d/%b/%Y')
start_day = (dt - timedelta(days=dt.weekday()))
if LAST_WEEK:
    start_day = start_day - timedelta(days=7)
end_day = start_day + timedelta(days=6)
print("Start: " + start_day.strftime('%Y-%m-%d'))
print("End: " + end_day.strftime('%Y-%m-%d'))


# %%

# Load toggl time entries for the specified project
TogglFetchEntriesUrl = 'https://api.track.toggl.com/api/v9/me/time_entries'
TimeEntries = TogglHttpGet(TogglFetchEntriesUrl, {
    'start_date': start_day.strftime('%Y-%m-%d'),
    'end_date': end_day.strftime('%Y-%m-%d')
})
# Filter time entries for the specified project
TimeEntries = [entry for entry in TimeEntries if entry['pid']
               == int(TOGGL_PROJECT_ID)]
print(json.dumps(TimeEntries, indent=4))


# %%
# Clear 7pace time entries for this week

url = f"https://geneteccentral.timehub.7pace.com/api/rest/workLogs/?api-version={SEVENPACE_API_VERSION}"
headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {SEVENPACE_API_KEY}'
}
response = requests.request("GET", url, headers=headers)
currentWeekWorklogs = []
for worklog in response.json()['data']:
    if worklog['timestamp'] >= start_day.strftime('%Y-%m-%d') and worklog['timestamp'] <= end_day.strftime('%Y-%m-%d'):
        currentWeekWorklogs.append(worklog)

if (len(currentWeekWorklogs) == 0):
    print("No entries already there in 7pace for this week")
else:
    print(json.dumps(
        list(map(lambda x: x['comment'], currentWeekWorklogs)), indent=2))

    inputResp = input(
        f"Deleting {str(len(currentWeekWorklogs))} entries. Continue ? (y/n)")
    if inputResp.lower() == 'n':
        exit

    error = False

    for worklog in currentWeekWorklogs:
        url = f"https://geneteccentral.timehub.7pace.com/api/rest/workLogs/{worklog['id']}?api-version={SEVENPACE_API_VERSION}"
        response = requests.request("DELETE", url, headers=headers)
    if not (response.status_code == 204 or response.status_code == 200):
        print("Error deleting worklog " + worklog['id'])
        print(response.text)
        error = True

    if not error:
        print(f"{str(len(currentWeekWorklogs))} worklogs deleted successfully")


# %%
# Fetch 7pace user id

url = f"https://geneteccentral.timehub.7pace.com/api/rest/me?api-version={SEVENPACE_API_VERSION}"

payload = {}
headers = {
    'Authorization': 'Bearer ' + SEVENPACE_API_KEY
}
response = requests.request("GET", url, headers=headers, data=payload)
if not response.ok:
    print("Error fetching user id", response.text)
else:
    USER_ID = response.json()['data']['user']['id']
    print("USER_ID=" + USER_ID)


# %%
# Fetch 7pace activities
url = f"https://geneteccentral.timehub.7pace.com/api/rest/activityTypes?api-version={SEVENPACE_API_VERSION}"
headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {SEVENPACE_API_KEY}'
}
resp = requests.request("GET", url, headers=headers, data=payload)

# Retun a name/id map of activities
activities = {}
for activity in resp.json()['data']['activityTypes']:
    activities[activity['id']] = activity['name']
print(json.dumps(activities, indent=2))


# %%
# Convert Toggl time entries to 7pace format

SevenPaceTimeEntries = []
for entry in TimeEntries:
    start = entry['start']
    duration = entry['duration']
    if (duration < 0):
        print("Ignoring entry with negative duration (pending timer)")
        continue
    notes = entry['description']
    workItemId = None
    numbers = [int(s) for s in notes.split() if s.isdigit()]
    if (numbers.__len__() > 0):
        workItemId = numbers[0]

    # Default for Internal Operations
    activityTypeId = "bc23a96d-f6c5-44fe-be60-337af432d71b"
    if ('technical debt' in notes.lower() or 'bug' in notes.lower()):
        activityTypeId = "140dc2a9-03a0-4431-9f6b-0120f2c1b82f"  # Bug
    elif ('feature' in notes.lower() or 'user story' in notes.lower() or 'pr' in notes.lower()):
        activityTypeId = "9cd0cb39-180d-4b19-9265-83f9753ff76c"  # Feature
    elif ('swattask' in notes.lower() or 'swat' in notes.lower()):
        activityTypeId = "6a79b89e-4c6d-4866-b07b-428b65f1b1d5"  # Customer issues
    elif ('professional development' in notes.lower() or 'formation' in notes.lower()):
        activityTypeId = "2a032e88-7d97-44d3-b28e-ce89b4277017"  # Professional development

    SevenPaceTimeEntries.append({
        'timeStamp': start,
        'length': duration,
        'lengthFriendly': "{:0>8}".format(str(timedelta(seconds=duration))),
        'comment': notes,
        "workItemId": workItemId,
        'userId': USER_ID,
        'activityTypeId': activityTypeId,
        "activityFriendly": activities[activityTypeId]
    })

print(json.dumps(SevenPaceTimeEntries, indent=2))


# %%
# Publish worklogs to 7pace


inputResp = input(
    f"{str(len(SevenPaceTimeEntries))} entries to add. Continue ? (y/n)")
if inputResp.lower() == 'n':
    exit

url = f"https://geneteccentral.timehub.7pace.com/api/rest/workLogs?api-version={SEVENPACE_API_VERSION}"
error = False
tfsEntries = []
devopsEntries = []
for entry in SevenPaceTimeEntries:
    if entry['workItemId'] != None and int(entry['workItemId']) > TFS_7PACE_WORK_ITEM_THRESHOLD_START:
        tfsEntries.append(entry)
    else:
        devopsEntries.append(entry)

for entry in devopsEntries:
    payload = json.dumps(entry)
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {SEVENPACE_API_KEY}'
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    print(json.dumps(response.json(), indent=2))
    if (response.status_code != 200):
        error = True

if (not error):
    print("Succeeded")

if (tfsEntries.__len__() > 0):
    print("TFS entries: ")
    print(json.dumps(tfsEntries, indent=2))
