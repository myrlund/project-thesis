# encoding: utf-8

from __future__ import unicode_literals
import requests
import json
from datetime import date, timedelta
from requests_oauthlib import OAuth1
from urlparse import parse_qs

REQUEST_TOKEN_URL = "https://api.twitter.com/oauth/request_token"
AUTHORIZE_URL = "https://api.twitter.com/oauth/authorize?oauth_token="
ACCESS_TOKEN_URL = "https://api.twitter.com/oauth/access_token"

CONSUMER_KEY = "bERRpxqRNywXn2goGyDLA"
CONSUMER_SECRET = "EesTZzoqKNXerlntfkmXNqnW5BKBvRjJIeoBtqOe2c"

OAUTH_TOKEN = "14317755-wlQ7wAY2S5oGnHpVnpTuPEjhbZ73OBPUrDWCWyiC5"
OAUTH_TOKEN_SECRET = "2mVNpK0PC45sKOK290oDBlYaDtzBMkeZR2qhnOGynQ"

def setup_oauth(config):
    """Authorize your app via identifier."""
    # Request token
    oauth = OAuth1(config['CONSUMER_KEY'], client_secret=config['CONSUMER_SECRET'])
    r = requests.post(url=REQUEST_TOKEN_URL, auth=oauth)
    credentials = parse_qs(r.content)

    resource_owner_key = credentials.get('oauth_token')[0]
    resource_owner_secret = credentials.get('oauth_token_secret')[0]

    # Authorize
    authorize_url = AUTHORIZE_URL + resource_owner_key
    print 'Please go here and authorize: ' + authorize_url

    verifier = raw_input('Please input the verifier: ')
    oauth = OAuth1(config['CONSUMER_KEY'],
                   client_secret=config['CONSUMER_SECRET'],
                   resource_owner_key=resource_owner_key,
                   resource_owner_secret=resource_owner_secret,
                   verifier=verifier)

    # Finally, Obtain the Access Token
    r = requests.post(url=ACCESS_TOKEN_URL, auth=oauth)
    credentials = parse_qs(r.content)
    token = credentials.get('oauth_token')[0]
    secret = credentials.get('oauth_token_secret')[0]

    return token, secret


def get_oauth(config):
    oauth = OAuth1(config['CONSUMER_KEY'],
                client_secret=config['CONSUMER_SECRET'],
                resource_owner_key=config['OAUTH_TOKEN'],
                resource_owner_secret=config['OAUTH_TOKEN_SECRET'])
    return oauth

class Tweet:
    FIELDS = ('id', 'text', 'lang')

    def __init__(self, data):
        for field in self.FIELDS:
            setattr(self, field, data[field])
        self.user = data['user']['screen_name']
        self.data = data
        self.sentiment = None
        self.filtered_text = None

    def __unicode__(self):
        s = u""
        if self.sentiment:
            s = (u"<%s> " % self.sentiment).ljust(11)
        return s + u"@%s: «%s»" % (self.user, self.text)

class Twitter:
    RESOURCE_URL_TEMPLATE = "https://api.twitter.com/1.1/%s.json"

    def __init__(self, config):
        self.oauth = get_oauth(config)
    
    def api_resource(self, resource):
        return Twitter.RESOURCE_URL_TEMPLATE % resource

    def api_request(self, resource, payload):
        url = self.api_resource(resource)
        r = requests.get(url=url, auth=self.oauth, params=payload)
        return r.json()

    def search(self, term, result_type='popular', count=10):
        payload = {
            'q': term,
            'result_type': result_type,
            'count': count,
            'lang': 'en',
        }
        data = self.api_request("search/tweets", payload)
        return data["statuses"]

class NotEnoughTweetsError(ValueError):
    pass
