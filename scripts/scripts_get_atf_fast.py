import subprocess
import json
import codecs
import os
from lxml import html as lxml_html
from urllib.request import urlopen
from pathlib import Path
from urllib.error import URLError
import shutil
from random import sample
import math
import click
import time
from multiprocessing import Pool

from scripts_translated import atf_parser

# ---/ CDLI variables /--------------------------------------------------------
#
class CDLI:
  '''
  Basic parameters and functionality for CDLI data.
  '''
  
  CDLI_URL = 'https://cdli.ucla.edu'
  CDLI_SEARCH_URL = "https://cdli.ucla.edu/search/search_results.php?"
  QUERY_PATH = "../query"
  FILTERED_QUERY_PATH = "../ur3_corpus_data"
  SEARCH_PARAMS = ["SearchMode",
                   "PrimaryPublication",
                   "MuseumNumber",
                   "Provenience",
                   "Period",
                   "Genre",
                   "TextSearch",
                   "ObjectID",
                   "requestFrom",
                   "offset"]
  CDLI_ENTRY_PARAMS = ['Primary publication',
                       'Author(s)',
                       'Publication date',
                       'Secondary publication(s)',
                       'Collection',
                       'Museum no.',
                       'Accession no.',
                       'Provenience',
                       'Excavation no.',
                       'Period',
                       'Dates referenced',
                       'Object type',
                       'Remarks',
                       'Material',
                       'Language',
                       'Genre',
                       'Sub-genre',
                       'CDLI comments',
                       'Catalogue source',
                       'ATF source',
                       'Translation',
                       'UCLA Library ARK',
                       'Composite no.',
                       'Seal no.',
                       'CDLI no.']

# ---/ Common functions /------------------------------------------------------
#
class common_functions:

  def load_json(self, path):
    with codecs.open(path, 'r', 'utf-8') as f:
      json_data = json.load(f)
    return json_data
  
  def dump(self, data, filename):
    with codecs.open(filename, 'w', 'utf-8') as dump:
      dump.write(data)

  def get_html(self, url="", path="", repeated=False):
    html = None
    if url:
      try:
        with urlopen(url) as response:
          html = lxml_html.parse(response).getroot()
      except (TimeoutError, URLError) as e:
        if repeated==False:
          print('TimeoutError: %s\nTrying again...' %(url))
          return self.get_html(url=url, repeated=True)
        else:
          print('TimeoutError: %s\nFailed' %(url))
          self.errors.append('TimeoutError: %s' %(url))
          return None
    elif path:
      html = lxml_html.parse(path).getroot()
    return html

#---/ ATF /--------------------------------------------------------------------

class atf(common_functions, CDLI):

  def get_ATF_versions(self, ID):
    ATF_lst = []
    url = self.CDLI_URL+"/search/revhistory.php/?txtpnumber=%s&" \
          %(ID[1:])
    html = self.get_html(url)
    if html!=None:
      for br in html.xpath("*//del/br"):
        br.tail = "\n" + br.tail if br.tail else "\n"
      for tag in html.xpath("//div[@class='revcontent']"):
        atf_txt = self.cut_ATF(tag.text_content()).replace("\n\n", "\n")
        ATF_lst.append(atf_txt)
    return ATF_lst

  def cut_ATF(self, atf):
    # note that this removes version info
    # use atf[:atf.find('&P')] to retreve it
    return atf[atf.find('&P'):]

  def load_and_dump_aft_standalone(self, ID):
    self.dump_atf(self.get_ATF_versions(ID), ID)

  def dump_atf(self, ATF_versions, ID):
    # dumps latest version only
    if ATF_versions:
      self.dump(ATF_versions[0],
                "%s/atf_new/%s.atf" %(self.FILTERED_QUERY_PATH,
                                  ID))
a = atf()
def get_atf(filename):
  if '.atf' in filename and filename not in ready_lst:
    ID = filename.split('.')[0]
    a.load_and_dump_aft_standalone(ID)

files_lst = os.listdir("../ur3_corpus_data/atf")
ready_lst = os.listdir("../ur3_corpus_data/atf_new")

if __name__ == '__main__':
  with Pool(processes=5) as pool:
    pool.map(get_atf, files_lst)
  









      
