import requests
from fake_useragent import UserAgent
import config
import csv
import time
import random
from bs4 import BeautifulSoup

# Here I provide some proxies for not getting caught while scraping
ua = UserAgent() # From here we generate a random user agent
proxies = [] # Will contain proxies [ip, port]


# Retrieve a random index proxy (we need the index to delete it if not working)
def random_proxy():
    return random.randint(0, len(proxies) - 1)


def setProxies():
    headers = {
            'User-Agent': ua.random
        }
    proxies_req = requests.request('GET','https://www.sslproxies.org/', headers=headers)
    proxies_doc = proxies_req.text
      
    soup = BeautifulSoup(proxies_doc, 'html.parser')
    proxies_table = soup.find(id='proxylisttable')
    
    print('Got full table data for proxies')
      
    # Save proxies in the array
    for row in proxies_table.tbody.find_all('tr'):
        ip = row.find_all('td')[0].string
        port = row.find_all('td')[1].string
        proxy = {
            'https': 'https://' + ip + ':' + port,
            'http': 'http://' + ip + ':' + port,            
        }
        try:
            requests.get('https://httpbin.org/ip', proxies=proxy, timeout=5)
            proxies.append({
                'ip':   row.find_all('td')[0].string,
                'port': row.find_all('td')[1].string
                })
            print('Validated proxy '+ proxy['https'])
        except:
            print('Proxy not valid '+ proxy['https'])
    


def getSession(useProxy=True):
    if useProxy:
        # Choose a random proxy
        proxy_index = random_proxy()
        proxy = proxies[proxy_index]
        proxy = {
                'https': 'https://' + proxy['ip'] + ':' + proxy['port'],
                'http': 'http://' + proxy['ip'] + ':' + proxy['port'],            
            }
    else:
        proxy = {}
    user_agent = ua.random
    sess = requests.Session()
    sess.proxies = proxy
    sess.headers['User-Agent'] = user_agent
    
    auth_url = "https://api.bniconnectglobal.com/auth-api/authenticate"
    auth_payload = '''{{
        "client_id":"IDENTITY_PORTAL",
        "user_id":"{user}",
        "password":"{pwd}"
    }}'''.format(user=config.USER, pwd=config.PASSWORD)
    
    auth_headers = {
     'authorization': 'Basic SURFTlRJVFlfUE9SVEFMOkdjVlN2JE1vODk1d0I2XjRTNA==',
     'Content-Type': 'application/json'
    }
    

    try:
        if useProxy:
            print('Try Connecting to BNI using Proxy '+ proxy['https'])
        else:
            print('Try Connecting to BNI without using Proxy')
        response = sess.request("POST", auth_url, headers=auth_headers, data=auth_payload)
        token = response.json()
    except:
        print('Error Connecting to BNI. Trying different Proxy!')
        if useProxy:
            del proxies[proxy_index]
            print('Proxy ' + proxy['https'] + ' deleted.')
        return getSession(useProxy)
        
    
    cookie_url = "https://www.bniconnectglobal.com/web/j_spring_security_jwt_check"
    
    cookie_payload = 'j_refresh='+token['content']['refresh_token']+'&j_access='+token[
            'content']['access_token']+'&j_expiry='+str(token['content'][
            'expires_in'])+'&j_username='+config.USER+'&j_password='+config.PASSWORD
    form_headers = {
      'Content-Type': 'application/x-www-form-urlencoded'
    }
    try:
        if useProxy:
            print('Getting Cookies using Proxy '+ proxy['https'])
        else:
            print('Getting Cookies without using Proxy')
        response = sess.request("POST", cookie_url, headers=form_headers, data=cookie_payload)
    except:
        print('Error Connecting to BNI. Trying different Proxy!')
        if useProxy:
            del proxies[proxy_index]
            print('Proxy ' + proxy['https'] + ' deleted.')
        return getSession(useProxy)
    
    return sess
    
