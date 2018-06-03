from bq_conductor.bq_manager.bq_client import BQClient

# TODO: check qu'il n'y a pas deux vues a 'cached' qui ont le meme output final
# TODO: dans un cas d'interpretation de 'factorised views' a plusieurs composantes: check consistency with repo for NEED_REPO_DEF
# TODO: dans le cas d'une vue vnameCVIT_SUFFIX: check que vname n'existe pas, ou alors que c'est une table + check
#       que c'est contenu dans le repo, et sinon warning a l'utilisateur
# TODO check que partitioned_field fait parti des champs du resultat d'un dry run si long-term memory existe

class BQInfoHandler():
    bq_client = None
    bq_conductor_conf = None

    def __init__(self, path_to_conf_file):
        self.bq_client = BQClient(path_to_conf_file)
        self.update_data()
        self.bq_conductor_conf = self.bq_client.bq_conductor_conf

    def update_data(self):
        print("Starting to retrieve raw details for project "
              "(list tables and views: in case of view dry run the contained SQL)")
        self.raw_details = self.bq_client.get_all_details()
        print("\t details retrieved")
