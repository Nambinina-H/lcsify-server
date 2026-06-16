from app.clients import client_repository


def list_clients():
    return client_repository.list_all()


def create_client(name):
    return client_repository.create(name)


def rename_client(client_id, name):
    return client_repository.rename(client_id, name)


def delete_client(client_id):
    return client_repository.delete(client_id)