# -*- coding: utf-8 -*-
from flask import Flask
from flask import render_template

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html", network_data="""
        ///////////////////////////////// graph DATA BUILDING
            var nodes = [];
            var edges = [];
            // randomly create some nodes and edges
            for (var i = 0; i < 18; i++) {
            nodes.push({id: i,
                        label: 'table_not_so_long' + String(i),
                        title: 'popup' + String(i),
                        shape: 'text'}); // dataset_name_ultra_long_to_read\n
            }
            nodes.push({id: 18, label: 'table_nsl_but_bigger_18', shape: 'box'}); // ellipse, circle, database, box, text
            edges.push({from: 0, to: 1});
            edges.push({from: 0, to: 6});
            edges.push({from: 0, to: 13});
            edges.push({from: 0, to: 11});
            edges.push({from: 1, to: 2});
            edges.push({from: 2, to: 3});
            edges.push({from: 2, to: 4});
            edges.push({from: 3, to: 5});
            edges.push({from: 1, to: 10});
            edges.push({from: 1, to: 7});
            edges.push({from: 2, to: 8});
            edges.push({from: 2, to: 9});
            edges.push({from: 3, to: 14});
            edges.push({from: 1, to: 12});
            edges.push({from: 16, to: 12});
            edges.push({from: 15, to: 12});
            edges.push({from: 18, to: 12});
            edges.push({from: 17, to: 12});

            // create a network
            var container = document.getElementById('mynetwork');
            var data = {
            nodes: nodes,
            edges: edges
            };
        ///////////////////////////////// graph DATA BUILDING ends
    """)

if __name__ == "__main__":
    app.run(host='0.0.0.0',port=5000,debug=True)