import asyncio
import aiohttp
import aiofiles
import re
import os
import time
import json
import subprocess
import tempfile
import requests
import random
import urllib.parse
import sys
import zipfile
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# ========= НАСТРОЙКИ =========
SOURCES_FILE = "sources.txt"
OUTPUT_FILE = "url.txt"
CLEAN_FILE = "url_clean.txt"
FILTERED_FILE = "url_filtered.txt"
NAMED_FILE = "url_named.txt"
WORK_FILE = "url_work.txt"

XRAY_MAX_WORKERS = 20  
XRAY_TEST_URL = "https://www.gstatic.com/generate_204"
XRAY_TIMEOUT = 5       

# ========= РЕГУЛЯРКИ =========
VLESS_REGEX = re.compile(r"vless://[^\s]+", re.IGNORECASE)
UUID_REGEX = re.compile(r"[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}")

# ========= ПОЛНЫЙ СЛОВАРЬ ВСЕХ СТРАН МИРА =========
ALL_COUNTRIES = {
    'AD': 'Andorra', 'AE': 'United Arab Emirates', 'AF': 'Afghanistan', 'AG': 'Antigua and Barbuda', 
    'AI': 'Anguilla', 'AL': 'Albania', 'AM': 'Armenia', 'AO': 'Angola', 'AQ': 'Antarctica', 
    'AR': 'Argentina', 'AS': 'American Samoa', 'AT': 'Austria', 'AU': 'Australia', 'AW': 'Aruba', 
    'AX': 'Åland Islands', 'AZ': 'Azerbaijan', 'BA': 'Bosnia and Herzegovina', 'BB': 'Barbados', 
    'BD': 'Bangladesh', 'BE': 'Belgium', 'BF': 'Burkina Faso', 'BG': 'Bulgaria', 'BH': 'Bahrain', 
    'BI': 'Burundi', 'BJ': 'Benin', 'BL': 'Saint Barthélemy', 'BM': 'Bermuda', 'BN': 'Brunei', 
    'BO': 'Bolivia', 'BQ': 'Bonaire, Sint Eustatius and Saba', 'BR': 'Brazil', 'BS': 'Bahamas', 
    'BT': 'Bhutan', 'BV': 'Bouvet Island', 'BW': 'Botswana', 'BY': 'Belarus', 'BZ': 'Belize', 
    'CA': 'Canada', 'CC': 'Cocos (Keeling) Islands', 'CD': 'DR Congo', 'CF': 'Central African Republic', 
    'CG': 'Congo', 'CH': 'Switzerland', 'CI': 'Côte d\'Ivoire', 'CK': 'Cook Islands', 'CL': 'Chile', 
    'CM': 'Cameroon', 'CN': 'China', 'CO': 'Colombia', 'CR': 'Costa Rica', 'CU': 'Cuba', 'CV': 'Cabo Verde', 
    'CW': 'Curaçao', 'CX': 'Christmas Island', 'CY': 'Cyprus', 'CZ': 'Czechia', 'DE': 'Germany', 
    'DJ': 'Djibouti', 'DK': 'Denmark', 'DM': 'Dominica', 'DO': 'Dominican Republic', 'DZ': 'Algeria', 
    'EC': 'Ecuador', 'EE': 'Estonia', 'EG': 'Egypt', 'EH': 'Western Sahara', 'ER': 'Eritrea', 'ES': 'Spain', 
    'ET': 'Ethiopia', 'FI': 'Finland', 'FJ': 'Fiji', 'FK': 'Falkland Islands', 'FM': 'Micronesia', 
    'FO': 'Faroe Islands', 'FR': 'France', 'GA': 'Gabon', 'GB': 'United Kingdom', 'GD': 'Grenada', 
    'GE': 'Georgia', 'GF': 'French Guiana', 'GG': 'Guernsey', 'GH': 'Ghana', 'GI': 'Gibraltar', 
    'GL': 'Greenland', 'GM': 'Gambia', 'GN': 'Guinea', 'GP': 'Guadeloupe', 'GQ': 'Equatorial Guinea', 
    'GR': 'Greece', 'GS': 'South Georgia', 'GT': 'Guatemala', 'GU': 'Guam', 'GW': 'Guinea-Bissau', 
    'GY': 'Guyana', 'HK': 'Hong Kong', 'HM': 'Heard Island and McDonald Islands', 'HN': 'Honduras', 
    'HR': 'Croatia', 'HT': 'Haiti', 'HU': 'Hungary', 'ID': 'Indonesia', 'IE': 'Ireland', 'IL': 'Israel', 
    'IM': 'Isle of Man', 'IN': 'India', 'IO': 'British Indian Ocean Territory', 'IQ': 'Iraq', 
    'IR': 'Iran', 'IS': 'Iceland', 'IT': 'Italy', 'JE': 'Jersey', 'JM': 'Jamaica', 'JO': 'Jordan', 
    'JP': 'Japan', 'KE': 'Kenya', 'KG': 'Kyrgyzstan', 'KH': 'Cambodia', 'KI': 'Kiribati', 'KM': 'Comoros', 
    'KN': 'Saint Kitts and Nevis', 'KP': 'North Korea', 'KR': 'South Korea', 'KW': 'Kuwait', 'KY': 'Cayman Islands', 
    'KZ': 'Kazakhstan', 'LA': 'Laos', 'LB': 'Lebanon', 'LC': 'Saint Lucia', 'LI': 'Liechtenstein', 
    'LK': 'Sri Lanka', 'LR': 'Liberia', 'LS': 'Lesotho', 'LT': 'Lithuania', 'LU': 'Luxembourg', 
    'LV': 'Latvia', 'LY': 'Libya', 'MA': 'Morocco', 'MC': 'Monaco', 'MD': 'Moldova', 'ME': 'Montenegro', 
    'MF': 'Saint Martin', 'MG': 'Madagascar', 'MH': 'Marshall Islands', 'MK': 'North Macedonia', 
    'ML': 'Mali', 'MM': 'Myanmar', 'MN': 'Mongolia', 'MO': 'Macao', 'MP': 'Northern Mariana Islands', 
    'MQ': 'Martinique', 'MR': 'Mauritania', 'MS': 'Montserrat', 'MT': 'Malta', 'MU': 'Mauritius', 
    'MV': 'Maldives', 'MW': 'Malawi', 'MX': 'Mexico', 'MY': 'Malaysia', 'MZ': 'Mozambique', 'NA': 'Namibia', 
    'NC': 'New Caledonia', 'NE': 'Niger', 'NF': 'Norfolk Island', 'NG': 'Nigeria', 'NI': 'Nicaragua', 
    'NL': 'Netherlands', 'NO': 'Norway', 'NP': 'Nepal', 'NR': 'Nauru', 'NU': 'Niue', 'NZ': 'New Zealand', 
    'OM': 'Oman', 'PA': 'Panama', 'PE': 'Peru', 'PF': 'French Polynesia', 'PG': 'Papua New Guinea', 
    'PH': 'Philippines', 'PK': 'Pakistan', 'PL': 'Poland', 'PM': 'Saint Pierre and Miquelon', 'PN': 'Pitcairn', 
    'PR': 'Puerto Rico', 'PS': 'Palestine', 'PT': 'Portugal', 'PW': 'Palau', 'PY': 'Paraguay', 'QA': 'Qatar', 
    'RE': 'Réunion', 'RO': 'Romania', 'RS': 'Serbia', 'RU': 'Russia', 'RW': 'Rwanda', 'SA': 'Saudi Arabia', 
    'SB': 'Solomon Islands', 'SC': 'Seychelles', 'SD': 'Sudan', 'SE': 'Sweden', 'SG': 'Singapore', 
    'SH': 'Saint Helena', 'SI': 'Slovenia', 'SJ': 'Svalbard and Jan Mayen', 'SK': 'Slovakia', 'SL': 'Sierra Leone', 
    'SM': 'San Marino', 'SN': 'Senegal', 'SO': 'Somalia', 'SR': 'Suriname', 'SS': 'South Sudan', 'ST': 'Sao Tome and Principe', 
    'SV': 'El Salvador', 'SX': 'Sint Maarten', 'SY': 'Syria', 'SZ': 'Eswatini', 'TC': 'Turks and Caicos Islands', 
    'TD': 'Chad', 'TF': 'French Southern Territories', 'TG': 'Togo', 'TH': 'Thailand', 'TJ': 'Tajikistan', 
    'TK': 'Tokelau', 'TL': 'Timor-Leste', 'TM': 'Turkmenistan', 'TN': 'Tunisia', 'TO': 'Tonga', 'TR': 'Turkey', 
    'TT': 'Trinidad and Tobago', 'TV': 'Tuvalu', 'TW': 'Taiwan', 'TZ': 'Tanzania', 'UA': 'Ukraine', 
    'UG': 'Uganda', 'UM': 'United States Minor Outlying Islands', 'US': 'United States', 'UY': 'Uruguay', 
    'UZ': 'Uzbekistan', 'VA': 'Vatican City', 'VC': 'Saint Vincent and the Grenadines', 'VE': 'Venezuela', 
    'VG': 'British Virgin Islands', 'VI': 'US Virgin Islands', 'VN': 'Vietnam', 'VU': 'Vanuatu', 'WF': 'Wallis and Futuna', 
    'WS': 'Samoa', 'YE': 'Yemen', 'YT': 'Mayotte', 'ZA': 'South Africa', 'ZM': 'Zambia', 'ZW': 'Zimbabwe'
}

