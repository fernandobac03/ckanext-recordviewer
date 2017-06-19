import logging
import ckan.plugins as p
from ckan.lib.base import BaseController
import ckan.lib.helpers as h
from ckan.common import OrderedDict, _, json, request, c, g, response
from paste.deploy.converters import asbool
from urllib import urlencode
import datetime
import mimetypes
import cgi
import ckan.logic as logic
import ckan.lib.base as base
import ckan.lib.maintain as maintain
import ckan.lib.i18n as i18n
import ckan.lib.navl.dictization_functions as dict_fns
import ckan.model as model
import ckan.lib.datapreview as datapreview
import ckan.lib.plugins
import ckan.lib.uploader as uploader
import ckan.lib.render
import ckan.plugins.toolkit as toolkit

from ckan.common import config
import ckan.controllers.package as pkgcontroller


log = logging.getLogger(__name__)
render = base.render
abort = base.abort
redirect = h.redirect_to

NotFound = logic.NotFound
NotAuthorized = logic.NotAuthorized
ValidationError = logic.ValidationError
check_access = logic.check_access
get_action = logic.get_action
tuplize_dict = logic.tuplize_dict
clean_dict = logic.clean_dict
parse_params = logic.parse_params
flatten_to_string_key = logic.flatten_to_string_key

lookup_package_plugin = ckan.lib.plugins.lookup_package_plugin

get_action = logic.get_action


def _encode_params(params):
    return [(k, v.encode('utf-8') if isinstance(v, basestring) else str(v))
            for k, v in params]

class RVController(BaseController):
 

    def _setup_template_variables(self, context, data_dict, package_type=None):
        return lookup_package_plugin(package_type).\
            setup_template_variables(context, data_dict)

    def index(self):
	#print(sys.path)
	return p.toolkit.render("base1.html")

    def record_read(self, id, resource_id, record_id, data=None, errors=None,
                      error_summary=None):

        if request.method == 'POST' and not data:
            #data = data or \
               # clean_dict(dict_fns.unflatten(tuplize_dict(parse_params(
           #                                                request.POST))))
            ## we don't want to include save as it is part of the form
            del data['save']

            context = {'model': model, 'session': model.Session,
                       'api_version': 3, 'for_edit': True,
                       'user': c.user, 'auth_user_obj': c.userobj}

            data['package_id'] = id
            try:
                if resource_id:
                    data['id'] = resource_id
              #      get_action('resource_update')(context, data)
             #   else:
             #       get_action('resource_create')(context, data)
            except ValidationError, e:
                errors = e.error_dict
                error_summary = e.error_summary
                return self.resource_edit(id, resource_id, data,
                                          errors, error_summary)
            except NotAuthorized:
                abort(403, _('Unauthorized to edit this resource'))
            h.redirect_to(controller='package', action='resource_read', id=id,
                          resource_id=resource_id)

        context = {'model': model, 'session': model.Session,
                   'api_version': 3, 'for_edit': True,
                   'user': c.user, 'auth_user_obj': c.userobj}
      #  pkg_dict = get_action('package_show')(context, {'id': id})
       # if pkg_dict['state'].startswith('draft'):
        #    # dataset has not yet been fully created
         #   resource_dict = get_action('resource_show')(context,
          #                                              {'id': resource_id})
           # fields = ['url', 'resource_type', 'format', 'name', 'description',
            #          'id']
          #  data = {}
             #for field in fields:
             #   data[field] = resource_dict[field]
        #    return self.new_resource(id, data=data)
        ## resource is fully created
        try:
	     resource_dict =""#agregado por mi
     #       resource_dict = get_action('resource_show')(context,
      #                                                  {'id': resource_id})
        except NotFound:
            abort(404, _('Resource not found'))
        #c.pkg_dict = pkg_dict
        c.resource = resource_dict
        # set the form action
        c.form_action = h.url_for(controller='package',
                                  action='resource_edit',
                                  resource_id=resource_id,
                                  id=id)
        if not data:
            data = resource_dict

        #package_type = pkg_dict['type'] or 'dataset'
	package_type = 'dataset' # agregado por mi
        errors = errors or {}
        error_summary = error_summary or {}

        datarecord= self.getRecordData(id, resource_id, record_id)

        vars = {'data': datarecord, 'errors': errors,
                'error_summary': error_summary, 'action': 'edit',
                'dataset_type': package_type}

        return render('recordviewer/record/record_read.html', extra_vars=vars)

    def getRecordData(self, id, resource_id, record_id):
        """Setup variables available to templates"""

        record_list = []
        records = []
        item_count = 0
	
        # Only try and load record, if record_id exist
        if record_id:

            # We only want to get records that have record_id as id
            # So add filters to the datastore search params
            params = {
                'resource_id': resource_id,
                'filters': {
                    '_id': record_id
                }
            }

            context = {'model': model, 'session': model.Session, 'user': c.user or c.author}
            data = toolkit.get_action('datastore_search')(context, params)

            item_count = data.get('total', 0)
            records = data['records']

            for record in data['records']:
                record_list.append({
                    'record_id': record['_id'],
                    'record': record
                })

        page_params = {
            'collection':records,
            #'page': current_page,
            #'url': self.pager_url,
            #'items_per_page': records_per_page,
            'item_count': item_count,
        }
        return {
            'recordinf':  record_list,
            'resource_id': resource_id,
            'record_id': record_id,
	    'package_id': id
        }

