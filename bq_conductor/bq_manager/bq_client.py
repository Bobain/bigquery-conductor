from google.cloud import bigquery
from google.oauth2 import service_account
import imp, pip, json, time

# < utils functions for client
def job_result_raise_if_error(job, add_message):
    """ raising an error if a BQ job ended on error """
    assert job.state == 'DONE' and (job.errors is None or len(job.errors) == 0), \
        "Query failed with error: %s %" % (job.error_result, add_message)


def get_job_config(**kwargs):
    """ setting a bigquery.QueryJobConfig() attributes according to the values in dictionary """
    job_config = bigquery.QueryJobConfig()
    for k, v in kwargs.iteritems():
        assert hasattr(job_config, k), "Unknown BigQuery job configuration parameter: %s" % k
        setattr(job_config, k, v)
    return job_config
# >

# ref : https://google-cloud-python.readthedocs.io/en/latest/bigquery/usage.html

class BQClient():
    _client = None
    bq_conductor_conf = None
    project_id = None

    def __init__(self, path_to_conf_file):
        self.bq_conductor_conf = imp.load_source('bq_client_conf', path_to_conf_file)
        credentials = service_account.Credentials.from_service_account_file(
            self.bq_conductor_conf.GOOGLE_APPLICATION_CREDENTIALS)
        # scoped_credentials = credentials.with_scopes(
        #     ['https://www.googleapis.com/auth/cloud-platform'])
        self._client = bigquery.Client(project=self.bq_conductor_conf.GOOGLE_CLOUD_PROJECT,
                                 credentials=credentials)
        self.DEFAULTS = self.bq_conductor_conf.DEFAULTS
        self.project_id = self.bq_conductor_conf.GOOGLE_CLOUD_PROJECT

    def create_dataset(self, dataset_id, location=None):
        """ creating a dataset """
        dataset = bigquery.Dataset(self._client.dataset(dataset_id))
        dataset.location = self.DEFAULTS['location'] if location is None else location
        return self._client.create_dataset(dataset)

    def delete_dataset(self, dataset_id, **kwargs):
        """ deleting a dataset """
        return self._client.delete_dataset(bigquery.Dataset(self._client.dataset(dataset_id)), **kwargs)

    def get_dataset_ids(self):
        """ getting the list of datasets in the project """
        return [d.dataset_id for d in self._client.list_datasets(include_all=False)]

    def get_tables_ids(self, dataset_id):
        """ getting the list of tables (and views) in a specific dataset """
        return [d.table_id for d in self._client.list_tables(dataset=self._client.dataset(dataset_id))]

    def get_all_details(self):
        start_time = time.time()
        print('Starting to retrieve all details for project: this may be long...')
        details = dict()
        for d in self._client.list_datasets(include_all=False):
            d_full_id = self.bq_conductor_conf.GOOGLE_CLOUD_PROJECT + '.' + d.dataset_id
            details[d_full_id] = dict()
            for t in self._client.list_tables(dataset=self._client.dataset(d.dataset_id)):
                # TODO: do not get these details now, but only when needed? Fo now just list tables
                # the next call turns 35 seconds (already too slow for just the list of tables) into more than 6 minutes
                details[d_full_id][t.table_id] = self._client.get_table(t.reference).to_api_repr()
        print('\tFinished to retrieve all details for project: it took %g seconds' % (time.time()-start_time))
        return details

    def list_all_objects(self):
        pass

    def create_view(self, dataset_id, view_name, viewSQL, use_legacy_sql=None):
        """ creating a view """
        dataset = self._client.dataset(dataset_id)
        table = bigquery.Table(dataset.table(view_name))
        table.view_query = viewSQL
        table.view_use_legacy_sql = self.DEFAULTS['use_legacy_sql'] if use_legacy_sql is None else use_legacy_sql
        return self._client.create_table(table)

    def delete_view(self, dataset_id, table_id):
        """ deleting a view """
        self.delete_table(dataset_id, table_id)

    def create_table_from_query(self, dataset_id, table_id, query_sql, async=True):
        """ creating a table with the output of a query """
        return self._query_into_table(dataset_id, table_id, query_sql, bigquery.WriteDisposition.WRITE_TRUNCATE,
                                      async=async)

    def get_referenced_tables_in_sql(self, sql):
        """ TODO: get tables (and views?) referenced in a view """
        job_config = bigquery.QueryJobConfig()
        job_config.query_parameters = True
        job = self._client.query(sql, location=self.DEFAULTS['location'], job_config=job_config)
        job_result_raise_if_error(job, "(query was: %s)" % sql)
        return job.referenced_tables

    def insert_query_into_table(self, dataset_id, table_id, query_sql, async=True):
        """ insert (append) the output of a query into a table """
        return self._query_into_table(dataset_id, table_id, query_sql, bigquery.WriteDisposition.WRITE_APPEND,
                               async=async)

    def _query_into_table(self, dataset_id, table_id, query_sql, write_disposition, async=True):
        job_config = bigquery.QueryJobConfig()
        table_ref = self._client.dataset(dataset_id).table(table_id)
        job_config.destination = table_ref
        job_config.write_disposition = write_disposition
        if async:
            return self._client.query(query_sql, job_config=job_config)
        else:
            job = self._client.query(query_sql, job_config=job_config)
            job.result()
            job_result_raise_if_error(job, "(query was: %s)" % query_sql)

    def _query_sync(self, query_sql, **kwargs):
        """ execute an sql query """
        job = self._client.query(query_sql, job_config=get_job_config(**kwargs))
        rslt = job.result()
        job_result_raise_if_error(job, "(query was: %s)" % query_sql)
        return job, rslt

    def view_dryrun(self, dataset_id, view_id):
        return self._query_dryrun(self.get_view_sql(dataset_id, view_id))

    def _query_dryrun(self, query, **kwargs):
        """
        :param query: should be a dictionary with keys: 'sql' and 'use_legacy_sql'
        :param kwargs:  additional configuration
        :return:
        """
        job_config = bigquery.QueryJobConfig()
        job_config.dry_run = True
        job_config.use_query_cache = False
        job_config.use_legacy_sql = query['use_legacy_sql']
        for k, v in kwargs.iteritems():
            assert hasattr(job_config, k)
            setattr(job_config, k, v)
        query_job = self._client.query(query['sql'],
                                       location=self.bq_conductor_conf.DEFAULTS['location'], job_config=job_config)

        # A dry run query completes immediately.
        assert query_job.state == 'DONE'
        assert query_job.dry_run

        return query_job

    def query_to_dataframe(self, query_sql):
        """ synchronously execute some sql and return result as a pandas.dataframe"""
        assert 'pandas' in [p.key for p in pip.get_installed_distributions()], \
            "package pandas need to be installed to use bq_client.BQClient.query_to_dataframe"
        job, rslt = self._query_sync(query_sql)
        return job.to_dataframe()

    def query(self, query_sql):
        """ synchronously execute some sql and return result"""
        job, rslt = self._query_sync(query_sql)
        return rslt

    def delete_table(self, dataset_id, table_id):
        """ deletes a table (works for views)"""
        table_ref = self._client.dataset(dataset_id).table(table_id)
        return self._client.delete_table(table_ref)

    def get_table(self, dataset_id, table_id):
        """ returns full information for a table (or view)"""
        dataset_ref = self._client.dataset(dataset_id)
        table_ref = dataset_ref.table(table_id)
        return self._client.get_table(table_ref)

    def get_view_sql(self, dataset_id, view_id):
        """ retrieves the sql that defines a view as a dictionary:
            'sql' key will contain sql of the view
            'use_legacy_sql' key will let you know if that's legacy sql or not
        """
        table = self.get_table(dataset_id, view_id)
        assert hasattr(table, 'view_query'), "Looks like %s is a table and not a view"
        return dict(sql=table.view_query, use_legacy_sql=table.view_use_legacy_sql)


if __name__ == "__main__":
    import os
    bqclient = BQClient(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', 'tests', 'examples',
                                     'basic_tests', 'bq_conductor_conf.py'))