# ========= ОГРОМНЫЙ СПИСОК ДОМЕНОВ =========
DOMAIN_NAMES = {
    'x5.ru': 'Пятёрочка', '5ka.ru': 'Пятёрочка', '5ka-cdn.ru': 'Пятёрочка', '5ka.static.ru': 'Пятёрочка',
    'ads.x5.ru': 'Пятёрочка', 'perekrestok.ru': 'Перекрёсток', 'vprok.ru': 'Перекрёсток', 'dixy.ru': 'Дикси',
    'fasssst.ru': 'Fasssst', 'rontgen.fasssst.ru': 'Fasssst', 'res.fasssst.ru': 'Fasssst', 'yt.fasssst.ru': 'Fasssst',
    'fast.strelkavpn.ru': 'StrelkaVPN', 'strelkavpn.ru': 'StrelkaVPN', 'maviks.ru': 'Maviks', 'ru.maviks.ru': 'Maviks',
    'a.ru.maviks.ru': 'Maviks', 'tree-top.cc': 'TreeTop', 'a.ru.tree-top.cc': 'TreeTop', 'connect-iskra.ru': 'Iskra',
    '212-wl.connect-iskra.ru': 'Iskra', 'vk.com': 'VK', 'vk.ru': 'VK', 'vkontakte.ru': 'VK', 'userapi.com': 'VK',
    'cdn.vk.com': 'VK', 'cdn.vk.ru': 'VK', 'id.vk.com': 'VK', 'id.vk.ru': 'VK', 'login.vk.com': 'VK',
    'login.vk.ru': 'VK', 'api.vk.com': 'VK', 'api.vk.ru': 'VK', 'im.vk.com': 'VK', 'm.vk.com': 'VK',
    'm.vk.ru': 'VK', 'sun6-22.userapi.com': 'VK', 'sun6-21.userapi.com': 'VK', 'sun6-20.userapi.com': 'VK',
    'sun9-38.userapi.com': 'VK', 'sun9-101.userapi.com': 'VK', 'pptest.userapi.com': 'VK', 'vk-portal.net': 'VK',
    'stats.vk-portal.net': 'VK', 'akashi.vk-portal.net': 'VK', 'vkvideo.ru': 'VK Видео', 'm.vkvideo.ru': 'VK Видео',
    'queuev4.vk.com': 'VK', 'eh.vk.com': 'VK', 'cloud.vk.com': 'VK', 'cloud.vk.ru': 'VK', 'admin.cs7777.vk.ru': 'VK',
    'admin.tau.vk.ru': 'VK', 'analytics.vk.ru': 'VK', 'api.cs7777.vk.ru': 'VK', 'api.tau.vk.ru': 'VK',
    'away.cs7777.vk.ru': 'VK', 'away.tau.vk.ru': 'VK', 'business.vk.ru': 'VK', 'connect.cs7777.vk.ru': 'VK',
    'cs7777.vk.ru': 'VK', 'dev.cs7777.vk.ru': 'VK', 'dev.tau.vk.ru': 'VK', 'expert.vk.ru': 'VK',
    'id.cs7777.vk.ru': 'VK', 'id.tau.vk.ru': 'VK', 'login.cs7777.vk.ru': 'VK', 'login.tau.vk.ru': 'VK',
    'm.cs7777.vk.ru': 'VK', 'm.tau.vk.ru': 'VK', 'm.vkvideo.cs7777.vk.ru': 'VK Видео', 'me.cs7777.vk.ru': 'VK',
    'ms.cs7777.vk.ru': 'VK', 'music.vk.ru': 'VK Музыка', 'oauth.cs7777.vk.ru': 'VK', 'oauth.tau.vk.ru': 'VK',
    'oauth2.cs7777.vk.ru': 'VK', 'ord.vk.ru': 'VK', 'push.vk.ru': 'VK', 'r.vk.ru': 'VK', 'target.vk.ru': 'VK',
    'tech.vk.ru': 'VK', 'ui.cs7777.vk.ru': 'VK', 'ui.tau.vk.ru': 'VK', 'vkvideo.cs7777.vk.ru': 'VK Видео',
    'speedload.ru': 'Speedload', 'api.speedload.ru': 'Speedload', 'chat.speedload.ru': 'Speedload',
    'serverstats.ru': 'ServerStats', 'cdnfive.serverstats.ru': 'ServerStats', 'cdncloudtwo.serverstats.ru': 'ServerStats',
    'furypay.ru': 'FuryPay', 'api.furypay.ru': 'FuryPay', 'jojack.ru': 'JoJack', 'spb.jojack.ru': 'JoJack',
    'at.jojack.ru': 'JoJack', 'tcp-reset-club.net': 'TCP Reset', 'est01-ss01.tcp-reset-club.net': 'TCP Reset',
    'nl01-ss01.tcp-reset-club.net': 'TCP Reset', 'ru01-blh01.tcp-reset-club.net': 'TCP Reset', 'gov.ru': 'Госуслуги',
    'kremlin.ru': 'Кремль', 'government.ru': 'Правительство', 'duma.gov.ru': 'Госдума', 'genproc.gov.ru': 'Генпрокуратура',
    'epp.genproc.gov.ru': 'Генпрокуратура', 'cikrf.ru': 'ЦИК', 'izbirkom.ru': 'Избирком', 'gosuslugi.ru': 'Госуслуги',
    'sfd.gosuslugi.ru': 'Госуслуги', 'esia.gosuslugi.ru': 'Госуслуги', 'bot.gosuslugi.ru': 'Госуслуги',
    'contract.gosuslugi.ru': 'Госуслуги', 'novorossiya.gosuslugi.ru': 'Госуслуги', 'pos.gosuslugi.ru': 'Госуслуги',
    'lk.gosuslugi.ru': 'Госуслуги', 'map.gosuslugi.ru': 'Госуслуги', 'partners.gosuslugi.ru': 'Госуслуги',
    'gosweb.gosuslugi.ru': 'Госуслуги', 'voter.gosuslugi.ru': 'Госуслуги', 'gu-st.ru': 'Госуслуги', 'nalog.ru': 'ФНС',
    'pfr.gov.ru': 'ПФР', 'digital.gov.ru': 'Минцифры', 'adm.digital.gov.ru': 'Минцифры', 'xn--80ajghhoc2aj1c8b.xn--p1ai': 'Минцифры',
    'a.res-nsdi.ru': 'NSDI', 'b.res-nsdi.ru': 'NSDI', 'a.auth-nsdi.ru': 'NSDI', 'b.auth-nsdi.ru': 'NSDI',
    'ok.ru': 'Одноклассники', 'odnoklassniki.ru': 'Одноклассники', 'cdn.ok.ru': 'Одноклассники', 'st.okcdn.ru': 'Одноклассники',
    'st.ok.ru': 'Одноклассники', 'apiok.ru': 'Одноклассники', 'jira.apiok.ru': 'Одноклассники', 'api.ok.ru': 'Одноклассники',
    'm.ok.ru': 'Одноклассники', 'live.ok.ru': 'Одноклассники', 'multitest.ok.ru': 'Одноклассники', 'dating.ok.ru': 'Одноклассники',
    'tamtam.ok.ru': 'Одноклассники', '742231.ms.ok.ru': 'Одноклассники', 'ozon.ru': 'Ozon', 'www.ozon.ru': 'Ozon',
    'seller.ozon.ru': 'Ozon', 'bank.ozon.ru': 'Ozon', 'pay.ozon.ru': 'Ozon', 'securepay.ozon.ru': 'Ozon',
    'adv.ozon.ru': 'Ozon', 'invest.ozon.ru': 'Ozon', 'ord.ozon.ru': 'Ozon', 'autodiscover.ord.ozon.ru': 'Ozon',
    'st.ozone.ru': 'Ozon', 'ir.ozone.ru': 'Ozon', 'vt-1.ozone.ru': 'Ozon', 'ir-2.ozone.ru': 'Ozon',
    'xapi.ozon.ru': 'Ozon', 'owa.ozon.ru': 'Ozon', 'learning.ozon.ru': 'Ozon', 'mapi.learning.ozon.ru': 'Ozon',
    'ws.seller.ozon.ru': 'Ozon', 'wildberries.ru': 'Wildberries', 'wb.ru': 'Wildberries', 'static.wb.ru': 'Wildberries',
    'seller.wildberries.ru': 'Wildberries', 'banners.wildberries.ru': 'Wildberries', 'fw.wb.ru': 'Wildberries',
    'finance.wb.ru': 'Wildberries', 'jitsi.wb.ru': 'Wildberries', 'dnd.wb.ru': 'Wildberries', 'user-geo-data.wildberries.ru': 'Wildberries',
    'banners-website.wildberries.ru': 'Wildberries', 'chat-prod.wildberries.ru': 'Wildberries', 'a.wb.ru': 'Wildberries',
    'avito.ru': 'Avito', 'm.avito.ru': 'Avito', 'api.avito.ru': 'Avito', 'avito.st': 'Avito', 'img.avito.st': 'Avito',
    'sntr.avito.ru': 'Avito', 'stats.avito.ru': 'Avito', 'cs.avito.ru': 'Avito', 'www.avito.st': 'Avito',
    'st.avito.ru': 'Avito', 'www.avito.ru': 'Avito', 
    **{f'{i:02d}.img.avito.st': 'Avito' for i in range(100)},
    'sberbank.ru': 'Сбербанк', 'online.sberbank.ru': 'Сбербанк', 'sber.ru': 'Сбербанк', 'id.sber.ru': 'Сбербанк',
    'bfds.sberbank.ru': 'Сбербанк', 'cms-res-web.online.sberbank.ru': 'Сбербанк', 'esa-res.online.sberbank.ru': 'Сбербанк',
    'pl-res.online.sberbank.ru': 'Сбербанк', 'www.sberbank.ru': 'Сбербанк', 'vtb.ru': 'ВТБ', 'www.vtb.ru': 'ВТБ',
    'online.vtb.ru': 'ВТБ', 'chat3.vtb.ru': 'ВТБ', 's.vtb.ru': 'ВТБ', 'sso-app4.vtb.ru': 'ВТБ', 'sso-app5.vtb.ru': 'ВТБ',
    'gazprombank.ru': 'Газпромбанк', 'alfabank.ru': 'Альфа-Банк', 'metrics.alfabank.ru': 'Альфа-Банк', 'tinkoff.ru': 'Тинькофф',
    'tbank.ru': 'Тинькофф', 'cdn.tbank.ru': 'Тинькофф', 'hrc.tbank.ru': 'Тинькофф', 'cobrowsing.tbank.ru': 'Тинькофф',
    'le.tbank.ru': 'Тинькофф', 'id.tbank.ru': 'Тинькофф', 'imgproxy.cdn-tinkoff.ru': 'Тинькофф', 'banki.ru': 'Банки.ру',
    'yandex.ru': 'Яндекс', 'ya.ru': 'Яндекс', 'dzen.ru': 'Дзен', 'kinopoisk.ru': 'Кинопоиск', 'yastatic.net': 'Яндекс',
    'yandex.net': 'Яндекс', 'mail.yandex.ru': 'Яндекс Почта', 'disk.yandex.ru': 'Яндекс Диск', 'maps.yandex.ru': 'Яндекс Карты',
    'api-maps.yandex.ru': 'Яндекс Карты', 'enterprise.api-maps.yandex.ru': 'Яндекс Карты', 'music.yandex.ru': 'Яндекс Музыка',
    'yandex.by': 'Яндекс', 'yandex.com': 'Яндекс', 'travel.yandex.ru': 'Яндекс Путешествия', 'informer.yandex.ru': 'Яндекс',
    'mediafeeds.yandex.ru': 'Яндекс', 'mediafeeds.yandex.com': 'Яндекс', 'uslugi.yandex.ru': 'Яндекс Услуги',
    'kiks.yandex.ru': 'Яндекс', 'kiks.yandex.com': 'Яндекс', 'frontend.vh.yandex.ru': 'Яндекс', 'favicon.yandex.ru': 'Яндекс',
    'favicon.yandex.com': 'Яндекс', 'favicon.yandex.net': 'Яндекс', 'browser.yandex.ru': 'Яндекс Браузер',
    'browser.yandex.com': 'Яндекс Браузер', 'api.browser.yandex.ru': 'Яндекс Браузер', 'api.browser.yandex.com': 'Яндекс Браузер',
    'wap.yandex.ru': 'Яндекс', 'wap.yandex.com': 'Яндекс', '300.ya.ru': 'Яндекс', 'brontp-pre.yandex.ru': 'Яндекс',
    'suggest.dzen.ru': 'Дзен', 'suggest.sso.dzen.ru': 'Дзен', 'sso.dzen.ru': 'Дзен', 'mail.yandex.com': 'Яндекс Почта',
    'yabs.yandex.ru': 'Яндекс', 'neuro.translate.yandex.ru': 'Яндекс Перевод', 'cdn.yandex.ru': 'Яндекс',
    'zen.yandex.ru': 'Дзен', 'zen.yandex.com': 'Дзен', 'zen.yandex.net': 'Дзен', 'collections.yandex.ru': 'Яндекс Коллекции',
    'collections.yandex.com': 'Яндекс Коллекции', 'an.yandex.ru': 'Яндекс', 'sba.yandex.ru': 'Яндекс',
    'sba.yandex.com': 'Яндекс', 'sba.yandex.net': 'Яндекс', 'surveys.yandex.ru': 'Яндекс Опросы',
    'yabro-wbplugin.edadeal.yandex.ru': 'Яндекс', 'api.events.plus.yandex.net': 'Яндекс Плюс', 'speller.yandex.net': 'Яндекс Спеллер',
    'avatars.mds.yandex.net': 'Яндекс', 'avatars.mds.yandex.com': 'Яндекс', 'mc.yandex.ru': 'Яндекс', 'mc.yandex.com': 'Яндекс',
    '3475482542.mc.yandex.ru': 'Яндекс', 'zen-yabro-morda.mediascope.mc.yandex.ru': 'Яндекс', 'travel.yastatic.net': 'Яндекс',
    'api.uxfeedback.yandex.net': 'Яндекс', 'api.s3.yandex.net': 'Яндекс', 'cdn.s3.yandex.net': 'Яндекс',
    'uxfeedback-cdn.s3.yandex.net': 'Яндекс', 'uxfeedback.yandex.ru': 'Яндекс', 'cloudcdn-m9-15.cdn.yandex.net': 'Яндекс',
    'cloudcdn-m9-14.cdn.yandex.net': 'Яндекс', 'cloudcdn-m9-13.cdn.yandex.net': 'Яндекс', 'cloudcdn-m9-12.cdn.yandex.net': 'Яндекс',
    'cloudcdn-m9-10.cdn.yandex.net': 'Яндекс', 'cloudcdn-m9-9.cdn.yandex.net': 'Яндекс', 'cloudcdn-m9-7.cdn.yandex.net': 'Яндекс',
    'cloudcdn-m9-6.cdn.yandex.net': 'Яндекс', 'cloudcdn-m9-5.cdn.yandex.net': 'Яндекс', 'cloudcdn-m9-4.cdn.yandex.net': 'Яндекс',
    'cloudcdn-m9-3.cdn.yandex.net': 'Яндекс', 'cloudcdn-m9-2.cdn.yandex.net': 'Яндекс', 'cloudcdn-ams19.cdn.yandex.net': 'Яндекс',
    'http-check-headers.yandex.ru': 'Яндекс', 'cloud.cdn.yandex.net': 'Яндекс', 'cloud.cdn.yandex.com': 'Яндекс',
    'cloud.cdn.yandex.ru': 'Яндекс', 'dr2.yandex.net': 'Яндекс', 'dr.yandex.net': 'Яндекс', 's3.yandex.net': 'Яндекс',
    'static-mon.yandex.net': 'Яндекс', 'sync.browser.yandex.net': 'Яндекс', 'storage.ape.yandex.net': 'Яндекс',
    'strm-rad-23.strm.yandex.net': 'Яндекс', 'strm.yandex.net': 'Яндекс', 'strm.yandex.ru': 'Яндекс', 'log.strm.yandex.ru': 'Яндекс',
    'egress.yandex.net': 'Яндекс', 'cdnrhkgfkkpupuotntfj.svc.cdn.yandex.net': 'Яндекс', 'csp.yandex.net': 'Яндекс',
    'mail.ru': 'Mail.ru', 'e.mail.ru': 'Mail.ru', 'my.mail.ru': 'Mail.ru', 'cloud.mail.ru': 'Mail.ru', 'inbox.ru': 'Mail.ru',
    'list.ru': 'Mail.ru', 'bk.ru': 'Mail.ru', 'myteam.mail.ru': 'Mail.ru', 'trk.mail.ru': 'Mail.ru', '1l-api.mail.ru': 'Mail.ru',
    '1l.mail.ru': 'Mail.ru', '1l-s2s.mail.ru': 'Mail.ru', '1l-view.mail.ru': 'Mail.ru', '1link.mail.ru': 'Mail.ru',
    '1l-hit.mail.ru': 'Mail.ru', '2021.mail.ru': 'Mail.ru', '2018.mail.ru': 'Mail.ru', '23feb.mail.ru': 'Mail.ru',
    '2019.mail.ru': 'Mail.ru', '2020.mail.ru': 'Mail.ru', '1l-go.mail.ru': 'Mail.ru', '8mar.mail.ru': 'Mail.ru',
    '9may.mail.ru': 'Mail.ru', 'aa.mail.ru': 'Mail.ru', '8march.mail.ru': 'Mail.ru', 'afisha.mail.ru': 'Mail.ru',
    'agent.mail.ru': 'Mail.ru', 'amigo.mail.ru': 'Mail.ru', 'analytics.predict.mail.ru': 'Mail.ru', 'alpha4.minigames.mail.ru': 'Mail.ru',
    'alpha3.minigames.mail.ru': 'Mail.ru', 'answer.mail.ru': 'Mail.ru', 'api.predict.mail.ru': 'Mail.ru', 'answers.mail.ru': 'Mail.ru',
    'authdl.mail.ru': 'Mail.ru', 'av.mail.ru': 'Mail.ru', 'apps.research.mail.ru': 'Mail.ru', 'auto.mail.ru': 'Mail.ru',
    'bb.mail.ru': 'Mail.ru', 'bender.mail.ru': 'Mail.ru', 'beko.dom.mail.ru': 'Mail.ru', 'azt.mail.ru': 'Mail.ru',
    'bd.mail.ru': 'Mail.ru', 'autodiscover.corp.mail.ru': 'Mail.ru', 'aw.mail.ru': 'Mail.ru', 'beta.mail.ru': 'Mail.ru',
    'biz.mail.ru': 'Mail.ru', 'blackfriday.mail.ru': 'Mail.ru', 'bitva.mail.ru': 'Mail.ru', 'blog.mail.ru': 'Mail.ru',
    'bratva-mr.mail.ru': 'Mail.ru', 'browser.mail.ru': 'Mail.ru', 'calendar.mail.ru': 'Mail.ru', 'capsula.mail.ru': 'Mail.ru',
    'cdn.newyear.mail.ru': 'Mail.ru', 'cars.mail.ru': 'Mail.ru', 'code.mail.ru': 'Mail.ru', 'cobmo.mail.ru': 'Mail.ru',
    'cobma.mail.ru': 'Mail.ru', 'cog.mail.ru': 'Mail.ru', 'cdn.connect.mail.ru': 'Mail.ru', 'cf.mail.ru': 'Mail.ru',
    'comba.mail.ru': 'Mail.ru', 'compute.mail.ru': 'Mail.ru', 'codefest.mail.ru': 'Mail.ru', 'combu.mail.ru': 'Mail.ru',
    'corp.mail.ru': 'Mail.ru', 'commba.mail.ru': 'Mail.ru', 'crazypanda.mail.ru': 'Mail.ru', 'ctlog.mail.ru': 'Mail.ru',
    'cpg.money.mail.ru': 'Mail.ru', 'ctlog2023.mail.ru': 'Mail.ru', 'ctlog2024.mail.ru': 'Mail.ru', 'cto.mail.ru': 'Mail.ru',
    'cups.mail.ru': 'Mail.ru', 'da.biz.mail.ru': 'Mail.ru', 'da-preprod.biz.mail.ru': 'Mail.ru', 'data.amigo.mail.ru': 'Mail.ru',
    'dk.mail.ru': 'Mail.ru', 'dev1.mail.ru': 'Mail.ru', 'dev3.mail.ru': 'Mail.ru', 'dl.mail.ru': 'Mail.ru',
    'deti.mail.ru': 'Mail.ru', 'dn.mail.ru': 'Mail.ru', 'dl.marusia.mail.ru': 'Mail.ru', 'doc.mail.ru': 'Mail.ru',
    'dragonpals.mail.ru': 'Mail.ru', 'dom.mail.ru': 'Mail.ru', 'duck.mail.ru': 'Mail.ru', 'dev2.mail.ru': 'Mail.ru',
    'ds.mail.ru': 'Mail.ru', 'education.mail.ru': 'Mail.ru', 'dobro.mail.ru': 'Mail.ru', 'esc.predict.mail.ru': 'Mail.ru',
    'et.mail.ru': 'Mail.ru', 'fe.mail.ru': 'Mail.ru', 'finance.mail.ru': 'Mail.ru', 'five.predict.mail.ru': 'Mail.ru',
    'foto.mail.ru': 'Mail.ru', 'games-bamboo.mail.ru': 'Mail.ru', 'games-fisheye.mail.ru': 'Mail.ru', 'games.mail.ru': 'Mail.ru',
    'genesis.mail.ru': 'Mail.ru', 'geo-apart.predict.mail.ru': 'Mail.ru', 'golos.mail.ru': 'Mail.ru', 'go.mail.ru': 'Mail.ru',
    'gpb.finance.mail.ru': 'Mail.ru', 'gibdd.mail.ru': 'Mail.ru', 'health.mail.ru': 'Mail.ru', 'guns.mail.ru': 'Mail.ru',
    'horo.mail.ru': 'Mail.ru', 'hs.mail.ru': 'Mail.ru', 'help.mcs.mail.ru': 'Mail.ru', 'imperia.mail.ru': 'Mail.ru',
    'it.mail.ru': 'Mail.ru', 'internet.mail.ru': 'Mail.ru', 'infra.mail.ru': 'Mail.ru', 'hi-tech.mail.ru': 'Mail.ru',
    'jd.mail.ru': 'Mail.ru', 'journey.mail.ru': 'Mail.ru', 'junior.mail.ru': 'Mail.ru', 'juggermobile.mail.ru': 'Mail.ru',
    'kicker.mail.ru': 'Mail.ru', 'knights.mail.ru': 'Mail.ru', 'kino.mail.ru': 'Mail.ru', 'kingdomrift.mail.ru': 'Mail.ru',
    'kobmo.mail.ru': 'Mail.ru', 'komba.mail.ru': 'Mail.ru', 'kobma.mail.ru': 'Mail.ru', 'kommba.mail.ru': 'Mail.ru',
    'kombo.mail.ru': 'Mail.ru', 'kz.mcs.mail.ru': 'Mail.ru', 'konflikt.mail.ru': 'Mail.ru', 'kombu.mail.ru': 'Mail.ru',
    'lady.mail.ru': 'Mail.ru', 'landing.mail.ru': 'Mail.ru', 'la.mail.ru': 'Mail.ru', 'legendofheroes.mail.ru': 'Mail.ru',
    'legenda.mail.ru': 'Mail.ru', 'loa.mail.ru': 'Mail.ru', 'love.mail.ru': 'Mail.ru', 'lotro.mail.ru': 'Mail.ru',
    'mailer.mail.ru': 'Mail.ru', 'mailexpress.mail.ru': 'Mail.ru', 'man.mail.ru': 'Mail.ru', 'maps.mail.ru': 'Mail.ru',
    'marusia.mail.ru': 'Mail.ru', 'mcs.mail.ru': 'Mail.ru', 'media-golos.mail.ru': 'Mail.ru', 'mediapro.mail.ru': 'Mail.ru',
    'merch-cpg.money.mail.ru': 'Mail.ru', 'miniapp.internal.myteam.mail.ru': 'Mail.ru', 'media.mail.ru': 'Mail.ru',
    'mobfarm.mail.ru': 'Mail.ru', 'mowar.mail.ru': 'Mail.ru', 'mozilla.mail.ru': 'Mail.ru', 'mosqa.mail.ru': 'Mail.ru',
    'mking.mail.ru': 'Mail.ru', 'minigames.mail.ru': 'Mail.ru', 'nebogame.mail.ru': 'Mail.ru', 'money.mail.ru': 'Mail.ru',
    'net.mail.ru': 'Mail.ru', 'new.mail.ru': 'Mail.ru', 'newyear2018.mail.ru': 'Mail.ru', 'news.mail.ru': 'Mail.ru',
    'newyear.mail.ru': 'Mail.ru', 'nonstandard.sales.mail.ru': 'Mail.ru', 'notes.mail.ru': 'Mail.ru', 'octavius.mail.ru': 'Mail.ru',
    'operator.mail.ru': 'Mail.ru', 'otvety.mail.ru': 'Mail.ru', 'otvet.mail.ru': 'Mail.ru', 'otveti.mail.ru': 'Mail.ru',
    'panzar.mail.ru': 'Mail.ru', 'park.mail.ru': 'Mail.ru', 'pernatsk.mail.ru': 'Mail.ru', 'pets.mail.ru': 'Mail.ru',
    'pms.mail.ru': 'Mail.ru', 'pochtabank.mail.ru': 'Mail.ru', 'pokerist.mail.ru': 'Mail.ru', 'pogoda.mail.ru': 'Mail.ru',
    'polis.mail.ru': 'Mail.ru', 'primeworld.mail.ru': 'Mail.ru', 'pp.mail.ru': 'Mail.ru', 'ptd.predict.mail.ru': 'Mail.ru',
    'public.infra.mail.ru': 'Mail.ru', 'pulse.mail.ru': 'Mail.ru', 'pubg.mail.ru': 'Mail.ru', 'quantum.mail.ru': 'Mail.ru',
    'rate.mail.ru': 'Mail.ru', 'pw.mail.ru': 'Mail.ru', 'rebus.calls.mail.ru': 'Mail.ru', 'rebus.octavius.mail.ru': 'Mail.ru',
    'rev.mail.ru': 'Mail.ru', 'rl.mail.ru': 'Mail.ru', 'rm.mail.ru': 'Mail.ru', 'riot.mail.ru': 'Mail.ru',
    'reseach.mail.ru': 'Mail.ru', 's3.babel.mail.ru': 'Mail.ru', 'rt.api.operator.mail.ru': 'Mail.ru', 's3.mail.ru': 'Mail.ru',
    's3.media-mobs.mail.ru': 'Mail.ru', 'sales.mail.ru': 'Mail.ru', 'sangels.mail.ru': 'Mail.ru', 'sdk.money.mail.ru': 'Mail.ru',
    'service.amigo.mail.ru': 'Mail.ru', 'security.mail.ru': 'Mail.ru', 'shadowbound.mail.ru': 'Mail.ru', 'socdwar.mail.ru': 'Mail.ru',
    'sochi-park.predict.mail.ru': 'Mail.ru', 'souz.mail.ru': 'Mail.ru', 'sphere.mail.ru': 'Mail.ru', 'staging-analytics.predict.mail.ru': 'Mail.ru',
    'staging-sochi-park.predict.mail.ru': 'Mail.ru', 'staging-esc.predict.mail.ru': 'Mail.ru', 'stand.bb.mail.ru': 'Mail.ru',
    'sport.mail.ru': 'Mail.ru', 'stand.aoc.mail.ru': 'Mail.ru', 'stand.cb.mail.ru': 'Mail.ru', 'startrek.mail.ru': 'Mail.ru',
    'static.dl.mail.ru': 'Mail.ru', 'stand.pw.mail.ru': 'Mail.ru', 'stand.la.mail.ru': 'Mail.ru', 'stormriders.mail.ru': 'Mail.ru',
    'static.operator.mail.ru': 'Mail.ru', 'stream.mail.ru': 'Mail.ru', 'status.mcs.mail.ru': 'Mail.ru', 'street-combats.mail.ru': 'Mail.ru',
    'support.biz.mail.ru': 'Mail.ru', 'support.mcs.mail.ru': 'Mail.ru', 'team.mail.ru': 'Mail.ru', 'support.tech.mail.ru': 'Mail.ru',
    'tech.mail.ru': 'Mail.ru', 'tera.mail.ru': 'Mail.ru', 'tiles.maps.mail.ru': 'Mail.ru', 'todo.mail.ru': 'Mail.ru',
    'tidaltrek.mail.ru': 'Mail.ru', 'tmgame.mail.ru': 'Mail.ru', 'townwars.mail.ru': 'Mail.ru', 'tv.mail.ru': 'Mail.ru',
    'ttbh.mail.ru': 'Mail.ru', 'typewriter.mail.ru': 'Mail.ru', 'u.corp.mail.ru': 'Mail.ru', 'ufo.mail.ru': 'Mail.ru',
    'vkdoc.mail.ru': 'Mail.ru', 'vk.mail.ru': 'Mail.ru', 'voina.mail.ru': 'Mail.ru', 'warface.mail.ru': 'Mail.ru',
    'wartune.mail.ru': 'Mail.ru', 'weblink.predict.mail.ru': 'Mail.ru', 'warheaven.mail.ru': 'Mail.ru', 'welcome.mail.ru': 'Mail.ru',
    'webstore.mail.ru': 'Mail.ru', 'webagent.mail.ru': 'Mail.ru', 'wf.mail.ru': 'Mail.ru', 'whatsnew.mail.ru': 'Mail.ru',
    'wh-cpg.money.mail.ru': 'Mail.ru', 'wok.mail.ru': 'Mail.ru', 'www.biz.mail.ru': 'Mail.ru', 'wos.mail.ru': 'Mail.ru',
    'www.mail.ru': 'Mail.ru', 'www.pubg.mail.ru': 'Mail.ru', 'www.wf.mail.ru': 'Mail.ru', 'www.mcs.mail.ru': 'Mail.ru',
    'rs.mail.ru': 'Mail.ru', 'top-fwz1.mail.ru': 'Mail.ru', 'privacy-cs.mail.ru': 'Mail.ru', 'r0.mradx.net': 'Mail.ru',
    'rutube.ru': 'Rutube', 'static.rutube.ru': 'Rutube', 'rutubelist.ru': 'Rutube', 'pic.rutubelist.ru': 'Rutube',
    'ssp.rutube.ru': 'Rutube', 'preview.rutube.ru': 'Rutube', 'goya.rutube.ru': 'Rutube', 'smotrim.ru': 'Смотрим',
    'ivi.ru': 'Ivi', 'cdn.ivi.ru': 'Ivi', 'okko.tv': 'Okko', 'start.ru': 'Start', 'wink.ru': 'Wink', 'kion.ru': 'Kion',
    'premier.one': 'Premier', 'more.tv': 'More.tv', 'm.47news.ru': '47 News', 'lenta.ru': 'Лента.ру', 'gazeta.ru': 'Газета.ру',
    'kp.ru': 'Комсомольская Правда', 'rambler.ru': 'Рамблер', 'ria.ru': 'РИА Новости', 'tass.ru': 'ТАСС', 'interfax.ru': 'Интерфакс',
    'kommersant.ru': 'Коммерсант', 'vedomosti.ru': 'Ведомости', 'rbc.ru': 'РБК', 'russian.rt.com': 'RT', 'iz.ru': 'Известия',
    'mk.ru': 'Московский Комсомолец', 'rg.ru': 'Российская Газета', 'www.kinopoisk.ru': 'Кинопоиск', 'widgets.kinopoisk.ru': 'Кинопоиск',
    'payment-widget.plus.kinopoisk.ru': 'Кинопоиск', 'external-api.mediabilling.kinopoisk.ru': 'Кинопоиск', 'external-api.plus.kinopoisk.ru': 'Кинопоиск',
    'graphql-web.kinopoisk.ru': 'Кинопоиск', 'graphql.kinopoisk.ru': 'Кинопоиск', 'tickets.widget.kinopoisk.ru': 'Кинопоиск',
    'st.kinopoisk.ru': 'Кинопоиск', 'quiz.kinopoisk.ru': 'Кинопоиск', 'payment-widget.kinopoisk.ru': 'Кинопоиск',
    'payment-widget-smarttv.plus.kinopoisk.ru': 'Кинопоиск', 'oneclick-payment.kinopoisk.ru': 'Кинопоиск', 'microapps.kinopoisk.ru': 'Кинопоиск',
    'ma.kinopoisk.ru': 'Кинопоиск', 'hd.kinopoisk.ru': 'Кинопоиск', 'crowdtest.payment-widget-smarttv.plus.tst.kinopoisk.ru': 'Кинопоиск',
    'crowdtest.payment-widget.plus.tst.kinopoisk.ru': 'Кинопоиск', 'api.plus.kinopoisk.ru': 'Кинопоиск', 'st-im.kinopoisk.ru': 'Кинопоиск',
    'sso.kinopoisk.ru': 'Кинопоиск', 'touch.kinopoisk.ru': 'Кинопоиск', '2gis.ru': '2ГИС', '2gis.com': '2ГИС',
    'api.2gis.ru': '2ГИС', 'keys.api.2gis.com': '2ГИС', 'favorites.api.2gis.com': '2ГИС', 'styles.api.2gis.com': '2ГИС',
    'tile0.maps.2gis.com': '2ГИС', 'tile1.maps.2gis.com': '2ГИС', 'tile2.maps.2gis.com': '2ГИС', 'tile3.maps.2gis.com': '2ГИС',
    'tile4.maps.2gis.com': '2ГИС', 'api.photo.2gis.com': '2ГИС', 'filekeeper-vod.2gis.com': '2ГИС', 'i0.photo.2gis.com': '2ГИС',
    'i1.photo.2gis.com': '2ГИС', 'i2.photo.2gis.com': '2ГИС', 'i3.photo.2gis.com': '2ГИС', 'i4.photo.2gis.com': '2ГИС',
    'i5.photo.2gis.com': '2ГИС', 'i6.photo.2gis.com': '2ГИС', 'i7.photo.2gis.com': '2ГИС', 'i8.photo.2gis.com': '2ГИС',
    'i9.photo.2gis.com': '2ГИС', 'jam.api.2gis.com': '2ГИС', 'catalog.api.2gis.com': '2ГИС', 'api.reviews.2gis.com': '2ГИС',
    'public-api.reviews.2gis.com': '2ГИС', 'mapgl.2gis.com': '2ГИС', 'd-assets.2gis.ru': '2ГИС', 'disk.2gis.com': '2ГИС',
    's0.bss.2gis.com': '2ГИС', 's1.bss.2gis.com': '2ГИС', 'ams2-cdn.2gis.com': '2ГИС', 'tutu.ru': 'Туту.ру', 'img.tutu.ru': 'Туту.ру',
    'rzd.ru': 'РЖД', 'ticket.rzd.ru': 'РЖД', 'pass.rzd.ru': 'РЖД', 'cargo.rzd.ru': 'РЖД', 'company.rzd.ru': 'РЖД',
    'contacts.rzd.ru': 'РЖД', 'team.rzd.ru': 'РЖД', 'my.rzd.ru': 'РЖД', 'prodvizhenie.rzd.ru': 'РЖД', 'disk.rzd.ru': 'РЖД',
    'market.rzd.ru': 'РЖД', 'secure.rzd.ru': 'РЖД', 'secure-cloud.rzd.ru': 'РЖД', 'travel.rzd.ru': 'РЖД', 'welcome.rzd.ru': 'РЖД',
    'adm.mp.rzd.ru': 'РЖД', 'link.mp.rzd.ru': 'РЖД', 'pulse.mp.rzd.ru': 'РЖД', 'mp.rzd.ru': 'РЖД', 'ekmp-a-51.rzd.ru': 'РЖД',
    'cdek.ru': 'СДЭК', 'cdek.market': 'СДЭК', 'calc.cdek.ru': 'СДЭК', 'pochta.ru': 'Почта России', 'ws-api.oneme.ru': 'Oneme',
    'rostelecom.ru': 'Ростелеком', 'rt.ru': 'Ростелеком', 'mts.ru': 'МТС', 'megafon.ru': 'Мегафон', 'beeline.ru': 'Билайн',
    'tele2.ru': 'Tele2', 't2.ru': 'Tele2', 'www.t2.ru': 'Tele2', 'msk.t2.ru': 'Tele2', 's3.t2.ru': 'Tele2', 'yota.ru': 'Yota',
    'domru.ru': 'Дом.ру', 'ertelecom.ru': 'ЭР-Телеком', 'selectel.ru': 'Selectel', 'timeweb.ru': 'Timeweb', 'gismeteo.ru': 'Гисметео',
    'meteoinfo.ru': 'Метео', 'rp5.ru': 'RП5', 'hh.ru': 'HeadHunter', 'superjob.ru': 'SuperJob', 'rabota.ru': 'Работа.ру',
    'auto.ru': 'Auto.ru', 'sso.auto.ru': 'Auto.ru', 'drom.ru': 'Drom', 'avto.ru': 'Avto.ru', 'eda.ru': 'Eda.ru',
    'food.ru': 'Food.ru', 'edadeal.ru': 'Edadeal', 'delivery-club.ru': 'Delivery Club', 'leroymerlin.ru': 'Леруа Мерлен',
    'lemanapro.ru': 'Лемана Про', 'cdn.lemanapro.ru': 'Лемана Про', 'static.lemanapro.ru': 'Лемана Про', 'dmp.dmpkit.lemanapro.ru': 'Лемана Про',
    'receive-sentry.lmru.tech': 'Лемана Про', 'partners.lemanapro.ru': 'Лемана Про', 'petrovich.ru': 'Петрович', 'maxidom.ru': 'Максидом',
    'vseinstrumenti.ru': 'ВсеИнструменты', '220-volt.ru': '220 Вольт', 'max.ru': 'Max', 'dev.max.ru': 'Max', 'web.max.ru': 'Max',
    'api.max.ru': 'Max', 'legal.max.ru': 'Max', 'st.max.ru': 'Max', 'botapi.max.ru': 'Max', 'link.max.ru': 'Max',
    'download.max.ru': 'Max', 'i.max.ru': 'Max', 'help.max.ru': 'Max', 'mos.ru': 'Мос.ру', 'taximaxim.ru': 'Такси Максим',
    'moskva.taximaxim.ru': 'Такси Максим'
}


