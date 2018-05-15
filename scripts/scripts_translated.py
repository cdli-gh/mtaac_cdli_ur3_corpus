import subprocess
import os
import codecs
import json
import re
from pathlib import Path

def is_int(char):
  try:
    int(char)
    return True
  except ValueError:
    return False  

#---/ATF parser/---------------------------------------------------------------
#
class atf_parser:
  
  re_brc = re.compile(r'(\(.+\))')
  punct_lst = [':', ';', '?', '.', ',', '”', '“']
  
  def __init__(self, path, filenames, dest_path, prefix):
    self.data = []
    self.texts = []
    if not os.path.exists(dest_path):
      os.makedirs(dest_path)
    self.load_collection(path, filenames)
    self.parse_data()
    self.export_csv(dest_path, prefix)
    self.export_for_giza(dest_path, prefix)

  def load_collection(self, path, filenames):
    for f in filenames:
      with codecs.open(path+'/'+f, 'r', 'utf-8') as f:
        self.data+=f.readlines()

  def parse_data(self):
    for line in self.data:
      line = line.strip('\n')
      if line:
        if '&P' in line and ' = ' in line:
          if 'CDLI' in locals():
            self.texts.append({'CDLI': CDLI,
                               'PUB': PUB,
                               'lines_lst': lines_lst})
          CDLI, PUB = line.strip('&').split(' = ', 1)
          lines_lst = []
        elif '#tr.en' in line:
          translation = line.replace('#tr.en', '').strip(' :')
          lines_lst.append({'no': line_no,
                            'translit': translit,
                            'translation': translation,
                            'normalization': self.normalize(translit)
                            })
        elif is_int(line[0]) and '. ' in line:
          line_no, translit = line.split('. ', 1)
        else:
          pass
        # the parser is designed to extract only certain, relevant data.
        # extend here to retrieve other information.

  def export_csv(self, path, prefix):
    data_str = ''
    for txt in self.texts:
      for l in txt['lines_lst']:
        data_str+='%s$%s\n' %(l['normalization'],
                              self.process_trs(l['translation']))
    self.dump(data_str, path+'/sum_eng_%s.csv' %prefix)

  def export_for_giza(self, path, prefix):
    data_str_normalization = ''
    data_str_translation = ''
    for txt in self.texts:
      for l in txt['lines_lst']:
        data_str_normalization+='%s\n' %l['normalization']
        data_str_translation+='%s\n' %self.process_trs(l['translation'])
    self.dump(data_str_normalization, path+'/sumerian_'+prefix)
    self.dump(data_str_translation, path+'/english_'+prefix)

  def normalize(self, translit):
    n_lst = []
    if '($' in translit:
      re_translit_comment = re.compile(r'(( |-|)\(\$.+\$\)( |-|))')
      translit = re_translit_comment.sub('', translit)
    for token in translit.split(' '):
      t = transliteration(token)
      if t.defective:
        n = 'X'
      else:
        n = t.normalization
      n_lst.append(n)
    return ' '.join(n_lst)

  def dump(self, data, filename):
    with codecs.open(filename, 'w', 'utf-8') as dump:
      dump.write(data)

  def process_trs(self, line):
    '''
    Functions to process translated. 
    '''
    line = self.add_punct_spaces(line)
    line = self.escape_numbers(line)
    return line
  
  def add_punct_spaces(self, line):
    '''
    Add spaces to translation before and after punctuation signs.
    Remove square brackets. 
    '''
    line = self.re_brc.sub('', line)
    line = line.replace('...', '…')
    for sq_brc in ['[', ']']:
      line = line.replace(sq_brc, '')
    i = 0
    while i < len(line):
      c = line[i]
      if i>0 and c in self.punct_lst:
        if line[i-1] not in [' ']:
          line = '%s %s' %(line[:i], line[i:])
          i+=1
      if i+1 < len(line) and c in self.punct_lst:  
        if line[i+1] not in [' ', '\n']:
          line = '%s %s' %(line[:i+1], line[i+1:])
          i+=1
      i+=1
    return line.strip(' ')

  def escape_numbers(self, line):
    '''
    Replace numbers in translation or sequences of numbers with NUMB.
    '''
    replace_lst = []
    for t in line.split(' '):
      t_clean = t.replace("/", "").replace("…", "")
      if is_int(t_clean)==True or t in ['Ø', 'n', '+', 'n+']:
        replace_lst.append(t)
      elif t[-2:] in ['th', 'st', 'rd', 'nd'] and is_int(t[:-2])==True:
        line = line.replace(t, "NUMB"+t[-2:])
        (line, replace_lst) = self.replace_numb(line, replace_lst)
      else:
        (line, replace_lst) = self.replace_numb(line, replace_lst)
    return line

  def replace_numb(self, line, replace_lst):
    '''
    Subfunction of `self.escape_numbers()`.
    '''
    if len(replace_lst):
      line = line.replace(" ".join(replace_lst), "NUMB")
      replace_lst = []
    return (line, replace_lst)  

