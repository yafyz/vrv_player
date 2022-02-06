import json
import os
import re
import sys
import urllib.request
import urllib.error
import tempfile
import subprocess

from vrv import VRV_Data, get_vrv_data_for_url

# constants

SEASONS_URI = "https://api.vrv.co/cms/v2/US/M2/-/seasons"
EPISODES_URI = "https://api.vrv.co/cms/v2/US/M2/-/episodes"
VLC_PATH = "C:\\Program Files (x86)\\VideoLAN\\VLC\\" if os.name == "nt" else "" # expect that on non windows machines, vlc is gonna be in path

USE_MPV = False
for v in sys.argv:
    if v == "--mpv":
        USE_MPV = True
        sys.argv.remove(v)
        print("Using mpv")
        break

# top functions

def do_request(req) -> urllib.error.HTTPError:
    try:
        return urllib.request.urlopen(req)
    except urllib.error.HTTPError as res:
        print(res.read())
        raise res

# Crunch classes

class StreamInfo:
    url: str

    def __init__(self, stream_info: dict) -> None:
        self.__dict__.update(stream_info)

class SubtitleInfo:
    locale: str
    url: str

    def __init__(self, stream_info: dict) -> None:
        self.__dict__.update(stream_info)

class PlaybackInfo:
    audio_locale: str
    subtitles: dict[str, SubtitleInfo]
    streams: dict[str, StreamInfo]

    def __init__(self, playback_data: dict) -> None:
        self.subtitles = dict[str, SubtitleInfo]()
        self.streams = dict[str, StreamInfo]()
        self.audio_locale = playback_data["audio_locale"]

        for k,v in playback_data["streams"]["download_hls"].items():
            self.streams[k] = StreamInfo(v)

        for k,v in playback_data["subtitles"].items():
            self.subtitles[k] = SubtitleInfo(v)

    def get_default_stream(self) -> StreamInfo:
        try:
            return self.streams[list(self.streams.keys())[0]]#self.streams[""]
        except Exception as e:
            raise e
    def try_get_subtitles(self, lang) -> str:
        if lang in self.subtitles:
            return self.subtitles[lang].url
        return None

# VRV classes

class Episode:
    id: str
    title: str
    playback: str

    playback_info: PlaybackInfo

    def __init__(self, episode_data) -> None:
        self.__dict__.update(episode_data)

    def load_playback_info(self) -> None:
        with do_request(self.playback) as res:
            data = json.loads(res.read())
            self.playback_info = PlaybackInfo(data)

class Season:
    id: str
    title: str

    episodes: list[Episode]

    def __init__(self, season_data) -> None:
        self.episodes = list[Episode]()
        self.__dict__.update(season_data)

    def load_episodes(self, vrv: VRV_Data):
        self.episodes.clear()
        with do_request("%s?season_id=%s&Policy=%s&Signature=%s&Key-Pair-Id=%s" % (EPISODES_URI, self.id, vrv.policy, vrv.signature, vrv.key_pair_id)) as res:
            data = json.loads(res.read())
            for episode in data["items"]:
                self.episodes.append(Episode(episode))

class Series:
    id: str
    seasons: list[Season]

    def __init__(self, series_id: str) -> None:
        self.seasons = list[Season]()
        self.id = series_id

    def load_seasons(self, vrv: VRV_Data) -> None:
        self.seasons.clear()
        with do_request("%s?series_id=%s&Policy=%s&Signature=%s&Key-Pair-Id=%s" % (SEASONS_URI, series_id, vrv.policy, vrv.signature, vrv.key_pair_id)) as res:
            data = json.loads(res.read())
            for season in data["items"]:
                self.seasons.append(Season(season))

# functions
#--no-qt-name-in-title --no-video-title-show
def open_vlc(file: str, sub: str=None, title: str=None, autoexit: bool=True) -> None:
    args = [VLC_PATH+"vlc", file]
    if title:
        args.append("--meta-title")
        args.append(title)
    if sub:
        args.append("--sub-file")
        args.append(sub)
    if autoexit:
        args.append("--play-and-exit")
    subprocess.call(args, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

def open_mpv(file: str, sub: str=None, title: str=None) -> None:
    args = ["mpv", file]
    if title:
        args.append("--force-media-title=%s" % title.replace("\"", "\\\""))
    if sub:
        args.append("--sub-file=%s" % sub.replace("\"", "\\\""))
    subprocess.call(args, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

def get_bytes(url: str) -> bytes:
    with do_request(url) as res:
        return res.read()

def play_stream(stream_url: str, sub_url: str = None, title: str=None) -> None:
    if USE_MPV:
        open_mpv(stream_url, title=title, sub=sub_url)
    else:
        f = None
        if sub_url:
            sub = get_bytes(sub_url)
            f = tempfile.NamedTemporaryFile("wb", delete=False)
            f.write(sub)
            f.close()
            try:
                open_vlc(stream_url, f.name, title)
            finally:
                os.remove(f.name)
        else:
            open_vlc(stream_url, title=title)

# code

if len(sys.argv) < 2:
    series_id = input("Series ID/VRV Url: ")
else:
    series_id = sys.argv[1]

if len(matches := re.findall("vrv\.co\/series\/([^\/]*)", series_id)) > 0:
    series_id = matches[0]

sub_lang = "en-US"

print("Getting VRV policy data, this might take a while...")
vrv = get_vrv_data_for_url("https://vrv.co/watch/%s/" % series_id)
series = Series(series_id)
series.load_seasons(vrv)

print("(%s) Contains %d season(s)" % (series_id, len(series.seasons)))

for season in series.seasons:
    print("    %s (%s) \"%s\"" % (str(series.seasons.index(season)).rjust(len(str(len(series.seasons))), "0"), season.id, season.title))
    season.load_episodes(vrv)
    for episode in season.episodes:
        print("        %s (%s) \"%s\"" % (str(season.episodes.index(episode)).rjust(len(str(len(season.episodes))), "0"), episode.id, episode.title))

while True:
    if (sub_opt := input("\nSubtitle language (currently: %s): " % sub_lang).strip()) != "":
        sub_lang = sub_opt
        print("Subtitle language set to: %s" % sub_lang)

    try:
        season_idx = int(input("Season index: "))
        season = series.seasons[season_idx]
        while True:
            episode_index = int(input("Episode index: "))
            episode = season.episodes[episode_index]
            if not "playback_info" in episode.__dict__:
                episode.load_playback_info()
            pbi = episode.playback_info
            play_stream(pbi.get_default_stream().url, pbi.try_get_subtitles(sub_lang), "%s - %d. %s" % (season.title, episode_index, episode.title))
    except Exception as e:
#        raise e
        pass
