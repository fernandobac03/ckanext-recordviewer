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
    
    def algo(self, data=None, errors=None):

 	from ckan.lib.search import SearchError, SearchQueryError
        package_type = 'dataset' #only for dataset type 'dataset'

        try:
            context = {'model': model, 'user': c.user,
                       'auth_user_obj': c.userobj}
            check_access('site_read', context)
        except NotAuthorized:
            abort(403, _('Not authorized to see this page'))

        # unicode format (decoded from utf8)
        q = c.q = request.params.get('q', u'')
        c.query_error = False
        page = h.get_page_number(request.params)

        limit = int(config.get('ckan.datasets_per_page', 20))

        # most search operations should reset the page counter:
        params_nopage = [(k, v) for k, v in request.params.items()
                         if k != 'page']

        def drill_down_url(alternative_url=None, **by):
            return h.add_url_param(alternative_url=alternative_url,
                                   controller='package', action='search',
                                   new_params=by)

        c.drill_down_url = drill_down_url

        def remove_field(key, value=None, replace=None):
            return h.remove_url_param(key, value=value, replace=replace,
                                      controller='package', action='search')

        c.remove_field = remove_field

        sort_by = request.params.get('sort', None)
        params_nosort = [(k, v) for k, v in params_nopage if k != 'sort']

        def _sort_by(fields):
            """
            Sort by the given list of fields.
            Each entry in the list is a 2-tuple: (fieldname, sort_order)
            eg - [('metadata_modified', 'desc'), ('name', 'asc')]
            If fields is empty, then the default ordering is used.
            """
            params = params_nosort[:]

            if fields:
                sort_string = ', '.join('%s %s' % f for f in fields)
                params.append(('sort', sort_string))
            return search_url(params, package_type)

        c.sort_by = _sort_by
        if not sort_by:
            c.sort_by_fields = []
        else:
            c.sort_by_fields = [field.split()[0]
                                for field in sort_by.split(',')]

        def pager_url(q=None, page=None):
            params = list(params_nopage)
            params.append(('page', page))
            return search_url(params, package_type)

        c.search_url_params = urlencode(_encode_params(params_nopage))

        try:
            c.fields = []
            # c.fields_grouped will contain a dict of params containing
            # a list of values eg {'tags':['tag1', 'tag2']}
            c.fields_grouped = {}
            search_extras = {}
            fq = ''
            for (param, value) in request.params.items():
                if param not in ['q', 'page', 'sort'] \
                        and len(value) and not param.startswith('_'):
                    if not param.startswith('ext_'):
                        c.fields.append((param, value))
                        fq += ' %s:"%s"' % (param, value)
                        if param not in c.fields_grouped:
                            c.fields_grouped[param] = [value]
                        else:
                            c.fields_grouped[param].append(value)
                    else:
                        search_extras[param] = value

            context = {'model': model, 'session': model.Session,
                       'user': c.user, 'for_view': True,
                       'auth_user_obj': c.userobj}

            if package_type and package_type != 'dataset':
                # Only show datasets of this particular type
                fq += ' +dataset_type:{type}'.format(type=package_type)
            else:
                # Unless changed via config options, don't show non standard
                # dataset types on the default search page
                if not asbool(
                        config.get('ckan.search.show_all_types', 'False')):
                    fq += ' +dataset_type:dataset'

            facets = OrderedDict()

            default_facet_titles = {
                'organization': _('Organizations'),
                'groups': _('Groups'),
                'tags': _('Tags'),
                'res_format': _('Formats'),
                'license_id': _('Licenses'),
                }

            for facet in h.facets():
                if facet in default_facet_titles:
                    facets[facet] = default_facet_titles[facet]
                else:
                    facets[facet] = facet

            # Facet titles
            for plugin in p.PluginImplementations(p.IFacets):
                facets = plugin.dataset_facets(facets, package_type)

            c.facet_titles = facets

            data_dict = {
                'q': q,
                'fq': fq.strip(),
                'facet.field': facets.keys(),
                'rows': limit,
                'start': (page - 1) * limit,
                'sort': sort_by,
                'extras': search_extras,
                'include_private': asbool(config.get(
                    'ckan.search.default_include_private', True)),
            }

            query = get_action('package_search')(context, data_dict)
            c.sort_by_selected = query['sort']

            c.page = h.Page(
                collection=query['results'],
                page=page,
                url=pager_url,
                item_count=query['count'],
                items_per_page=limit
            )
            c.search_facets = query['search_facets']
            c.page.items = query['results']
        except SearchQueryError, se:
            # User's search parameters are invalid, in such a way that is not
            # achievable with the web interface, so return a proper error to
            # discourage spiders which are the main cause of this.
            log.info('Dataset search query rejected: %r', se.args)
            abort(400, _('Invalid search query: {error_message}')
                  .format(error_message=str(se)))
        except SearchError, se:
            # May be bad input from the user, but may also be more serious like
            # bad code causing a SOLR syntax error, or a problem connecting to
            # SOLR
            log.error('Dataset search error: %r', se.args)
            c.query_error = True
            c.search_facets = {}
            c.page = h.Page(collection=[])
        c.search_facets_limits = {}
        for facet in c.search_facets.keys():
            try:
                limit = int(request.params.get('_%s_limit' % facet,
                            int(config.get('search.facets.default', 10))))
            except ValueError:
                abort(400, _('Parameter "{parameter_name}" is not '
                             'an integer').format(
                      parameter_name='_%s_limit' % facet))
            c.search_facets_limits[facet] = limit

        self._setup_template_variables(context, {},
                                       package_type=package_type)

