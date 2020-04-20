# -*- coding: utf-8 -*-

import os

import google.oauth2.credentials
import google_auth_oauthlib.flow
import googleapiclient.discovery
import requests
from flask import Flask, url_for, render_template, request, redirect, session, jsonify

from gdriveloader import GDriveFiles, GDriveIndex

# This variable specifies the name of a file that contains the OAuth 2.0
# information for this application, including its client_id and client_secret.
CLIENT_SECRETS_FILE = "client_id.json"

# This OAuth 2.0 access scope allows for full read/write access to the
# authenticated user's account and requires requests to use an SSL connection.
SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly',
          'https://www.googleapis.com/auth/drive.readonly',
          'https://www.googleapis.com/auth/drive.file']

API_SERVICE_NAME = 'drive'
API_VERSION = 'v3'

app = Flask(__name__, template_folder="templates")
# Note: A secret key is included in the sample so that it works.
# If you use this code in your application, replace this with a truly secret
# key. See https://palletsprojects.com/quickstart/#sessions.
app.secret_key = os.environ["GAPP_SECRET"]


def has_no_empty_params(rule):
    defaults = rule.defaults if rule.defaults is not None else ()
    arguments = rule.arguments if rule.arguments is not None else ()
    return len(defaults) >= len(arguments)


@app.route('/')
def index():
    return render_template("index.html")


@app.route("/search")
def search_page():
    return render_template("search.html")


@app.route("/load")
def load_page():
    return render_template("load.html")


@app.route("/reload")
def reload_page():
    return render_template("reload.html")


@app.route("/test")
def test_page():
    return render_template("test.html")


@app.route("/site-map")
def site_map():
    links = []
    for rule in app.url_map.iter_rules():
        # Filter out rules we can't navigate to in a browser
        # and rules that require parameters
        if "GET" in rule.methods and has_no_empty_params(rule):
            url = url_for(rule.endpoint, **(rule.defaults or {}))
            links.append((url, rule.endpoint))
    # links is now a list of url, endpoint tuples
    return render_template("all_links.html", links=links)


def load(fl):
    if 'credentials' not in session:
        return redirect(url_for('authorize'))

    # Load credentials from the session.
    credentials = google.oauth2.credentials.Credentials(
        **session['credentials'])

    drive = googleapiclient.discovery.build(
        API_SERVICE_NAME, API_VERSION, credentials=credentials)
    gfiles = GDriveFiles(drive, session['credentials']['client_id'], app.logger)
    gfiles.load(fl=fl)
    context = {"loaded": gfiles.index_exists}
    context.update(gfiles.get_timers_load())
    return jsonify(**context)


@app.route('/api/load')
def load_index():
    return load(False)


@app.route('/api/reload')
def reload_index():
    return load(True)


@app.route('/api/search', methods=["GET"])
def gdrive_search():
    query = request.args.get('query')
    context = {"search": query is not None}
    gindex = GDriveIndex(session['credentials']['client_id'])
    if query is not None:
        try:
            context["docs"] = gindex.find(query)
        except Exception as e:
            context["docs"] = None
        context["query"] = query
    return jsonify(**context)


@app.route('/api/test')
def test_api_request():
    if 'credentials' not in session:
        return redirect(url_for('authorize'))

    # Load credentials from the session.
    credentials = google.oauth2.credentials.Credentials(
        **session['credentials'])

    drive = googleapiclient.discovery.build(
        API_SERVICE_NAME, API_VERSION, credentials=credentials)

    files = drive.files().list(q="'me' in owners",
                               fields='nextPageToken, files(id, name, mimeType, webViewLink)').execute()

    # Save credentials back to session in case access token was refreshed.
    # ACTION ITEM: In a production app, you likely want to save these
    #              credentials in a persistent database instead.
    session['credentials'] = credentials_to_dict(credentials)

    return jsonify(**files)


@app.route('/authorize')
def authorize():
    # Create flow instance to manage the OAuth 2.0 Authorization Grant Flow steps.
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES)

    # The URI created here must exactly match one of the authorized redirect URIs
    # for the OAuth 2.0 client, which you configured in the API Console. If this
    # value doesn't match an authorized URI, you will get a 'redirect_uri_mismatch'
    # error.
    flow.redirect_uri = url_for('oauth2callback', _external=True)

    authorization_url, state = flow.authorization_url(
        # Enable offline access so that you can refresh an access token without
        # re-prompting the user for permission. Recommended for web server apps.
        access_type='offline',
        # Enable incremental authorization. Recommended as a best practice.
        include_granted_scopes='true')

    # Store the state so the callback can verify the auth server response.
    session['state'] = state

    return redirect(authorization_url)


@app.route('/oauth2callback')
def oauth2callback():
    # Specify the state when creating the flow in the callback so that it can
    # verified in the authorization server response.
    state = session['state']

    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES, state=state)
    flow.redirect_uri = url_for('oauth2callback', _external=True)

    # Use the authorization server's response to fetch the OAuth 2.0 tokens.
    authorization_response = request.url
    flow.fetch_token(authorization_response=authorization_response)

    # Store credentials in the session.
    # ACTION ITEM: In a production app, you likely want to save these
    #              credentials in a persistent database instead.
    credentials = flow.credentials
    session['credentials'] = credentials_to_dict(credentials)

    return redirect(url_for('index'))


def revoke():
    if 'credentials' not in session:
        return redirect(url_for('authorize'))

    credentials = google.oauth2.credentials.Credentials(
        **session['credentials'])

    revoke = requests.post('https://oauth2.googleapis.com/revoke',
                           params={'token': credentials.token},
                           headers={'content-type': 'application/x-www-form-urlencoded'})

    status_code = getattr(revoke, 'status_code')
    if status_code != 200:
        app.logger.debug("revoke_status_code={}".format(status_code))


@app.route('/revoke')
def revoke_page():
    revoke()
    return redirect(url_for("index"))


@app.context_processor
def utility_processor():
    def index_exists():
        if 'credentials' in session:
            client_id = session['credentials']['client_id']
            index_path = os.path.join("drive_files", client_id, "index.json")
            return os.path.exists(index_path)
        return False

    return dict(index_exists=index_exists, debug=app.debug)


def clear_credentials():
    if 'credentials' in session:
        del session['credentials']


@app.route('/clear')
def clear_credentials_page():
    clear_credentials()
    return redirect(url_for("index"))


@app.route("/logout")
def exit_page():
    revoke()
    clear_credentials()
    return redirect(url_for("index"))


def credentials_to_dict(credentials):
    return {'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes}


if __name__ == '__main__':
    # When running locally, disable OAuthlib's HTTPs verification.
    # ACTION ITEM for developers:
    #     When running in production *do not* leave this option enabled.
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

    # Specify a hostname and port that are set as a valid redirect URI
    # for your API project in the Google API Console.
    app.run('localhost', 8080, debug=True)

    print(app.url_defaults)
