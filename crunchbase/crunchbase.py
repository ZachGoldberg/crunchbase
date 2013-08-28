#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Python library for the CrunchBase api.
Copyright (c) 2010 Apurva Mehta <mehta.apurva@gmail.com> for CrunchBase class

Edits made by Alexander Pease <alexander@usv.com> to...
  * Ensure compliance with 2013 API key requirement
  * Fix namespace conventions (ex: 'Kapor Capital' is sent as 'kapor+capital')
  * Functions requiring parsing of CrunchBase-return JSON (ex. list investors)
  * If HTTP request fails, return None instead of raising Exception
  * Set strict=false for json.loads(). Avoids some errors in the CB API.
  * Sanitize strings used as argument for __webRequest

"""

__author__ = 'Apurva Mehta, Patrick Reilly, Daniel Mendalka'
__version__ = '1.0.3'

import logging
import unicodedata
import urllib
import urllib2


API_BASE_URL = 'http://api.crunchbase.com/'
API_VERSION = '1'
API_URL = API_BASE_URL + 'v' + '/' + API_VERSION + '/'
logger = logging.getLogger('crunchbase')


class CrunchBase(object):

    def __init__(self, api_key, cache={}):
        self.api_key = api_key
        self.__cache = cache

    def __webRequest(self, url):
        try:
            opener = urllib2.build_opener(NotModifiedHandler())
            req = urllib2.Request(url)

            if url in self.__cache:
                if 'etag' in self.__cache[url]:
                    logger.debug('Adding ETag to request header: '\
                        + self.__cache[url]['etag'])
                    req.add_header('If-None-Match',
                                   self.__cache[url]['etag'])
                if 'last_modified' in self.__cache[url]:
                    logger.debug('Adding Last-Modified to request header: '\
                        + self.__cache[url]['last_modified'])
                    req.add_header('If-Modified-Since',
                                   self.__cache[url]['last_modified'])

            url_handle = opener.open(req)

            if hasattr(url_handle, 'code') and url_handle.code == 304:
                logger.debug('Got 304 response, no body send')
                return self.__cache[url]['response']
            else:
                headers = url_handle.info()
                response = url_handle.read()

                cache_data = {
                    'response': response,
                    'last_modified': headers.getheader('Last-Modified'),
                    'url': url.replace('?api_key=' + self.api_key, '')}

                if headers.getheader('Last-Modified'):
                    cache_data['last_modified'] = \
                        headers.getheader('Last-Modified')

                if headers.getheader('ETag'):
                    cache_data['etag'] = headers \
                        .getheader('ETag').replace('"', '')

                self.__cache[url] = cache_data
                return response
        except urllib2.HTTPError, e:
            logger.warn('HTTPError calling ' + url)
            logger.warn(str(e))
            return None

    def getCache(self, url=None):
        if url is not None:
            return self.__cache[url]
        else:
            return self.__cache

    def search(self, query, page='1'):
        """This returns result of search query in JSON format"""

        return self.__getJsonData("search", query=None,
                                  options={"query": query,
                                           "page": page})

    def __getJsonData(self, namespace, query='', options=None):

        query = query.replace(' ', '+')
        query = unicodedata.normalize('NFKD',
                                      query.decode('utf-8')) \
            .encode('ascii', 'ignore')

        if query:
            query += ".js"

        if options is None:
            options = {}

        if self.api_key:
            options["api_key"] = self.api_key

        option_str = ""
        if options:
            option_str = "?%s" % urllib.urlencode(options)


        url = "%s%s%s%s" % (API_URL,
                           namespace,
                           query,
                           option_str)

        response = self.__webRequest(url)
        if response is not None:
            response = json.loads(response, strict=False)
        return response

    def getData(self, namespace, query=''):
        result = self.__getJsonData(namespace, '/%s' % query)
        return result

    def getCompanyData(self, name):
        """This returns the data about a company in JSON format."""

        result = self.__getJsonData('company', '/%s' % name)
        return result

    def getPersonData(self, *args):
        """This returns the data about a person in JSON format."""

        result = self.__getJsonData('person', '/%s' % '-'
                                    .join(args).lower().replace(' ', '-'))
        return result

    def getFinancialOrgData(self, orgName):
        """ This returns the data about a financial organization
        in JSON format."""

        result = self.__getJsonData('financial-organization', '/%s' % orgName)
        return result

    def getProductData(self, name):
        """This returns the data about a product in JSON format."""

        result = self.__getJsonData('product', name)
        return result

    def getServiceProviderData(self, name):
        """This returns the data about a service provider in JSON format."""

        result = self.__getJsonData('service-provider', '/%s' % name)
        return result

    def listCompanies(self):
        """This returns the list of companies in JSON format."""

        result = self.__getJsonData('companies')
        return result

    def listPeople(self):
        """This returns the list of people in JSON format."""

        result = self.__getJsonData('people')
        return result

    def listFinancialOrgs(self):
        """This returns the list of financial organizations in JSON format."""

        result = self.__getJsonData('financial-organizations')
        return result

    def listProducts(self):
        """This returns the list of products in JSON format."""

        result = self.__getJsonData('products')
        return result

    def listServiceProviders(self):
        """This returns the list of service providers in JSON format."""

        result = self.__getJsonData('service-providers')
        return result

    def listCompanyInvestors(self, name):
        """Returns the list of financial organizations
        invested in a given company"""

        company = self.getCompanyData(name)
        investors = []
        for rounds in company['funding_rounds']:
            for org in rounds['investments']:
                if org['financial_org'] is not None:
                    if org['financial_org']['name'] not in investors:
                        investors.append(org['financial_org']['name'])
        return investors

    def listInvestorPortfolio(self, orgName):
        """Returns a list of companies invested in by orgName"""

        investor = self.getFinancialOrgData(orgName)
        portfolio = []
        for investment in investor['investments']:
            portfolio.append(investment['funding_round']['company']['name'])
        return portfolio


class CrunchBaseResponse(object):

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.__dict__)


class CrunchBaseError(Exception):

    pass


class NotModifiedHandler(urllib2.BaseHandler):

    def http_error_304(self, req, fp, code, message, headers):
        addinfourl = urllib2.addinfourl(fp, headers, req.get_full_url())
        addinfourl.code = code
        return addinfourl
