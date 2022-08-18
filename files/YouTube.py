#!/usr/bin/python

import httplib
import httplib2
import os, sys
import requests
import pathlib
import random
import sys
import time

from apiclient.discovery import build
from apiclient.errors import HttpError
from apiclient.http import MediaFileUpload
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import argparser, run_flow

Credentials_type = input("Do you want to use default client_secret file or your own? 1 for Default and 0 for Custom:\n")

if Credentials_type == "1":
  CT = 1
elif Credentials_type == "0":
  CT = 0
else:
  sys.exit("Input Error: It must be either 1 or 0.")

if CT == 0:
  CLIENT_SECRETS_FILE = input("Enter client secret file path:\n")
  if pathlib.Path(CLIENT_SECRETS_FILE).exists():
    pass
  elif not CLIENT_SECRETS_FILE:
    print("Path empty! using default.")
    CT = 1
  else:
    print("Given path not exist! using default")
    CT = 1
else:
  pass

PATH_TO_CREDENTIALS = "/content/MCT/credentials.json"
Crendentials_dir = pathlib.PurePath(PATH_TO_CREDENTIALS).parents[0]

if pathlib.Path(Credentials_dir).exists():
  pass
else:
  !mkdir {Credentials_dir}

DCS = [
"https://www.caduceus.ml/files/client_secret.json",
"https://raw.githubusercontent.com/TheCaduceus/thecaduceus.github.io/main/files/client_secret.json"
]

if CT == 1:
  try: 
    requests.get(DCS[0])
    sn == 1
  except:
    try:
      requests.get(DCS[1])
      sn = 2
    except:
      print("Unable to download default client secret! Please provide your own client secret:")
      CLIENT_SECRETS_FILE = input()
      if pathlib.Path(CLIENT_SECRETS_FILE).exists():
        pass
      elif not CLIENT_SECRETS_FILE:
        sys.exit("Path Error: Path can't be blank!")
      else:
        sys.exit("Path Error: Given path not exists")
else:
  pass

if CT == 1 and sn == 1:
  print("Downloading Default Credentials through Source 1!")
  !wget {DCS[0]} -O {PATH_TO_CREDENTIALS}
  CLIENT_SECRETS_FILE = PATH_TO_CREDENTIALS
elif CT == 1 and sn == 2:
  print("Downloading Default Credentials through Source 2!")
  !wget {DCS[1]} -O {PATH_TO_CREDENTIALS}
  CLIENT_SECRETS_FILE = PATH_TO_CREDENTIALS
else:
  pass # In case of Custom


httplib2.RETRIES = 1

MAX_RETRIES = 10

RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError, httplib.NotConnected,
  httplib.IncompleteRead, httplib.ImproperConnectionState,
  httplib.CannotSendRequest, httplib.CannotSendHeader,
  httplib.ResponseNotReady, httplib.BadStatusLine)

RETRIABLE_STATUS_CODES = [500, 502, 503, 504]

YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

MISSING_CLIENT_SECRETS_MESSAGE = """
WARNING: Please configure OAuth 2.0

To make this function run you will need to populate the client_secrets.json file
found at:

   %s

with information from the API Console
https://console.developers.google.com/

For more information about the client_secrets.json file format, please visit:
https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
""" % os.path.abspath(os.path.join(os.path.dirname(__file__),
                                   CLIENT_SECRETS_FILE))

VALID_PRIVACY_STATUSES = ("public", "private", "unlisted")


def get_authenticated_service(args):
  flow = flow_from_clientsecrets(CLIENT_SECRETS_FILE,
    scope=YOUTUBE_UPLOAD_SCOPE,
    message=MISSING_CLIENT_SECRETS_MESSAGE)

  storage = Storage("%s-oauth2.json" % sys.argv[0])
  credentials = storage.get()

  if credentials is None or credentials.invalid:
    credentials = run_flow(flow, storage, args)

  return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
    http=credentials.authorize(httplib2.Http()))

def initialize_upload(youtube, options):
  tags = None
  if options.keywords:
    tags = options.keywords.split(",")

  body=dict(
    snippet=dict(
      title=options.title,
      description=options.description,
      tags=tags,
      categoryId=options.category
    ),
    status=dict(
      privacyStatus=options.privacyStatus
    )
  )

  # Call the API's videos.insert method to create and upload the video.
  insert_request = youtube.videos().insert(
    part=",".join(body.keys()),
    body=body,

    media_body=MediaFileUpload(options.file, chunksize=-1, resumable=True)
  )

  resumable_upload(insert_request)

def resumable_upload(insert_request):
  response = None
  error = None
  retry = 0
  while response is None:
    try:
      print "Uploading file..."
      status, response = insert_request.next_chunk()
      if response is not None:
        if 'id' in response:
          print "Video id '%s' was successfully uploaded." % response['id']
        else:
          exit("The upload failed with an unexpected response: %s" % response)
    except HttpError, e:
      if e.resp.status in RETRIABLE_STATUS_CODES:
        error = "A retriable HTTP error %d occurred:\n%s" % (e.resp.status,
                                                             e.content)
      else:
        raise
    except RETRIABLE_EXCEPTIONS, e:
      error = "A retriable error occurred: %s" % e

    if error is not None:
      print error
      retry += 1
      if retry > MAX_RETRIES:
        exit("No longer attempting to retry.")

      max_sleep = 2 ** retry
      sleep_seconds = random.random() * max_sleep
      print "Sleeping %f seconds and then retrying..." % sleep_seconds
      time.sleep(sleep_seconds)

if __name__ == '__main__':
  argparser.add_argument("--file", required=True, help="Video file to upload")
  argparser.add_argument("--title", help="Video title", default="Test Title")
  argparser.add_argument("--description", help="Video description",
    default="Test Description")
  argparser.add_argument("--category", default="22",
    help="Numeric video category. " +
      "See https://developers.google.com/youtube/v3/docs/videoCategories/list")
  argparser.add_argument("--keywords", help="Video keywords, comma separated",
    default="")
  argparser.add_argument("--privacyStatus", choices=VALID_PRIVACY_STATUSES,
    default=VALID_PRIVACY_STATUSES[0], help="Video privacy status.")
  args = argparser.parse_args()

  if not os.path.exists(args.file):
    exit("Please specify a valid file using the --file= parameter.")

  youtube = get_authenticated_service(args)
  try:
    initialize_upload(youtube, args)
  except HttpError, e:
    print "An HTTP error %d occurred:\n%s" % (e.resp.status, e.content)
