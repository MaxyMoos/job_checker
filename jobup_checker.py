from bs4 import BeautifulSoup
import requests

import re
import time
import random
import logging
import sys

import smtplib
from email.message import EmailMessage
from email.headerregistry import Address

from secrets import GMAIL_ADDRESS, GMAIL_PWD, EMAIL_FROM, EMAIL_TO


# The URL of job postings to check
JOBUP_URL = "https://www.jobup.ch/search/joblist.asp?cmd=showresults&mode=home&addcriterias=&categories=11&cantons=GE"
FREQ = 60 * 10  # Polling frequency, in seconds
ALL_JOBS = []

# Logging config
logging.basicConfig(format="%(asctime)s - %(message)s", datefmt="%d/%m/%Y %I:%M:%S %p")
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

random.seed()


def is_redirection(souped_page):
    script_nodes = souped_page.find_all('script', language='JavaScript')
    return len(script_nodes) > 0


def get_redirection_url(souped_page):
    redir_soup = BeautifulSoup(souped_page.find('noscript').string, 'html5lib')
    return redir_soup.a['href'] if redir_soup.a else souped_page


def process_jobs(job_postings, known_ids):
    new_jobs = []

    for job in job_postings:
        job_id = int(job.span['pid'])
        if len(ALL_JOBS) > 0 and not job_id in known_ids or len(ALL_JOBS) == 0:
            job_company = job.find('label', class_='C_PNAME').string[2:]
            job_title = job.span.div.a.string
            job_url = "https://www.jobup.ch" + job.span.div.a['href']

            # Fetch the job description
            job_details = requests.get(job_url)
            souped_details = BeautifulSoup(job_details.content, 'html5lib')

            if is_redirection(souped_details):
                job_desc = get_redirection_url(souped_details)
            elif souped_details.find('div', id='description'):
                job_desc = "\n".join(souped_details.find('div', id='description').stripped_strings)
            else:
                job_desc = "Description could not be retrieved.".format(job_url)

            log.info("{} - {}:\n{}\n**********".format(job_company,
                                                       job_title,
                                                       job_desc))
            new_jobs.append({
                             'job_id': job_id,
                             'job_company': job_company,
                             'job_title': job_title,
                             'job_desc': job_desc,
                             'job_url': job_url,
                            })
    return new_jobs


def send_email(new_jobs):
    msg = EmailMessage()
    msg['Subject'] = "{} nouvelles offre(s) sur JobUp !".format(len(new_jobs))
    msg['From'] = Address(EMAIL_FROM, GMAIL_ADDRESS)
    msg['To'] = Address(EMAIL_TO, GMAIL_ADDRESS)
    text = []
    for job in new_jobs:
        job_text = "*{} - {}*:\n\n{}\n{}\n\n".format(job['job_title'],
                                                     job['job_company'],
                                                     job['job_desc'],
                                                     job['job_url'])
        text.append(job_text)
    msg.set_content("**************\n".join(text))
    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(GMAIL_ADDRESS, GMAIL_PWD)
            server.send_message(msg)
            log.info("E-mail sent!")
    except Exception as e:
        log.error("Error: could not send email at this time:\n" + str(e))


def poll_jobs():
    """Poll JobUp for most recent jobs, parse them & send an email if need be.

    The delay is built into this function so we cannot accidentally spam jobup with requests
    with repeated calls to poll_jobs
    """
    global ALL_JOBS

    try:
        log.info("Checking job postings...")

        html_contents = requests.get(JOBUP_URL)
        souped = BeautifulSoup(html_contents.content, 'html5lib')
        id_regex = re.compile("result_posting_[1-9]{7}")
        job_postings = souped.find_all(id=id_regex)

        known_ids = [item['job_id'] for item in ALL_JOBS]

        new_jobs = process_jobs(job_postings, known_ids)
        ALL_JOBS = new_jobs + ALL_JOBS

        if len(new_jobs) > 0:
            log.info("Preparing email")
            send_email(new_jobs)

        # Wait for the appropriate time before fetching again
        delay = FREQ + random.randint(0, 10)
        log.info("Found {} new jobs. Checking again in {} minutes {} seconds".format(
            len(new_jobs),
            delay // 60,
            delay % 60)
        )
        time.sleep(delay)
    except KeyboardInterrupt:
        log.info("Execution interrupted by user. Exiting...")
        sys.exit()


if __name__ == '__main__':
    while(True):
        poll_jobs()
