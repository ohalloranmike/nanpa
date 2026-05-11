from zipfile import ZipFile
import sqlite3
import csv
import os
import os.path
import time
import logging
import requests

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
import uvicorn

ac_headers = []
ac_oc = []
caac_oc = []
AreaCodesOfficeCodes = []
AreaCodesOnly = []
fivex_codes = []
codes900 = []
FGDCICCodes = []
FGBCICCodes = []
N11Codes = []
results = []

now = time.time()
days_old = now - 60 * 60 * 24 * 1  # 10 days old...Number of seconds in 10 days
new_database_file = False

myport = 5001
myip = 'localhost'
myurl = 'http://' + myip + ':' + str(myport)

_project_root = os.path.dirname(os.path.abspath(__file__))
FilePath = os.path.join(_project_root, 'static', 'NANPA') + os.sep
USACMapPath = os.path.join(_project_root, 'static', 'USACMaps') + os.sep
os.makedirs(FilePath, exist_ok=True)
os.makedirs(USACMapPath, exist_ok=True)

USACMapFilePath = '/USACMaps/'
StateFilePath = '/USStateMaps/'
USTerritoryFilePath = '/USTerritoryACMaps/'
CanadaFilePath = '/CanadaACMaps/'
CountryFilePath = '/CountryACMaps/'
ACOCDownloadUrl = 'https://reports.nanpa.com/public/CoCodeAssignment_Utilized_AllStates_Public.zip'
ACDownloadUrl = 'https://reports.nanpa.com/public/npa_report.csv'
CanadaOCDownloadUrl = 'https://www.cnac.ca/data/COCodeStatus_ALL.zip'

LinkHome = 'http://' + myip + ':' + str(myport)
LinkACMaps = 'http://' + myip + ':' + str(myport) + '/acmaps?state='

LinkAnchor = '<a href="http://'
LinkByAC = LinkAnchor + myip + ':' + str(myport) + '/areacodes?npa='
LinkByOC = LinkAnchor + myip + ':' + str(myport) + '/officecodes?npa-nxx='

States = {
    'AK': 'ALASKA',
    'AL': 'ALABAMA',
    'AR': 'ARKANSAS',
    'AZ': 'ARIZONA',
    'CA': 'CALIFORNIA',
    'CO': 'COLORADO',
    'CT': 'CONNECTICUT',
    'DC': 'DISTRICT OF COLUMBIA',
    'DE': 'DELAWARE',
    'FL': 'FLORIDA',
    'GA': 'GEORGIA',
    'HI': 'HAWAII',
    'IA': 'IOWA',
    'ID': 'IDAHO',
    'IL': 'ILLINOIS',
    'IN': 'INDIANA',
    'KS': 'KANSAS',
    'KY': 'KENTUCKY',
    'LA': 'LOUISIANA',
    'MA': 'MASSACHUSETTS',
    'MD': 'MARYLAND',
    'ME': 'MAINE',
    'MI': 'MICHIGAN',
    'MN': 'MINNESOTA',
    'MO': 'MISSOURI',
    'MS': 'MISSISSIPPI',
    'MT': 'MONTANA',
    'NC': 'NORTH CAROLINA',
    'ND': 'NORTH DAKOTA',
    'NE': 'NEBRASKA',
    'NH': 'NEW HAMPSHIRE',
    'NJ': 'NEW JERSEY',
    'NM': 'NEW MEXICO',
    'NV': 'NEVADA',
    'NY': 'NEW YORK',
    'OH': 'OHIO',
    'OK': 'OKLAHOMA',
    'OR': 'OREGON',
    'PA': 'PENNSYLVANIA',
    'RI': 'RHODE ISLAND',
    'SC': 'SOUTH CAROLINA',
    'SD': 'SOUTH DAKOTA',
    'TN': 'TENNESSEE',
    'TX': 'TEXAS',
    'UT': 'UTAH',
    'VA': 'VIRGINIA',
    'VT': 'VERMONT',
    'WA': 'WASHINGTON',
    'WI': 'WISCONSIN',
    'WV': 'WEST VIRGINIA',
    'WY': 'WYOMING'
}

USTerritory = {
    'AS': 'AMREICAN SOMOA',
    'GU': 'GUAM',
    'PR': 'PUERTO RICO',
    'USVI': 'US VIRGIN ISLANDS',
    'CNMI': 'NORTHERN MARIANNA ISLANDS'
}

CanadaPTAbbr = {
    'AB': 'ALBERTA',
    'BC': 'BRITISH COLUMBIA',
    'MB': 'MANITOBA',
    'NB': 'NEW BRUNSWICK',
    'NL': 'NEWFOUNDLAND AND LABRADOR',
    'NS-PEI': 'NOVA SCOTIA - PRINCE EDWARD ISLAND',
    'ON': 'ONTARIO',
    'QC': 'QUEBEC',
    'SK': 'SASKATCHEWAN',
    'YT-NWT-NU': 'YUKON-NW TERR. - NUNAVUT'
}

CanadaPT = {
    'ALBERTA': 'AB',
    'BRITISH COLUMBIA': 'BC',
    'MANITOBA': 'MB',
    'NEW BRUNSWICK': 'NB',
    'NEWFOUNDLAND AND LABRADOR': 'NL',
    'NOVA SCOTIA - PRINCE EDWARD ISLAND': 'NS-PEI',
    'ONTARIO': 'ON',
    'QUEBEC': 'QC',
    'SASKATCHEWAN': 'SK',
    'YUKON-NW TERR. - NUNAVUT': 'YT-NWT-NU',
}

Country = {
    'JAMAICA': 'JAMAICA',
    'BAHAMAS': 'BAHAMAS',
    'BARBADOS': 'BARBADOS',
    'ANGUILLA': 'ANGUILLA',
    'ANTIGUA/BARBUDA': 'ANTIGUA/BARBUDA',
    'BRITISH VIRGIN ISLANDS': 'BRITISH VIRGIN ISLANDS',
    'CAYMAN ISLANDS': 'CAYMAN ISLANDS',
    'BERMUDA': 'BERMUDA',
    'GRENADA': 'GRENADA',
    'TURKS & CAICOS ISLANDS': 'TURKS & CAICOS ISLANDS',
    'MONTSERRAT': 'MONTSERRAT',
    'SINT MAARTEN': 'SINT MAARTEN',
    'ST. LUCIA': 'ST. LUCIA',
    'DOMINICA': 'DOMINICA',
    'ST. VINCENT & GRENADINES': 'ST. VINCENT & GRENADINES',
    'DOMINICAN REPUBLIC': 'DOMINICAN REPUBLIC',
    'TRINIDAD & TOBAGO': 'TRINIDAD & TOBAGO',
    'ST. KITTS & NEVIS': 'ST. KITTS & NEVIS'
}


