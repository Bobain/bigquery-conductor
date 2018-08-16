import os
import time

from bq_conductor.bq_manager.bq_client import BQClient

if __name__ == '__main__':

    bqclient = BQClient(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'bq_conductor_conf.py'))

    d ='aaaaa_test_bq_conductor'
    fake_view_name = "test_view_bq_conductor"
    fake_table_name = "test_table_bq_conductor"

    print("Running basic tests")

    try:
        # creating a dataset
        assert not(d in bqclient.get_dataset_ids()), "dataset: %s already here interrupting tests" % d
        bqclient.create_dataset(d)
        assert (d in bqclient.get_dataset_ids()), "Could not create dataset"

        # creating a view in this dataset
        assert len(bqclient.get_tables_ids(d)) == 0, "WTF a newly created dataset is not empty?"
        bqclient.create_view(d, fake_view_name, 'SELECT CURRENT_TIMESTAMP() as date_test_created_field',
                             use_legacy_sql=False)
        tables_in_dataset = bqclient.get_tables_ids(d)
        assert (len(tables_in_dataset) == 1) and (fake_view_name == tables_in_dataset[0]), "Could not create a view"

        # using the SQL inside this view to create a new table for the result of the request
        sql = bqclient.get_view_sql(d, fake_view_name)['sql']
        all_details_about_view = bqclient.get_table(d, fake_view_name)
        bqclient.create_table_from_query(d, fake_table_name, sql, async=False)
        tables_in_dataset = bqclient.get_tables_ids(d)
        assert (len(tables_in_dataset) == 2) and (fake_view_name in tables_in_dataset) \
               and (fake_table_name in tables_in_dataset), \
            "Could not create a table from a query"
        assert (len(list(bqclient.query('select * from %s.%s' % (d, fake_table_name)))) == 1), \
            "Something looks wrong when creating a table from sql query"

        bqclient.insert_query_into_table(d, fake_table_name, sql, async=False)
        assert (len(tables_in_dataset) == 2) and (fake_view_name in tables_in_dataset) \
               and (fake_table_name in tables_in_dataset), \
            "Problem with inserting data from query into table"

        assert (len(list(bqclient.query('select * from %s.%s' % (d, fake_table_name)))) == 2), \
            "Could not insert data into a table"

        qdr = bqclient._query_sync('(SELECT * from %s.%s) UNION ALL (SELECT * from %s.%s)'
                                              % (d, fake_table_name, d, fake_view_name), use_legacy_sql=False)
    except:
        # cleaning the mess
        try:
            bqclient.delete_table(d, fake_table_name)
        except:
            pass
        try:
            bqclient.delete_table(d, fake_view_name)
        except:
            pass
        try:
            bqclient.delete_dataset(d)
        except:
            pass

    test_dependencies = bqclient.bq_conductor_conf.get_sql_dependencies(
        '(SELECT * from `project.dataset1.dep1`) UNION ALL (SELECT * FROM `project.dataset1.dep2`)')

    assert set(test_dependencies) == set(['project.dataset1.dep1', 'project.dataset1.dep2']), \
        "There is a problem to identify dependencies in a SQL query, even for a very basic query"

    print("How much time does it take to retrieve all details about objects in your Bigquery project?")
    t = time.time()
    all_details = bqclient.get_all_details()
    print("\tit takes: %g seconds" % (time.time()-t))

    print("\tBasic tests ok.")


