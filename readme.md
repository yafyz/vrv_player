# what does it do

plays VRV content through VLC or MPV

proxy support for bypassing VRV being unavailable in your country

(only used to get Policy Data, which is needed for all the requests)

probably only works for crunch

# how to use
`py vrv_player.py` or `py vrv_player.py (SERIES_ID/VRV_URL)`

to launch with mpv use `--mpv` flag, ex `py vrv_player.py --mpv`

mpv rn only works if its in path

requires `urllib3`

requires a config file named `config.json` which contains proxy info

```json
{
    "proxy": {
        "username": "",
        "password": "",
        "host": ""
    }
}
```

the proxy should be located in USA

for free decent proxy, you can use windscribe

1. install the extension
2. select USA location (ex. US central - Dallas)
3. right click on a page -> "View Debug Log"
4. ctrl+f -> "authCredentials" for proxy username and password
5. ctrl+f -> "proxy location" for proxy ips