def getSearchUsers(session):
    result_url = "https://www.bniconnectglobal.com/web/secure/networkAddConnectionsJson"
    result_payload = 'searchMembers=Search+Members&formSubmit=true&memberKeywords='+config.SEARCH_KEYWORD+\
        '&memberFirstName='+config.FIRST_NAME+'&memberLastName='+config.LAST_NAME+'&memberCompanyName='\
            +config.COMPANY_NAME+'&memberIdCountry='+str(config.COUNTRY_ID)+'&memberCity='+config.CITY+'&memberState='+config.STATE
    form_headers = {
      'Content-Type': 'application/x-www-form-urlencoded'
    }
    response = session.request("POST", result_url,headers=form_headers,data =result_payload)

    result = response.json()
        
    soup = BeautifulSoup(result['aaData'][0], 'lxml')
    
    user_ids = []
    
    for user in soup.findAll('a', class_='link'):
        user_ids.append(user.attrs['href'].split('?')[-1].split('=')[-1])
        
    return user_ids

def getUserIdDetails(session, csv_writer, user_id):
    user_url = 'https://www.bniconnectglobal.com/web/secure/networkProfile?userId='+ user_id
    response = session.request("GET", user_url)
    
    soup = BeautifulSoup(response.text, 'lxml')    
    user_details = soup.find('div', class_='networkhometabs')
    
    if not user_details:
        print('\nRequest time-out! Sleeping for 10 sec')
        time.sleep(10)
        print('Getting new Session')
        session = getSession(useProxy=False)
        return getUserIdDetails(session, csv_writer, user_id)
        
    
    if user_details:
        name = user_details.find('label', {'for': 'memberDisplayName'})
        name = name.find('span', class_='fieldtext').text if name else ''
        prof = user_details.find('label', {'for': 'memberPrimaryCategory'})
        prof = prof.find('span', class_='fieldtext').text if prof else ''
        desc = user_details.find('label', {'for': 'memberPersonalStatementMemoryHook'})
        desc = desc.find('span', class_='fieldtext').text if desc else ''
        comp = user_details.find('label', {'for': 'memberCompanyName'})
        comp = comp.find('span', class_='fieldtext').text if comp else ''
        ph = user_details.find('label', {'for': 'memberPhoneNumber'})
        ph = ph.find('span', class_='fieldtext').text if ph else ''
        dn = user_details.find('label', {'for': 'personDirectNumber'})
        dn = dn.find('span', class_='fieldtext').text if dn else ''
        mob = user_details.find('label', {'for': 'memberMobileNumber'})
        mob = mob.find('span', class_='fieldtext').text if mob else ''
        email = user_details.find('label', {'for': 'memberEmail'})
        email = email.find('span', class_='fieldtext').text if email else ''
        site = user_details.find('label', {'for': 'memberWebsite'})
        site = site.find('span', class_='fieldtext').text if site else ''
        soc = user_details.find('label', {'for': 'memberSocialNetworkingLinks'})
        soc = soc.find('span', class_='fieldtext').text if soc else ''
        add = user_details.find('label', {'for': 'memberAddressLine1'})
        add = add.find('span', class_='fieldtext').text if add else ''
        city = user_details.find('label', {'for': 'memberCity'})
        city = city.find('span', class_='fieldtext').text if city else ''
        state = user_details.find('label', {'for': 'memberState'})
        state = state.find('span', class_='fieldtext').text if state else ''
        country = user_details.find('label', {'for': 'memberCountry'})
        country = country.find('span', class_='fieldtext').text if country else ''
        postal = user_details.find('label', {'for': 'memberZipCode'})
        postal = postal.find('span', class_='fieldtext').text if postal else ''
        
        csv_writer.writerow([user_id, name, prof, desc, comp, ph, dn, mob, email, site, soc, add, city,
                             state, country, postal])
        
    return session
    

# Main function
def main():
    useProxy = False
    if useProxy:
        setProxies()
    session = getSession(useProxy=useProxy)
    user_ids = getSearchUsers(session=session)
    with open('bni_scrape.csv', 'w', newline='', encoding='utf-8') as csv_file:
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(['user_id', 'Name', 'Profession', 'Description', 'Company', 'Phone', 'Direct_Number', 'Mobile', 'Email', 'Website', 'Social', 'Address', 'City', 'State', 'Country', 'Zip'])
        i = 1
        for user_id in user_ids:
            print('Scraping Member: {0}'.format(user_id))
            time.sleep(5)
            session = getUserIdDetails(session, csv_writer, user_id)
            print('Done Scraping {0} out of {1}'.format(i, len(user_ids)))
            i+=1



if __name__ == '__main__':
    main()