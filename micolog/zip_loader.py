# Wrapper for loading templates from zipfile.
import zipfile,logging,os
from django.template import TemplateDoesNotExist
from django.conf import settings
logging.debug("zipload imported")
zipfile_cache={}
_TEMPLATES_='templates'
def get_from_zipfile(zipfilename,name):
    logging.debug("get_from_zipfile(%s,%s)"%(zipfilename,name))
    zipfile_object = zipfile_cache.get(zipfilename)
    if zipfile_object is None:
      try:
        zipfile_object = zipfile.ZipFile(zipfilename)
      except (IOError, RuntimeError), err:
        logging.error('Can\'t open zipfile %s: %s', zipfilename, err)
        zipfile_object = ''
      zipfile_cache[zipfilename] = zipfile_object

    if zipfile_object == '':
      return None
    try:
      data = zipfile_object.read(name)
      return data
    except (KeyError, RuntimeError), err:
      return None


def get_template_sources(template_dirs=None):
    if not template_dirs:
        template_dirs = settings.TEMPLATE_DIRS
    for template_dir in template_dirs:
        if template_dir.endswith(".zip"):
            yield template_dir#os.path.join(template_dir, zip_name)

def load_template_source(template_name, template_dirs=None):
    tried = []
    logging.debug("zip_loader::load_template_source:"+template_name)
##    spart= template_name.split('/')
##    theme_name=spart[0]
##
##    zipfile=theme_name+".zip"
##    template_file=os.path.join(theme_name,*spart[1:])
    template_file='/'.join((_TEMPLATES_, template_name))
    for zipfile in get_template_sources(template_dirs):
        try:
            return (get_from_zipfile(zipfile,template_file), os.path.join(zipfile,template_file))
        except IOError:
            tried.append(zipfile)
    if tried:
        error_msg = "Tried %s" % tried
    else:
        error_msg = "Your TEMPLATE_DIRS setting is empty. Change it to point to at least one template directory."
    raise TemplateDoesNotExist, error_msg

load_template_source.is_usable = True
