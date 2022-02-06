import json
import os
import re
import codecs
from datetime import datetime
from hashlib import sha1
import hmac
import random
from urllib.parse import quote_plus as urlencode
import urllib3

with open("config.json") as f:
    conf = json.loads(f.read())

proxy_user = conf["proxy"]["username"]
proxy_pass = conf["proxy"]["password"]
proxy_url  = conf["proxy"]["host"]

VRV_CORE_INDEX = "https://api.vrv.co/core/index"

class VRV_Data:
    policy: str
    signature: str
    key_pair_id: str

    def __init__(self, policy, signature, key_pair_id) -> None:
        self.policy = policy
        self.signature = signature
        self.key_pair_id = key_pair_id

class OAuth:
    @staticmethod
    def make_base_string(http_method: str, url: str, oauth_key: str, oauth_nonce: str, oauth_sig_method: str, oauth_timestamp: str) -> str:
        return "%s&%s&%s" % (http_method, urlencode(url), urlencode("oauth_consumer_key=%s&oauth_nonce=%s&oauth_signature_method=%s&oauth_timestamp=%s&oauth_version=1.0" % (oauth_key, oauth_nonce, oauth_sig_method, oauth_timestamp)))

    @staticmethod
    def make_sig(oauth_key, oauth_secret, oauth_nonce, oauth_timestamp, http_method, http_url) -> str:
        key = bytes("%s&" % oauth_secret, "utf8")
        raw = bytes(OAuth.make_base_string(http_method, http_url, oauth_key, oauth_nonce, "HMAC-SHA1", oauth_timestamp), "utf8")
        hashed = hmac.new(key, raw, sha1)
        return str(codecs.encode(hashed.digest(), "base64").strip(), "utf8")

    @staticmethod
    def gen_nonce() -> str:
        return str(codecs.encode(random.randbytes(24), "base64").strip(), "utf8")

    @staticmethod
    def make_oauth_header(oauth_key, oauth_secret, http_method, http_url) -> str:
        timestamp = int(datetime.now().timestamp())
        nonce = OAuth.gen_nonce()
        sig = urlencode(OAuth.make_sig(oauth_key, oauth_secret, nonce, timestamp, http_method, http_url))
        return "OAuth oauth_consumer_key=\"%s\", oauth_nonce=\"%s\", oauth_signature=\"%s\", oauth_signature_method=\"HMAC-SHA1\", oauth_timestamp=\"%d\", oauth_version=\"1.0\"" % (oauth_key, nonce, sig, timestamp)

def get_VRV_data(proxman: urllib3.ProxyManager, oauth_header: str) -> tuple[bool, dict[str, str]]:
    policies = {}

    res: urllib3.HTTPResponse = proxman.request(url=VRV_CORE_INDEX, method="GET", headers={"authorization": oauth_header})
    data = json.loads(res.data)
    res.close()

    if res.status != 200:
        print(data)
        return (False, None)
    else:
        for policy in data["signing_policies"]:
            policies[policy["name"]] = policy["value"]

        return (True, policies)

def get_vrv_data_for_url(url) -> str:
    proxman = urllib3.proxy_from_url("https://%s:%s@%s" % (proxy_user, proxy_pass, proxy_url),
                                proxy_headers={"Proxy-Authorization": "Basic %s" % str(codecs.encode(bytes("%s:%s" % (proxy_user, proxy_pass), "utf8"), "base64").strip(), "utf8")})

    res: urllib3.HTTPResponse = proxman.request("GET", url)
    data = str(res.data)
    res.close()

    jsdata = json.loads(re.findall("window.__APP_CONFIG__\ =\ (.*?);", data)[0])
    oauth_header = OAuth.make_oauth_header(jsdata["cxApiParams"]["oAuthKey"], jsdata["cxApiParams"]["oAuthSecret"], "GET", VRV_CORE_INDEX)

    success, vrv_data = get_VRV_data(proxman, oauth_header)
    if not success:
        return get_vrv_data_for_url(url)

    os.system('cls' if os.name=='nt' else 'clear')
    return VRV_Data(vrv_data["Policy"], vrv_data["Signature"], vrv_data["Key-Pair-Id"])
