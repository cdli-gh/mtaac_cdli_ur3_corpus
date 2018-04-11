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

# Dependencies:
# lxml
# click
# atf2conll

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

# ---/ Primary query /---------------------------------------------------------
#
class CDLI_query_primary(CDLI, common_functions):
  '''
  Scrap CDLI and save JSON and ATF files in subdirs of query folder.
  Use `self.query()` with a dictionary of CDLI PHP search parameters, i.e.
  ```{"SearchMode": "Text",
  "Period": "ur+iii",
  "offset": "0",
  "requestFrom": "Submit"}```
  '''
  def __init__(self):
    pass

  def makedirs_query(self):
    for path in [self.QUERY_PATH,
                 self.QUERY_PATH+'/atf',
                 self.QUERY_PATH+'/json',
                 self.QUERY_PATH+'/html',]:
      if not os.path.exists(path):
        os.makedirs(path) 

  def query(self, query_dict):
    self.errors = []
    self.makedirs_query()
    self.dump(json.dumps(query_dict),
              self.QUERY_PATH+'/query_variables.json')
    search_url = self.get_search_url(query_dict)
    self.get_and_dump_html_all(search_url)
    self.download_and_query_html_all(query_dict)
    self.dump_errors()

  def download_and_query_html_all(self, url):
    i = 1
    html = self.get_html(url=url)
    print('downloading page %s' %(i))
    self.dump_html(html, i)
    while html is not None:
      html = self.get_next_html(html)
      if html is not None:
        i+=1
        print('downloading page %s' %(i))
        self.dump_html(html, i)

  def dump_errors(self):
    self.dump("\n".join(self.errors), self.QUERY_PATH+"/errors.log")

  def dump_html(self, html, i):
    filename = '%s/html/CDLI_query_%s.html' %(self.QUERY_PATH,
                                              str(i).zfill(3))
    self.dump(lxml_html.tostring(html).decode('utf-8'), filename)

  def load_and_query_html_all(self, query_dict):
    _path = '%s/html/' %(self.QUERY_PATH)
    for dirpath, dirnames, filenames in os.walk(_path):
      i = 1
      for filename in [f for f in sorted(filenames) if f.endswith('.html')]:
        if i > len(os.listdir('%s/json/' %(self.QUERY_PATH))):
          path = os.path.join(dirpath, filename)
          html = self.get_html(path=path)
          self.collect_and_dump_json(html, query_dict, i)
        i+=1
        
  def collect_and_dump_json(self, html, query_dict, i):
    print('parsing page %s' %(i))
    entries_lst = self.collect_entries(html)
    json_data = {"query": query_dict, "page": i, "entries": entries_lst}
    filename = '%s/json/CDLI_query_%s.json' %(self.QUERY_PATH,
                                              str(i).zfill(3))
    self.dump(json.dumps(json_data), filename)
    
  def collect_entries(self, html):
    entries_lst = []
    tags_lst = html.xpath("//table[@class='full_object_table']")
    for tag in tags_lst:
      entry_dict = self.get_entry_params(tag)
      ATF_versions = self.get_ATF_versions_from_dict(entry_dict)
      self.dump_atf(ATF_versions, entry_dict['CDLI no.'])
      entry_dict = self.define_translated(ATF_versions, entry_dict)
      entries_lst.append(entry_dict)
    return entries_lst

  def define_translated(self, ATF_versions, entry_dict):
    # adds 'translated' boolean to entry_dict when atf file exists
    if ATF_versions:
      entry_dict['translated'] = False
      if '#tr.' in ATF_versions[0]:
        entry_dict['translated'] = True
    return entry_dict

  def get_entry_params(self, tag):
    entry_dict = {}
    for key in self.CDLI_ENTRY_PARAMS:
      xpath_expr = "tr/td/table/tr/td[text()='%s']" \
                   "/following-sibling::td/text()" \
                   %(key)
      value = tag.xpath(xpath_expr)
      if not value:
        value = ""
      else:
        value = value[0]
      entry_dict[key] = value
    return entry_dict
    
  def get_next_html(self, html):
    next_url = html.xpath("//a[text()='NEXT']/@href")
    if next_url:
      search_url = self.CDLI_URL + next_url[0]
      return self.get_html(url=search_url)

  def get_ATF_versions_from_dict(self, entry_dict):
    ATF_lst = []
    if entry_dict['ATF source'] not in ['no atf', '']:
      ATF_lst = self.get_ATF_versions(entry_dict["CDLI no."])
    return ATF_lst

  def get_ATF_versions(self, ID):
    ATF_lst = []
    url = self.CDLI_URL+"/search/revhistory.php/?txtpnumber=%s&" \
          %(ID[1:])
    html = self.get_html(url)
    if html!=None:
      for tag in html.xpath("//div[@class='revcontent']"):
        atf_txt = self.cut_ATF(tag.text_content())
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
                "%s/atf/%s.atf" %(self.QUERY_PATH,
                                  ID))
  
  def get_search_url(self, search_params_dict):
    search_str = self.CDLI_SEARCH_URL
    for key in self.SEARCH_PARAMS:
      value = ""
      if key in search_params_dict.keys():
        value = search_params_dict[key]
      search_str+="%s=%s&" %(key, value)
    return search_str[:-1]

