# GitHub Deployment Status

This small app creates basic inidicators about the status of a specific repo

In order to make this app work, you have to create a file named `app.config` in an `env` folder.

The file should have the following structure:
```
[SECRETS]
GITHUB_PAT = secret

[REPOSITORY]
OWNER = org_or_username
REPO_NAME = repo_name
ENVIRONMENT = env1,env2,env3
```

You can just rename and edit the [`app.config.example`](https://github.com/pedrolacerda/github-deployment-status/blob/master/app.config.exemple) file in the root of this repo.
