from dateutil import parser
import logging
import os
import pytz

import feedparser
from github import Github
import yaml

logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')

GITHUB_TOKEN = os.environ.get("GH_ACCESS_TOKEN", None)
GITHUB_ORGANISATION = "osism"
g = Github(GITHUB_TOKEN)

utc = pytz.UTC

# Get the timestamp of the last cron run
repo = g.get_repo("osism/github-actions-overlord")
for w in repo.get_workflows():
    if w.name == "Run github actions overlord":
        for r in w.get_runs(branch="main"):
            t_last_run = utc.localize(r.created_at)
            break

logging.info(f"Last run: {t_last_run}")

with open("config.yaml") as fp:
    d = yaml.safe_load(fp)

# Checking all defined repositories
for r in d:
    handle_reactions = False

    b = "main"
    logging.info(f"Fetching feed {GITHUB_ORGANISATION}/{r}/commits/{b}.atom")
    f = feedparser.parse(f"https://github.com/{GITHUB_ORGANISATION}/{r}/commits/{b}.atom")
    for entry in f['entries']:
        t_updated = parser.parse(entry['updated'])
        logging.info(f"Last commit on {b} in {GITHUB_ORGANISATION}/{r}: {t_updated}")

        if t_updated > t_last_run:
            handle_reactions = True

        break

    if handle_reactions:
        logging.info(f"Checking {r} for reactions")

        # Check all defined reactions
        for t in d[r]:

            # Get repository of reaction
            repo = g.get_repo(f"{GITHUB_ORGANISATION}/{t}")

            # NOTE: repo.get_workflow() only works with IDs
            for w in repo.get_workflows():

                # Check if workflow should be dispatched
                if w.name in d[r][t]:
                    logging.info(f"Creating dispatch for workflow '{t}/{w.name}'")
                    w.create_dispatch(repo.get_branch("main"))