# ========= УСТАНОВКА XRAY ДЛЯ GITHUB ACTIONS =========
def download_xray():
    xray_bin = "./xray"
    if os.path.exists(xray_bin):
        return xray_bin
        
    print("⬇️ Ядро Xray не найдено. Скачиваю для Linux (GitHub Actions)...", flush=True)
    url = "https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-64.zip"
    zip_path = "xray.zip"
    
    try:
        response = requests.get(url, timeout=30)
        with open(zip_path, 'wb') as f:
            f.write(response.content)
            
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extract('xray', '.')
            
        os.chmod(xray_bin, 0o755) 
        os.remove(zip_path)
        print("✅ Xray успешно установлен!", flush=True)
        return xray_bin
    except Exception as e:
        print(f"❌ Ошибка скачивания Xray: {e}", flush=True)
        return None

# ========= ЛОГИКА ПАРСИНГА И ФИЛЬТРАЦИИ =========
def extract_all_possible_domains(vless_url: str) -> list:
    domains = set()
    try:
        if not vless_url.startswith("vless://"): return []
        content = vless_url[8:]
        at_pos = content.find('@')
        if at_pos == -1: return []
        after_at = content[at_pos+1:]
        
        q_pos = after_at.find('?')
        if q_pos != -1:
            host_part = after_at[:q_pos]
            query_part = after_at[q_pos+1:]
        else:
            host_part = after_at
            query_part = ""
        
        if ':' in host_part: host = host_part.split(':', 1)[0]
        else: host = host_part
        
        if host and '.' in host: domains.add(host.lower())
        
        if query_part:
            if '#' in query_part: query_part = query_part.split('#', 1)[0]
            for param in query_part.split('&'):
                if '=' in param:
                    k, v = param.split('=', 1)
                    v_decoded = urllib.parse.unquote(v).lower()
                    if k.lower() in ['sni', 'host'] and '.' in v_decoded:
                        domains.add(v_decoded)
                    elif k.lower() == 'path':
                        path_parts = re.findall(r'[a-zA-Z0-9][a-zA-Z0-9\-\.]+[a-zA-Z0-9]\.[a-zA-Z]{2,}', v_decoded)
                        for d in path_parts: domains.add(d.lower())
        return list(domains)
    except:
        return []