#---/ATF normalizer/-----------------------------------------------------------
#
class transliteration:

  def __init__(self, translit):
    self.defective = False
    self.raw_translit = translit
    translit = translit.strip(' ')
    translit = translit.replace('source: ', 'source:')
    if ' ' in translit:
      self.defective = True
      return None
    for expt in ['_', '...', 'line', '(X', 'X)', '.X',
                 ' X', 'Xbr','-X', 'ṭ', 'ṣ', 'missing']:
      if expt in translit or expt.lower() in translit.lower():
        self.defective = True
        return None
    if '<<' in translit:
      re_extra_sign = re.compile(r'(( |-|)<<.+>>( |-|))')
      translit = re_extra_sign.sub('', translit)
    if translit.lower()!=translit:
      # ! PROBLEMATIC: TOO MANY SIGNS IGNORED
      # ! CHANGE THIS
##      self.defective = True
##      return None
      pass
    extra = re.compile('(\[|\]|\{\?\}|\{\!\}|\\\|/|<|>)')
    translit = extra.sub('', translit)
    translit = self.standardize_translit(translit)
    translit = self.remove_determinatives(translit)
    self.base_translit = translit
    self.sign_list = self.parse_signs(translit)
    for el in self.sign_list:
      if 'x' in el['value'].lower() and '×' not in el['value'].lower():
        self.defective = True
        return None
      if '(' in el['value']:
        pass
        print([self.raw_translit, self.base_translit, el['value'], self.sign_list])
    i=0
    while i < len(self.sign_list):
      self.sign_list[i] = self.get_unicode_index(self.sign_list[i])
      i+=1
    self.set_normalizations()

  def parse_signs(self, translit):
    signs_lst = []
    re_x_index = re.compile(r'(?P<a>[\w])x')
    re_x_sign = re.compile(r'(ₓ\(.+\))')
    re_brc = re.compile(r'(\(.+\))')
    re_source = re.compile(r'(?P<a>.+)(?P<b>\(source:)(?P<c>[^)]+)(?P<d>\))')
    re_index = re.compile(r'(?P<sign>[^\d]+)(?P<index>\d+)')
    re_brc_div = re.compile(r'(?P<a>\([^\)]+)(?P<b>-+)(?P<c>[^\(]+\))')
    if re_brc_div.search(translit):
      translit = re_brc_div.sub(lambda m: m.group().replace('-',"="),
                                translit)    
    for sign in list(filter(lambda x: x!='', translit.split('-'))):
      index = ''
      emendation = ''
      value_of = ''
      if re_x_index.search(sign):
        sign = re_x_index.sub('\g<a>ₓ', sign)
      if 'ₓ(' in sign.lower():
        index='x'
        value_of = re_x_sign.search(sign).group().strip('ₓ()').replace('=',"-")
        sign = re_x_sign.sub('', sign)
      if re_brc.search(sign):
        if sign[0]=='(' and sign[-1]==')':
          sign = sign.strip('()')
        else:
          value_of = re_brc.search(sign).group().strip('()').replace('=',"-")
          sign = re_brc.sub('', sign)
      if 'x' in sign.lower() and len(sign)>1:
        pass
      if re_source.search(sign):
        emendation = re_source.sub(r'\g<c>', sign).replace('=',"-")
        sign = re_source.sub(r'\g<a>', sign)
      if re_index.search(sign):
        i = 0
        for x in re_index.finditer(sign):
          if i==0:
            index = x.groupdict()['index']
            sign = x.groupdict()['sign']
          else:
            pass
            #print(self.raw_translit, sign, i, x.groupdict()['sign'], x.groupdict()['index'])
          i+=1
      signs_lst.append({'value': sign,
                        'index': index,
                        'emendation': emendation,
                        'value_of': value_of
                        })
    return signs_lst

  def set_normalizations(self):
    norm_flat_lst = [s['value'] for s in self.sign_list]
    norm_unicode_lst = [s['u_sign'] for s in self.sign_list]
    i = 0
    self.normalization = ''
    self.normalization_u = ''
    while i < len(norm_flat_lst):
      if self.normalization:
        if self.normalization[-1]==norm_flat_lst[i][0]:
          self.normalization+=norm_flat_lst[i][1:]
          self.normalization_u+=norm_unicode_lst[i][1:]
        else:
          self.normalization+=norm_flat_lst[i]
          self.normalization_u+=norm_unicode_lst[i]
      else:
        self.normalization+=norm_flat_lst[i]
        self.normalization_u+=norm_unicode_lst[i]
      i+=1
  
  def standardize_translit(self, translit):
    std_dict = {'š':'c', 'ŋ':'j', '₀':'0', '₁':'1', '₂':'2',
                '₃':'3', '₄':'4', '₅':'5', '₆':'6', '₇':'7',
                '₈':'8', '₉':'9', '+':'-', 'Š':'C', 'Ŋ':'J',
                'sz': 'c', 'SZ': 'C', '·':'', '°':'', '#':'',
                '!':'', '?': ''}
    for key in std_dict.keys():
      translit = translit.replace(key, std_dict[key])
    times = re.compile(r'(?P<a>[\w])x(?P<b>[\w])')
    if times.search(translit):
      translit = times.sub('\g<a>×\g<b>', translit)
    return translit

  def get_unicode_index(self, sign_dict):
    vow_lst = ['a', 'A', 'e', 'E', 'i', 'I', 'u', 'U']
    re_last_vow = re.compile(r'(%s)' %('|'.join(vow_lst)))
    sign_dict['u_sign'] = sign_dict['value']
    if sign_dict['index'] not in ['', 'x']:
      val = sign_dict['value']
      try:
        v = re_last_vow.findall(val)[-1]
      except:
        print(val, self.raw_translit)
      esc = chr((vow_lst.index(v)+1)*1000+int(sign_dict['index']))
      i = val.rfind(v)
      u_sign = '%s%s%s' %(val[:i], esc, val[i+1:])
      sign_dict['u_sign']=u_sign
    return sign_dict    

  def revert_unicode_index(self, u_sign):
    vow_lst = ['a', 'A', 'e', 'E', 'i', 'I', 'u', 'U']    
    i =0
    while i < len(u_sign):
      n = ord(u_sign[i])
      if n > 1000:
        vow_i = int(str(n)[0])-1
        index = int(str(n)[2:])
        return {'value': u_sign[:i]+vow_lst[vow_i]+u_sign[i+1:],
                'index': index}
      i+=1

  def remove_determinatives(self, translit):
    det = re.compile('(\{.*?\})')
    return det.sub('', translit)

