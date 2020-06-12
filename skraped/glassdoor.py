import os
import logging
import json
import csv
import time
import random
from bs4 import BeautifulSoup
from .scraper_base import ScraperBase

lgr = logging.getLogger()


class Glassdoor(ScraperBase):
    """Glasdoor scraper class"""

    def __init__(self, config={}):
        self.config = config
        super().__init__(config)
        self.base_url = 'https://www.glassdoor.com'
        self.url = 'https://www.glassdoor.com/Job/jobs.htm?'
        self.query_params = {
            'jobType': '',
            'typedKeyword': self.config.get('keywords'),
            'sc.keyword': self.config.get('keywords').lower(),
            'locT': 'N',
            'locId': '130',
            'suggestChosen': 'false',
            'clickSource': 'searchBtn',
            'suggestCount': '0',
        }
        self.scrape_data = []
        self.sleep_seconds = self.config["delay"]

    def scrape(self):  # pragma: nocover
        """
        Entry point for Glassdoor scraper
        """
        self.build_url()
        pages = self.get_pages()
        if pages:
            job_links = self.get_job_links(pages)
            if not job_links:
                lgr.error(
                    'Failed to retrieve job links from Glassdoor search page results')
                return []
            job_links = self.run_pre_scrape_filters(job_links, source="glassdoor")
            super().process_job_details(self, "extract_job_details", job_links)
        return self.scrape_data
    
    def build_url(self):
        """Builds full url from query parameters specified"""
        first_query = self.query_params.popitem()
        self.url += str(first_query[0])+'=' + \
            '+'.join(first_query[1].split(" "))
        for key, value in self.query_params.items():
            self.url += '&' + str(key)+'='+'+'.join(value.split(" "))
        return self.url

    def get_pages(self):
        """
        Retrieves each job results page upto the pagination limit.
        """
        pages, page_count = [], 0
        next_page_url = self.url
        next_res = self.send_request(next_page_url, 'get')
        while next_res is not None:
            page_soup = BeautifulSoup(next_res, 'lxml')
            pages.append(page_soup)
            page_count += 1
            # lgr.info(f'Fetched page {page_count} of Glassdoor results')
            footer = page_soup.find(
                'div', {'id': 'FooterPageNav', 'class': 'pageNavBar'})
            if footer:
                next_page = footer.find('li', {'class': 'next'})
                if not next_page:
                    break
                next_page_url = next_page.find('a')['href']
                if not next_page_url:
                    break
                next_page_url = self.base_url + next_page_url
                next_res = self.send_request(next_page_url, 'get')
            else:
                break
        lgr.info(f'\nRetrieved {page_count} Glassdoor result page(s)')
        return pages

    def get_job_links(self, pages_soup):
        """
        Retrieves job links from scraped pages
        @param pages_soup: The parsed HTML for each of the pages to be processed
        @type pages_soup: BeautifulSoup
        @return: List of the extracted job links
        @rtype: List
        """
        job_links = set()
        for page in pages_soup:
            links = page.find_all(
                'a', {'class': ['jobInfoItem', 'jobTitle', 'jobLink']})
            if links:
                links = [link['href'] for link in links if hasattr(link, 'href')]
                for link in links:
                    if link not in job_links:
                        job_links.add(self.base_url + link)
        return list(job_links)

    def extract_job_details(self, job_url, delay = 0, **kwargs):
        """
        Extracts job details from each job link
        @param job_url: A link/url to the job details page
        @type job_url: str
        @param delay: A value in seconds to delay this scraper operation
        @type delay: int
        @param kwargs: Extra key-value pair arguments to be passed
        @return: The extracted job details
        @rtype: dict
        """
        time.sleep(delay)
        lgr.info(f"Delay: {delay}s. Processing {job_url}")
        res = self.send_request(job_url, 'get')
        if not res:  # pragma: nocover
            lgr.error(f'{job_url} details request returned None')
            return None
        soup = BeautifulSoup(res, 'lxml')
        if not soup:  # pragma: nocover
            lgr.error(f'Failed to parse the response HTML for this post {job_url}')
            return None
        job_details = {
            'title': '',
            'company': '',
            'job_link': job_url,
            'application_link': '',
            'description': '',
            'job_id': '',
            'source': 'Glassdoor'
        }
        title = soup.find('div', {'class': 'e11nt52q5'})
        company_container = [child for child in soup.find(
            'div', {'class': 'e11nt52q1'})]
        company_name = soup.find('div', {'class': 'e11nt52q1'}).text
        if company_container:
            company_name = company_container[0]
        apply_btn = soup.find(
            'a', {'class': ['gd-ui-button', 'applyButton', 'e1ulk49s0', 'css-1m0gkmt']})
        if not apply_btn:  # pragma: nocover
            # Try checking for a button instead. Glassdoor uses both btns and anchor tags
            apply_btn = soup.find(
                'button', {'class': ['gd-ui-button', 'applyButton', 'e1ulk49s0', 'css-1m0gkmt']})
        description = soup.find('div', {'class': 'desc'})

        job_details['title'] = title.text.encode(
            'ascii', 'ignore').decode('utf-8') if title else ''
        job_details['company'] = company_name.encode(
            'ascii', 'ignore').decode('utf-8') if company_name else ''
        if hasattr(apply_btn, 'href') and apply_btn.name != 'button':
            application_link = self.base_url + apply_btn['href']
        elif hasattr(apply_btn, 'data-job-url'):  # pragma: nocover
            application_link = self.base_url + apply_btn['data-job-url']
        else:  # pragma: nocover
            application_link = ''
        link_redirect = self.send_request(
            application_link, 'get', return_raw=True)
        if link_redirect is not None:
            application_link = link_redirect.url
        job_details['application_link'] = (application_link).encode(
            'ascii', 'ignore').decode('utf-8')
        job_details['description'] = description.text.encode(
            'ascii', 'ignore').decode('utf-8').strip() if description else ''
        job_details['job_id'] = apply_btn['data-job-id'] if apply_btn else ''

        return job_details