def filter_by_sni(vless_url: str) -> bool:
    domains = extract_all_possible_domains(vless_url)
    
    # Сначала проверяем наш гигантский словарь
    for domain in domains:
        if domain in DOMAIN_NAMES: return True
        parts = domain.split('.')
        for i in range(len(parts) - 1):
            sub = ".".join(parts[i:])
            if sub in DOMAIN_NAMES: return True
        if len(parts) >= 2:
            base = ".".join(parts[-2:])
            if base in DOMAIN_NAMES: return True
        for key in DOMAIN_NAMES:
            if domain.endswith("." + key): return True

    # Затем проверяем whitelist (если он есть)
    if os.path.exists("whitelist.txt"):
        with open("whitelist.txt", "r", encoding="utf-8") as f:
            whitelist = [l.strip().lower() for l in f if l.strip()]
        for domain in domains:
            for w in whitelist:
                if domain == w or domain.endswith("." + w): return True

    return False

def detect_protocol(vless_url: str) -> str:
    try:
        query = urllib.parse.urlparse(vless_url).query
        params = dict(urllib.parse.parse_qsl(query))
        transport = params.get("type", "").lower()
        if transport in ("ws", "websocket"): return "WS"
        if transport in ("grpc", "gun"): return "gRPC"
        if transport == "tcp": return "TCP"
        return transport.upper() if transport else "TCP"
    except:
        return "TCP"

