# -*- coding: utf-8 -*-
from flask import Flask
from flask import render_template
from data2html import get_html_for_search_menu, get_interpreter_options
import json

app = Flask(__name__)

data = dict()

@app.route("/")
def index():
    # return render_template("tests.html")
    return render_template("index.html", network_data=
    " var data = graphToDisplay;"
    # """
    #     ///////////////////////////////// graph DATA BUILDING
    #         var nodes = [];
    #         var edges = [];
    #         // randomly create some nodes and edges
    #         for (var i = 0; i < 18; i++) {
    #         nodes.push({id: i,
    #                     label: 'table_not_so_long' + String(i),
    #                     title: 'popup' + String(i),
    #                     shape: 'text'}); // dataset_name_ultra_long_to_read\n
    #         }
    #         nodes.push({id: 18, label: 'table_nsl_but_bigger_18', shape: 'box'}); // ellipse, circle, database, box, text
    #         edges.push({from: 0, to: 1});
    #         edges.push({from: 0, to: 6});
    #         edges.push({from: 0, to: 13});
    #         edges.push({from: 0, to: 11});
    #         edges.push({from: 1, to: 2});
    #         edges.push({from: 2, to: 3});
    #         edges.push({from: 2, to: 4});
    #         edges.push({from: 3, to: 5});
    #         edges.push({from: 1, to: 10});
    #         edges.push({from: 1, to: 7});
    #         edges.push({from: 2, to: 8});
    #         edges.push({from: 2, to: 9});
    #         edges.push({from: 3, to: 14});
    #         edges.push({from: 1, to: 12});
    #         edges.push({from: 16, to: 12});
    #         edges.push({from: 15, to: 12});
    #         edges.push({from: 18, to: 12});
    #         edges.push({from: 17, to: 12});
    #
    #         // create a network
    #         var container = document.getElementById('mynetwork');
    #         var data = {
    #         nodes: nodes,
    #         edges: edges
    #         };
    #     ///////////////////////////////// graph DATA BUILDING ends
    # """
                           ,
   search_menu=get_html_for_search_menu(data['project_details'], lambda x: x.replace(data['project_conf'].GOOGLE_CLOUD_PROJECT + '.', '')),
   project_details="var projectDetails = " + json.dumps(data['project_details']) + ";",
   graphs_data="var graphsData = " + json.dumps(data['graphs']) + ";",
   fid_to_interpreted_id="var fullIdToInterpretedId = " + json.dumps(data['full_id_to_interpreted_nodes']) + ";",
   interpreters_list=get_interpreter_options(data['interpreters_list'])
   )

if __name__ == "__main__":
    import os
    from bq_conductor.bq_manager.bq_info_handler import BQInfoHandler
    bq_info_handler = BQInfoHandler(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..',
                                                 'tests', 'examples', 'basic_tests', 'bq_conductor_conf.py'))
    data['project_details'] = bq_info_handler.raw_details
    data['graphs'] = bq_info_handler.interpreted_graphs
    data['interpreters_list'] = bq_info_handler.interpreted_graphs.keys()
    data['project_conf'] = bq_info_handler.bq_conductor_conf
    data['full_id_to_interpreted_nodes'] = bq_info_handler.full_id_to_interpreted_nodes
    app.run(host='0.0.0.0', port=5000, debug=True)