from bq_conductor.bq_manager.bq_client import BQClient
from google.cloud.bigquery import TableReference, DatasetReference, UDFResource
import datetime, warnings, time
from graphviz import Digraph

# TODO: check qu'il n'y a pas deux vues a 'cached' qui ont le meme output final
# TODO: dans un cas d'interpretation de 'factorised views' a plusieurs composantes: check consistency with repo for NEED_REPO_DEF
# TODO: dans le cas d'une vue vnameCVIT_SUFFIX: check que vname n'existe pas, ou alors que c'est une table + check
#       que c'est contenu dans le repo, et sinon warning a l'utilisateur
# TODO check que partitioned_field fait parti des champs du resultat d'un dry run si long-term memory existe
# TODO warning about too long SQL in views

STATIC_TABLES = []
BROKEN_DEP_MESS = "Broken dependencies:"

URL_BQ = "https://console.cloud.google.com/bigquery?project={project_id}&amp;p={project_id}&amp;d={dataset}&amp;t={table}&amp;page=table"


def full_id_to_pdt_id(full_id):
    pdt_id = full_id.split('.')
    return (pdt_id[0] + '.' + pdt_id[1], pdt_id[2])

class BasicVisualizer():
    bq_info_handler = None

    def __init__(self, path_to_conf_file):
        self.bq_info_handler = BQInfoHandler(path_to_conf_file=path_to_conf_file, retrieve_all_data=False)
        self.bq_info_handler.raw_details = dict()

    def visualize_dependencies(self, dataset, view, interpreter, rel_dir):
        dirn = os.getcwd() + '/' + rel_dir + '/'
        if not os.path.isdir(dirn):
            os.mkdir(dirn)
        self.bq_info_handler.get_full_dependency(dataset, view, interpreter=interpreter)
        dot = Digraph(comment=dataset + '.' + view)
        subgraphs = dict()
        cached_views_dep_todo = []
        all_nodes_here = []
        for d in bv.bq_info_handler.raw_details:
            d_name = d.split('.')[-1]
            subgraphs[d_name] = dot.subgraph(name='cluster_' + d_name)
            with subgraphs[d_name] as s:
                s.attr(label=d_name)
                s.attr(style='filled')
                s.attr(color='lightgrey')
            for t in bv.bq_info_handler.iterate_retrieved_dataset(d):
                n_id = d + '.' + t
                if not(n_id in bv.bq_info_handler.raw_details[dataset][view]['full_dependencies'] \
                    or n_id == dataset + '.' + view):
                    continue
                all_nodes_here += [(d, t, n_id)]
                node_attr = dict(href=URL_BQ.format(table=t, project_id=d.split('.')[0], dataset=d_name),
                                 target="_blank", style='filled', color='white')
                if n_id == dataset + '.' + view:
                    node_attr.update(dict(color='lightgreen'))
                elif 'cached_view_name' in bv.bq_info_handler.raw_details[d][t]:
                    node_attr.update(dict(color='lightblue'))
                    if interpreter != "Include cached views dependencies":
                        cvn = bv.bq_info_handler.get_raw_details(d, t)['cached_view_name']
                        node_attr.update(dict(href='file://' + dirn + d + '.' + cvn + '.svg'))
                        cached_views_dep_todo += [(d, cvn)]
                elif bv.bq_info_handler.raw_details[d][t]['type'] == 'TABLE':
                    node_attr.update(dict(color='red'))
                with subgraphs[d_name] as s:
                    s.node(n_id, label=t, **node_attr)
        for d, t, n_id in all_nodes_here:
            for t_dep in bv.bq_info_handler.raw_details[d][t]['first_order_dependencies']:
                dot.edge(n_id, t_dep)
        fn = dataset + '.' + view
        fullfn = dirn + fn
        fn = dot.render(fullfn, format='svg')
        print('file://' + fullfn + '.svg')
        for d, cvn in cached_views_dep_todo:
            if not(os.path.isfile(dirn+d+'.'+cvn)):
                self.visualize_dependencies(d, cvn, interpreter, rel_dir)
        return fn