#---/CoNLL file functions/-----------------------------------------------------
#
class conll_file:
  '''
  Parses the CoNLL data.
  '''
  def __init__(self, path):
    self.tokens_lst = []
    self.info_dict = {}
##    self.corpus = 'Secondary'
##    if 'ORACC Sumerian' in str(path):
##      self.corpus = 'Primary'
    with codecs.open(str(path.resolve()), 'r', 'utf-8') as f:
      self.data = f.read()
    self.parse()

  def parse(self):
    token_ID = ''
    for l in self.data.splitlines():
      if l:
        if l[0] not in ['#', ' ']:
          self.add_token(l.split('\t'), token_ID)
        elif l[0]=='#':
          if ': ' in l:
            info_lst = l.strip('# ').split(': ')
            key = info_lst[0].strip(' ')
            value = ': '.join(info_lst[1:]).strip(' ')
            self.info_dict[key] = value
          elif '.' in l:
            token_ID = l.strip('# ')
          else:
            l = l.strip('# ')
            if l:
              if 'WORD' in l and 'ID' in l:
                self.info_dict['legend'] = l.split('\t')
              else:
                self.info_dict['title'] = l
    #print(len(self.tokens_lst))
                
  def add_token(self, token_lst, token_ID):
    token_dict = {'TOKEN ID': token_ID}
    if 'legend' not in self.info_dict.keys():
      if token_lst[-1] not in ['_', 'proper', 'emesal', 'glossakk']:
        print('-1', token_lst[-1])
      legend = ['ID', 'WORD', 'BASE', 'POS', 'SENSE']
    else:
      legend = self.info_dict['legend']
    i = 0
    while i < len(legend):
      if legend[i]=='POS':
        token_dict[legend[i]] = self.adjust_POS(token_lst[i])
      else:
        token_dict[legend[i]] = token_lst[i]
      i+=1
    if 'WORD' in token_dict.keys():
      tw = transliteration(token_dict['WORD'])
      if tw.defective==False:
        token_dict['WORD'] = [tw.normalization, tw.normalization_u]
    if 'BASE' in token_dict.keys():
      tb = transliteration(token_dict['BASE'])
      if tb.defective==False:
        token_dict['BASE'] = [tb.normalization, tb.normalization_u]
    if self.filter_token(token_dict)!=False:
      self.tokens_lst.append(token_dict)
    
  def adjust_POS(self, POS_tag):
    #Escape '/' in the tags to make affixtrain run correctly.
    if '/' in POS_tag:
      POS_tag = POS_tag.split('/')[0]
    if ':' in POS_tag:
      POS_tag = POS_tag.split(':')[0]
    return POS_tag

  def filter_token(self, t):
    if 'LANG' in t.keys():
      if 'akk' in t['LANG']:
        return False
    try:
      if '_' in ''.join(t['WORD'])+''.join(t['BASE'])+t['POS']:
        return False
    except KeyError:
      return False
    if type(t['WORD'])!=list or type(t['BASE'])!=list:
      return False
    return True