def parse_vless(link):
    """Превращает vless:// ссылку в JSON-объект для Xray"""
    try:
        url = urllib.parse.urlparse(link)
        params = dict(urllib.parse.parse_qsl(url.query))
        
        config = {
            "protocol": "vless",
            "settings": {
                "vnext": [{
                    "address": url.hostname,
                    "port": int(url.port),
                    "users": [{"id": url.username, "encryption": "none"}]
                }]
            },
            "streamSettings": {
                "network": params.get('type', 'tcp'),
                "security": params.get('security', 'none'),
                "tlsSettings": {"serverName": params.get('sni', url.hostname)} if params.get('security') == 'tls' else {},
                "realitySettings": {
                    "publicKey": params.get('pbk', ''),
                    "shortId": params.get('sid', ''),
                    "serverName": params.get('sni', url.hostname),
                    "spiderX": params.get('spx', '/')
                } if params.get('security') == 'reality' else {}
            }
        }
        
        if params.get('type') == 'ws':
            config["streamSettings"]["wsSettings"] = {"path": params.get('path', '/')}
        elif params.get('type') == 'grpc':
            config["streamSettings"]["grpcSettings"] = {"serviceName": params.get('serviceName', '')}
            
        return config
    except:
        return None

async def download_source(session, url):
    try:
        async with session.get(url, timeout=20) as resp:
            if resp.status == 200:
                return VLESS_REGEX.findall(await resp.text())
    except: pass
    return []