class BQInfoHandler():
    bq_client = None
    bq_conductor_conf = None
    interpreted_graphs = {
        "Natural dependencies": dict(nodes=dict(), graphs=[], js_graphs=[], interpreted_id_to_js_graph_num=dict()),
        "First order dependencies": dict(nodes=dict(), graphs=[], js_graphs=[], interpreted_id_to_js_graph_num=dict()),
        "Include cached views dependencies": dict(nodes=dict(), graphs=[], js_graphs=[],
                                                  interpreted_id_to_js_graph_num=dict()),
        # "Caching interpreter": dict(nodes=dict(), graphs=[], js_graphs=[], interpreted_id_to_js_graph_num=dict()),
        # "Caching cut-off": dict(nodes=dict(), graphs=[], js_graphs=[], interpreted_id_to_js_graph_num=dict())
    }
    full_id_to_interpreted_nodes = {"Natural dependencies": dict(), "Include Cached views dependencies": dict()}
    errors_to_raise = dict()
    raw_details = None
    did_full_update = False
    lazy_load_memory = []

    def __init__(self, path_to_conf_file, retrieve_all_data=True):
        self.bq_client = BQClient(path_to_conf_file)
        if retrieve_all_data:
            self.update_data()
        self.bq_conductor_conf = self.bq_client.bq_conductor_conf

    def get_details_from_dt_id(self, dt_id):
        p, d, t = dt_id.split('.')
        return self.raw_details[p + '.' + d][t]

    def update_data(self):
        start_time = time.time()
        print("Starting to retrieve raw details for project")
        self.raw_details = self.bq_client.get_all_details()
        # TODO for all interpreters:
        # Building dependencies graphs. i.e. graphs in which table or views are connected through some
        # computations in views
        for interpreter in self.interpreted_graphs:
            temp_graphs = []
            temp_all_graphs_deps = set()
            for d in self.raw_details:
                for t in self.raw_details[d]:
                    table_full_dep = self.get_full_dependency(d, t, interpreter)
                    interpreted_id = self.get_interpreter_id(interpreter, d, t)
                    dep_nodes = [self.get_interpreter_id(interpreter, dt_id) for dt_id in table_full_dep]
                    all_nodes_here = set([interpreted_id] + dep_nodes)
                    full_id = d + '.' + t
                    # self.interpreted_graphs[interpreter]['nodes'][interpreted_id] = dict(
                    #                             first_order=self.get_view_first_order_dependencies(d, t, interpreter),
                    #                             full=table_full_dep,
                    #                             interpreted_id=interpreted_id
                    #                         )
                    self.full_id_to_interpreted_nodes[interpreter][full_id] = interpreted_id
                    if interpreter == "Natural dependencies":
                        if len(temp_all_graphs_deps.intersection(all_nodes_here)) == 0:
                            temp_graphs.append(all_nodes_here)
                        else:
                            # Then we'll add those to a graph, but we might also have to unions some graphs
                            graphs_to_be_gathered = []
                            for i, g in enumerate(temp_graphs):
                                if len(g.intersection(all_nodes_here)) > 0:
                                    graphs_to_be_gathered.append(i)
                            new_graph = all_nodes_here
                            for i in reversed(graphs_to_be_gathered):
                                new_graph = new_graph.union(temp_graphs.pop(i))
                            temp_graphs.append(new_graph)
                        temp_all_graphs_deps = temp_all_graphs_deps.union(all_nodes_here)
                    elif interpreter == "First order dependencies":
                        self.interpreted_graphs[interpreter]['interpreted_id_to_js_graph_num'][interpreted_id] = len(temp_graphs)
                        temp_graphs.append(all_nodes_here)
                        if interpreted_id in temp_all_graphs_deps:
                            for g in temp_graphs:
                                if interpreted_id in g:
                                    g.add(interpreted_id)
                        temp_all_graphs_deps.add(interpreted_id)
                    else:
                        raise NotImplementedError()
            for g in temp_graphs:
                for t in g:
                    if t in self.interpreted_graphs[interpreter]['nodes']: # if is not a broken dependency
                        self.interpreted_graphs[interpreter]['nodes'][t]['dep_graph'] = list(g)
            # making it json serializable
            self.interpreted_graphs[interpreter]['graphs'] = [list(g) for g in temp_graphs]
            # Building graphs for javascript:
            for js_graph_num, g in enumerate(self.interpreted_graphs[interpreter]['graphs']):
                tmp_nodes = []
                tmp_edges = []
                tmp_id_to_num = dict()
                i = 0
                for n in g:
                    is_broken_node = not(n in self.full_id_to_interpreted_nodes[interpreter])
                    tmp_nodes.append(
                        dict(id=self.full_id_to_interpreted_nodes[interpreter][n]
                        if not(is_broken_node) else ("%s DOES NOT EXIST!" % n),
                             # this will be displayed on graph: make it short
                             label=self.full_id_to_interpreted_nodes[interpreter][n].split('.')[-1]
                             if not(is_broken_node) else ("%s DOES NOT EXIST!" % n),
                             title=n if not(is_broken_node) else "%s DOES NOT EXIST!" % n, # popup when hovering node
                             shape='text', # TODO make shape depend on type (table, view, or chaching mecanism)
                             color='blue' if not(is_broken_node) else 'red' ))
                    tmp_id_to_num[n] = i
                    i += 1
                for i, n in enumerate(g):
                    if interpreter == "Natural dependencies":
                        self.interpreted_graphs[interpreter]['interpreted_id_to_js_graph_num'][n] = js_graph_num
                    if n in self.interpreted_graphs[interpreter]['nodes']:
                        for e in self.interpreted_graphs[interpreter]['nodes'][n]['first_order_dependencies']:
                            if e in g: # otherwise it means we don't want to display this here
                                tmp_edges.append({'to': n, 'from': e})
                self.interpreted_graphs[interpreter]['js_graphs'].append(dict(nodes=tmp_nodes, edges=tmp_edges))
        print("\t details retrieved. it took %g seconds" % (time.time() - start_time))
        # making it json serializable: we need lists and not sets as dependencies
        for interpreter in self.interpreted_graphs:
            for n in self.interpreted_graphs[interpreter]['nodes']:
                for sd in ['first_order_dependencies', 'full_dependencies']:
                    self.interpreted_graphs[interpreter]['nodes'][n][sd] = list(self.interpreted_graphs[interpreter]['nodes'][n][sd])
        self.did_full_update = True

    def get_interpreter_id(self, interpreter, *args):
        assert len(args) in [1, 2], "Wrong number of inputs"
        if len(args) == 2:
            d, t = args
        else:
            p, d, t = args[0].split('.')
            d = p + '.' + d
        if interpreter in ["Natural dependencies", "First order dependencies", "Include cached views dependencies"]:
            return d + '.' + t
        else:
            raise NotImplementedError()

    def get_full_dependency(self, dataset_id, view_id, interpreter):
        assert interpreter in ["Natural dependencies", "First order dependencies",
                               "Include cached views dependencies"], "Not yet implemented"
        if interpreter == "First order dependencies":
            return self.get_view_first_order_dependencies(dataset_id, view_id, interpreter)
        view_full_id = self.get_interpreter_id(interpreter, dataset_id, view_id)
        if view_full_id in self.interpreted_graphs[interpreter]['nodes'] \
                and 'full_dependencies' in self.interpreted_graphs[interpreter]['nodes'][view_full_id]:
            return self.interpreted_graphs[interpreter]['nodes'][view_full_id]['full_dependencies']
        next_to_be_added_dependencies = self.get_view_first_order_dependencies(dataset_id, view_id, interpreter)
        dep = set()
        while len(next_to_be_added_dependencies) > 0:
            to_be_added_dependencies = next_to_be_added_dependencies.copy()
            next_to_be_added_dependencies = set()
            for add_dep in to_be_added_dependencies:
                d_id, v_id = full_id_to_pdt_id(add_dep)
                dep.add(add_dep)
                dep_for_this_one = self.get_view_first_order_dependencies(d_id, v_id, interpreter)
                if isinstance(dep_for_this_one, basestring):
                    if 'dependencies_error' in self.interpreted_graphs[interpreter]['nodes'][view_full_id]:
                        self.interpreted_graphs[interpreter]['nodes'][view_full_id]['dependencies_error'].append(dep_for_this_one)
                    else:
                        self.interpreted_graphs[interpreter]['nodes'][view_full_id]['dependencies_error'] = [dep_for_this_one]
                else:
                    next_to_be_added_dependencies.update(dep_for_this_one)
        self.interpreted_graphs[interpreter]['nodes'][view_full_id]['full_dependencies'] = dep
        return self.interpreted_graphs[interpreter]['nodes'][view_full_id]['full_dependencies']

    def get_raw_details(self, dataset_id, view_id):
        if self.did_full_update:
            return self.raw_details[dataset_id][view_id]
        if dataset_id not in self.raw_details:
            self.raw_details[dataset_id] = dict()
        if view_id not in self.raw_details[dataset_id]:
            try:
                self.raw_details[dataset_id][view_id] = self.bq_client._client.get_table( \
                    TableReference(DatasetReference(self.bq_conductor_conf.GOOGLE_CLOUD_PROJECT,
                                                    dataset_id.split('.')[-1]), view_id)).to_api_repr()
            except:
                self.raw_details[dataset_id][view_id] = None
        return self.raw_details[dataset_id][view_id]

    def iterate_retrieved_dataset(self, dataset):
        for t in self.raw_details[dataset]:
            if self.raw_details[dataset][t] is not None:
                yield t

    # Note 1: in case of a table we will return (set(), '# This is just a table')
    # except for "Include cached views dependencies" interpreter: in which we will look through cached view dependencies
    def get_view_first_order_dependencies(self, dataset_id, view_id, interpreter):
        assert interpreter in ["Natural dependencies", "First order dependencies",
                               "Include cached views dependencies"], "Not yet implemented"
        view_full_id = self.get_interpreter_id(interpreter, dataset_id, view_id)
        if view_full_id in self.interpreted_graphs[interpreter]['nodes'] \
                and 'first_order_dependencies' in self.interpreted_graphs[interpreter]['nodes'][view_full_id]:
            return self.interpreted_graphs[interpreter]['nodes'][view_full_id]['first_order_dependencies']
            # return "%s '%s.%s' does not exist" % (BROKEN_DEP_MESS, dataset_id, view_id)
        view_full_metadata = self.get_raw_details(dataset_id, view_id)
        if interpreter == "Include cached views dependencies" and view_full_metadata["type"] != 'VIEW':
            view_full_metadata = self.get_raw_details(dataset_id, view_id + self.bq_conductor_conf.CVIT_SUFFIX)
            if view_full_metadata is None:
                view_full_metadata = self.get_raw_details(dataset_id, view_id)
            else:
                view_full_metadata['cached_view_name'] = view_id + self.bq_conductor_conf.CVIT_SUFFIX
            raise NotImplementedError() # We'd rather say this table depends on the view and explore the views dependencies
        elif view_full_metadata["type"] != 'VIEW':
            if self.get_raw_details(dataset_id, view_id + self.bq_conductor_conf.CVIT_SUFFIX) is not None:
                view_full_metadata['cached_view_name'] = view_id + self.bq_conductor_conf.CVIT_SUFFIX
        self.interpreted_graphs[interpreter]['nodes'][view_full_id] = view_full_metadata
        if view_full_metadata["type"] != 'VIEW':  # Note 1
            self.interpreted_graphs[interpreter]['nodes'][view_full_id]['first_order_dependencies'] = set()
            if view_full_id not in STATIC_TABLES \
                    and datetime.date.fromtimestamp(
                float(view_full_metadata['lastModifiedTime']) / 1000.0) < \
                    datetime.date.today() - datetime.timedelta(days=2):
                # checking that the tables we rely on do not seem to be dead
                # (no updates, for instance because of a removed view to be cached)
                err_mess = "ERROR: %s.%s seem to be a dead table (no modification since %s)" \
                           % (dataset_id, view_id,
                              datetime.datetime.fromtimestamp(float(view_full_metadata['lastModifiedTime'])
                                                              / 1000.0).strftime('%Y-%m-%d %H:%M:%S'))
                warnings.warn(err_mess)
                self.errors_to_raise[view_full_id] = Exception(err_mess)
            return self.interpreted_graphs[interpreter]['nodes'][view_full_id]['first_order_dependencies']
        sql_query = view_full_metadata['view']['query']
        # TODO: test that sql query does not contain some dataset_id.table_id without ` surrounding it
        # TODO: wildcards queries https://cloud.google.com/bigquery/docs/querying-wildcard-tables
        # we will need info from project in this case... I suppose the _TABLE_SUFFIX mecanism will force us to use
        # referenced tables: but before trying this, we'll need to get sure that queries cannot be used with wildcards
        # (as said in limitations at the bottom of doc)
        assert '_TABLE_SUFFIX' not in sql_query, "Wildcard queries not implemented"
        dep = self.bq_client.bq_conductor_conf.get_sql_dependencies(sql_query)
        for i, d in enumerate(dep):
            assert '*' not in d, "Wildcard queries not implemented"
            dep_count_dot = d.count('.')
            assert dep_count_dot in [1, 2], "Dont know what to do with such reference: %s (sql=%s)" % (dep, sql_query)
            if dep_count_dot == 1:
                dep[i] = view_full_metadata["tableReference"]["projectId"] + '.' + d
        if dep is not None:
            dep = set([t.replace(' ', '') for t in dep])
        else:
            dep = set()
        self.interpreted_graphs[interpreter]['nodes'][view_full_id]['first_order_dependencies'] = dep
        return self.interpreted_graphs[interpreter]['nodes'][view_full_id]['first_order_dependencies']


if __name__ == '__main__':
    import os, sys, shutil
    bv = BasicVisualizer(os.getenv("BQ_CONDUCTOR_CONF"))
    dirn = './bqc_dot_tmp'
    if os.path.isdir(dirn):
        shutil.rmtree(dirn)
    fn = bv.visualize_dependencies('.'.join(sys.argv[1].split('.')[0:2]), sys.argv[1].split('.')[2],
                                    "Natural dependencies", dirn)# "Include cached views dependencies") #
    # import webbrowser, os
    # webbrowser.open('file://' + os.path.realpath(filename))
