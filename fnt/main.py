# -*- coding: latin-1 -*-
# Author: elnerude

from bs4 import BeautifulSoup
from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.base import TorrentProvider
from couchpotato.core.media.movie.providers.base import MovieProvider
import traceback
import re
import requests
import urllib2
import json
import sys
import urllib

log = CPLog(__name__)

class fnt(TorrentProvider, MovieProvider):

    urls = {
        'base_url': 'https://fnt.nu',
        'search': 'https://www.fnt.nu/torrents/recherche/?%s',
        'login': 'https://fnt.nu/account-login.php',
        'movie_profile' : 'https://fnt.nu/FnT/fiche_film/',
    }

    search_params = {
        "afficher" : 1, "c100": 1, "c101": 1, "c127": 1, "c105": 1, "c106": 1, "c107": 1, 
        "c108": 1, "c130": 1, "c115": 1, "c128": 1, "c131": 1, "c140": 1, "c151": 1, 
        "visible": 1, "freeleech": 0, "nuke": 0, "3D": 0, "langue": 0,
        "sort": "size", "order": "desc"
    }

    #"anime-mhd" : "140"
    #"anime-hd"  : "151"
    #"dvdrip"    : "100"
    #"bdrip"     : "101"
    #"vostfr"    : "127"
    #"CINE - DVDR-PAL" : "102"
    #"CINE - DVDR-NTSC" : "103"
    #"CINE - DVDR-FULL" : "104"
    #"cine mhd 720"  : "105"
    #"cine mhd 1080" : "106" 
    #"cine hdrip 720" : "107"
    #"cine hdrip 1080" : "108"
    #"bluray" : "130"
    #"cine spectacle" : "115"
    #"cine documentaire" : "128"
    #"cine documentaire hd" : "131"
    #"CINE - BANDE-SON" : "147"

    http_time_between_calls = 1 #seconds
    cat_backup_id = None

    def getLoginParams(self):
        log.debug('Getting login params for fnt')
        return {
            'username': self.conf('username'),
            'password': self.conf('password'),
            'submit' : 'Se loguer'
        }

    def loginSuccess(self, output):
        log.debug('Checking login success for FNT: %s' % ('True' if not ('pseudo ou mot de passe non valide' in output.lower()) else 'False'))
        return not 'pseudo ou mot de passe non valide' in output.lower()

    #def login(self):

        #if any(requests.utils.dict_from_cookiejar(self.session.cookies).values()):
        #    return True

        #response = self.urlopen(self.urls['login'], data=self.getLoginParams())
        #if not response:
        #    log.error("Unable to connect to provider")
        #    return False

        #if not re.search('Pseudo ou mot de passe non valide', response):
        #    return True
        #else:
        #    logger.log(u"Invalid username or password. Check your settings", logger.WARNING)
        #    return False

        #return True

    def _searchOnTitle(self, title, movie, quality, results):
        # check for auth
        #if not self.lgin():
        #    return

        self.search_params['recherche'] = title

        search_url = self.urls['search'] % urllib.urlencode(self.search_params)
        #log.debug("search url '{0}'".format(search_url))

        data = self.getHTMLData(search_url, cache_timeout = 30)
        if not data:
            log.error("Failed fetching data. Traceback: %s" % traceback.format_exc())
            return

        #log.debug("getHTMLData %s" % data)

        try:
            html = BeautifulSoup(data, features=["html", "permissive"])
            result_table = html.find('table', {'id': 'tablealign3bis'})

            if not result_table:
                log.debug("Data returned from provider does not contain any torrents")
                return

            if result_table:
                rows = result_table.findAll("tr", {"class" : "ligntorrent"})

                for row in rows:
                    link = row.findAll('td')[1].find("a", href=re.compile("fiche_film"))

                    if link:
                        try:
                            result_title = link.text.encode("utf-8")
                            idt = link['href'].replace(self.urls['movie_profile'],'').replace('/','')
                            detail_url = link['href']
                            download_url = self.urls['base_url'] + "/" + row.find("a", href=re.compile(r"download\.php"))['href']
                        except (AttributeError, TypeError):
                            return

                        try:
                            detailTorrent = link['mtcontent']
                            seeders = int(detailTorrent.split("<font color='#00b72e'>")[1].split("</font>")[0])
                            leechers = int(detailTorrent.split("<font color='red'>")[1].split("</font>")[0])
                            size = self.parseSize(detailTorrent.split("<font color='#000'>Taille : </b>")[1].split("<br />")[0])
                            #FIXME
                            #size = -1
                        except Exception:
                            log.debug("Unable to parse torrent id & seeders & leechers. Traceback: %s " % traceback.format_exc())
                            return

                        if not all([result_title, download_url]):
                            return

                        #Filter unseeded torrent
                        #if seeders < self.minseed or leechers < self.minleech:
                        #    if mode != 'RSS':
                        #        log.debug("Discarding torrent because it doesn't meet the minimum seeders or leechers: {0} (S:{1} L:{2})".format(result_
                        #            , seeders, leechers))
                        #    continue

                        item = title, download_url, size, seeders, leechers

                        result = {
                            'id': idt,
                            'name' : result_title,
                            'url' : download_url,
                            'detail_url' : detail_url,
                            'size' : size,
                            'seeders' : seeders,
                            'leechers' : leechers
                            }

                        log.debug("Found result: %s result %s" % (result_title, result))



                        results.append(result)

        except Exception, e:
            log.error("Failed parsing provider. Traceback: %s" % traceback.format_exc())