# ---/ Query load & filter /---------------------------------------------------
#
class CDLI_query_functions(CDLI, common_functions):
  '''
  Functions for loading, filtering, and exporting a saved 
  primary query (`CDLI_query_primary().query()`).
  '''
  FILTER = [('Language', 'is', ['Sumerian']),
            ('ATF source', 'not', ['no atf', ''])]
  entries_lst = []
  
  def __init__(self, query_path=None, flter=None, good_atf=True):
    if query_path is not None:
      self.QUERY_PATH = query_path
    if flter is not None:
      self.FILTER = flter
    self.query_data = self.load_json(
      self.QUERY_PATH+'/query_variables.json')
    self.load_query()
    if good_atf==True:
      self.filter_good_atf()
    self.filter_query()
    self.quick_report()

  def quick_report(self):
    '''
    Quick report:
    - total
    - entries with atf data
    - entries with no atf data
    - atf data with translation
    - atf data with no translation
    '''
    atf_lst = [en for en in self.entries_lst if 'translated' in en.keys()]
    transl_lst = [en for en in atf_lst if en['translated']==True]
    print(
      'total: %s'
      '\nentries with atf data: %s'
      '\nentries with no atf: %s'
      '\natf with translation: %s'
      '\natf with no translation: %s'
      %(len(self.entries_lst),
        len(atf_lst),
        len(self.entries_lst)-len(atf_lst),
        len(transl_lst),
        len(atf_lst)-len(transl_lst)
        )
      )

  def filter_good_atf(self):
    """
    When appliend, only ATF files with lines remain.
    See ´self.check_atf_status()´ below.
    """
    print('filtering ATF: files that contain lines of text...')
    self.entries_lst = [en for en in self.entries_lst
                        if self.check_atf_status(en)=='good']

  def check_atf_status(self, entry):
    """
    Return ATF status on simple check.
    'good' - contains at least one line of text
    'poor' - no lines of text
    None - no atf found
    Note that this is not an ATF format checker.
    """
    filename = entry['CDLI no.']+'.atf'
    try:
      with codecs.open(self.QUERY_PATH+'/atf/'+filename,
                       'r', 'utf-8') as f:
        atf_str = str(f.read())
    except FileNotFoundError:
      return None
    for f_line in ["1.", "1'."]:
      if f_line in atf_str:
        return 'good'
    return 'poor'

  def load_query(self):
    '''
    Loads saved (primary) query in `self.QUERY_PATH`.
    Updates `self.entries_lst`.
    '''
    _path = self.QUERY_PATH+'/json'
    for filename in os.listdir(_path):
      path = str(Path(os.path.join(_path, filename)))
      self.entries_lst+=self.load_json(path)['entries']

  def filter_query(self):
    '''
    Filters loaded query by conditions in `self.FILTER`.
    Condition entry structure: `(field, condition, options)`.
    Parameters:
    - `field`: name of CDLI field in question.
    - `condition`: `'is'` and `'not'` for Pythonic `in` and `not in` resp.
    - `options`: list of field values to match.
    Updates `self.entries_lst`.
    '''
    for (field, condition, options) in self.FILTER:
      if condition=='is':
        self.entries_lst = [e for e in self.entries_lst \
                            if e[field].strip(' ') in options]
      elif condition=='not':
        self.entries_lst = [e for e in self.entries_lst \
                            if e[field].strip(' ') not in options]

  def list_query_field_values(self):
    '''
    Returns a `dict` with CDLI field names as keys
    and list of unique values in loaded query.
    Fileds are for now embedded, see `fields_lst` below.
    '''
    fields_lst = ['Genre', 'Sub-genre', 'Provenience',
                  'Language', 'ATF source']
    var_dict = {}
    for key in fields_lst:
      var_dict[key] = []
    for entry in self.entries_lst:
      for key in var_dict.keys():
        value = entry[key]
        if var_dict[key]==[]:
          var_dict[key].append([value, 1])
        elif value not in [e[0] for e in var_dict[key]]:
          var_dict[key].append([value, 1])
        else:
          ind = [e[0] for e in var_dict[key]].index(value)
          var_dict[key][ind][1]+=1
    return var_dict

  def print_values(self, var_dict):
    # NOT USED
    '''
    Prints a concordance of possible CDLI fields' values
    in `self.list_query_field_values()`'s output format.
    Can be useful for examining and cleaning the CDLI data.
    Not used at the moment.
    '''
    for key in var_dict.keys():
      vars_lst = sorted(var_dict[key], key = lambda e: -e[1])
      print('%s(s):\n\t%s\n\n'
                 %(key, '\n\t'.join(
                   ['%s\t%s' %(e[0], e[1]) for e in vars_lst]
                   )))

  def save_filtered(self, path=''):
    '''
    Exports filtered query to a new directory.
    Optional argument: `path` for the new directory's path.
    '''
    if not len(path):
      path = self.FILTERED_QUERY_PATH
    self.makedirs_query_filtered(path)
    self.dump_query_filtered(path)
    #self.copy_atf_filtered(path)
    self.atf2conll_filtered(path)

  def makedirs_query_filtered(self, path):
    '''
    Creates new directories for the exported query and a subdirectory
    for the ATF sources.
    '''
    for p in [path, path+'/atf']:
      if not os.path.exists(p):
        os.makedirs(p)

  def copy_atf_filtered(self, path):
    '''
    Copies ATF files (for filtered entries) to new destination.
    '''
    for entry in self.entries_lst:
      scr = '%s/atf/%s.atf' %(self.QUERY_PATH, entry['CDLI no.'])
      dest = '%s/atf/%s.atf' %(path, entry['CDLI no.'])
      try: 
        shutil.copyfile(scr, dest)
      except FileNotFoundError:
        print('%s: ATF source missing, removing entry from results'
                   %(entry['CDLI no.']))
        self.entries_lst.remove(entry)

  def atf2conll_filtered(self, path):
    '''
    Converts copied ATF to CoNLL with atf2conll,
    then moves 'output' to corpus and renames it to 'conll'.
    '''
    s = subprocesses()
    command = ['atf2conll', '-i', '%s/atf' %path]
    subprocess.Popen(command)
    shutil.move('%s/atf/output' %path,
                '%s/conll' %path)

  def dump_query_filtered(self, path):
    '''
    Dumps filtered JSON data.
    '''
    json_data = {"query": self.query_data,
                 "entries": self.entries_lst,
                 'filter': self.FILTER}
    filename = '%s/corpus_%s.json' %(path, time.strftime("%Y%m%d-%H%M%S"))
    self.dump(json.dumps(json_data), filename)

