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

from scripts_translated import atf_parser

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
    self.copy_atf_filtered(path)
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
  Functions to define types in query and divide a query into
  sections (80%, 10%, 10%), proportion with regard to type.
  Shares the common format for `self.entries_lst`.
  Arguments: filename with path.
  '''
  
  entries_lst = []
  UNCHANGABLE = []
  typs_lst = ['raw', 'trs', 'ann', 'trs-ann']

  def __init__(self):
    pass

  def split_and_dump_query(self, filename, unchangable=[], predefined=True):
    '''
    Function to make and dump split, copy conll files for annotation,
    and export translated data.
    ''' 
    self.predefined = predefined
    q = self.load_json('%s/%s' %(self.FILTERED_QUERY_PATH,
                                 filename))
    self.entries_lst = self.list_random_order(q['entries'])
    if unchangable is not None:
      self.UNCHANGABLE+=unchangable
    self.githup_update_annotated_unchangable()
    self.define_types()
    self.configure_types_and_split_all()
    self.dump_split(self.FILTERED_QUERY_PATH)
    self.copy_conll_to_annotate(self.FILTERED_QUERY_PATH)
    self.export_translated_data(self.FILTERED_QUERY_PATH)

  def update_data_from_atf(self, filename):
    '''
    Updates data from new ATF and old split (filename):
    1. Create new CoNLL files
    2. Copy CoNLL files for annotation
    3. Process translated parallel data
    See https://github.com/cdli-gh/mtaac_cdli_ur3_corpus/issues/2
    '''
    self.parts_lst = self.load_json('%s/%s' %(self.FILTERED_QUERY_PATH,
                                          filename))
    self.entries_lst_from_parts()
    self.atf2conll(self.FILTERED_QUERY_PATH)
    self.copy_conll_to_annotate(self.FILTERED_QUERY_PATH)
    self.export_translated_data(self.FILTERED_QUERY_PATH)

  def entries_lst_from_parts(self):
    self.entries_lst = []
    for p in self.parts_lst:
      self.entries_lst+=p['entries']
    
  def update_translated(self, filename):
    '''
    Function to load split and export translated data.
    ''' 
    self.parts_lst = self.load_json('%s/%s' %(self.FILTERED_QUERY_PATH,
                                              filename))
    self.export_translated_data(self.FILTERED_QUERY_PATH)

  def atf2conll(self, path):
    '''
    Converts ATF to CoNLL with atf2conll,
    then moves 'output' to corpus and renames it to 'conll'.
    '''
    s = subprocesses()
    command = ['atf2conll', '-i', '%s/atf' %path]
    s.run(command)
    shutil.move('%s/atf/output' %path,
                '%s/conll' %path)
    
  def define_types(self):
    '''
    Define type of entries in `self.entries_lst`. Options:
    'raw' - raw
    'trs' - translated
    'ann' - annotated
    'trs-ann' - translated and annotated
    '''
    for e in self.entries_lst:
      e['type']='raw'
      if 'translated' in e.keys():
        if e['translated']==True:
          e['type']='trs'
        del e['translated']
      if e['CDLI no.'] in self.UNCHANGABLE:
        if e['type']=='trs':
          e['type']='trs-ann'
        else:
          e['type']='ann'

  def configure_types_and_split_all(self):
    '''
    Workflow:
    1. split list to types
    2. calculate or/and define proportion for each type in corpus
    3. split each type list separately to corpus proportions
    4. merge corpus parts in different type lists.
    '''
    print('entries total init:', len(self.entries_lst))
    self.set_translated_annotated()
    self.set_raw_annotated()
    self.parts_lst = []
    for t in self.typs_lst:
      t_lst = self.list_entries_by_params(self.entries_lst, {'type': t})
      ss = self.standard_split(t_lst)
      if not len(self.parts_lst):
        self.parts_lst = ss
      else:
        for i in range(0,3):
          self.parts_lst[i]['entries']+=ss[i]['entries']
    self.print_report()

  def print_report(self):
    '''
    Print report for split evaluatuion.
    '''
    print('entries total:', len(self.entries_lst))
    for p in self.parts_lst:
      print('corpus part:', p['name'])
      print('entries:', len(p['entries']))
      for t in self.typs_lst:
        t_lst = self.list_entries_by_params(p['entries'], {'type': t})
        p_all = self.percent_of(t_lst, self.entries_lst)
        p_part = self.percent_of(t_lst, p['entries'])
        print('\ttype:', t,
              'percent in corpus: %s%%' %p_all,
              'percent in part: %s%%' %p_part,
              'entries: %s' %len(t_lst)
              )
        
  def set_translated_annotated(self):
    '''
    Define translated-annotated - random 20% of translated (incl. predefined).
    '''
    trs_ann = self.list_entries_by_params(self.entries_lst,
                                          {'type': 'trs-ann'})
    trs = self.list_entries_by_params(self.entries_lst,
                                      {'type': 'trs'})
    d = self.percent_of(trs_ann, trs+trs_ann)
    n = int(self.percent_count(trs+trs_ann, 20-d))
    trs_ann_fill = self.percent_of(range(0,n-1), trs)
    parts_lst = [{'name': 'trs', 'percent': 100-trs_ann_fill},
                 {'name': 'trs-ann', 'percent': trs_ann_fill,
                  'entries': trs_ann}]
    rest = self.list_entries_by_params(self.entries_lst,
                                          {'type': 'raw'})
    rest+=self.list_entries_by_params(self.entries_lst,
                                          {'type': 'ann'})
    self.split_and_update_types(parts_lst, trs, rest)

  def set_raw_annotated(self):
    '''
    Define annotated - random 5% of all texts (incl. predefined).
    The texts are randomly taken from the raw group.
    '''
    ann = self.list_entries_by_params(self.entries_lst,
                                          {'type': 'ann'})
    trs_ann = self.list_entries_by_params(self.entries_lst,
                                          {'type': 'trs-ann'})
    raw = self.list_entries_by_params(self.entries_lst,
                                      {'type': 'raw'})
    d = self.percent_of(ann+trs_ann, self.entries_lst)
    n = int(self.percent_count(self.entries_lst, int(5-d)))
    ann_raw_fill = self.percent_of(range(0,n-1), raw)
    parts_lst = [{'name': 'raw', 'percent': 100-ann_raw_fill},
                 {'name': 'ann', 'percent': ann_raw_fill,
                  'entries': ann}]
    rest = self.list_entries_by_params(self.entries_lst,
                                          {'type': 'trs'})
    rest+=trs_ann
    self.split_and_update_types(parts_lst, raw, rest)
    
  def split_and_update_types(self, parts_lst, source_lst, rest_lst):
    '''
    Shortcut to split and update type param. in entries according
    to given `p['name']`.
    '''
    parts_lst = self.items_split(parts_lst, source_lst)
    for p in parts_lst:
      for e in p['entries']:
        e['type'] = p['name']
      rest_lst+=p['entries']
    self.entries_lst = rest_lst
        
  def githup_update_annotated_unchangable(self):
    '''
    Updates `self.UNCHANGABLE` with a list of CDLI numbers
    already in Gold Corpus repository.
    '''
    self.github_list = [g.split('.')[0] for g in github_repo_list().file_lst
                        if g[0]=='P' and '.conll' in g]
    self.UNCHANGABLE = list(set(self.UNCHANGABLE+self.github_list))

  def standard_split(self, source_lst):
    '''
    Random division to train, test (gold), and develop subcorpora.
    Returns a list of dictionaries with the following format:
    - name: group's name ('train', 'test', or 'develop'),
    - percent: percent of the corpus (int),
    - entries: list of entries in the `self.entries_lst` format,
    - items: quantity of randomly defined entries,
    '''
    parts_lst = [{'name': 'train', 'percent': 80},
                 {'name': 'test', 'percent': 10},
                 {'name': 'develop', 'percent': 10}]
    return self.items_split(parts_lst, source_lst)

  def items_split(self, parts_lst, source_lst):
    '''
    Splits the corpus according to the percentage given in `parts_lst`.
    Recieves `parts_lst` as a list of dicts and `source_lst` in the format
    of `self.entries_lst`, returns `parts_lst` populated with entries.
    ! Prepopulated entries, when taken into account, have to be
    added to `el['entries']` separately, before or after this function.
    '''
    parts_lst = self.percentage_to_items(parts_lst, source_lst)
    prev = 0
    for el in parts_lst:
      if 'entries' not in el.keys():
        el['entries']=[]
      el['entries']+=source_lst[prev:prev+el['items']]
      prev+=el['items']
    return parts_lst

  def percentage_to_items(self, parts_lst, source_lst):
    '''
    Updates `parts_lst` to include the number of entries
    that matches given percent.
    Note that the `pre_count` argument's value is deducted from  
    entries in order to leave space for the predefined 
    entries.
    '''
    p_all = 0
    prc_lst = sorted([self._dec(self.percent_count(source_lst,
                                                   e['percent']))[1]
                      for e in parts_lst], key=lambda x: -x)
    for e in parts_lst:
      p = self.percent_count(source_lst, e['percent'])
      e['items'] = int(p)
      if prc_lst[0]!=0.0:
        e['items'] = int(self._dec(p)[0])
        if self._dec(p)[1]==prc_lst[0]:
          e['items']+=1
      p_all+=e['items']
    return parts_lst

  def copy_conll_to_annotate(self, path):
    '''
    Copies CoNLL files for annotation (filtered) to new destination.
    '''
    dest_path = '%s/conll_to_annotate' %(path)
    self.github_list = [g.split('.')[0] for g in github_repo_list().file_lst
                        if g[0]=='P' and '.conll' in g]
    entries_lst = self.list_entries_by_params(self.entries_lst,
                                              {'type': 'ann'})
    entries_lst+=self.list_entries_by_params(self.entries_lst,
                                             {'type': 'trs-ann'})
    entries_lst = [e for e in entries_lst if e['CDLI no.']
                   not in self.github_list]
    self.copy_conll_files(path, dest_path, entries_lst)

  def export_translated_data(self, path):
    '''
    Dumps translated corpus split and copies translated CoNLL
    files to new directory.
    '''
    trs_entries_lst = []
    dest_path = '%s/conll_translated' %path
    trs_parts_lst = []
    for p in self.parts_lst:
      p_trs = p
      p_trs['entries'] = self.list_entries_by_params(p['entries'],
                                                     {'type': 'trs'})
      p_trs['entries']+=self.list_entries_by_params(p['entries'],
                                                    {'type': 'trs-ann'})
      p_trs['items'] = len(p_trs['entries'])
      trs_parts_lst.append(p_trs)
      trs_entries_lst+=p_trs['entries']
    self.dump_split(path,
                    data=trs_parts_lst,
                    prefix='corpus_split_translated')
    self.copy_conll_files(path, dest_path, trs_entries_lst)
    self.process_parallel(path, trs_parts_lst)

  def process_parallel(self, path, trs_parts_lst):
    '''
    Processes and exports parallel data.
    '''
    output_path = '%s/atf' %(path)
    for p in trs_parts_lst:
      prefix = p['name']
      dest_path = '%s/translated_parallel_data' %(path)
      filenames = [e['CDLI no.']+'.atf' for e in p['entries']]
      a = atf_parser(output_path, filenames, dest_path, prefix)

  def _dec(self, i):
    '''
    Returns a tuple with dec and int.
    '''
    return math.modf(i)[::-1]

  def percent_count(self, whole_lst, percent):
    '''
    Recieves a list and a percent of items.
    Returns the number of items corr. to the precent of the list. 
    '''
    return (percent*len(whole_lst))/100.0

  def percent_of(self, section_lst, whole_lst):
    '''
    Recieves two lists and compares first length as percent of second.
    Returns the percent of section.
    '''
    section = len(section_lst)
    whole = len(whole_lst)
    percent = whole/100.0
    return section/percent
  
  def list_random_order(self, lst):
    '''
    Recieves a list and returns it sorted in random order.
    '''
    return sample(lst, len(lst))

  def list_entries_by_ids(self, entries_lst, ids_lst):
    '''
    Recieves a list of entries and a list of CDLI nos.
    Returns a list of entries matching nos.
    '''
    return [e for e in entries_lst if e['CDLI no.'] in ids_lst]

  def list_entries_by_params(self, entries_lst, param_dict):
    '''
    Recieves a list of entries and a dict. of params.
    Returns a list of entries matching params.
    '''
    return [e for e in entries_lst if self.match_params(e, param_dict)==True]

  def match_params(self, target_dict, param_dict):
    for k in param_dict.keys():
      if target_dict[k]!=param_dict[k]:
        return False
    return True

  def copy_conll_files(self, path, dest_path, entries_lst):
    '''
    Copies CoNLL files in list to new destination. Missing files IDs
    are saved in `no_conll.json`.
    '''
    if not os.path.exists(dest_path):
      os.makedirs(dest_path)
    not_copied_lst = []
    for e in entries_lst:
      scr = '%s/conll/%s.conll' %(path,
                                  e['CDLI no.'])
      dest = '%s/%s.conll' %(dest_path, e['CDLI no.'])
      try:
        shutil.copyfile(scr, dest)
      except FileNotFoundError:
        not_copied_lst.append(e['CDLI no.'])
    if not_copied_lst!=[]:
      self.dump(json.dumps(not_copied_lst), '%s/no_conll.json' %dest_path) 

  def dump_split(self, path, data=[], prefix=''):
    '''
    Dumps JSON data.
    '''
    json_data = data
    if data==[]:
      json_data = self.parts_lst
    if not len(prefix):
      prefix = 'corpus_split'
    filename = '%s/%s_%s.json' \
               %(path, prefix, time.strftime("%Y%m%d-%H%M%S"))
    self.dump(json.dumps(json_data), filename)

# ---/ Split functions /-------------------------------------------------------
#
##class split_data_functions(CDLI, common_functions):
##  '''
##  Functions to manipulate the JSON split format.
##  '''
##  def __init__(self, filename):
##    self.filename = filename
##    self.parts_lst = self.load_json('%s/%s'
##                                    %(self.FILTERED_QUERY_PATH, filename))
##    self.train_entries_lst = self.parts_lst[0]['entries']
##    self.test_entries_lst = self.parts_lst[1]['entries']
##    self.develop_entries_lst = self.parts_lst[2]['entries']
##    self.github_list = [g.split('.')[0] for g in github_repo_list().file_lst
##                        if g[0]=='P' and '.conll' in g]
##
##  def copy_gold_conll(self):
##    '''
##    Copies gold CoNLL files (for filtered entries) to new destination.
##    '''
##    path = '%s/conll_gold' %(self.FILTERED_QUERY_PATH)
##    if not os.path.exists(path):
##      os.makedirs(path)
##    for entry in self.test_entries_lst:
##      if entry['CDLI no.'] not in self.github_list:
##        scr = '%s/conll/%s.conll' %(self.FILTERED_QUERY_PATH,
##                                    entry['CDLI no.'])
##        dest = '%s/%s.conll' %(path, entry['CDLI no.'])
##        shutil.copyfile(scr, dest)
##
##  def redefine_unchangable(self, unchangable):
##    '''
##    Corrects split data with a list of new unchangable ids and these
##    in Github gold corpus repo.
##    '''
##    print('redefining unchangable entries')
##    unchangable = list(set(unchangable+self.github_list))
##    train_ids_lst = [e['CDLI no.'] for e in self.train_entries_lst]
##    test_ids_lst = [e['CDLI no.'] for e in self.test_entries_lst]
##    develop_ids_lst = [e['CDLI no.'] for e in self.develop_entries_lst]
##    for u in unchangable:
##      if u in train_ids_lst:
##        self.redefine_entry(u, 'train', unchangable)
##      elif u in develop_ids_lst:
##        self.redefine_entry(u, 'develop', unchangable)
##    self.update_parts_lst()
##    self.dump_redefined()
##
##  def redefine_entry(self, ID, group, unchangable):
##    '''
##    Subfunction of self.redefine_unchangable().
##    Changes self.parts_lst.
##    Place entry from train / devel and replace it with
##    one from test, but not in unchangable.
##    '''
##    print('move %s from %s to test' %(ID, group))
##    d = {'train': self.train_entries_lst,
##         'develop': self.develop_entries_lst}
##    entry = [e for e in d[group] if e['CDLI no.']==ID][0]
##    self.test_entries_lst.append(entry)
##    d[group].remove(entry)
##    for e in self.test_entries_lst:
##      if e['CDLI no.'] not in unchangable:
##        print('move %s from test to %s' %(e['CDLI no.'], group))
##        d[group].append(e)
##        self.test_entries_lst.remove(e)
##        break
##    self.train_entries_lst = d['train']
##    self.develop_entries_lst = d['develop']
##
##  def update_parts_lst(self):
##    '''
##    Updates changes in self.parts_lst.
##    '''
##    self.parts_lst[0]['entries'] = self.train_entries_lst
##    self.parts_lst[1]['entries'] = self.test_entries_lst
##    self.parts_lst[2]['entries'] = self.develop_entries_lst
##
##  def dump_redefined(self):
##    '''
##    Dumps updated self.parts_lst.
##    '''
##    path = '%s/%s.redef' %(self.FILTERED_QUERY_PATH, self.filename)
##    self.dump(json.dumps(self.parts_lst), path)
    
