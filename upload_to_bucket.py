from google.cloud import storage

def upload_to_gcs(bucket_name, source_file_path, destination_blob_name):

    try:
        # Initialiser le client Google Cloud Storage
        storage_client = storage.Client()

        # Récupérer le bucket
        bucket = storage_client.bucket(bucket_name)

        # Créer un blob dans le bucket
        blob = bucket.blob(destination_blob_name)

        # Téléverser le fichier local
        blob.upload_from_filename(source_file_path)

        print(
            f"Fichier {source_file_path} téléversé avec succès dans le bucket {bucket_name} sous le nom {destination_blob_name}."
        )
    except Exception as e:
        print(f"Erreur lors du téléversement : {e}")


if __name__ == "__main__":
    BUCKET_NAME = "blind_storage_bucket"
    SOURCE_FILE_PATH = "/home/user/blindStorage/Hello.txt"
    DESTINATION_BLOB_NAME = "test/hello.txt"

    upload_to_gcs(BUCKET_NAME, SOURCE_FILE_PATH, DESTINATION_BLOB_NAME)