# ---/ Query split /-----------------------------------------------------------
#
class CDLI_query_split_functions(CDLI, common_functions):
  '''
  Functions to divide a query into sections (80%, 10%, 10%).
  Shares the common format for `self.entries_lst`.
  '''
  entries_lst = []
  UNCHANGABLE = []

  def __init__(self, entries_lst, unchangable=[]):
    self.entries_lst = entries_lst
    if unchangable is not None:
      self.UNCHANGABLE+=unchangable
    self.githup_update_gold_unchangable()
    self.random_plus_corpus_split()
    
  def githup_update_gold_unchangable(self):
    '''
    Updates `self.UNCHANGABLE` with a list of CDLI numbers
    already in Gold Corpus repository.
    '''
    github_list = [g.split('.')[0] for g in github_repo_list().file_lst
                   if g[0]=='P' and '.conll' in g]
    self.UNCHANGABLE = list(set(self.UNCHANGABLE+github_list))

  def random_plus_corpus_split(self):
    '''
    Random division to train, test (gold), and develop subcorpora.
    Returns a list of dictionaries with the following format:
    - name: group's name ('train', 'test', or 'develop'),
    - percent: percent of the corpus (int),
    - entries: list of entries in the `self.entries_lst` format,
    - items: quantity of randomly defined entries,
    - pre (optional): quantity of predefined entries,
    - and some others.
    '''
    entries_gold = [e for e in self.entries_lst
                    if e['CDLI no.'] \
                    in self.UNCHANGABLE]
    entries_lst = [e for e in self.entries_lst
                   if e not in entries_gold]
    entries_lst = sample(entries_lst, len(entries_lst))
    parts_lst = [{'name': 'train', 'percent': 80},
               {'name': 'test', 'percent': 10, 'pre': len(entries_gold)},
               {'name': 'develop', 'percent': 10}]
    parts_lst = self.percentage_to_items(parts_lst)
    prev = 0
    for el in parts_lst:
      el['entries'] = entries_lst[prev:prev+el['items']]
      prev+=el['items']
      if el['name']=='test':
        el['entries']+=entries_gold
    self.parts_lst = parts_lst

  def percentage_to_items(self, parts_lst):
    '''
    Subfunction of `self.random_plus_corpus_split()`.
    Updates `parts_lst` to include the number of entries
    that matches given percent.
    Note that the `pre` argument's value is deducted from  
    entries in order to leave space for the predefined Gold
    entries.
    '''
    whole = len(self.entries_lst)
    ints = 0
    for el in parts_lst:
      (el['int'], el['dec']) = math.modf((el['percent']*whole)/100.0)
      ints+=el['int']
    for el in sorted(parts_lst, key=lambda x: -x['int']):
      if ints > 0:
        el['items'] = int(el['dec']+1)
        ints-=1
      else:
        el['items'] = int(el['dec'])
      if 'pre' in el.keys():
        el['items']-=el['pre']
    return parts_lst

  def dump_split(self, path):
    '''
    Dumps JSON data.
    '''
    json_data = self.parts_lst
    #! include query and filter data
    filename = '%s/corpus_split_%s.json' \
               %(path, time.strftime("%Y%m%d-%H%M%S"))
    self.dump(json.dumps(json_data), filename)

