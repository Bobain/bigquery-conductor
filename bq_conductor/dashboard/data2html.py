import time
DEBUG = False


def get_interpreter_options(interpreter_list):
    return "\n".join(['<option value="%s" %s>%s</option>'
                      % (interpreter, 'selected="true"' if i == 0 else '', interpreter)
                      for i, interpreter in enumerate(interpreter_list)])


def get_html_for_search_menu(project_details, text_formatter):
    print("Creating search bar data")
    start_time = time.time()
    if DEBUG:
        return """
        <div class="selectorSideBarFirstList">
          <div class="selectorSideBarFirstListElmnt" onclick="panelControlDisplay(this)">Coffee
            <div class="selectorSideBar2ndList">
                <div class="selectorSideBar2ndListElmnt" fullId="Ristretto" onclick="drawGraphContaining(this)">Ristretto</div>
                <div class="selectorSideBar2ndListElmnt" fullId="Expresso" onclick="drawGraphContaining(this)">Expresso</div>
            </div>
          </div>
          <div class="selectorSideBarFirstListElmnt" onclick="panelControlDisplay(this)">Tea
            <div class="selectorSideBar2ndList">
                <div class="selectorSideBar2ndListElmnt" fullId="Black tea" onclick="drawGraphContaining(this)">Black tea</div>
                <div class="selectorSideBar2ndListElmnt" fullId="Green Tea" onclick="drawGraphContaining(this)">Green tea</div>
            </div>
          </div>
          <div class="selectorSideBarFirstListElmnt" onclick="panelControlDisplay(this)">Milk
              <div class="selectorSideBar2ndList">
                <div class="selectorSideBar2ndListElmnt" fullId="Cow" onclick="drawGraphContaining(this)">Cow</div>
                <div class="selectorSideBar2ndListElmnt" fullId="Soy" onclick="drawGraphContaining(this)">Soy</div>
            </div>
          </div>
        </div>
        """
    html = """<div class="selectorSideBarFirstList">
    """
    for dataset_id, tables_dict in sorted(project_details.iteritems(), key=lambda x: x[0].lower()):
        if len(tables_dict) > 0:
            html += """<div class="selectorSideBarFirstListElmnt" onclick="panelControlDisplay(this)">%s
                <div class="selectorSideBar2ndList">
                """ % text_formatter(dataset_id)
            for table_id, table in sorted(tables_dict.iteritems()):
                html += """<div class="selectorSideBar2ndListElmnt" fullId="%s" onclick="drawGraphContaining(this)">%s</div>
                """ % (dataset_id + '.' + table_id, table_id)
            html += """
                    </div>
                </div>
            """
    html += '</div>'
    print("\tCreated search bar data. It took: %g seconds" % (time.time()-start_time))
    return html