#        return render(self._search_template(package_type),
#                       extra_vars={'dataset_type': package_type})




#	variable=''

#        if request.method== 'POST':                                           
#            print("!!!!!!!!!!!!!!!!!!1 POsted FROM EXTENSION!!!!!!!!!!!1")    
#            variable = request.params.get('sel')
        
#	c.link = str("/dataset/dictionary/new_dict/"+"prueba")
#	return render("package/new_data_dict.html",extra_vars={'package_id':variable})
	return render("record/view_record.html")

################################################################
 
 
#Agregando para pruebas


#######################################################################

 def recordurl(self, package_name, resource_id, record_id):

        """
        View an individual record
        :param id:
        :param resource_id:
        :param record_id:
        :return: html
        """
        #self._load_data(package_name, resource_id, record_id)

        #view_cls = resource_view_get_view(c.resource)

	#return view_cls.render_record(c)
	return render("dataset/"+package_name+"/resource/"+resource_id+"/record/"+record_id")


 def _load_data(self, package_name, resource_id, record_id):
        """
        Load the data for dataset, resource and record (into C var)
        @param package_name:
        @param resource_id:
        @param record_id:
        @return:
        """
        self.context = {'model': model, 'session': model.Session, 'user': c.user or c.author}

        # Try & get the resource
        try:
            c.resource = get_action('resource_show')(self.context, {'id': resource_id})
            c.package = get_action('package_show')(self.context, {'id': package_name})
            # required for nav menu
            c.pkg = self.context['package']
            c.pkg_dict = c.package
            record = get_action('record_show')(self.context, {'resource_id': resource_id, 'record_id': record_id})
            c.record_dict = record['data']
            record_field_types = {f['id']: f['type'] for f in record['fields']}

        except NotFound:
            abort(404, _('Resource not found'))
        except NotAuthorized:
            abort(401, _('Unauthorized to read resource %s') % package_name)

        field_names = {
            'image': c.resource.get('_image_field', None),
            'title': c.resource.get('_title_field', None),
            'latitude': None,
            'longitude': None
        }
        # Get lat/long fields
        # Loop through all the views - if we have a tiled map view with lat/lon fields
        # We'll use those fields to add the map
        views = p.toolkit.get_action('resource_view_list')(self.context, {'id': resource_id})
        for view in views:
            if view['view_type'] == TILED_MAP_TYPE:
                field_names['latitude'] = view[u'latitude_field']
                field_names['longitude'] = view[u'longitude_field']
                break

        # If this is a DwC dataset, add some default for image and lat/lon fields
        if c.resource['format'].lower() == 'dwc':
            for field_name, dwc_field in [('latitude', 'decimalLatitude'), ('longitude', 'decimalLongitude')]:
                if dwc_field in c.record_dict:
                    field_names[field_name] = dwc_field

        # Assign title based on the title field
        c.record_title = c.record_dict.get(field_names['title'], 'Record %s' % c.record_dict.get('_id'))

        # Sanity check: image field hasn't been set to _id
        if field_names['image'] and field_names['image'] != '_id':

            try:
                image_field_type = record_field_types[field_names['image']]
            except KeyError:
                pass
            else:
                default_copyright = '<small>&copy; The Trustees of the Natural History Museum, London</small>'
                licence_id = c.resource.get('_image_licence') or 'cc-by'
                short_licence_id = licence_id[:5].lower()
                # licence_id = c.resource.get('_image_licence') or 'ODC-BY-1.0'
                # Set default licence - cc-by
                licence = model.Package.get_license_register()['cc-by']
                # Try and overwrite default licence with more specific one
                for l_id in [licence_id, short_licence_id]:
                    try:
                        licence = model.Package.get_license_register()[l_id]
                        break
                    except KeyError:
                        continue

                default_licence = 'Licence: %s' % link_to(licence.title, licence.url, target='_blank')

                image_field_value = c.record_dict.pop(field_names['image'])

                if image_field_value:

                    c.images = []

                    # DOn't test for field type, just try and convert image to json
                    try:
                        images = json.loads(image_field_value)
                    except ValueError:
                        # String field value
                        try:
                            # Pop the image field so it won't be output as part of the record_dict / field_data dict (see self.view())
                            c.images = [{'title': c.record_title, 'href': image.strip(), 'copyright': '%s<br />%s' % (default_licence, default_copyright)} for image in image_field_value.split(';') if image.strip()]
                        except (KeyError, AttributeError):
                            # Skip errors - there are no images
                            pass
                    else:
                        for image in images:
                            href = image.get('identifier', None)
                            if href:
                                license_link = link_to(image.get('license'), image.get('license')) if image.get('license', None) else None
                                c.images.append({
                                    'title': image.get('title', None) or c.record_title,
                                    'href': href,
                                    'copyright': '%s<br />%s' % (license_link or default_licence, image.get('rightsHolder', None) or default_copyright),
                                    'record_id': record_id,
                                    'resource_id': resource_id,
                                    'link': url_for(
                                        controller='ckanext.nhm.controllers.record:RecordController',
                                        action='view',
                                        package_name=package_name,
                                        resource_id=resource_id,
                                        record_id=record_id
                                    ),
                                })


        if field_names['latitude'] and field_names['longitude']:
            latitude, longitude = c.record_dict.get(field_names['latitude']), c.record_dict.get(field_names['longitude'])

            if latitude and longitude:
                c.record_map = json.dumps({
                    'type': 'Point',
                    'coordinates': [longitude, latitude]
})