# ---/ Split functions /-------------------------------------------------------
#
class split_functions(CDLI, common_functions):

  def __init__(self, filename):
    self.parts_lst = self.load_json('%s/%s'
                                    %(self.FILTERED_QUERY_PATH, filename))

  def copy_gold_conll(self):
    '''
    Copies gold CoNLL files (for filtered entries) to new destination.
    '''
    g_entries_lst = [e for e in self.parts_lst
                     if e['name']=='test'][0]['entries']
    path = '%s/conll_gold' %(self.FILTERED_QUERY_PATH)
    if not os.path.exists(path):
      os.makedirs(path)
    github_list = [g.split('.')[0] for g in github_repo_list().file_lst
                   if g[0]=='P' and '.conll' in g]
    for entry in g_entries_lst:
      if entry['CDLI no.'] not in github_list:
        scr = '%s/conll/%s.conll' %(self.FILTERED_QUERY_PATH,
                                    entry['CDLI no.'])
        dest = '%s/%s.conll' %(path, entry['CDLI no.'])
        shutil.copyfile(scr, dest)

# ---/ Github repo query /-----------------------------------------------------
#
class github_repo_list(common_functions):
  '''
  Uses for retreaving structure of a Github repo 
  without downloading the repo itself.
  Serves for filtering a predefined Gold Corpus,
  but can be adjusted for further Github usage.
  '''
  GITHUB_URL = "https://github.com"
  ORG = 'cdli-gh'
  REPO = 'mtaac_gold_corpus'
  BRANCH = 'master'
  FOLDER = 'morph/to_dict'
  URL = ("%s/%s/%s/tree/%s/%s" %(GITHUB_URL, ORG, REPO, BRANCH, FOLDER))

  def __init__(self):
    html = self.get_html(url=self.URL)
    self.dirs_lst = self.get_entities(html, typ='directory')
    self.file_lst = self.get_entities(html, typ='file', no_typ='directory')

  def get_entities(self, html, typ, no_typ=''):
    if len(no_typ):
      no_typ = "[not(contains(@class, '%s'))]" % no_typ
    return html.xpath("//td[@class='icon'][svg[contains(@class, '%s')]%s]"
                      "/following-sibling::td[@class='content']/span/a/text()"
                      % (typ, no_typ))

# ---/ Variables /-------------------------------------------------------------
#
# Standard `CDLI_QUERY_DICT` for Ur III to pass to primary query. 
# Params `offset` and `requestFrom` should be left unchanged.
CDLI_QUERY_DICT = {
  "SearchMode": "Text",
  "Period": "ur+iii",
  "offset": "0",
  "requestFrom": "Submit"
  }
# list of predefined CDLI nos. for Gold Corpus.
UNCHANGABLE = [
  "P142656",
  "P458899",
  "P101779",
  "P101799",
  "P102280",
  "P103152",
  "P103343",
  "P105331",
  "P105373",
  "P105448",
  "P106442",
  "P339512",
  "P105373",
  "P142759",
  "P142766",
  "P142818",
  "P142827",
  "P248587",
  "P248598",
  "P248655",
  "P248772",
  "P248792",
  "P248816",
  "P248817",
  "P248863",
  "P248871",
  "P248881"
  ]

# ---/ Main /------------------------------------------------------------------
#
if __name__ == "__main__":
  '''primary query: '''
##  pq = CDLI_query_primary()
##  pq.query(CDLI_QUERY_DICT)

  '''filter: '''
##  qf = CDLI_query_functions()
  '''save filtered data:'''
##  qf.save_filtered()

  '''split: '''  
##  qs = CDLI_query_split_functions(qf.entries_lst)
##  qs.dump_split(qf.FILTERED_QUERY_PATH)

  '''copy gold CoNLL'''
##  sf = split_functions('corpus_split_20180410-224554.json')
##  sf.copy_gold_conll()

