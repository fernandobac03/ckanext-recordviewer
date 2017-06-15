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
import ckan.plugins as p
import ckan.lib.render

from ckan.common import config
import ckan.controllers.package as pkgcontroller


log = logging.getLogger(__name__)

pkggg = pkgcontroller.PackageController()


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

        datarecord= self.getRecordData(resource_id, record_id)

        vars = {'data': datarecord, 'errors': errors,
                'error_summary': error_summary, 'action': 'edit',
     #           'resource_form_snippet': self._resource_form(package_type),
                'dataset_type': package_type}



        return render('recordviewer/record/record_read.html', extra_vars=vars)

    def getRecordData(self, resource_id, record_id):
        """Setup variables available to templates"""

        #self.datastore_fields = self._get_datastore_fields(data_dict['resource']['id'])

        #field_separator = config.get("ckanext.gallery.field_separator", ';')
        #records_per_page = config.get("ckanext.gallery.records_per_page", 30)

        #current_page = request.params.get('page', 1)

        #image_field = data_dict['resource_view'].get('image_field')
        #gallery_title_field = data_dict['resource_view'].get('gallery_title_field', None)
        #modal_title_field = data_dict['resource_view'].get('modal_title_field', None)

        #thumbnail_params = data_dict['resource_view'].get('thumbnail_params', None)
        #thumbnail_field = data_dict['resource_view'].get('thumbnail_field', None)

        #image_list = []
        #records = []
        #item_count = 0

        # Only try and load images, if an image field has been selected
        if record_id:

         #   offset = (int(current_page) - 1) * records_per_page

            # We only want to get records that have both the image field populated
            # So add filters to the datastore search params
            params = {
                'resource_id': resource_id,
           #     'limit': records_per_page,
          #      'offset': offset,
                #'filters': {
                #    image_field: IS_NOT_NULL
                #}
            }

            ## Add filters from request
            #filter_str = request.params.get('filters')
            #if filter_str:
            #    for f in filter_str.split('|'):
            #        try:
            #            (name, value) = f.split(':')
            #            params['filters'][name] = value

#                    except ValueError:
 #                       pass

            # Full text filter
            fulltext = request.params.get('q')
            if fulltext:
                params['q'] = fulltext

            context = {'model': model, 'session': model.Session, 'user': c.user or c.author}
            data = toolkit.get_action('datastore_search')(context, params)


            item_count = data.get('total', 0)
            records = data['records']

            for record in data['records']:

                try:
                    images = record.get(image_field, None).split(field_separator)
                except AttributeError:
                    pass
                else:
                    # Only add if we have an image
                    if images:

                        gallery_title = record.get(gallery_title_field, None)
                        modal_title = record.get(modal_title_field, None)
                        thumbnails = record.get(thumbnail_field, None).split(field_separator)

                        for i, image in enumerate(images):

                            image = image.strip()

                            if thumbnails:
                                try:
                                    thumbnail = thumbnails[i]
                                except IndexError:
                                    # If we don't have a thumbnail with the same index
                                    # Use the first thumbnail image
                                    thumbnail = thumbnails[0]

                                thumbnail = thumbnail.strip()

                                # If we have thumbnail params, add them here
                                if thumbnail_params:
                                    q = '&' if '?' in thumbnail else '?'
                                    thumbnail += q + thumbnail_params
                            if (record_id==record['_id']):
                                image_list.append({
                                    'url': image,
                                    'thumbnail': thumbnail,
                                    'gallery_title': gallery_title,
                                    'modal_title': modal_title,
                                    'record_id': record['_id']
                                })

        page_params = {
            'collection':records,
            'page': current_page,
            'url': self.pager_url,
            'items_per_page': records_per_page,
            'item_count': item_count,
        }

        # Add filter params to page links
        for key in ['q', 'filters']:
            value = request.params.get(key)
            if value:
                page_params[key] = value

        page = h.Page(**page_params)

        #return {
        #    'images': image_list,
        #    'datastore_fields':  self.datastore_fields,
        #    'defaults': {},
        #    'resource_id': data_dict['resource']['id'],
        #    'package_name': data_dict['package']['name'],
        #    'page': page
        #}


        return {
            'recordinf': image_list,
            'resource_id': resource_id,
            'record_id': record_id
        }