#---/CoNLL corpus functions/---------------------------------------------------
#
class conll_collection:
  '''
  Сollects .conll files and exports the data for training.
  '''
  def __init__(self, split_path, conll_path):
    self.conll_lst = []
    self.collect_files(conll_path)
    self.make_tokens_dict()
    self.tokens_dict = self.load_tokens_dict()
    self.export_data()

  def collect_files(self, path):
    '''
    Collects CoNLL files from given path.
    '''
    self.legends = []
    for f in os.listdir(path):
      if '.conll' in f:
        c = conll_file('%s/%s' %(path, f))
        #c.corpus = 'Primary'
        self.conll_lst.append(c)
        if 'legend' in c.info_dict.keys():
          self.legends.append(c.info_dict['legend'])

  def export_data(self):
    pass
        

##  def export_data(self):
##    self.export_training_data()
##    self.export_testing_data()
##    self.export_training_data(True)
##    self.export_testing_data(True)
##    
##  def export_training_data(self, primary_only=''):
##    csv_norm_dump = ''
##    csv_norm_u_dump = ''
##    primary_prefix=''
##    if primary_only==True:
##      primary_prefix='_primary'
##    for k in self.tokens_dict.keys():
##      if self.tokens_dict[k]['EX_CLASS']=='train':
##        if (primary_only==True and self.tokens_dict[k]['CORPUS']=='Primary') or \
##           primary_only in [False, '']:
##          csv_norm_dump+='\t'.join([self.tokens_dict[k]['WORD'][0],
##                                    self.tokens_dict[k]['BASE'][0],
##                                    self.tokens_dict[k]['POS']+'\n'])
##          csv_norm_u_dump+='\t'.join([self.tokens_dict[k]['WORD'][1],
##                                    self.tokens_dict[k]['BASE'][1],
##                                    self.tokens_dict[k]['POS']+'\n'])
##    self.dump(csv_norm_dump, 'training_data%s_norm' %(primary_prefix))
##    self.dump(csv_norm_u_dump, 'training_data%s_norm_u' %(primary_prefix))
##
##  def export_testing_data(self, primary_only=''):
##    csv_norm_dump = ''
##    csv_norm_u_dump = ''
##    csv_norm_test_dump = ''
##    csv_norm_u_test_dump = ''
##    csv_norm_stem_dump = ''
##    csv_norm_stem_u_dump = ''
##    primary_prefix=''
##    if primary_only==True:
##      primary_prefix='_primary'
##    for k in self.tokens_dict.keys():
##      if self.tokens_dict[k]['EX_CLASS']=='test':
##        if (primary_only==True and self.tokens_dict[k]['CORPUS']=='Primary') or \
##           primary_only in [False, '']:
##          csv_norm_dump+='\t'.join([self.tokens_dict[k]['WORD'][0],
##                                    self.tokens_dict[k]['BASE'][0],
##                                    self.tokens_dict[k]['POS']+'\n'])
##          csv_norm_u_dump+='\t'.join([self.tokens_dict[k]['WORD'][1],
##                                      self.tokens_dict[k]['BASE'][1],
##                                      self.tokens_dict[k]['POS']+'\n'])
##          csv_norm_test_dump+=self.tokens_dict[k]['WORD'][0]+'\n'
##          csv_norm_u_test_dump+=self.tokens_dict[k]['WORD'][1]+'\n'
##          csv_norm_stem_dump+=self.tokens_dict[k]['BASE'][0]+'\n'
##          csv_norm_stem_u_dump+=self.tokens_dict[k]['BASE'][1]+'\n'
##    self.dump(csv_norm_dump, 'testing_full_data%s_norm' %(primary_prefix))
##    self.dump(csv_norm_u_dump, 'testing_full_data%s_norm_u' %(primary_prefix))
##    self.dump(csv_norm_test_dump, 'testing_data%s_norm' %(primary_prefix))
##    self.dump(csv_norm_u_test_dump, 'testing_data%s_norm_u'%(primary_prefix))
##    self.dump(csv_norm_stem_dump, 'testing_stem_data%s_norm' %(primary_prefix))
##    self.dump(csv_norm_stem_u_dump, 'testing_stem_data%s_norm_u'%(primary_prefix))

  def make_tokens_dict(self):
    self.tokens_dict = {}
    exx_counter = 0
    for c in self.conll_lst:
      corpus = c.corpus
      for t in c.tokens_lst:
        t_key = '\t'.join([t['WORD'][0], t['BASE'][1], t['POS']])
        self.tokens_dict[t_key] = t
        self.tokens_dict[t_key]['COUNT'] = 0
        self.tokens_dict[t_key]['EX_CLASS'] = 'train'
        self.tokens_dict[t_key]['CORPUS'] = corpus
        if exx_counter % 8==0:
          self.tokens_dict[t_key]['EX_CLASS'] = 'develop'
        if exx_counter % 9==0:
          self.tokens_dict[t_key]['EX_CLASS'] = 'test'
        exx_counter+=1
        self.tokens_dict[t_key]['COUNT']+=1
        if corpus=='Primary' and self.tokens_dict[t_key]['CORPUS']!=corpus:
          self.tokens_dict[t_key]['CORPUS']=corpus
    self.dump(json.dumps(self.tokens_dict), 'tokens_dict.json')

  def load_tokens_dict(self):
    with open('tokens_dict.json') as data_file:
      return json.load(data_file)
    
  def dump(self, data, filename):
    with codecs.open(filename, 'w', 'utf-8') as dump:
      dump.write(data)

if __name__ == "__main__":
  pass
##  path = Path(
##    os.path.join('cdli_atf_20170816_UrIII_admin_translated_public.txt'))
##  a = atf_parser(path)
















