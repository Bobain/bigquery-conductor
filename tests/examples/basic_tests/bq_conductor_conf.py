import os
import re

# < Google cloud project configuration
GOOGLE_CLOUD_PROJECT = 'ulule-database' # id for project (letters, not digits)
os.environ['GOOGLE_CLOUD_PROJECT'] = GOOGLE_CLOUD_PROJECT # setting it as env for big query client
GOOGLE_APPLICATION_CREDENTIALS = '/home/tonigor/git_repos/bigquery-conductor/UluleDatabase-850a3f482837.json' # path to p12 or json file for credentials
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = GOOGLE_APPLICATION_CREDENTIALS # setting it as env for big query client

DEFAULTS = dict(
    location='EU',
    use_legacy_sql=False # changing to true most probably wont work
)
# >

# < * Configuration for 'cache views/computations in tables' mecanism
# < Suffixes for naming views whose output should be cached in tables
CVIT_SUFFIX = "_to_be_cached" # the whole output of the view should be stored in a table daily
# each day we should append an output table with the newly available inputs, this output table will be partitioned,
# with partitioning field named: PARTITIONING_FIELD_NAME
BICVIT_SUFFIX = "_to_be_partition_cached"
FICVIT_SUFFIX = "_to_be_long_and_mid_term_cached"
OTF_SUFFIX = "_and_otf"
# make a custom caching component using the three basic ones:
# 1) long-term memory table: append some new computation outputs to a table (optionally delete some of the oldest ones)
# 2) mid-term memory table:  destroyed and fully recomputed once a day. You may need this one for data that:
#       - either are still subject to changes with future data coming
#       - or are still subject to some fixes (they are in a sort of quarantine window:
#           waiting a certain number of days to be labelled as 'good data')
# 3) short-term output of computations: this final output is a view that unions data from cached tables
#       (component 1 and 2) with the output of the very same SQL applied to still unprocessed (still not
#       cached by component 2 or 3) data
#
# if any view in BigQuery has a name containing one of the above suffixes,
# this package will interpret it as a scheduling for caching the output of the view with the following rules :
# if one and only one of the suffixes : CVIT_SUFFIX, BICVIT_SUFFIX, or FICVIT_SUFFIX is found in the name of the view,
# then it means it asks for caching its outputs with components:
#   CVIT_SUFFIX -> mid-term (cache the whole output daily + if parametrized: do that only on a date based window)
#   BICVIT_SUFFIX -> long-term (incrementally cache output in partitionned table
#                                   + if parametrized: do that only on a date based window)
#   FICVIT_SUFFIX -> long-term + mid-term
# On top of which can be added the final suffix OTF_SUFFIX which will add the 'short-term component'.
# In such a case, the final output will still be a view, but it aggregates pre-computed data and on the fly computations
#
# The name of the final output  is either a table or a view (when there is more than one component).
# Its name will be the name of the scheduling view without the above suffixes
#   (one mandatory + optionally 'short-term' one)
# But there might be intermediary tables with the following suffixes:
MIDTERM_OTF_SUFFIX = "_cached_midterm" # for the cached part of a mid-term + short-term caching process
LONG_TERM_OTF_SUFFIX = "_cached_longterm" # for the cached part of long-term + short-term process
# Important notice for computation scheduling/view naming when using the current package:
#   The potential final view (in case of more than one component) will be reinstalled daily,
#   all the configurations of this view should be done with a configuration in a 'factorized views repository',
#   as any change made outside of this repository (a directory of configurations of computations scheduling)
#   will be overridden daily before caching outputs.
# For instance, do not create a view named vnameCVIT_SUFFIX and a view named vname: the last one will be
#   overridden daily when using this package to cache computations
# When creating a view named vname{{main_suffix}}[{{OTF_SUFFIX}}] the final output will be named vname
# FULL list of secondary outputs (tables) in relevant cases:
# if vname + CVIT_SUFFIX + OTF_SUFFIX
#           -> vname + MIDTERM_OTF_SUFFIX
# if vname + BVIT_SUFFIX + OTF_SUFFIX
#           -> vname + LONG_TERM_OTF_SUFFIX
# if vname + FICVIT_SUFFIX + OTF_SUFFIX
#           -> vname + MIDTERM_OTF_SUFFIX and vname + LONG_TERM_OTF_SUFFIX
# Anyway in all of this cases you need a repository that contains the configuration to define the separation
# between components : might either be different tables, or SQL based date condition (or both), so you should know
# what is meant here. if not, go to TODO: link to full doc about 'factorized views repository'
#
SUFFIX_FULL_LIST = [CVIT_SUFFIX, BICVIT_SUFFIX, FICVIT_SUFFIX, OTF_SUFFIX, MIDTERM_OTF_SUFFIX, LONG_TERM_OTF_SUFFIX]
assert len(set(SUFFIX_FULL_LIST)) == len(SUFFIX_FULL_LIST), "Suffixes should be unique"
for s in SUFFIX_FULL_LIST:
    for s2 in SUFFIX_FULL_LIST:
        if s == s2:
            continue
        assert not(s in s2), "Problem with suffixes, '%s' is part of '%s'" % (s, s2)
# we will check that definition in 'factorized views repository' when view name contains one of those:
# the first ones are required because it indicates several components, therefore we need to know how are data separated
# the last two ones BICVIT_SUFFIX, FICVIT_SUFFIX are required because when need a template query in order to be able
# to inject partitioning condition into its SQL
NEED_REPO_DEF = [OTF_SUFFIX, MIDTERM_OTF_SUFFIX, LONG_TERM_OTF_SUFFIX, BICVIT_SUFFIX, FICVIT_SUFFIX]
# Finally, the only caching process that does not require to define it inside a 'factorized views repository' is when
# you name a view as vnameCVIT_SUFFIX : it will consider that vanme has to be a table in the same repository, and will
# daily erase its content to replace it with the output of vnameCVIT_SUFFIX
# >
# name of the field that will be used as partitioning variable for output tables of views
# that has to be partitioned tables
PARTITIONING_FIELD_NAME = "date" # you may want to stick with default naming _PARTITIONTIME: change it here.
# > *


# Bigquery dataset used to store statistics about computations scheduled with this package
THIS_PACKAGE_SYSTEM_DATASET = "bq_conductor_stats" # will be used to store some statistics about computations launched

# May be used to retrieve additional informations about all queries run in bigquery in order to see bottlenecks,
# expensive queries, etc.
# You need to set it up on your own, using: https://cloud.google.com/bigquery/audit-logs and when following these steps:
#   DO NOT filter for queries exceeding 5GB as asked with:
#       "protoPayload.serviceData.jobCompletedEvent.job.jobStatistics.totalBilledBytes > 5000000000"
#   instead: no condition so we have all stats from all queries and jobs
BIGQUERY_FULL_EXPORT_DATASET = "a_bigquery_audit_logs"

# path to 'repository': a directory in which you store bigquery views, tests to made on tables and views,
#   scheduled computations configuration, etc
PATH_TO_REPO = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'bq-conductor-test-repo')

# regular expression used to analyse the SQL of a query and get dependent tables or views
# needed because unfortunately the dry run of a query does not provide dependencies on views:
# we have to guess it from the SQL
REGEXP_FOR_SQL_DEPENDENCIES = re.compile("`([^`]*)`")