# ---/ Parallel corpus functions /---------------------------------------------
#
##class translated_corpus_functions(CDLI, common_functions):
##  '''
##  Functions to get translated corpus data from filtered query.
##  '''
##  def __init__(self, filename):
##    self.filename = filename
##    q = self.load_json('%s/%s' %(self.FILTERED_QUERY_PATH, filename))
##    tr_lst = [e for e in q['entries'] if 'translated' in e.keys()]
##    self.entries_lst = [e for e in tr_lst if e['translated']==True]
##
##  def dump_translated(self):
##    '''
##    Dumps JSON data.
##    '''
##    json_data = {'entries': self.entries_lst,
##                 'source_query': '%s/%s' %(self.FILTERED_QUERY_PATH,
##                                           self.filename)}
##    filename = '%s/corpus_translated_%s.json' \
##               %(self.FILTERED_QUERY_PATH, time.strftime("%Y%m%d-%H%M%S"))
##    self.dump(json.dumps(json_data), filename)
##
##  def split_and_dump(self):
##    qs = CDLI_query_split_functions(
##      entries_lst=self.entries_lst,
##      predefined=False)
##    qs.dump_split(self.FILTERED_QUERY_PATH, prefix='corpus_translated_split')
##
##  def process_translated(self):
##    pass
    