# ========= ТЕСТЕР =========
class XrayTester:
    def __init__(self, items, output_file, xray_path):
        self.items = items
        self.output_file = output_file
        self.xray_path = xray_path

    def _worker(self, data):
        link = data['raw']
        xray_part = data['xray']
        
        port = random.randint(20000, 40000)
        full_config = {
            "log": {"loglevel": "none"},
            "inbounds": [{"port": port, "listen": "127.0.0.1", "protocol": "socks"}],
            "outbounds": [xray_part, {"protocol": "freedom", "tag": "direct"}]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tf:
            json.dump(full_config, tf)
            cfg_path = tf.name

        success = False
        proc = None
        try:
            proc = subprocess.Popen([self.xray_path, "-c", cfg_path], 
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1.5) 

            r = requests.get(XRAY_TEST_URL, 
                             proxies={'http': f'socks5h://127.0.0.1:{port}', 'https': f'socks5h://127.0.0.1:{port}'}, 
                             timeout=XRAY_TIMEOUT)
            if r.status_code == 204:
                success = True
        except: pass
        finally:
            if proc:
                proc.terminate()
                try: proc.wait(timeout=2)
                except: proc.kill()
            if os.path.exists(cfg_path):
                try: os.remove(cfg_path)
                except: pass
        
        return link if success else None

    def run(self):
        total = len(self.items)
        print(f"🔎 Тестирую {total} валидных узлов...", flush=True)
        results = []
        
        with ThreadPoolExecutor(max_workers=XRAY_MAX_WORKERS) as executor:
            futures = [executor.submit(self._worker, item) for item in self.items]
            for i, f in enumerate(as_completed(futures)):
                res = f.result()
                if res: results.append(res)
                if (i+1) % 50 == 0 or (i+1) == total:
                    print(f"📊 Прогресс: {i+1}/{total} | Рабочих найдено: {len(results)}", flush=True)

        with open(self.output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(results))
        return len(results)

# ========= ГЛАВНЫЙ ЦИКЛ =========
async def main():
    print(f"🚀 Старт парсера: {datetime.now().strftime('%H:%M:%S')}", flush=True)

    if not os.path.exists(SOURCES_FILE):
        print("❌ ОШИБКА: Нет файла sources.txt!"); return

    xray_binary = download_xray()
    if not xray_binary:
        print("❌ Не удалось получить Xray. Остановка.")
        return

    # 1. Сбор ссылок
    async with aiofiles.open(SOURCES_FILE, 'r') as f:
        urls = [l.strip() for l in await f.readlines() if l.strip()]

    print(f"🌐 Опрос {len(urls)} источников...", flush=True)
    async with aiohttp.ClientSession() as session:
        tasks = [download_source(session, u) for u in urls]
        all_links = []
        for res in await asyncio.gather(*tasks): all_links.extend(res)

    unique_links = list(set([l for l in all_links if UUID_REGEX.search(l)]))
    print(f"📥 Найдено уникальных VLESS: {len(unique_links)}", flush=True)

    # 2. Фильтрация по SNI (DOMAIN_NAMES и whitelist.txt)
    print("🔍 Фильтрация по словарю SNI...", flush=True)
    filtered_links = [l for l in unique_links if filter_by_sni(l)]
    print(f"🎯 Прошли фильтрацию: {len(filtered_links)}", flush=True)

    # 3. Именование (№1 | TCP MAX | @obwhitel) и подготовка к тесту
    test_items = []
    for idx, link in enumerate(filtered_links, start=1):
        clean_link = link.split('#')[0]
        protocol = detect_protocol(clean_link)
        
        # Строгое формирование имени
        new_name = urllib.parse.quote(f"№{idx} | {protocol} MAX | @obwhitel")
        final_link = f"{clean_link}#{new_name}"
        
        x_cfg = parse_vless(final_link)
        if x_cfg:
            test_items.append({"raw": final_link, "xray": x_cfg})

    # 4. Тест и сохранение
    if test_items:
        tester = XrayTester(test_items, WORK_FILE, xray_binary)
        loop = asyncio.get_event_loop()
        count = await loop.run_in_executor(None, tester.run)
        print(f"✅ ФАЙЛ УСПЕШНО СОХРАНЕН: {WORK_FILE}. Найдено рабочих: {count}", flush=True)
    else:
        print("⏭️ После фильтрации не осталось ссылок для тестирования.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"💥 Ошибка: {e}", flush=True)
        sys.exit(1)
