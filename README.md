# bigquery-conductor


git clone https://github.com/Bobain/bigquery-conductor.git

# copy you bigquery json credentials file into the directory of this package

cp ./data-maker/UluleDatabase-850a3f482837.json ./bigquery-conductor/UluleDatabase-850a3f482837.json

# create a virtualenv

virtualenv .env

. .env/bin/activate

cd bigquery-conductor

pip install -r requirements.txt

python setup.py develop

cd ..

# produce first visualization

python ./bigquery-conductor/bq_conductor/bq_manager/bq_info_handler.py "ulule-database.a_ulule_partner_visibility.monthly_brands_metrics_to_be_cached"

# open the first file that was printed in console in a webbrowser