# ---/ Github repo query /-----------------------------------------------------
#
class github_repo_list(common_functions):
  '''
  Uses for retreaving structure of a Github repo 
  without downloading the repo itself.
  Serves for filtering a predefined Gold Corpus,
  but can be adjusted for further Github usage.
  ! WARNING: Will not work correctly with directories
  of < 1000 files !
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

class subprocesses(common_functions):

  def __init__(self):
    self.subprocesses_list = []
    self.pending_lst = []
    self.max = 4
    
  def run(self, cmd, cwd=''):
    print('\nrun %s' %(' '.join(cmd)))
    if not cwd:
      cwd = os.getcwd()
    print(r'%s' %(cwd))
    p = subprocess.Popen(cmd,
                         cwd=r'%s' %(cwd),
                         stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT)
    output = self.trace_console(p)
    self.dump(output, 'atf2conll.log')
      
  def trace_console(self, p):
    output = ""
    try:
      for line in iter(p.stdout.readline, b''):
        output += line.rstrip().decode('utf-8')+'\n'
    except ValueError:
      print('subprocess stopped.')
    return output

# ---/ Main /------------------------------------------------------------------
#
if __name__ == "__main__":
  pass

#---/ Older Functions, might be outdated /-------------------------------------
#
  '''primary query: '''
##  pq = CDLI_query_primary()
##  pq.query(CDLI_QUERY_DICT)

  '''Filter: '''
##  qf = CDLI_query_functions()
  
  '''Save filtered data:'''
##  qf.save_filtered()

  '''Split: '''
##  qs = CDLI_query_split_functions(qf.entries_lst, unchangable=UNCHANGABLE)
##  qs.dump_split(qf.FILTERED_QUERY_PATH)

  '''Redefine unchagable
  (when unchangable=UNCHANGABLE omitted in CDLI_query_split_functions())
  '''
#  sf = split_data_functions('corpus_split_20180410-224554.json')
#  sf.redefine_unchangable(UNCHANGABLE)
  
  '''Copy gold CoNLL'''
#  sf.copy_gold_conll()

  '''Find and dump translated '''
##  tr = translated_corpus_functions('corpus_20180410-215511.json')
##  tr.dump_translated()

  '''ATF 2 CoNLL with logging'''
##  sps = subprocesses()
##  command = ['atf2conll', '-i', '../ur3_corpus_data/atf']
##  sps.run(command)
  
  '''Find error messages in log'''
##  with codecs.open('atf2conll.log', 'r', 'utf-8') as f:
##    errors_str = ''
##    for l in f.readlines():
##      if 'error' in l.lower():
##        errors_str+=l
##  with codecs.open('atf2conll_errors.log', 'w', 'utf-8') as f:
##      f.write(errors_str)

  '''Split and dump translated'''
##  tr = translated_corpus_functions('corpus_20180410-215511.json')
##  tr.split_and_dump()


#---/ Updated Functions /------------------------------------------------------
#
  '''Split: '''
##  qs = CDLI_query_split_functions()
##  qs.split_and_dump_query('corpus_20180410-215511.json', unchangable=UNCHANGABLE)

  '''Update translated: '''
##  qs = CDLI_query_split_functions()
##  qs.update_translated('corpus_split_20180418-225438.json')

  '''Update from new ATF, old split: '''
  '''See https://github.com/cdli-gh/mtaac_cdli_ur3_corpus/issues/2'''
  qs = CDLI_query_split_functions()
  qs.update_data_from_atf('corpus_split_20180418-225438.json')

  

    

  



