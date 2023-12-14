This script is used to convert toggl time entries to 7pace

## Requirements

- Create the .env file starting from the .env.template file
- Toggl entries should be the result of the work item copy button
- Configurate the .env file with the correct values

## How to use

- Toggl entries should be under the form of a work item copy button
  -> [Activity type] [Work item id]: [Work item title]
  e.g. Bug 25426: Something - description
  When no activity type detected, it will be considered as a Internal operation (no need id in this case)
- Make sur to fill the .env correctly before running the script (see below section)
- Run the script
- The script will ask you if you want to delete the already there entries in 7pace for the week
- The script will then inform you how many entries will be added and ask for a continue confirmation
- Make sure to check the entries in 7pace to make sure everything is correct

## .ENV file

Duplicate the .env.template file and rename it to .env

### TOGGL_API_KEY

https://track.toggl.com/profile -> API Token

### TOGGL_WORKSPACE_ID

[https://track.toggl.com/reports/detailed/ - >https://track.toggl.com/reports/detailed/[WORKSPACE_ID]]

### TOGGL_PROJECT_ID

[https://track.toggl.com/reports/detailed/ - >Click on the project in the bottom box -> https://track.toggl.com/reports/detailed/[WORKSPACE_ID]/period/thisWeek/projects/[PROJECT_ID]]

### SEVENPACE_API_KEY

[https://dev.azure.com/GenetecCentral/Unification/_apps/hub/7pace.Timetracker.Configuration -> Create New Token]

### SEVENPACE_API_VERSION

Api version of 7pace

### LAST_WEEK

If True, will only consider work items that were updated in the last week (vs current week)

### TFS_7PACE_WORK_ITEM_THRESHOLD_START

Will be considered a TFS work item (not Azure Devops) if the work item id is greater than this number
