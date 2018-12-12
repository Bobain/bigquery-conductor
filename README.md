# bigquery-conductor


git clone https://github.com/Bobain/bigquery-conductor.git

# copy you bigquery json credentials file into the directory of this package

cp ../data-maker/UluleDatabase-850a3f482837.json ./bigquery-conductor/UluleDatabase-850a3f482837.json

# create a virtualenv

virtualenv .env
. .env/bin/activate
cd bigquery-conductor
pip install -r requirements.txt
python setup.py develop