logger = logging.getLogger(__name__)
REQUEST_TIMEOUT_SECONDS = 30
DOWNLOAD_RETRIES = 3
DB_PATH = os.path.join(FilePath, 'pn.db')


def download_file(url: str, destination: str) -> None:
    last_error = None
    for attempt in range(1, DOWNLOAD_RETRIES + 1):
        try:
            response = requests.get(url, allow_redirects=True, timeout=REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()
            with open(destination, 'wb') as out_file:
                out_file.write(response.content)
            return
        except requests.RequestException as exc:
            last_error = exc
            logger.warning("Download failed (%s/%s) for %s: %s", attempt, DOWNLOAD_RETRIES, url, exc)
    raise RuntimeError(f"Failed to download {url}") from last_error


def refresh_database() -> None:
    # Mutate module-level lists and rebind them later; declare global so early .append() is not
    # treated as a local assignment (UnboundLocalError).
    global ac_oc, caac_oc

    # check to see if the database & downloaded files exist, and if pn.db is older than 1 day.
    ch_npa_report_csv = os.path.isfile(FilePath + 'npa_report.csv')
    ch_CoCodeAssignment_Utilized_AllStates_Public_txt = os.path.isfile(FilePath + 'CoCodeAssignment_Utilized_AllStates_Public.txt')
    ch_CoCodeAssignment_Utilized_AllStates_Public_zip = os.path.isfile(FilePath + 'CoCodeAssignment_Utilized_AllStates_Public.zip')
    ch_COCodeStatus_ALL_csv = os.path.isfile(FilePath + 'COCodeStatus_ALL.csv')
    ch_COCodeStatus_ALL_zip = os.path.isfile(FilePath + 'COCodeStatus_ALL.zip')


    # List of files to remove
    files_to_remove = [
        'npa_report.csv',
        'CoCodeAssignment_Utilized_AllStates_Public.txt',
        'CoCodeAssignment_Utilized_AllStates_Public.zip',
        'COCodeStatus_ALL.zip',
        'COCodeStatus_ALL.csv'
    ]

    # Attempt to delete files
    for file in files_to_remove:
        file_path = os.path.join(FilePath, file)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except PermissionError:
                logger.warning("Could not delete file in use: %s", file_path)

    # download the files
    download_file(ACDownloadUrl, FilePath + 'npa_report.csv')

    download_file(ACOCDownloadUrl, FilePath + 'CoCodeAssignment_Utilized_AllStates_Public.zip')
    with ZipFile(FilePath + 'CoCodeAssignment_Utilized_AllStates_Public.zip', 'r') as zipObj:
        zipObj.extractall(FilePath)

    download_file(CanadaOCDownloadUrl, FilePath + 'COCodeStatus_ALL.zip')
    with ZipFile(FilePath + 'COCodeStatus_ALL.zip', 'r') as zipObj:
        zipObj.extractall(FilePath)


    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        ac_oc = []
        caac_oc = []

        # Drop tables from pn.db
        cur.execute("DROP TABLE IF EXISTS oc;")
        cur.execute("DROP TABLE IF EXISTS ac;")
        cur.execute("DROP TABLE IF EXISTS caoc;")
        cur.execute("DROP TABLE IF EXISTS ocn;")
        conn.commit()

        # Creates a new sqlite table 'oc' for US office-codes.
        with open(FilePath + 'CoCodeAssignment_Utilized_AllStates_Public.txt', 'r', newline='\n') as OCs:
            OC = csv.reader(OCs, delimiter='\t')
            for Row in OC:
                ac_oc.append(Row)
        # Headers need some fixing up
        oc_headers = ac_oc[0]
        oc_headers[-1] = 'InService'
        oc_fixed_headers = []
        for item in oc_headers:
            myitem = item.replace('-', '')
            myitem = myitem.replace('/', '')
            myitem = myitem.replace(' ', '')
            oc_fixed_headers.append(myitem)
        cur.execute('CREATE TABLE oc (' + oc_fixed_headers[0] + ' text, ' +
                oc_fixed_headers[1] + ' text, ' + oc_fixed_headers[2] + ' text, ' +
                oc_fixed_headers[3] + ' text, ' + oc_fixed_headers[4] + ' text, ' +
                oc_fixed_headers[5] + ' text, ' + oc_fixed_headers[6] + ' text, ' +
                oc_fixed_headers[7] + ' text, ' + oc_fixed_headers[8] + ' text, ' +
                oc_fixed_headers[9] + ' text, ' + oc_fixed_headers[10] + ' text);')
        ac_oc.pop(0)
        ac_oc = [[item.replace("'", '') for item in row] for row in ac_oc]
        ac_oc = [[item.replace('"', '') for item in row] for row in ac_oc]
        ac_oc = [[item.strip() for item in row] for row in ac_oc]
        cur.executemany("insert into oc values(?,?,?,?,?,?,?,?,?,?,?)", ac_oc)
        conn.commit()

        # Creates a new sqlite table 'ac' for North America area-codes.
        area_codes = []
        with open(FilePath + 'npa_report.csv', 'r', newline='\n') as ACs:
            AC = csv.reader(ACs, delimiter=',')
            for Row in AC:
                area_codes.append(Row)
        area_codes.pop(0)
        ac_headers = area_codes[0]
        # No need to fix these headers, but keep this filler line just in case I need to fix them in the future...
        ac_fixed_headers = ac_headers
        cur.execute('CREATE TABLE ac (' + ac_fixed_headers[0] + ' text, ' +
                ac_fixed_headers[1] + ' text, ' + ac_fixed_headers[2] + ' text, ' +
                ac_fixed_headers[3] + ' text, ' + ac_fixed_headers[4] + ' text, ' +
                ac_fixed_headers[5] + ' text, ' + ac_fixed_headers[6] + ' text, ' +
                ac_fixed_headers[7] + ' text, ' + ac_fixed_headers[8] + ' text, ' +
                ac_fixed_headers[9] + ' text, ' + ac_fixed_headers[10] + ' text, ' +
                ac_fixed_headers[11] + ' text, ' + ac_fixed_headers[12] + ' text, ' +
                ac_fixed_headers[13] + ' text, ' + ac_fixed_headers[14] + ' text, ' +
                ac_fixed_headers[15] + ' text, ' + ac_fixed_headers[16] + ' text, ' +
                ac_fixed_headers[17] + ' text, ' + ac_fixed_headers[18] + ' text, ' +
                ac_fixed_headers[19] + ' text, ' + ac_fixed_headers[20] + ' text, ' +
                ac_fixed_headers[21] + ' text, ' + ac_fixed_headers[22] + ' text, ' +
                ac_fixed_headers[23] + ' text, ' + ac_fixed_headers[24] + ' text, ' +
                ac_fixed_headers[25] + ' text, ' + ac_fixed_headers[26] + ' text, ' +
                ac_fixed_headers[27] + ' text, ' + ac_fixed_headers[28] + ' text, ' +
                ac_fixed_headers[29] + ' text, ' + ac_fixed_headers[30] + ' text, ' +
                ac_fixed_headers[31] + ' text);')
        area_codes.pop(0)  # Deletes the file date that is first entry in file
        area_codes = [[item.replace("'", '') for item in row] for row in area_codes]
        area_codes = [[item.replace('"', '') for item in row] for row in area_codes]
        area_codes = [[item.strip() for item in row] for row in area_codes]
        # some rows are missing the dialing info at the end.
        # 3 of the areacodes have an extra field that needs removed. I raised the issue with NANPA.
        for row in area_codes:
            if len(row) == 17:
                row.extend(["", "", "", "", "", "", "", "", "", "", "", "", "", "", ""])
            if len(row) == 33:
                row.pop(22)
            if len(row) != 32:
                logger.warning("Unexpected area code row shape: %s", row)
        cur.executemany("insert into ac values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        area_codes)
        conn.commit()

        # Creates a new sqlite table 'caoc' for Canada office-codes.
        with open(FilePath + 'COCodeStatus_ALL.csv', 'r', newline='\n') as CAOCs:
            CAOC = csv.reader(CAOCs, delimiter=',')
            for Row in CAOC:
                caac_oc.append(Row)
        # Headers need some fixing up
        caoc_headers = caac_oc[0]
        caoc_fixed_headers = []
        for item in caoc_headers:
            myitem = item.replace('-', '')
            myitem = myitem.replace('/', '')
            myitem = myitem.replace('(', '')
            myitem = myitem.replace(')', '')
            myitem = myitem.replace(' ', '')
            caoc_fixed_headers.append(myitem)
        cur.execute('CREATE TABLE caoc (' + caoc_fixed_headers[0] + ' text, ' +
                caoc_fixed_headers[1] + ' text, ' + caoc_fixed_headers[2] + ' text, ' +
                caoc_fixed_headers[3] + ' text, ' + caoc_fixed_headers[4] + ' text, ' +
                caoc_fixed_headers[5] + ' text, ' + caoc_fixed_headers[6] + ' text, ' +
                caoc_fixed_headers[7] + ' text, ' + caoc_fixed_headers[8] + ' text);')
        caac_oc.pop(0)
        caac_oc.pop(0)
        caac_oc = [[item.replace("'", '') for item in row] for row in caac_oc]
        caac_oc = [[item.replace('"', '') for item in row] for row in caac_oc]
        caac_oc = [[item.strip() for item in row] for row in caac_oc]
        cur.executemany("insert into caoc values(?,?,?,?,?,?,?,?,?)", caac_oc)
        conn.commit()

        # create a new OCN Company list.
        ocnlist = []
        cur.execute("select OCN, Company from oc;")
        row = cur.fetchone()
        while row:
            if row not in ocnlist and row[0] != '':
                ocnlist.append(row)
            row = cur.fetchone()
        ocnlist.sort()
        cur.execute("CREATE TABLE ocn ('OCN', 'Company')")
        cur.executemany("insert into ocn values(?,?)", ocnlist)
        conn.commit()


app = FastAPI()
templates = Jinja2Templates(directory=os.path.join(_project_root, "templates"))


@app.on_event("startup")
def startup_refresh_database() -> None:
    try:
        refresh_database()
    except Exception as exc:
        logger.exception("Database refresh failed on startup: %s", exc)


def render_template_response(request: Request, template_name: str, **context):
    return templates.TemplateResponse(template_name, {"request": request, **context})


_static_root = os.path.join(_project_root, "static")


@app.get('/')
def home(request: Request):
    return render_template_response(request, 'index.html', LinkHome=LinkHome, LinkACMaps=LinkACMaps, States=States
                           , CanadaPTAbbr=CanadaPTAbbr, USTerritory=USTerritory, Country=Country
                           , CanadaPT=CanadaPT)


@app.get('/officecodes')
def officecodes(request: Request):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()

        use = {
            'AS': 'AS indicates codes that are "ASSIGNED" to a service provider.',
            'RV': 'RV indicates codes that have been "RESERVED" by a service provider. The identity of the service provider is considered proprietary information and will not be shown.',
            'VC': 'VC indicates codes that are "VACANT"; they are available for assignment to a service provider.',
            'PR': 'PR indicates codes that are "PROTECTED" for a split; that is, these codes are assigned in the old or the new NPA and can not be assigned in the other NPA until after the end of permissive dialing.',
            'UA': 'UA indicates codes that are "UNAVAILABLE" for assignment. These codes include, but are not limited to, test and special use codes (e.g., 958, 959, 555, time), N11 and other unique codes (e.g., 976, 950), codes set aside for pooling, and codes with special dialing arrangements (e.g., 7-digit dialing cross NPA boundary).'
        }
        acoc_headers = []
        acoc_return = {}
        caoc_headers = []
        ac_headers = []
        ac_return = {}
        mapfile = ''
        state_name = ''
        state = ''
        country = ''
        RateCenter = ''
        ocn = ''
        companyname = ''

        if 'npa-nxx' in request.query_params:
            npanxx = request.query_params['npa-nxx']
            npa_code = npanxx[0:3]
            office_code = npanxx[4:7]
            if len(npanxx) == 7:
                cur.execute("PRAGMA table_info(oc);")
                row = cur.fetchall()
                for item in row:
                    acoc_headers.append(item[1])

                cur.execute("PRAGMA table_info(caoc);")
                row = cur.fetchall()
                for item in row:
                    caoc_headers.append(item[1])

                cur.execute("PRAGMA table_info(ac);")
                row = cur.fetchall()
                for item in row:
                    ac_headers.append(item[1])

                try:
                    cur.execute("select * from oc where NPANXX=?", (npanxx,))
                    acoc_tuple = cur.fetchall()
                    ocn = acoc_tuple[0][2]
                    companyname = acoc_tuple[0][3]
                    RateCenter = acoc_tuple[0][4]
                    state = acoc_tuple[0][0]
                    acoc_return = dict(zip(acoc_headers, acoc_tuple[0]))
                except Exception:
                    try:
                        cur.execute("select * from caoc where NPA=? and COCodeNXX=?", (npa_code, office_code))
                        acoc_tuple = cur.fetchall()
                        ocn = acoc_tuple[0][5]
                        companyname = acoc_tuple[0][4]
                        RateCenter = acoc_tuple[0][3]
                        state = acoc_tuple[0][0]
                        acoc_return = dict(zip(caoc_headers, acoc_tuple[0]))
                    except Exception:
                        return render_template_response(request, "error.html", LinkHome=LinkHome, error="Unable to find " + npanxx)
                try:
                    cur.execute("select * from ac where NPA_ID=?", (npa_code,))
                    ac_tuple = cur.fetchall()
                    country = ac_tuple[0][9]
                    ac_return = dict(zip(ac_headers, ac_tuple[0]))
                except Exception:
                    return render_template_response(request, "error.html", LinkHome=LinkHome, error="Unable to find " + npa_code)

                if country == 'US':
                    if state in States:
                        state_name = States[state]
                        return render_template_response(request, "ac-oc.html", LinkHome=LinkHome, ac_return=ac_return, use=use,
                                               state_name=state_name, state=state, country=country, acoc_return=acoc_return,
                                               npanxx=npanxx, npa_code=npa_code, myurl=myurl,
                                               USACMapFilePath=USACMapFilePath,
                                               StateFilePath=StateFilePath, RateCenter=RateCenter, ocn=ocn,
                                               companyname=companyname)
                    if state == 'VI':
                        state = 'USVI'
                    if state == 'NN':
                        state = 'CNMI'
                    if state in USTerritory:
                        if state == 'PR':
                            state_name = USTerritory[state]
                            mapfile = 'Puerto_Rico_787_939.gif'
                        if state == 'AS':
                            state_name = USTerritory[state]
                            mapfile = 'American_Samoa_684.gif'
                        if state == 'GU':
                            state_name = USTerritory[state]
                            mapfile = 'Guam_671.gif'
                        if state == 'CNMI':
                            state_name = USTerritory[state]
                            mapfile = 'Northern_Marianna_Islands_670.gif'
                        if state == 'USVI':
                            state_name = USTerritory[state]
                            mapfile = 'US_Virgin_Islands_340.gif'
                        return render_template_response(request, "territory-ac-oc.html", LinkHome=LinkHome, ac_tuple=ac_tuple, npanxx=npanxx
                                               , ac_return=ac_return, state_name=state_name, state=state, country=country
                                               , npa_code=npa_code, myurl=myurl, acoc_return=acoc_return
                                               , USTerritoryFilePath=USTerritoryFilePath, mapfile=mapfile
                                               , RateCenter=RateCenter, use=use, ocn=ocn, companyname=companyname)
                if country == 'CANADA':
                    state_name = ac_tuple[0][8]
                    state = CanadaPT[state_name]
                    if state_name == 'QUEBEC':
                        mapfile = 'qc-s.png'
                    if state_name == 'BRITISH COLUMBIA':
                        mapfile = 'bc-s.png'
                    if state_name == 'ONTARIO':
                        mapfile = 'on-s.png'
                    return render_template_response(request, "canada-ac-oc.html", LinkHome=LinkHome, ac_return=ac_return,
                                           companyname=companyname,
                                           state_name=state_name, state=state, country=country, acoc_return=acoc_return,
                                           npanxx=npanxx, npa_code=npa_code, myurl=myurl, CanadaFilePath=CanadaFilePath,
                                           mapfile=mapfile, RateCenter=RateCenter, ocn=ocn)
            return render_template_response(request, "error.html", LinkHome=LinkHome, error="Unable to find... " + npanxx)
        return render_template_response(request, "error.html", LinkHome=LinkHome, error='URL is not correct.')


@app.get('/compstate')
def compstate(request: Request):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()

        cs_list = []
        state = ''

        if 'cs' in request.query_params:
            state = request.query_params['cs']
        try:
            cur.execute("select distinct OCN, Company from oc where State=? order by Company", (state,))
            row = cur.fetchall()
            for each in row:
                cs_list.append(each)
            return render_template_response(request, "cs.html", LinkHome=LinkHome, myurl=myurl, cs_list=cs_list, state=state)
        except Exception as exc:
            logger.exception("Failed compstate lookup: %s", exc)
            return render_template_response(request, "error.html", LinkHome=LinkHome, error="Unable to find ")


@app.get('/rcstate')
def rcstate(request: Request):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()

        rcs_list = []
        state = ''

        if 'rcs' in request.query_params:
            state = request.query_params['rcs']
        try:
            cur.execute("select distinct RateCenter from oc where State=? order by RateCenter", (state,))
            row = cur.fetchall()
            for each in row:
                rcs_list.append(each[0])
            return render_template_response(request, "rcs.html", LinkHome=LinkHome, myurl=myurl, rcs_list=rcs_list, state=state)
        except Exception as exc:
            logger.exception("Failed rcstate lookup: %s", exc)
            return render_template_response(request, "error.html", LinkHome=LinkHome, error="Unable to find ")


@app.get('/ratecenter')
def ratecenter(request: Request):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()

        acoc_headers = []
        ac_oc_list = []
        ac_oc_companylist = []
        acoc_return = {}
        ac_headers = []
        ac_return = {}
        mapfile = ''
        state_name = ''
        country = ''
        RateCenter = ''

        if 'rc' in request.query_params and 'state' in request.query_params and 'country' in request.query_params:
            RateCenter = request.query_params['rc']
            state = request.query_params['state']
            country = request.query_params['country']

            if country == 'US':
                if state == 'PUERTO RICO':
                    state = 'PR'
                if state == 'USVI':
                    state = 'VI'
                if state == 'CNMI':
                    state = 'NN'
                try:
                    cur.execute("select NPANXX, Company from oc where RateCenter=? and State=? order by NPANXX", (RateCenter, state))
                    row = cur.fetchone()
                    while row:
                        ac_oc_list.append(row)
                        row = cur.fetchone()
                    cur.execute("select NPANXX, Company from oc where RateCenter=? and State=? order by Company,NPANXX", (RateCenter, state))
                    row = cur.fetchone()
                    while row:
                        ac_oc_companylist.append(row)
                        row = cur.fetchone()
                    return render_template_response(request, "rc.html", LinkHome=LinkHome, myurl=myurl, RateCenter=RateCenter
                                           , ac_oc_list=ac_oc_list, ac_oc_companylist=ac_oc_companylist, state=state)
                except Exception as exc:
                    logger.exception("Failed US ratecenter lookup: %s", exc)
                    return render_template_response(request, "error.html", LinkHome=LinkHome, error="Unable to find " + RateCenter)
            if country == 'CANADA':
                try:
                    cur.execute("select NPA, COCodeNXX, Company from caoc where RateCenter=? order by NPA, COCodeNXX", (RateCenter,))
                    row = cur.fetchone()
                    while row:
                        ac_oc_list.append(row)
                        row = cur.fetchone()
                    cur.execute("select NPA, COCodeNXX, Company from caoc where RateCenter=? order by Company, NPA, COCodeNXX", (RateCenter,))
                    row = cur.fetchone()
                    while row:
                        ac_oc_companylist.append(row)
                        row = cur.fetchone()
                    return render_template_response(request, "carc.html", LinkHome=LinkHome, myurl=myurl, RateCenter=RateCenter
                                           , ac_oc_list=ac_oc_list, ac_oc_companylist=ac_oc_companylist, state=state)
                except Exception as exc:
                    logger.exception("Failed Canada ratecenter lookup: %s", exc)
                    return render_template_response(request, "error.html", LinkHome=LinkHome, error="Unable to find " + RateCenter)
        return render_template_response(request, "error.html", LinkHome=LinkHome, error='URL is not correct.')


@app.get('/company')
def company(request: Request):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()

        acoc_headers = []
        ac_oc_list = []
        ac_oc_rclist = []
        acoc_return = {}
        ac_headers = []
        ac_return = {}
        mapfile = ''
        state_name = ''
        country = ''
        ocn = ''
        companyname = ''

        if 'ocn' in request.query_params:
            ocn = request.query_params['ocn']
            companyname = request.query_params['companyname']
            country = request.query_params['country']
            state = request.query_params['state']
            if country == 'US':
                if state == 'PUERTO RICO':
                    state = 'PR'
                if state == 'USVI':
                    state = 'VI'
                if state == 'CNMI':
                    state = 'NN'
                try:
                    cur.execute("select NPANXX, RateCenter from oc where OCN=? and State=?", (ocn, state))
                    row = cur.fetchone()
                    while row:
                        ac_oc_list.append(row)
                        row = cur.fetchone()

                    cur.execute("select NPANXX, RateCenter from oc where OCN=? and State=? order by RateCenter, NPANXX", (ocn, state))
                    row = cur.fetchone()
                    while row:
                        ac_oc_rclist.append(row)
                        row = cur.fetchone()
                    return render_template_response(request, "company.html", LinkHome=LinkHome, myurl=myurl, ocn=ocn
                                           , ac_oc_list=ac_oc_list, companyname=companyname, state=state
                                           , ac_oc_rclist=ac_oc_rclist)
                except Exception as exc:
                    logger.exception("Failed US company lookup: %s", exc)
                    return render_template_response(request, "error.html", LinkHome=LinkHome, error="Unable to find " + ocn)
            if country == 'CANADA':
                try:
                    cur.execute("select NPA, COCodeNXX, RateCenter from caoc where OCN=? order by NPA, COCodeNXX", (ocn,))
                    row = cur.fetchone()
                    while row:
                        ac_oc_list.append(row)
                        row = cur.fetchone()
                    cur.execute("select NPA, COCodeNXX, RateCenter from caoc where OCN=? order by RateCenter, NPA, COCodeNXX", (ocn,))
                    row = cur.fetchone()
                    while row:
                        ac_oc_rclist.append(row)
                        row = cur.fetchone()
                    return render_template_response(request, "ca-company.html", LinkHome=LinkHome, myurl=myurl, ocn=ocn
                                           , state=state, ac_oc_list=ac_oc_list, ac_oc_rclist=ac_oc_rclist
                                           , companyname=companyname)
                except Exception as exc:
                    logger.exception("Failed Canada company lookup: %s", exc)
                    return render_template_response(request, "error.html", LinkHome=LinkHome, error="Unable to find " + ocn)
        return render_template_response(request, "error.html", LinkHome=LinkHome, error='URL is not correct.')


@app.get('/ocnall')
def companyall(request: Request):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()

        ocnall_list = []
        try:
            cur.execute(
                "select Company, OCN, State from oc where Company is not '' and OCN is not '' order by Company, State")
            row = cur.fetchone()
            while row:
                if row not in ocnall_list:
                    ocnall_list.append(row)
                row = cur.fetchone()
            return render_template_response(request, "ocn-all.html", LinkHome=LinkHome, myurl=myurl, ocnall_list=ocnall_list)
        except Exception as exc:
            logger.exception("Failed OCN all lookup: %s", exc)
            return render_template_response(request, "error.html", LinkHome=LinkHome, error="Unable to find OCN")


@app.get('/ocn')
def ocn(request: Request):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()

        ac_oc_list = []
        ac_oc_rclist = []
        ac_oc_stlist = []

        if 'ocn' in request.query_params:
            ocn = request.query_params['ocn'].upper()
            try:
                cur.execute("select Company from oc where OCN=?", (ocn,))
                row = cur.fetchone()
                companyname = str(row[0])
            except Exception as exc:
                logger.exception("Failed OCN company lookup: %s", exc)
                return render_template_response(request, "error.html", LinkHome=LinkHome, error="Unable to find " + ocn)
            try:
                cur.execute("select NPANXX, State, RateCenter from oc where OCN=? order by NPANXX", (ocn,))
                row = cur.fetchone()
                while row:
                    ac_oc_list.append(row)
                    row = cur.fetchone()

                cur.execute("select NPANXX, RateCenter, State from oc where OCN=? order by State, RateCenter, NPANXX", (ocn,))
                row = cur.fetchone()
                while row:
                    ac_oc_rclist.append(row)
                    row = cur.fetchone()

                cur.execute("select NPANXX, State, RateCenter from oc where OCN=? order by State, NPANXX", (ocn,))
                row = cur.fetchone()
                while row:
                    ac_oc_stlist.append(row)
                    row = cur.fetchone()

                return render_template_response(request, "ocn.html", LinkHome=LinkHome, myurl=myurl, ocn=ocn
                                       , ac_oc_list=ac_oc_list, companyname=companyname
                                       , ac_oc_rclist=ac_oc_rclist, ac_oc_stlist=ac_oc_stlist)
            except Exception as exc:
                logger.exception("Failed OCN lookup: %s", exc)
                return render_template_response(request, "error.html", LinkHome=LinkHome, error="Unable to find " + ocn)
        return render_template_response(request, "error.html", LinkHome=LinkHome, error='URL is not correct.')


@app.get('/canadaocnall')
def canadaocnall(request: Request):
    caoc_headers = []
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()

        ocnall_list = []

        cur.execute("PRAGMA table_info(caoc);")
        row = cur.fetchall()
        for item in row:
            caoc_headers.append(item[1])

        if request.query_params['sort'] == 'company':
            header = ['Company', 'OCN', 'Province']
            try:
                cur.execute("select distinct Company, OCN, Province from caoc "
                            "Where Company is not '' and OCN is not '' and Province is not '' "
                            "order by Company, Province, OCN")
                row = cur.fetchone()
                while row:
                    ocnall_list.append(row)
                    row = cur.fetchone()
                return render_template_response(request, "ca-ocn-all.html", LinkHome=LinkHome, header=header, ocnall_list=ocnall_list,
                                       caoc_headers=caoc_headers)
            except Exception as exc:
                logger.exception("Failed canada OCN all by company: %s", exc)
                return render_template_response(request, "error.html", LinkHome=LinkHome, error="Unable to find OCN")
        if request.query_params['sort'] == 'ocn':
            header = ['OCN', 'Company']
            try:
                cur.execute("select distinct OCN, Company from caoc "
                            "Where Company is not '' and OCN is not '' "
                            "order by OCN, Company")
                row = cur.fetchone()
                while row:
                    ocnall_list.append(row)
                    row = cur.fetchone()
                return render_template_response(request, "ca-ocn-all.html", LinkHome=LinkHome, header=header, ocnall_list=ocnall_list,
                                       caoc_headers=caoc_headers)
            except Exception as exc:
                logger.exception("Failed canada OCN all by OCN: %s", exc)
                return render_template_response(request, "error.html", LinkHome=LinkHome, error="Unable to find OCN")


@app.get('/canadaexall')
def canadaexall(request: Request):
    caoc_headers = []
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()

        ocnall_list = []

        cur.execute("PRAGMA table_info(caoc);")
        row = cur.fetchall()
        for item in row:
            caoc_headers.append(item[1])

        if request.query_params['sort'] == 'npa':
            header = ['ExchangeArea', 'NPA', 'COCodesNXX', 'Company', 'OCN', 'Status', 'Remarks']
            try:
                cur.execute("select ExchangeArea, NPA, COCodeNXX, Company, OCN, Status, Remarks from caoc "
                            "where Company is not '' and OCN is not '' "
                            "order by ExchangeArea, NPA, COCodeNXX, Company, OCN, Status")
                row = cur.fetchone()
                while row:
                    ocnall_list.append(row)
                    row = cur.fetchone()
                return render_template_response(request, "ca-ex-all.html", LinkHome=LinkHome, header=header, ocnall_list=ocnall_list,
                                       caoc_headers=caoc_headers)
            except Exception as exc:
                logger.exception("Failed canada exchange all by NPA: %s", exc)
                return render_template_response(request, "error.html", LinkHome=LinkHome, error="Unable to find OCN")
        if request.query_params['sort'] == 'company':
            header = ['ExchangeArea', 'Company', 'OCN', 'NPA', 'COCodesNXX', 'Status', 'Remarks']
            try:
                cur.execute("select ExchangeArea, Company, OCN, NPA, COCodeNXX, Status, Remarks from caoc "
                            "where Company is not '' and OCN is not '' "
                            "order by ExchangeArea, Company, OCN, NPA, COCodeNXX, Status")
                row = cur.fetchone()
                while row:
                    ocnall_list.append(row)
                    row = cur.fetchone()
                return render_template_response(request, "ca-ex-all.html", LinkHome=LinkHome, header=header, ocnall_list=ocnall_list,
                                       caoc_headers=caoc_headers)
            except Exception as exc:
                logger.exception("Failed canada exchange all by company: %s", exc)
                return render_template_response(request, "error.html", LinkHome=LinkHome, error="Unable to find OCN")


@app.get('/areacodes')
def areacodes(request: Request):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()

        ac_tuple = ()
        ac_headers = []
        ac_oc_list = []
        acoclist_as = []
        acoclist_rv = []
        acoclist_vc = []
        acoclist_pr = []
        acoclist_ua = []
        acoclist_inservice = []
        acoclist_forspecialuse = []
        acoclist_notavailable = []
        acoclist_other = []
        statuslist = []
        officecodelist = []

        ac_return = {}
        ac_oc_dict = {}

        state_name = ''
        state = ''
        country = ''
        mapfile = ''

        if 'npa' in request.query_params and len(request.query_params['npa']) == 3:
            npa_code = request.query_params['npa']
            npanxx = str(npa_code) + '-'

            cur.execute("PRAGMA table_info(ac);")
            row = cur.fetchall()
            for item in row:
                ac_headers.append(item[1])
            try:
                cur.execute("select * from ac where NPA_ID=?", (npa_code,))
                ac_tuple = cur.fetchall()
                state = ac_tuple[0][8]
                country = ac_tuple[0][9]
                ac_return = dict(zip(ac_headers, ac_tuple[0]))
            except Exception as exc:
                logger.exception("Failed areacode lookup: %s", exc)
                return render_template_response(request, "error.html", LinkHome=LinkHome, error="Unable to find " + npa_code)

            if country == 'US':
                cur.execute("select distinct Use from oc where NPANXX like ? order by Use;", (npanxx + '%',))
                row = cur.fetchall()
                for each in row:
                    statuslist.append(each[0])
                for item in statuslist:
                    cur.execute("select NPANXX from oc where NPANXX like ? and Use=? order by NPANXX;", (npanxx + '%', item))
                    row = cur.fetchall()
                    for items in row:
                        officecodelist.append(items[0][-3:])
                    ac_oc_dict[item] = officecodelist
                    officecodelist = []

                if state in States:
                    state_name = States[state]
                    return render_template_response(request, "ac.html", LinkHome=LinkHome, ac_tuple=ac_tuple, ac_return=ac_return
                                           , ac_oc_list=ac_oc_list, state_name=state_name, npa_code=npa_code, myurl=myurl
                                           , USACMapFilePath=USACMapFilePath, StateFilePath=StateFilePath
                                           , ac_oc_dict=ac_oc_dict)
                if state in USTerritory:
                    if state == 'PR':
                        state_name = USTerritory[state]
                        mapfile = 'Puerto_Rico_787_939.gif'
                    if state == 'AS':
                        state_name = USTerritory[state]
                        mapfile = 'American_Samoa_684.gif'
                    if state == 'GU':
                        state_name = USTerritory[state]
                        mapfile = 'Guam_671.gif'
                    if state == 'CNMI':
                        state_name = USTerritory[state]
                        mapfile = 'Northern_Marianna_Islands_670.gif'
                    if state == 'USVI':
                        state_name = USTerritory[state]
                        mapfile = 'US_Virgin_Islands_340.gif'
                    return render_template_response(request, "territory-ac.html", LinkHome=LinkHome, ac_tuple=ac_tuple, ac_return=ac_return
                                           , state_name=state_name, npa_code=npa_code, myurl=myurl, ac_oc_list=ac_oc_list
                                           , USTerritoryFilePath=USTerritoryFilePath, mapfile=mapfile
                                           , ac_oc_dict=ac_oc_dict)
            if country == 'CANADA':
                cur.execute("select distinct Status from caoc where NPA=? order by Status;", (npa_code,))
                row = cur.fetchall()
                for each in row:
                    statuslist.append(each[0])
                for item in statuslist:
                    cur.execute("select COCodeNXX from caoc where NPA=? and Status=? order by COCodeNXX;", (npa_code, item))
                    row = cur.fetchall()
                    for items in row:
                        officecodelist.append(items[0])
                    ac_oc_dict[item] = officecodelist
                    officecodelist = []

                if state == 'QUEBEC':
                    state_name = 'QUEBEC'
                    mapfile = 'qc-s.png'
                if state == 'BRITISH COLUMBIA':
                    state_name = 'BRITISH COLUMBIA'
                    mapfile = 'bc-s.png'
                if state == 'ONTARIO':
                    state_name = 'ONTARIO'
                    mapfile = 'on-s.png'
                state = CanadaPT[state]
                return render_template_response(request, "canada-ac.html", LinkHome=LinkHome, ac_tuple=ac_tuple, ac_return=ac_return
                                       , state_name=state_name, state=state, npa_code=npa_code, myurl=myurl
                                       , CanadaFilePath=CanadaFilePath, mapfile=mapfile, ac_oc_dict=ac_oc_dict)

            mapfile = ''
            if state == 'JAMAICA':
                state_name = 'JAMAICA'
                mapfile = 'Jamaica_876.gif'
            if state == 'BAHAMAS':
                state_name = 'BAHAMAS'
                mapfile = 'Bahamas_242.gif'
            if state == 'BARBADOS':
                state_name = 'BARBADOS'
                mapfile = 'Barbados_246.gif'
            if state == 'ANGUILLA':
                mapfile = 'Anguilla_264.gif'
            if state == 'ANTIGUA/BARBUDA':
                state_name = 'ANTIGUA/BARBUDA'
                mapfile = 'Antigua_and_Barbuda_268.gif'
            if state == 'BRITISH VIRGIN ISLANDS':
                state_name = 'BRITISH VIRGIN ISLANDS'
                mapfile = 'British_Virgin_Islands_284.gif'
            if state == 'CAYMAN ISLANDS':
                state_name = 'CAYMAN ISLANDS'
                mapfile = 'Cayman_Islands_345.gif'
            if state == 'BERMUDA':
                state_name = 'BERMUDA'
                mapfile = 'Bermuda_441.gif'
            if state == 'GRENADA':
                state_name = 'GRENADA'
                mapfile = 'Grenada_473.gif'
            if 'TURKS' in state:
                state_name = 'TURKS'
                mapfile = 'Turks_and_Caicos_Islands_649.gif'
            if state == 'MONTSERRAT':
                state_name = 'MONTSERRAT'
                mapfile = 'Montserrat_664.gif'
            if state == 'SINT MAARTEN':
                state_name = 'SINT MAARTEN'
                mapfile = 'Sint_Maarten_721.gif'
            if 'ST. LUCIA' in state:
                state_name = 'Saint Lucia'
                mapfile = 'Saint_Lucia_758.gif'
            if state == 'DOMINICA':
                state_name = 'DOMINICA'
                mapfile = 'Dominica_767.gif'
            if 'VINCENT' in state:
                state_name = 'Saint Vincent and The Grenadines'
                mapfile = 'Saint_Vincent_and_The_Grenadines_784.gif'
            if state == 'DOMINICAN REPUBLIC':
                state_name = 'Dominican Republic'
                mapfile = 'Dominican_Republic_809_829_849.gif'
            if 'TRINIDAD' in state:
                state_name = 'Trinidad and Tobago'
                mapfile = 'Trinidad_and_Tobago_868.gif'
            if 'ST. KITTS' in state:
                state_name = 'Saint Kitts and Nevis'
                mapfile = 'Saint_Kitts_and_Nevis_869.gif'
            return render_template_response(request, "country-ac.html", LinkHome=LinkHome, ac_tuple=ac_tuple, ac_return=ac_return
                                   , state_name=state_name, npa_code=npa_code, myurl=myurl
                                   , CountryFilePath=CountryFilePath, mapfile=mapfile)
        return render_template_response(request, "error.html", LinkHome=LinkHome, error='URL is not correct')


@app.get('/aclist')
def aclist(request: Request):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        try:
            cur.execute("select NPA_ID, type_of_code, location, country, assigned, reserved, in_service"
                        " from ac order by NPA_ID")
            row = cur.fetchone()
            ac_list_assigned = []
            ac_list_unassigned = []
            ac_list_reserved = []
            if row is not None:
                while row:
                    list_row = list(row)
                    if list_row[4] == "Yes":
                        acla = dict(zip(['NPA_ID', 'type_of_code', 'location', 'country'], row))
                        ac_list_assigned.append(acla)
                    elif list_row[5] == 'Yes':
                        aclr = dict(zip(['NPA_ID', 'type_of_code', 'location', 'country'], row))
                        ac_list_reserved.append(aclr)
                    else:
                        aclu = dict(zip(['NPA_ID', 'type_of_code', 'location', 'country'], row))
                        ac_list_unassigned.append(aclu)
                    row = cur.fetchone()
            return render_template_response(request, "aclist-npa.html", LinkHome=LinkHome, myurl=myurl, ac_list_assigned=ac_list_assigned
                                   , ac_list_reserved=ac_list_reserved, ac_list_unassigned=ac_list_unassigned)
        except Exception as exc:
            logger.exception("Failed area code list lookup: %s", exc)
            return render_template_response(request, "error.html", LinkHome=LinkHome, error='Error getting the list of NPAs.')


@app.get('/acmaps')
def acmaps(request: Request):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()

        mapfile = ''
        statename = ''
        if 'state' in request.query_params:
            state = str(request.query_params['state']).upper()
            StateACs = []
            if state in States:
                cur.execute("select NPA_ID from ac where LOCATION=?", (state,))
                row = cur.fetchone()
                while row:
                    row = str(row).replace('(', '')
                    row = str(row).replace(')', '')
                    row = str(row).replace('[', '')
                    row = str(row).replace(']', '')
                    row = str(row).replace(',', '')
                    row = str(row).replace("'", '')
                    StateACs.append(row)
                    row = cur.fetchone()
                statename = States[state]
                return render_template_response(request, "maps.html", LinkHome=LinkHome, statename=statename, StateACs=StateACs, state=state
                                       , USACMapFilePath=USACMapFilePath, StateFilePath=StateFilePath)
            elif state in CanadaPT:
                cur.execute("select NPA_ID from ac where LOCATION=?", (state,))
                row = cur.fetchone()
                while row:
                    row = str(row).replace('(', '')
                    row = str(row).replace(')', '')
                    row = str(row).replace('[', '')
                    row = str(row).replace(']', '')
                    row = str(row).replace(',', '')
                    row = str(row).replace("'", '')
                    StateACs.append(row)
                    row = cur.fetchone()
                statename = CanadaPT[state]
                if state == 'BRITISH COLUMBIA':
                    mapfile = 'bc-s.png'
                elif state == 'ONTARIO':
                    mapfile = 'on-s.png'
                elif state == 'QUEBEC':
                    mapfile = 'qc-s.png'
                return render_template_response(request, "canada-maps.html", LinkHome=LinkHome, statename=statename
                                       , StateACs=StateACs, state=state, CanadaFilePath=CanadaFilePath
                                       , mapfile=mapfile)
            elif state in USTerritory:
                cur.execute("select NPA_ID from ac where LOCATION=?", (state,))
                row = cur.fetchone()
                while row:
                    row = str(row).replace('(', '')
                    row = str(row).replace(')', '')
                    row = str(row).replace('[', '')
                    row = str(row).replace(']', '')
                    row = str(row).replace(',', '')
                    row = str(row).replace("'", '')
                    StateACs.append(row)
                    row = cur.fetchone()
                statename = USTerritory[state]
                if state == 'AS':
                    mapfile = 'American_Samoa_684.gif'
                if state == 'GU':
                    mapfile = 'Guam_671.gif'
                if state == 'PR':
                    mapfile = 'Puerto_Rico_787_939.gif'
                if state == 'USVI':
                    mapfile = 'US_Virgin_Islands_340.gif'
                if state == 'CNMI':
                    mapfile = 'Northern_Marianna_Islands_670.gif'
                return render_template_response(request, "territory-maps.html", LinkHome=LinkHome, statename=statename
                                       , StateACs=StateACs, state=state, USTerritoryFilePath=USTerritoryFilePath
                                       , mapfile=mapfile)
            # Dominica needs seperated out so it doesn't capture DOMINICAN REPUBLIC ACs.
            elif state == 'DOMINICA':
                cur.execute("select NPA_ID from ac where LOCATION=?", ("DOMINICA",))
                row = cur.fetchone()
                while row:
                    row = str(row).replace('(', '')
                    row = str(row).replace(')', '')
                    row = str(row).replace('[', '')
                    row = str(row).replace(']', '')
                    row = str(row).replace(',', '')
                    row = str(row).replace("'", '')
                    StateACs.append(row)
                    row = cur.fetchone()
                mapfile = 'Dominica_767.gif'
                return render_template_response(request, "country-maps.html", LinkHome=LinkHome
                                       , StateACs=StateACs, state=state, CountryFilePath=CountryFilePath, mapfile=mapfile)
            else:
                cur.execute("select NPA_ID from ac where LOCATION Like ?", ('%' + state + '%',))
                row = cur.fetchone()
                while row:
                    row = str(row).replace('(', '')
                    row = str(row).replace(')', '')
                    row = str(row).replace('[', '')
                    row = str(row).replace(']', '')
                    row = str(row).replace(',', '')
                    row = str(row).replace("'", '')
                    StateACs.append(row)
                    row = cur.fetchone()
                if state == 'JAMAICA':
                    mapfile = 'Jamaica_876.gif'
                if state == 'BAHAMAS':
                    mapfile = 'Bahamas_242.gif'
                if state == 'BARBADOS':
                    mapfile = 'Barbados_246.gif'
                if state == 'ANGUILLA':
                    mapfile = 'Anguilla_264.gif'
                if state == 'ANTIGUA/BARBUDA':
                    mapfile = 'Antigua_and_Barbuda_268.gif'
                if state == 'BRITISH VIRGIN ISLANDS':
                    mapfile = 'British_Virgin_Islands_284.gif'
                if state == 'CAYMAN ISLANDS':
                    mapfile = 'Cayman_Islands_345.gif'
                if state == 'BERMUDA':
                    mapfile = 'Bermuda_441.gif'
                if state == 'GRENADA':
                    mapfile = 'Grenada_473.gif'
                if 'TURKS' in state:
                    mapfile = 'Turks_and_Caicos_Islands_649.gif'
                if state == 'MONTSERRAT':
                    mapfile = 'Montserrat_664.gif'
                if state == 'SINT MAARTEN':
                    mapfile = 'Sint_Maarten_721.gif'
                if 'ST. LUCIA' in state:
                    mapfile = 'Saint_Lucia_758.gif'
                if state == 'DOMINICA':
                    mapfile = 'Dominica_767.gif'
                if 'VINCENT' in state:
                    mapfile = 'Saint_Vincent_and_The_Grenadines_784.gif'
                if state == 'DOMINICAN REPUBLIC':
                    mapfile = 'Dominican_Republic_809_829_849.gif'
                if 'TRINIDAD' in state:
                    mapfile = 'Trinidad_and_Tobago_868.gif'
                if 'ST. KITTS' in state:
                    mapfile = 'Saint_Kitts_and_Nevis_869.gif'
                return render_template_response(request, "country-maps.html", LinkHome=LinkHome
                                       , StateACs=StateACs, state=state, CountryFilePath=CountryFilePath, mapfile=mapfile)
        else:
            return render_template_response(request, "error.html", LinkHome=LinkHome, error='The URL appears to be incorrect.')


app.mount("/NANPA", StaticFiles(directory=os.path.join(_static_root, "NANPA")), name="static_nanpa")
app.mount("/USACMaps", StaticFiles(directory=os.path.join(_static_root, "USACMaps")), name="static_usacmaps")
app.mount("/USStateMaps", StaticFiles(directory=os.path.join(_static_root, "USStateMaps")), name="static_usstatemaps")
app.mount("/USTerritoryACMaps", StaticFiles(directory=os.path.join(_static_root, "USTerritoryACMaps")), name="static_usterritory")
app.mount("/CanadaACMaps", StaticFiles(directory=os.path.join(_static_root, "CanadaACMaps")), name="static_canada")
app.mount("/CountryACMaps", StaticFiles(directory=os.path.join(_static_root, "CountryACMaps")), name="static_country")


if __name__ == "__main__":
    uvicorn.run(app, host=myip, port=myport)

